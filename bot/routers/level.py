from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove
from bot.routers.keyboard import level_keyboard


router = Router()


@router.message(Command("level"))
async def level_handler(message: Message):
    kb = level_keyboard()
    await message.answer(
        "📚 English Vocablary in Use Kitobni qaysi qismidan boshlamoqchisiz?",
        reply_markup=kb.as_markup(resize_keyboard=True),
    )


@router.message(
    F.text.in_(
        [
            "📗 Elementary",
            "📘 Pre-intermediate & Intermediate",
            "📙 Upper intermediate",
            "📕 Advanced",
        ]
    )
)
async def level_selected(message: Message):
    selected_level = message.text

    await message.answer(
        f"✅ Siz {selected_level} darajasini tanladingiz!",
        reply_markup=ReplyKeyboardRemove(),
    )

