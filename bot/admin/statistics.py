from aiogram import Router 
from aiogram.types import Message
from aiogram.filters import Command

router = Router()

@router.message(Command("statistics"))
async def statistics_handler(message: Message):
    await message.answer("Statistics bo'limi")