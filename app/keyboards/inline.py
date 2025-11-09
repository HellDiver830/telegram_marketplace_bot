from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup


def product_browse_keyboard(product_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="«", callback_data=f"prod_prev:{product_id}")
    kb.button(text="Купить", callback_data=f"prod_buy:{product_id}")
    kb.button(text="»", callback_data=f"prod_next:{product_id}")
    kb.adjust(3)
    return kb.as_markup()


def moderation_keyboard(product_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="«", callback_data=f"mod_prev:{product_id}")
    kb.button(text="Добавить", callback_data=f"mod_approve:{product_id}")
    kb.button(text="Отклонить", callback_data=f"mod_reject:{product_id}")
    kb.button(text="Изменить", callback_data=f"mod_edit:{product_id}")
    kb.button(text="»", callback_data=f"mod_next:{product_id}")
    kb.adjust(4, 1)
    return kb.as_markup()


def withdrawals_keyboard(withdraw_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="«", callback_data=f"wd_prev:{withdraw_id}")
    kb.button(text="Выплата проведена", callback_data=f"wd_paid:{withdraw_id}")
    kb.button(text="»", callback_data=f"wd_next:{withdraw_id}")
    kb.adjust(3)
    return kb.as_markup()
