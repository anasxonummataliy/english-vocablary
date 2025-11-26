import os

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")
print(TOKEN)

router = Router()


@router.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(
        "Buyruqlar: \n 1. start - botni boshlash uchun \n" \
        " 2. help - botning buyruqlari haqida \n" \
        " 3. admin - adminga bot haqida muammo yoki taklif bo'lsa yozish uchun."
    )
