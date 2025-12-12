from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram import Bot, Router

router = Router()

@router.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(f"Salom {message.from_user.first_name}, Ahvolingiz yaxshimi?")


@router.message()
async def message_handler(message: Message):
    await message.answer('Mavjud bo\'lmagan command!')
