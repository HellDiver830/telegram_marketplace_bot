from aiogram.fsm.state import StatesGroup, State


class WithdrawState(StatesGroup):
    details = State()
