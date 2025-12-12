import os
from aiogram.filters import Filter
from aiogram.types import Message

from dotenv import load_dotenv
load_dotenv()

class isAdmin(Filter):
    async def __call__(self, message: Message):
        return message.from_user.id == int(os.getenv("ADMIN"))
