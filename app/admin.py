from aiogram.types import Message
from aiogram.filters import Filter
from os import getenv
from dotenv import load_dotenv

load_dotenv()
ADMIN = getenv("ADMIN")

class isAdmin(Filter):
    async def __call__(self, message : Message):
        return message.from_user.id == ADMIN #type:ignore

