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


def format_words_text(words: list, unit_id: int, unit_info: dict, level: str, start_num: int = 1) -> str:
    level_display = level.capitalize()
    text = (
        f"📚 <b>{level_display} — Unit {unit_id}</b>\n"
        f"📌 <b>{html.escape(unit_info['title'])}</b>\n"
        f"<i>{html.escape(unit_info['topic'])}</i>\n\n"
        f"{'━' * 20}\n\n"
    )
    for i, word in enumerate(words, start=start_num):
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
        if i < start_num + len(words) - 1:
            text += f"\n{'─' * 18}\n\n"
    return text


@router.callback_query(F.data.startswith("words_"))
async def show_words_handler(callback: CallbackQuery, redis: Redis):
    raw_data = callback.data.removeprefix("words_").strip()
    print(
        f"[DEBUG words] callback.data={callback.data!r} raw_data={raw_data!r}",
        flush=True,
    )

    page = 1
    if "_page_" in raw_data:
        raw_data, page_str = raw_data.split("_page_", 1)
        try:
            page = int(page_str)
        except ValueError:
            page = 1

    try:
        import re
        unit_id_match = re.search(r'\d+', raw_data)
        if unit_id_match:
            unit_id = int(unit_id_match.group())
        else:
            raise ValueError
    except Exception:
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

    start_idx = (page - 1) * 7
    end_idx = page * 7
    preview_words = words[start_idx:end_idx]

    if not preview_words:
        await callback.answer("❌ Bu sahifada so'zlar yo'q.", show_alert=True)
        return

    text = format_words_text(preview_words, unit_id, unit_info, clean_level, start_num=start_idx + 1)
    
    page_total = (len(words) + 6) // 7
    text += f"\n📄 Sahifa: <b>{page}/{page_total}</b>\n"

    ikb = InlineKeyboardBuilder()
    
    # Pagination buttons row
    page_row = []
    if page > 1:
        page_row.append(
            InlineKeyboardButton(
                text="⬅️ Oldingisi",
                callback_data=f"words_Unit_{unit_id}_page_{page - 1}",
            )
        )
    if len(words) > page * 7:
        page_row.append(
            InlineKeyboardButton(
                text="Keyingisi ➡️",
                callback_data=f"words_Unit_{unit_id}_page_{page + 1}",
            )
        )
    if page_row:
        ikb.row(*page_row)

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

    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=ikb.as_markup(),
        )
    except TelegramBadRequest as e:
        logger.warning(f"edit_text failed: {e}")
        try:
            await callback.message.answer(
                text,
                parse_mode="HTML",
                reply_markup=ikb.as_markup(),
            )
        except Exception as send_err:
            logger.error(f"send error: {send_err}")
    except Exception as e:
        logger.error(f"Error in show_words_handler: {e}")
        await callback.answer("❌ Xatolik yuz berdi.", show_alert=True)
        return

    await callback.answer()
