from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("help"))
async def help_handler(message: Message):
    help_text = (
        "❓ **Botdan qanday foydalanish mumkin?**\n\n"
        "Quyidagi buyruqlar orqali botni boshqarishingiz mumkin:\n\n"
        "🚀 /start — Botni qayta ishga tushirish va asosiy menyuga qaytish.\n"
        "📚 /level — 'English Vocabulary in Use' kitobining darajalarini tanlash.\n"
        "⏰ /reminder — Unitlarni o'rganish uchun eslatma sozlash (9 soat yoki 1 kun).\n"
        "ℹ️ /help — Hozirgi siz ko'rib turgan yordam oynasini ko'rsatish.\n"
        "👨‍💻 /admin — Bot bo'yicha takliflar yoki texnik muammolar yuzasidan adminga murojaat qilish.\n\n"
        "--- \n"
        "💡 *Maslahat:* Agar bot javob bermay qolsa, /start buyrug'ini yuboring."
    )

    await message.answer(help_text, parse_mode="Markdown")
