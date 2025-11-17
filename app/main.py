import sys
import logging
import os
import asyncio

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from aiogram.types import BotCommandScopeChat, BotCommandScopeAllPrivateChats


from commands import *
from router.start import router as handler_router


load_dotenv()
TOKEN = os.getenv("TOKEN") or ""
ADMIN = os.getenv("ADMIN") or ""

dp = Dispatcher()
bot = Bot(TOKEN)


@dp.startup()
async def start_message(bot: Bot) -> None:
    admin_commands = [
        BotCommand(command='/start', description='Boshlash🏁'),
        BotCommand(command='/users', description='User list📚'),
        BotCommand(command='/check', description='Botni tekshirish☑️')
    ]
    user_command = [
        BotCommand(command='start', description='Boshlash'),  # type: ignore
        BotCommand(command='help', description='Yordam'),  # type:ignore
    ]
    await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=ADMIN))
    await bot.set_my_commands(user_command, scope=BotCommandScopeAllPrivateChats())
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
