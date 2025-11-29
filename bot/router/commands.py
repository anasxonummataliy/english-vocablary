import os

from aiogram import Bot, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import BotCommand, Message
from aiogram.enums import ChatAction

from dotenv import load_dotenv

load_dotenv()
router = Router()
ADMIN = os.getenv("ADMIN") or ""


async def intilize_settings(bot: Bot):
    command = [
        BotCommand(command="start", description="Boshlash"),  # type: ignore
        BotCommand(command="help", description="Yordam"),  # type:ignore
        BotCommand(command="admin", description="Adminga xabar yozish"),
    ]
    await bot.set_my_commands(commands=command)


@router.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(
        "Buyruqlar: \n 1. start - botni boshlash uchun \n"
        " 2. help - botning buyruqlari haqida \n"
        " 3. admin - adminga bot haqida muammo yoki taklif bo'lsa yozish uchun."
    )


@router.message(CommandStart())
async def start_handler(message: Message, bot: Bot):
    await bot.send_chat_action(
        chat_id=message.from_user.id, action=ChatAction.TYPING
    ) 
    if message.from_user.id != int(ADMIN):
        print(type((message.from_user.id)))  
        if message.from_user.last_name is not None: 
            await message.answer(
                f"Assalomu alaykum {message.from_user.first_name} {message.from_user.last_name} bizning botimizga hush kelibsiz!"
            )  
        else:
            await message.answer(f"Assalomu alaykum {message.from_user.first_name} bizning botimizga hush kelibsiz!")  # type: ignore
