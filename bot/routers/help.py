from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

@router.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(
        "Buyruqlar: \n 1. /start - botni boshlash uchun \n"
        " 2. /level - English Vocablary in Use kitobining qismlari"
        " 3. /help - botning buyruqlari haqida \n"
        " 4. /admin - adminga bot haqida muammo yoki taklif bo'lsa yozish uchun."
    )
