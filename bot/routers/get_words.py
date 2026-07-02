import os
import json
import html
import logging
from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from redis.asyncio import Redis

router = Router()
logger = logging.getLogger(__name__)


async def get_unit_words(level: str, unit_id: int) -> list | None:
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
    level_display = level.capitalize()
    text = (
        f"📚 <b>{level_display} — Unit {unit_id}</b>\n"
        f"📌 <b>{html.escape(unit_info['title'])}</b>\n"
        f"<i>{html.escape(unit_info['topic'])}</i>\n\n"
        f"{'━' * 20}\n\n"
    )
    for i, word in enumerate(words, start=1):
        word_str = html.escape(word.get("word", ""))
        transcription = html.escape(word.get("transcription", ""))
        pos = html.escape(word.get("part_of_speech", ""))
        uzbek = html.escape(word.get("uzbek", "—"))
        description = html.escape(word.get("description", ""))
        example = html.escape(word.get("example", ""))
        text += (
            f"<b>{i}. {word_str}</b>  <code>{transcription}</code>\n"
            f"   🇺🇿 <b>{uzbek}</b>\n"
            f"   📖 <i>{pos}</i> — {description}\n"
            f"   ✏️ <i>{example}</i>\n"
        )
        if i < len(words):
            text += f"\n{'─' * 18}\n\n"
    return text


@router.callback_query(F.data.startswith("words_"))
async def show_words_handler(callback: CallbackQuery, redis: Redis):
    raw_data = callback.data.removeprefix("words_").strip()
    print(f"[DEBUG words] callback.data={callback.data!r} raw_data={raw_data!r}", flush=True)

    try:
        unit_id = int(raw_data.replace("Unit", "").replace("_", "").strip())
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

    if isinstance(raw_level, bytes):
        raw_level = raw_level.decode()
    clean_level = "".join(filter(str.isalnum, raw_level)).lower()

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
            callback_data=f"test_Unit_{unit_id}",
            style="success",
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text="🔁 So'zlarni takrorlash",
            callback_data=f"review_{unit_id}",
            style="primary",
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text="⬅️ Orqaga",
            callback_data=f"select_Unit {unit_id}",
        )
    )

    MAX_LEN = 4000
    # HTML teglar o'rtasida qirqmaslik — so'z chegarasida qirqamiz
    if len(text) <= MAX_LEN:
        chunks = [text]
    else:
        # So'zlarni ajratib chiqamiz — har bir so'z bloki alohida
        # So'z bloklari `\n\n{'─' * 18}\n\n` bilan ajratilgan
        separator = f"\n{'─' * 18}\n\n"
        parts = text.split(separator)
        chunks = []
        current = ""
        for part in parts:
            if len(current) + len(part) + len(separator) > MAX_LEN:
                if current:
                    chunks.append(current.rstrip())
                current = part
            else:
                if current:
                    current += separator + part
                else:
                    current = part
        if current:
            chunks.append(current.rstrip())

    try:
        await callback.message.edit_text(
            chunks[0],
            parse_mode="HTML",
            reply_markup=ikb.as_markup() if len(chunks) == 1 else None,
        )
        for idx, chunk in enumerate(chunks[1:], start=1):
            is_last = (idx == len(chunks) - 1)
            await callback.message.answer(
                chunk,
                parse_mode="HTML",
                reply_markup=ikb.as_markup() if is_last else None,
            )
    except TelegramBadRequest as e:
        logger.warning(f"edit_text failed: {e}")
        for idx, chunk in enumerate(chunks):
            is_last = (idx == len(chunks) - 1)
            try:
                await callback.message.answer(
                    chunk,
                    parse_mode="HTML",
                    reply_markup=ikb.as_markup() if is_last else None,
                )
            except Exception as send_err:
                logger.error(f"send chunk error: {send_err}")
    except Exception as e:
        logger.error(f"Error in show_words_handler: {e}")
        await callback.answer("❌ Xatolik yuz berdi.", show_alert=True)
        return

    await callback.answer()
