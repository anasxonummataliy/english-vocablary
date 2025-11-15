import sys
import logging
import os
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardButton, BotCommand
from aiogram.filters import Filter, CommandStart
from dotenv import load_dotenv


from commands import *
from .hendler import router as handler_router


load_dotenv()
TOKEN = os.getenv("TOKEN") or ""
ADMIN = os.getenv("ADMIN") or ""

dp = Dispatcher()

@dp.message(CommandStart)
async def start_message(message: Message):
    if message.from_user.id != int(ADMIN):  # type:ignore
        print(type((message.from_user.id)))  # type:ignore
        if message.from_user.last_name is not None: #type:ignore
            await message.answer(f"Assalomu alaykum {message.from_user.first_name} {message.from_user.last_name} bizning botimizga hush kelibsiz!") #type:ignore
        else:
            await message.answer(f"Assalomu alaykum {message.from_user.first_name} bizning botimizga hush kelibsiz!" ) #type:ignore
    else:
        await message.answer("Admin")


async def main() -> None:
    dp.include_router(handler_router)
    bot = Bot(TOKEN)  # type:ignore
    await intilize_settings(bot)
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
