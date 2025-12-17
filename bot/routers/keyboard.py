from aiogram.utils.keyboard import ReplyKeyboardBuilder

async def level_keyboard():
    kb = ReplyKeyboardBuilder()
    kb.button(text="📗 Elementary")
    kb.button(text="📘 Pre-intermediate & Intermediate")
    kb.button(text="📙 Upper intermediate")
    kb.button(text="📕 Advanced")
    kb.adjust(1)
    return kb




