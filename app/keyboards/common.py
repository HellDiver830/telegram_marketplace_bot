from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="Добавить карточку")],
        [KeyboardButton(text="Посмотреть карточки")],
        [KeyboardButton(text="Баланс")],
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="Админ меню")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
