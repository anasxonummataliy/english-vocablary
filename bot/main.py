import sys
import logging
import os
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.enums import ChatMemberStatus
from aiogram.filters import Filter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from aiogram.types import BotCommandScopeChat, BotCommandScopeAllPrivateChats, InlineKeyboardButton
from aiogram.utils.i18n import gettext as _
from aiogram.utils.i18n import lazy_gettext as __

from router.commands import intilize_settings,  router as command_router
from utils.middleware import IsJoinChannelMiddleware
from admin.admin import router as admin_router

load_dotenv()
TOKEN = os.getenv("TOKEN") or ""
ADMIN = os.getenv("ADMIN") or ""

dp = Dispatcher()
bot = Bot(TOKEN)
CHANNEL_ID = os.getenv("CHANNEL_ID") or ""


@dp.startup()
async def start_message(bot: Bot) -> None:
    # await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=ADMIN))
    # await bot.set_my_commands(user_command, scope=BotCommandScopeAllPrivateChats())
    await bot.send_message(ADMIN, 'Bot ishga tushdi✅')

@dp.shutdown()
async def shotdown_message(bot: Bot) -> None:
    await bot.send_message(ADMIN, "Bot to'xtatildi❌")



async def main() -> None:
    dp.update.outer_middleware.register(IsJoinChannelMiddleware())
    dp.include_router(command_router)
    dp.include_router(admin_router)

    await intilize_settings(bot)
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
