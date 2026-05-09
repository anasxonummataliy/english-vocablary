import sys
import logging
import os
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommandScopeAllPrivateChats, BotCommandScopeChat
from dotenv import load_dotenv

from bot.middleware.channel import IsJoinChannelMiddleware
from bot.middleware.user_activity import UserActivityMiddleware
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


async def start_bot() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    await bot.set_webhook(os.getenv("WEBHOOK_URL") or "")
    logging.info(f"{await bot.get_webhook_info()}")
    dp.message.middleware(IsJoinChannelMiddleware())
    dp.message.middleware(UserActivityMiddleware())
    dp.include_router(middleware_router)
    dp.include_router(admin_router)
    dp.include_router(user_router)
    await create_db_and_tables()
    await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=ADMIN))
    await bot.set_my_commands(user_command, scope=BotCommandScopeAllPrivateChats())


if __name__ == "__main__":
    asyncio.run(start_bot())
