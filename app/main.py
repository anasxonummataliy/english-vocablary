import sys
import logging
import os
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardButton
from aiogram.filters import Filter, CommandStart
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")
ADMIN = os.getenv("ADMIN")

dp = Dispatcher()

async def main() -> None:
    bot = Bot(TOKEN) #type:ignore
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())



    