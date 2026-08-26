import os
from aiogram import Bot, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.enums import ChatAction, ChatType
from bot.routers.keyboard import main_menu_inline_keyboard
from dotenv import load_dotenv

load_dotenv()

router = Router()


async def send_welcome_message(message: Message, bot: Bot):
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    ikb = await main_menu_inline_keyboard()

    full_name = message.from_user.full_name if message.from_user else "Foydalanuvchi"

    welcome_text = (
        f"🌟 <b>Assalomu alaykum, {full_name}!</b>\n\n"
        f"Bot orqali <b>English Vocabulary in Use</b> va <b>4000 Essential English Words</b> kitoblari "
        f"asosida so'zlarni o'rganishingiz, flash card va testlar orqali bilimingizni sinashingiz hamda "
        f"bilmagan so'zlaringizni <b>Savatchaga</b> saqlab borishingiz mumkin. 🚀\n\n"
        f"Quyidagi bo'limlardan birini tanlang:"
    )

    await message.answer(
        welcome_text,
        reply_markup=ikb,
        parse_mode="HTML",
    )


@router.message(CommandStart())
async def start_handler(message: Message, bot: Bot):
    if not message.from_user:
        return

    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer(
            "👥 <b>Guruhda faqat Musobaqa (Quiz) rejimi ishlaydi!</b>\n\n"
            "🏆 Musobaqa boshlash uchun <b>/quiz</b> buyrug'ini bosing.\n"
            "📊 Reytinglarni ko'rish uchun <b>/top</b> buyrug'ini bosing.\n"
            "ℹ️ Yordam uchun <b>/help</b> buyrug'ini bosing.\n\n"
            "<i>So'zlarni shaxsan o'rganish va eslatma sozlash uchun botga shaxsiy (private) chatda yozing.</i>",
            parse_mode="HTML",
        )
        return

    await send_welcome_message(message, bot)
