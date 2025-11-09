import datetime as dt

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func

from app.filters.admin import AdminFilter
from app.logger import logger
from app.db.session import SessionLocal
from app.db.models import (
    User,
    Product,
    ProductStatus,
    WithdrawalRequest,
    WithdrawalStatus,
)
from app.keyboards.admin import admin_menu, edit_product_keyboard
from app.keyboards.common import main_menu
from app.keyboards.inline import moderation_keyboard, withdrawals_keyboard
from app.states.edit_card import EditCardState


router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.message(F.text == "Админ меню")
async def admin_menu_entry(message: Message):
    await message.answer("Админ меню:", reply_markup=admin_menu())


@router.message(F.text == "Назад")
async def admin_back(message: Message):
    async with SessionLocal() as session:
        q = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = q.scalar_one_or_none()
    is_admin = bool(user and user.is_admin)
    await message.answer("Главное меню", reply_markup=main_menu(is_admin=is_admin))


async def get_first_pending_product(session):
    q = await session.execute(
        select(Product)
        .where(Product.status == ProductStatus.PENDING)
        .order_by(Product.id.asc())
    )
    return q.scalars().first()


async def get_next_pending_product(session, current_id: int, direction: str):
    if direction == "next":
        stmt = (
            select(Product)
            .where(Product.status == ProductStatus.PENDING, Product.id > current_id)
            .order_by(Product.id.asc())
        )
    else:
        stmt = (
            select(Product)
            .where(Product.status == ProductStatus.PENDING, Product.id < current_id)
            .order_by(Product.id.desc())
        )
    q = await session.execute(stmt)
    return q.scalars().first()


async def send_moderation_product(msg_or_cb, product: Product):
    text = (
        f"ID: {product.id}\n"
        f"Автор: {product.user_id}\n\n"
        f"{product.title}\n"
        f"Цена: {product.price/100:.2f} ₽\n\n"
        f"{product.description}"
    )
    kb = moderation_keyboard(product.id)
    if product.photo_file_id:
        await msg_or_cb.answer_photo(product.photo_file_id, caption=text, reply_markup=kb)
    else:
        await msg_or_cb.answer(text, reply_markup=kb)


@router.message(F.text == "Модерация")
async def moderation_start(message: Message):
    async with SessionLocal() as session:
        product = await get_first_pending_product(session)
    if not product:
        await message.answer("Нет карточек на модерации.")
        return
    await send_moderation_product(message, product)


@router.callback_query(F.data.startswith("mod_prev:") | F.data.startswith("mod_next:"))
async def moderation_switch(callback: CallbackQuery):
    action, product_id_str = callback.data.split(":")
    direction = "next" if action == "mod_next" else "prev"
    current_id = int(product_id_str)
    async with SessionLocal() as session:
        product = await get_next_pending_product(session, current_id, direction)
    if not product:
        await callback.answer("Больше карточек нет.")
        return
    await callback.message.delete()
    await send_moderation_product(callback.message, product)


@router.callback_query(F.data.startswith("mod_approve:"))
async def moderation_approve(callback: CallbackQuery):
    product_id = int(callback.data.split(":")[1])
    async with SessionLocal() as session:
        q = await session.execute(select(Product).where(Product.id == product_id))
        product = q.scalar_one_or_none()
        if not product:
            await callback.answer("Карточка не найдена.")
            return
        product.status = ProductStatus.APPROVED
        await session.commit()
        logger.info("Карточка %s одобрена", product.id)
    await callback.answer("Одобрено.")
    await callback.message.delete()


@router.callback_query(F.data.startswith("mod_reject:"))
async def moderation_reject(callback: CallbackQuery):
    product_id = int(callback.data.split(":")[1])
    async with SessionLocal() as session:
        q = await session.execute(select(Product).where(Product.id == product_id))
        product = q.scalar_one_or_none()
        if not product:
            await callback.answer("Карточка не найдена.")
            return
        product.status = ProductStatus.REJECTED
        await session.commit()
        logger.info("Карточка %s отклонена", product.id)
    await callback.answer("Отклонено.")
    await callback.message.delete()


@router.callback_query(F.data.startswith("mod_edit:"))
async def moderation_edit(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    await state.update_data(edit_product_id=product_id)
    await state.set_state(EditCardState.choose_field)
    await callback.message.answer("Что меняем?", reply_markup=edit_product_keyboard())
    await callback.answer()


@router.message(EditCardState.choose_field)
async def edit_choose_field(message: Message, state: FSMContext):
    field_map = {
        "Название": "title",
        "Описание": "description",
        "Цена": "price",
        "Фото": "photo",
    }
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Редактирование отменено.")
        return

    field = field_map.get(message.text)
    if not field:
        await message.answer("Выбери поле с клавиатуры.")
        return

    await state.update_data(field=field)
    await state.set_state(EditCardState.new_value)

    if field == "price":
        await message.answer("Новая цена в рублях (целое число):")
    elif field == "photo":
        await message.answer("Отправь новое фото:")
    else:
        await message.answer("Введи новое значение:")


@router.message(EditCardState.new_value)
async def edit_new_value(message: Message, state: FSMContext):
    data = await state.get_data()
    product_id = data.get("edit_product_id")
    field = data.get("field")

    if not product_id or not field:
        await state.clear()
        await message.answer("Что-то пошло не так, начни заново.")
        return

    async with SessionLocal() as session:
        q = await session.execute(select(Product).where(Product.id == product_id))
        product = q.scalar_one_or_none()
        if not product:
            await state.clear()
            await message.answer("Карточка не найдена.")
            return

        if field == "price":
            if not message.text or not message.text.strip().isdigit():
                await message.answer("Цена должна быть целым числом.")
                return
            product.price = int(message.text.strip()) * 100
        elif field == "photo":
            if not message.photo:
                await message.answer("Отправь фото.")
                return
            product.photo_file_id = message.photo[-1].file_id
        elif field == "title":
            product.title = message.text.strip()
        elif field == "description":
            product.description = message.text.strip()

        await session.commit()
        logger.info("Карточка %s обновлена, поле %s", product.id, field)

    await state.clear()
    await message.answer("Карточка обновлена.")


@router.message(F.text == "Статистика")
async def statistics(message: Message):
    async with SessionLocal() as session:
        q = await session.execute(select(User))
        users = q.scalars().all()

        lines = []
        for user in users:
            s_total = select(func.count(Product.id)).where(Product.user_id == user.id)
            s_app = select(func.count(Product.id)).where(
                Product.user_id == user.id,
                Product.status == ProductStatus.APPROVED,
            )
            s_rej = select(func.count(Product.id)).where(
                Product.user_id == user.id,
                Product.status == ProductStatus.REJECTED,
            )
            total = (await session.execute(s_total)).scalar_one()
            approved = (await session.execute(s_app)).scalar_one()
            rejected = (await session.execute(s_rej)).scalar_one()

            lines.append(
                f"{user.tg_id} (@{user.username or '-'}): всего {total}, "
                f"одобрено {approved}, отклонено {rejected}"
            )

    if not lines:
        await message.answer("Пользователей пока нет.")
    else:
        await message.answer("\n".join(lines))


async def get_first_withdraw(session):
    q = await session.execute(
        select(WithdrawalRequest)
        .where(WithdrawalRequest.status == WithdrawalStatus.PENDING)
        .order_by(WithdrawalRequest.id.asc())
    )
    return q.scalars().first()


async def get_next_withdraw(session, current_id: int, direction: str):
    if direction == "next":
        stmt = (
            select(WithdrawalRequest)
            .where(WithdrawalRequest.status == WithdrawalStatus.PENDING, WithdrawalRequest.id > current_id)
            .order_by(WithdrawalRequest.id.asc())
        )
    else:
        stmt = (
            select(WithdrawalRequest)
            .where(WithdrawalRequest.status == WithdrawalStatus.PENDING, WithdrawalRequest.id < current_id)
            .order_by(WithdrawalRequest.id.desc())
        )
    q = await session.execute(stmt)
    return q.scalars().first()


async def send_withdraw(msg_or_cb, wd: WithdrawalRequest):
    user = wd.user
    text = (
        f"Заявка #{wd.id}\n"
        f"Пользователь: {user.tg_id} (@{user.username or '-'})\n"
        f"Сумма: {wd.amount/100:.2f} ₽\n"
        f"Реквизиты: {wd.details}"
    )
    kb = withdrawals_keyboard(wd.id)
    await msg_or_cb.answer(text, reply_markup=kb)


@router.message(F.text == "Заявки на вывод")
async def withdrawals_start(message: Message):
    async with SessionLocal() as session:
        wd = await get_first_withdraw(session)
    if not wd:
        await message.answer("Нет заявок на вывод.")
        return
    await send_withdraw(message, wd)


@router.callback_query(F.data.startswith("wd_prev:") | F.data.startswith("wd_next:"))
async def withdraw_switch(callback: CallbackQuery):
    action, withdraw_id_str = callback.data.split(":")
    direction = "next" if action == "wd_next" else "prev"
    current_id = int(withdraw_id_str)
    async with SessionLocal() as session:
        wd = await get_next_withdraw(session, current_id, direction)
    if not wd:
        await callback.answer("Больше заявок нет.")
        return
    await callback.message.delete()
    await send_withdraw(callback.message, wd)


@router.callback_query(F.data.startswith("wd_paid:"))
async def withdraw_paid(callback: CallbackQuery):
    withdraw_id = int(callback.data.split(":")[1])
    async with SessionLocal() as session:
        q = await session.execute(
            select(WithdrawalRequest).where(WithdrawalRequest.id == withdraw_id)
        )
        wd = q.scalar_one_or_none()
        if not wd:
            await callback.answer("Заявка не найдена.")
            return
        wd.status = WithdrawalStatus.PAID
        wd.paid_at = dt.datetime.utcnow()
        await session.commit()
        logger.info("Заявка на вывод %s помечена как выплаченная", wd.id)
    await callback.answer("Отмечено как выплачено.")
    await callback.message.delete()
