import os
import json
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from redis.asyncio import Redis


router = Router()


async def get_unit_words(level: str, unit_id: int):
    # Fayl yo'li to'g'riligini tekshiring (masalan: 'data/elementary.json')
    file_path = f"data/{level}.json"

    print(f"DEBUG: Qidirilayotgan fayl: {file_path}")  # Buni qo'shing

    if not os.path.exists(file_path):
        print(f"DEBUG: Fayl topilmadi!")
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        # JSON ichidagi 'units' ni tekshiramiz
        for u in data.get("units", []):
            # Unit ID ni string yoki int ekanini tekshiring
            if int(u["unit"]) == int(unit_id):
                return u["words"]
    return None


@router.callback_query(F.data.startswith("words_"))
async def show_words_handler(callback: CallbackQuery, redis: Redis):
    raw_data = callback.data.split("_")[1]

    try:
        unit_id = int(raw_data.replace("Unit ", "").strip())
    except ValueError:
        await callback.answer("❌ Unit raqamini aniqlashda xatolik", show_alert=True)
        return

    user_id = callback.from_user.id
    user_level = await redis.get(f"user:{user_id}:level")

    if not user_level:
        await callback.answer("⚠️ Sessiya muddati tugagan.", show_alert=True)
        return

    clean_level = "".join(filter(str.isalnum, user_level)).lower()

    words = await get_unit_words(clean_level, unit_id)

    if not words:
        await callback.answer(
            f"❌ Unit {unit_id} uchun so'zlar topilmadi.", show_alert=True
        )
        return

    text = f"📖 <b>{user_level}</b>\n"
    text += f"🎯 <b>Unit {unit_id} so'zlari:</b>\n\n"

    for word in words:
        text += f"🔹 <b>{word['word']}</b> {word['transcription']}\n"
        text += f"<i>{word['part_of_speech']}</i>: {word['description']}\n"
        text += f"📝 <i>Ex: {word['example']}</i>\n"
        text += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"

    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"select_Unit {unit_id}")
    )

    await callback.message.edit_text(
        text, parse_mode="HTML", reply_markup=ikb.as_markup()
    )
