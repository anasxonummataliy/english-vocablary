import os

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from dotenv import load_dotenv
load_dotenv()
router = Router()
ADMIN = os.getenv("ADMIN") or ""


@router.message(CommandStart)
async def start_handler(message: Message):
    if message.from_user.id != int(ADMIN):  # type:ignore
        print(type((message.from_user.id)))  # type:ignore
        if message.from_user.last_name is not None:  # type:ignore
            await message.answer(f"Assalomu alaykum {message.from_user.first_name} {message.from_user.last_name} bizning botimizga hush kelibsiz!") #type:ignore
        else:
            await message.answer(f"Assalomu alaykum {message.from_user.first_name} bizning botimizga hush kelibsiz!") # type: ignore
    else:
        await message.answer("Admin")
