import os

from aiogram import Bot, Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.enums import ChatAction

from dotenv import load_dotenv
from bot.database.session import session
from bot.routers.keyboard import level_keyboard
from bot.database.models.users import User

load_dotenv()
router = Router()


@router.message(CommandStart())
async def start_handler(message: Message, bot: Bot):
    user = session.query(User).filter_by(id=message.from_user.id).first()
    if not user:
        session.add(user.model_dump(*user))
        session.commit()
    await bot.send_chat_action(chat_id=message.from_user.id, action=ChatAction.TYPING)
    kb = level_keyboard()
    await message.answer(
        f"Assalomu alaykum {message.from_user.first_name} bizning botimizga hush kelibsiz! \n 📚 English Vocablary in Use Kitobni qaysi qismidan boshlamoqchisiz?",
        reply_markup=kb.as_markup(resize_keyboard=True),
    )
