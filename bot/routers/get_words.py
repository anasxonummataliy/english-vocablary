import os
import json
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from redis.asyncio import Redis


router = Router()


async def get_unit_words(level: str, unit_id: int) -> list | None:
    """
    JSON fayldan berilgan level va unit_id bo'yicha so'zlar ro'yxatini qaytaradi.
    """
    file_path = f"data/{level}.json"

    if not os.path.exists(file_path):
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for unit in data.get("units", []):
        if int(unit["unit"]) == int(unit_id):
            return unit.get("words", [])

    return None


async def get_unit_info(level: str, unit_id: int) -> dict | None:
    """
    Unit sarlavhasi va mavzusini qaytaradi.
    """
    file_path = f"data/{level}.json"

    if not os.path.exists(file_path):
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for unit in data.get("units", []):
        if int(unit["unit"]) == int(unit_id):
            return {
                "title": unit.get("title", ""),
                "topic": unit.get("topic", ""),
            }

    return None


def format_words_text(words: list, unit_id: int, unit_info: dict, level: str) -> str:
    """
    So'zlar ro'yxatini chiroyli HTML formatga o'giradi.
    Har bir so'z uchun: word, transcription, part_of_speech,
    uzbek manosi, inglizcha tavsif va misol ko'rsatiladi.
    """
    level_display = level.capitalize()

    text = (
        f"📚 <b>{level_display} — Unit {unit_id}</b>\n"
        f"📌 <b>{unit_info['title']}</b>\n"
        f"<i>{unit_info['topic']}</i>\n\n"
        f"{'━' * 20}\n\n"
    )

    for i, word in enumerate(words, start=1):
        word_str = word.get("word", "")
        transcription = word.get("transcription", "")
        pos = word.get("part_of_speech", "")
        uzbek = word.get("uzbek", "—")
        description = word.get("description", "")
        example = word.get("example", "")

        text += (
            f"<b>{i}. {word_str}</b>  <code>{transcription}</code>\n"
            f"   🇺🇿 <b>{uzbek}</b>\n"
            f"   📖 <i>{pos}</i> — {description}\n"
            f"   ✏️ <i>{example}</i>\n"
        )

        # So'nggi so'zdan keyin ajratgich qo'yilmaydi
        if i < len(words):
            text += f"\n{'─' * 18}\n\n"

    return text


@router.callback_query(F.data.startswith("words_"))
async def show_words_handler(callback: CallbackQuery, redis: Redis):
    """
    Tanlangan unit so'zlarini ko'rsatadi.
    Callback data format: words_{unit_id}
    """
    raw_data = callback.data.removeprefix("words_").strip()

    try:
        unit_id = int(raw_data.replace("Unit", "").strip())
    except ValueError:
        await callback.answer("❌ Unit raqamini aniqlashda xatolik.", show_alert=True)
        return

    user_id = callback.from_user.id
    raw_level = await redis.get(f"user:{user_id}:level")

    if not raw_level:
        await callback.answer(
            "⚠️ Sessiya muddati tugagan. Iltimos, qaytadan boshlang.",
            show_alert=True,
        )
        return

    # Redis bytes → str, faqat harf-raqam qoldirib kichik harfga o'tkazamiz
    if isinstance(raw_level, bytes):
        raw_level = raw_level.decode()
    clean_level = "".join(filter(str.isalnum, raw_level)).lower()

    # Unit ma'lumotlari va so'zlarni parallel olamiz
    unit_info = await get_unit_info(clean_level, unit_id)
    words = await get_unit_words(clean_level, unit_id)

    if not words or not unit_info:
        await callback.answer(
            f"❌ Unit {unit_id} uchun ma'lumot topilmadi.", show_alert=True
        )
        return

    text = format_words_text(words, unit_id, unit_info, clean_level)

    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(
            text="🧪 Testni boshlash",
            callback_data=f"test_{unit_id}",
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text="🔁 So'zlarni takrorlash",
            callback_data=f"review_{unit_id}",
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text="⬅️ Orqaga",
            callback_data=f"select_unit_{unit_id}",
        )
    )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=ikb.as_markup(),
    )
    await callback.answer()
