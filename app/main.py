import sys
import logging
import os
import asyncio

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv


from commands import *
from router.start import router as handler_router


load_dotenv()
TOKEN = os.getenv("TOKEN") or ""
ADMIN = os.getenv("ADMIN") or ""

dp = Dispatcher()
bot = Bot(TOKEN)


@dp.startup()
async def start_message(bot: Bot) -> None:
    await bot.send_message(ADMIN, 'Bot ishga tushdi✅')

@dp.shutdown()
async def shotdown_message(bot: Bot) -> None:
    await bot.send_message(ADMIN, "Bot to'xtatildi❌")


async def main() -> None:
    dp.include_router(handler_router)
    await intilize_settings(bot)
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
