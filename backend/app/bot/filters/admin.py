from aiogram.filters import BaseFilter
from aiogram.types import Message

from app.core.config import get_settings


class IsAdminFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        if message.from_user is None:
            return False
        return message.from_user.id in get_settings().admin_telegram_ids
