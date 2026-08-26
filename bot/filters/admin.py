import os
from typing import Union
from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery
from dotenv import load_dotenv

load_dotenv()


class isAdmin(Filter):
    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        admin_id_str = os.getenv("ADMIN")
        if not admin_id_str or not event.from_user:
            return False
        return event.from_user.id == int(admin_id_str)
