from aiogram.fsm.state import StatesGroup, State


class AddCardState(StatesGroup):
    title = State()
    description = State()
    price = State()
    photo = State()
