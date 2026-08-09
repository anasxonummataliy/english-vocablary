from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram import Router

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(f"Salom {message.from_user.first_name}, Admin panelga xush kelibsiz!")
