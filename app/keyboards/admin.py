from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def admin_menu() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="Модерация")],
        [KeyboardButton(text="Статистика")],
        [KeyboardButton(text="Заявки на вывод")],
        [KeyboardButton(text="Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def edit_product_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="Название"), KeyboardButton(text="Описание")],
        [KeyboardButton(text="Цена"), KeyboardButton(text="Фото")],
        [KeyboardButton(text="Отмена")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
