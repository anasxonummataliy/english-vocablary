from aiogram import Bot
from aiogram.types import BotCommand, Message



async def intilize_settings(bot: Bot):
    command = [
        BotCommand(command='start', description='Boshlash'),  # type: ignore
        BotCommand(command='help', description='Yordam'),  # type:ignore
    ]
    await bot.set_my_commands(commands=command)
