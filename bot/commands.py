from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import BotCommand, Message

router = Router()
@router.message(Command('help'))
async def about_command(message : Message, bot : Bot):
    await message.answer("""/start - Botni boshlash uchun,
/help - Botning buyruqlari haqida ma'lumot olish uchun""")

async def intilize_settings(bot: Bot):
    command = [
        BotCommand(command='start', description='Boshlash'),  # type: ignore
        BotCommand(command='help', description='Yordam'),  # type:ignore
    ]
    await bot.set_my_commands(commands=command)
