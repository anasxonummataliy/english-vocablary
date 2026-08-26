from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ChatType
from bot.routers.keyboard import main_menu_keyboard

router = Router()


@router.message(Command("help"))
async def help_handler(message: Message):
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        group_help = (
            "👥 <b>Guruhda botdan foydalanish bo'yicha yordam:</b>\n\n"
            "🚀 <b>/quiz</b> (yoki <code>/musobaqa</code>) — Guruhda unitlar yoki 20 ta aralash (Mix) savollar bo'yicha viktorina musobaqasini boshlash.\n"
            "🏆 <b>/top</b> (yoki <code>/leaderboard</code>) — Guruh a'zolarining jami ballari hamda har bir unit bo'yicha yetakchilar reytingini ko'rish.\n"
            "ℹ️ <b>/help</b> — Hozirgi yordam qo'llanmasini ko'rsatish.\n\n"
            "💡 <i>Maslahat: Musobaqa boshlash uchun guruhda /quiz buyrug'ini yuboring!</i>"
        )
        await message.answer(group_help, parse_mode="HTML")
        return

    private_help = (
        "❓ <b>Botdan qanday foydalanish mumkin?</b>\n\n"
        "Quyidagi buyruqlar va menyu orqali botni boshqarishingiz mumkin:\n\n"
        "🚀 <b>/start</b> — Botni qayta ishga tushirish va asosiy menyuga qaytish.\n"
        "📚 <b>/level</b> — Kitoblarni (Vocabulary in Use va 4000 Essential Words) tanlash.\n"
        "🟢 <b>/savat</b> — O'zingiz saqlagan notanish so'zlar savatchalari (o'rganish, flash card, test).\n"
        "🏆 <b>/top</b> — Unitlar va umumiy reytinglarni ko'rish.\n"
        "⏰ <b>/reminder</b> — Unitlarni o'rganish uchun eslatma sozlash.\n"
        "ℹ️ <b>/help</b> — Hozirgi yordam oynasini ko'rsatish.\n"
        "👨‍💻 <b>/admin</b> — Adminga murojaat qilish.\n\n"
        "💡 <i>Maslahat: Istalgan payt pastdagi menyu tugmalaridan foydalanishingiz mumkin!</i>"
    )

    kb = await main_menu_keyboard()
    await message.answer(
        private_help,
        parse_mode="HTML",
        reply_markup=kb.as_markup(resize_keyboard=True),
    )


@router.message(F.chat.type == ChatType.PRIVATE)
async def fallback_user_message_handler(message: Message):
    """Foydalanuvchi noma'lum matn yoki boshqa narsa yuborganda tushunarli yo'riqnoma ko'rsatish."""
    kb = await main_menu_keyboard()
    text = (
        "👋 <b>Sizga qanday yordam bera olaman?</b>\n\n"
        "Men sizga ingliz tili so'zlarini kitoblar bo'yicha o'rganishda, testlar va flash cardlar orqali "
        "bilimingizni sinashda yordam beraman! 🚀\n\n"
        "👇 <b>Quyidagi bo'limlardan birini tanlang:</b>\n\n"
        "📘 <b>English Vocabulary in Use</b> — Darslik bo'yicha so'zlar\n"
        "🔵 <b>4000 Essential English Words</b> — 1-6 kitoblar bo'yicha so'zlar\n"
        "🟢 <b>Mening savatcham</b> — Saqlangan so'zlaringiz\n"
        "⏰ <b>/reminder</b> — Kunlik/interval eslatmalar sozlash\n"
        "🏆 <b>/top</b> — Peshqadamlar reytingi\n"
        "ℹ️ <b>/help</b> — Qo'llanma"
    )
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=kb.as_markup(resize_keyboard=True),
    )
