from typing import Union

from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from app.config import ADMIN_IDS


class AdminFilter(BaseFilter):
    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        user = getattr(event, "from_user", None)
        if not user:
            return False
        return user.id in ADMIN_IDS
