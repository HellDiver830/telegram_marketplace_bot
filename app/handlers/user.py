from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
    LabeledPrice,
    PreCheckoutQuery,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import ADMIN_IDS, PAYMENT_PROVIDER_TOKEN
from app.logger import logger
from app.db.session import SessionLocal
from app.db.models import User, Product, ProductStatus, Purchase, WithdrawalRequest
from app.keyboards.common import main_menu
from app.keyboards.inline import product_browse_keyboard
from app.states.add_card import AddCardState
from app.states.withdraw import WithdrawState


router = Router()


async def get_or_create_user(session: AsyncSession, tg_user) -> User:
    q = await session.execute(select(User).where(User.tg_id == tg_user.id))
    user = q.scalar_one_or_none()
    if not user:
        user = User(
            tg_id=tg_user.id,
            username=tg_user.username,
            is_admin=tg_user.id in ADMIN_IDS,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info("Создан пользователь %s", tg_user.id)
    return user


@router.message(CommandStart())
async def cmd_start(message: Message):
    async with SessionLocal() as session:
        user = await get_or_create_user(session, message.from_user)
    await message.answer(
        "Привет. Это тестовый маркетплейс-бот.",
        reply_markup=main_menu(is_admin=user.is_admin),
    )


@router.message(F.text == "Добавить карточку")
async def add_card_start(message: Message, state: FSMContext):
    await state.set_state(AddCardState.title)
    await message.answer("Введи название товара:")


@router.message(AddCardState.title)
async def add_card_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AddCardState.description)
    await message.answer("Теперь описание:")


@router.message(AddCardState.description)
async def add_card_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(AddCardState.price)
    await message.answer("Цена в рублях (целое число):")


@router.message(AddCardState.price)
async def add_card_price(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("Нужно целое число. Попробуй ещё раз.")
        return
    price_rub = int(text)
    await state.update_data(price=price_rub * 100)
    await state.set_state(AddCardState.photo)
    await message.answer("Отправь фото товара или напиши 'нет':")


@router.message(AddCardState.photo)
async def add_card_photo(message: Message, state: FSMContext):
    photo_file_id = None
    if message.photo:
        photo_file_id = message.photo[-1].file_id
    elif message.text and message.text.lower() != "нет":
        await message.answer("Отправь фото или напиши 'нет'.")
        return

    data = await state.get_data()
    await state.clear()

    async with SessionLocal() as session:
        user = await get_or_create_user(session, message.from_user)
        product = Product(
            user_id=user.id,
            title=data["title"],
            description=data["description"],
            price=data["price"],
            photo_file_id=photo_file_id,
            status=ProductStatus.PENDING,
        )
        session.add(product)
        await session.commit()
        logger.info("Пользователь %s создал карточку %s в статусе pending", user.tg_id, product.id)

    await message.answer("Карточка создана и отправлена на модерацию.")


async def get_first_approved_product(session: AsyncSession) -> Product | None:
    q = await session.execute(
        select(Product)
        .where(Product.status == ProductStatus.APPROVED)
        .order_by(Product.id.asc())
    )
    return q.scalars().first()


async def get_next_product(session: AsyncSession, current_id: int, direction: str) -> Product | None:
    if direction == "next":
        stmt = (
            select(Product)
            .where(Product.status == ProductStatus.APPROVED, Product.id > current_id)
            .order_by(Product.id.asc())
        )
    else:
        stmt = (
            select(Product)
            .where(Product.status == ProductStatus.APPROVED, Product.id < current_id)
            .order_by(Product.id.desc())
        )
    q = await session.execute(stmt)
    return q.scalars().first()


async def send_product(message_or_cb, product: Product):
    text = (
        f"Товар #{product.id}\n\n"
        f"{product.title}\n"
        f"Цена: {product.price/100:.2f} ₽\n\n"
        f"{product.description}"
    )
    kb = product_browse_keyboard(product.id)
    if product.photo_file_id:
        await message_or_cb.answer_photo(product.photo_file_id, caption=text, reply_markup=kb)
    else:
        await message_or_cb.answer(text, reply_markup=kb)


@router.message(F.text == "Посмотреть карточки")
async def view_cards(message: Message):
    async with SessionLocal() as session:
        product = await get_first_approved_product(session)
    if not product:
        await message.answer("Пока нет одобренных карточек.")
        return
    await send_product(message, product)


@router.callback_query(F.data.startswith("prod_prev:") | F.data.startswith("prod_next:"))
async def product_switch(callback: CallbackQuery):
    action, product_id_str = callback.data.split(":")
    direction = "next" if action == "prod_next" else "prev"
    current_id = int(product_id_str)
    async with SessionLocal() as session:
        product = await get_next_product(session, current_id, direction)
    if not product:
        await callback.answer("Больше товаров нет.")
        return
    await callback.message.delete()
    await send_product(callback.message, product)


@router.callback_query(F.data.startswith("prod_buy:"))
async def product_buy(callback: CallbackQuery):
    product_id = int(callback.data.split(":")[1])
    async with SessionLocal() as session:
        q = await session.execute(
            select(Product).where(
                Product.id == product_id,
                Product.status == ProductStatus.APPROVED,
            )
        )
        product = q.scalar_one_or_none()
    if not product:
        await callback.answer("Товар недоступен.")
        return

    prices = [LabeledPrice(label=product.title, amount=product.price)]
    payload = f"product_{product.id}"

    await callback.message.answer_invoice(
        title=product.title,
        description=product.description[:200],
        payload=payload,
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="rub",
        prices=prices,
    )
    await callback.answer()


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout: PreCheckoutQuery):
    await pre_checkout.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    if not payload.startswith("product_"):
        return
    product_id = int(payload.split("_")[1])
    amount = message.successful_payment.total_amount

    async with SessionLocal() as session:
        q = await session.execute(select(Product).where(Product.id == product_id))
        product = q.scalar_one_or_none()
        if not product:
            return

        q_seller = await session.execute(select(User).where(User.id == product.user_id))
        seller = q_seller.scalar_one_or_none()
        buyer = await get_or_create_user(session, message.from_user)
        if not seller:
            return

        seller.balance += amount
        purchase = Purchase(
            buyer_id=buyer.id,
            product_id=product.id,
            amount=amount,
            payload=payload,
        )
        session.add(purchase)
        await session.commit()
        logger.info(
            "Покупка: buyer=%s product=%s amount=%s",
            buyer.tg_id,
            product.id,
            amount,
        )

    await message.answer("Оплата прошла успешно.")


@router.message(F.text == "Баланс")
async def show_balance(message: Message, state: FSMContext):
    async with SessionLocal() as session:
        user = await get_or_create_user(session, message.from_user)
    balance_rub = user.balance / 100

    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Вывести")],
            [KeyboardButton(text="Назад")],
        ],
        resize_keyboard=True,
    )
    await message.answer(f"Твой баланс: {balance_rub:.2f} ₽", reply_markup=kb)


@router.message(F.text == "Вывести")
async def withdraw_start(message: Message, state: FSMContext):
    async with SessionLocal() as session:
        user = await get_or_create_user(session, message.from_user)
    if user.balance <= 0:
        await message.answer("Баланс нулевой, выводить нечего.")
        return
    await state.set_state(WithdrawState.details)
    await message.answer("Введи реквизиты для вывода. Выводится вся сумма.")


@router.message(WithdrawState.details)
async def withdraw_details(message: Message, state: FSMContext):
    async with SessionLocal() as session:
        user = await get_or_create_user(session, message.from_user)
        if user.balance <= 0:
            await state.clear()
            await message.answer("Баланс нулевой, вывод невозможен.")
            return

        amount = user.balance
        user.balance = 0

        req = WithdrawalRequest(
            user_id=user.id,
            amount=amount,
            details=message.text.strip(),
        )
        session.add(req)
        await session.commit()
        logger.info("Заявка на вывод от %s на сумму %s", user.tg_id, amount)

    await state.clear()
    await message.answer("Заявка на вывод создана, админ посмотрит.")


@router.message(F.text == "Назад")
async def back_to_main(message: Message):
    async with SessionLocal() as session:
        user = await get_or_create_user(session, message.from_user)
    await message.answer("Главное меню", reply_markup=main_menu(is_admin=user.is_admin))
