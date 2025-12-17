import sys
import logging
import os
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommandScopeAllPrivateChats, BotCommandScopeChat
from dotenv import load_dotenv

from bot.middleware.channel import IsJoinChannelMiddleware
from bot.routers import user_router
from bot.middleware.channel import router as middleware_router
from bot.admin import admin_router 

from bot.admin.commands import admin_commands
from bot.routers.user_commands import user_command
from bot.database.base import create_db_and_tables

load_dotenv()
TOKEN = os.getenv("TOKEN") or ""

dp = Dispatcher()
bot = Bot(TOKEN)
CHANNEL_ID = os.getenv("CHANNEL_ID") or ""
ADMIN = int(os.getenv("ADMIN"))

@dp.startup()
async def start_message(bot: Bot) -> None:
    await create_db_and_tables()
    await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=ADMIN))
    await bot.set_my_commands(user_command, scope=BotCommandScopeAllPrivateChats())
    await bot.send_message(ADMIN, 'Bot ishga tushdi✅')

@dp.shutdown()
async def shotdown_message(bot: Bot) -> None:
    await bot.send_message(ADMIN, "Bot to'xtatildi❌")


async def main() -> None:
    dp.include_router(admin_router)
    dp.message.middleware(IsJoinChannelMiddleware())
    dp.include_router(middleware_router)
    dp.include_router(user_router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
