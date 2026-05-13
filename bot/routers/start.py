import os
from aiogram import Bot, Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.enums import ChatAction
from sqlalchemy import select

from dotenv import load_dotenv
from bot.database.session import get_async_session_context
from bot.routers.keyboard import level_keyboard
from bot.database.models.users import User

load_dotenv()
router = Router()


async def send_welcome_message(message: Message, bot: Bot):
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    kb = await level_keyboard()

    first_name = message.from_user.first_name if message.from_user else "Foydalanuvchi"

    welcome_text = (
        f"🌟 **Assalomu alaykum, {first_name}!**\n\n"
        f"Sizni ko'rib turganimizdan xursandmiz! Ushbu bot orqali "
        f"**'English Vocabulary in Use'** kitoblari asosida so'z boyligingizni oshirishingiz mumkin. 🚀\n\n"
        f"📚 Qaysi darajadan boshlashni xohlaysiz?"
    )

    await message.answer(
        welcome_text,
        reply_markup=kb.as_markup(resize_keyboard=True),
        parse_mode="Markdown",
    )


@router.message(CommandStart())
async def start_handler(message: Message, bot: Bot):
    if not message.from_user:
        return

    async with get_async_session_context() as session:
        stmt = select(User).where(User.tg_id == message.from_user.id)
        result = await session.execute(stmt)
        db_user = result.scalar_one_or_none()

        if not db_user:
            db_user = User(
                tg_id=message.from_user.id,
                first_name=message.from_user.first_name,
                username=message.from_user.username,
            )
            session.add(db_user)
            await session.commit()

    await send_welcome_message(message, bot)


@router.message()
async def some(message: Message, bot: Bot):
    await send_welcome_message(message, bot)
