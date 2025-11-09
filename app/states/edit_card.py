from aiogram.fsm.state import StatesGroup, State


class EditCardState(StatesGroup):
    choose_field = State()
    new_value = State()
