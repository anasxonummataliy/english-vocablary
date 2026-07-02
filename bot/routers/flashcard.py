import random
import json

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from redis.asyncio import Redis

from bot.routers.get_words import get_unit_words

router = Router()


# ==================== FLASH CARD TUR TANLASH ====================
@router.callback_query(F.data.startswith("flash_"))
async def flash_mode_selection(callback: CallbackQuery):
    # unit_id "Unit 5" formatida keladi — bo'sh joyni _ bilan almashtiramiz
    unit_raw = callback.data.removeprefix("flash_")
    unit_safe = unit_raw.replace(" ", "_")  # "Unit 5" -> "Unit_5"

    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(
            text="🇺🇿 O'zbekcha → 🇬🇧 Inglizcha",
            callback_data=f"fmode_uz_en_{unit_safe}",
            style="success",
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text="🇬🇧 Inglizcha → 🇺🇿 O'zbekcha",
            callback_data=f"fmode_en_uz_{unit_safe}",
            style="success",
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text="📖 Ta'rif → 🇬🇧 Inglizcha",
            callback_data=f"fmode_desc_en_{unit_safe}",
            style="primary",
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text="⬅️ Orqaga",
            callback_data=f"select_{unit_raw}",
        )
    )

    try:
        await callback.message.edit_text(
            "🃏 <b>Flash card turini tanlang:</b>\n\n"
            "Bir tomonda savol — tugmani bossangiz javob ko'rinadi.",
            parse_mode="HTML",
            reply_markup=ikb.as_markup(),
        )
    except TelegramBadRequest:
        pass

    await callback.answer()


# ==================== FLASH CARD BOSHLASH ====================
@router.callback_query(F.data.startswith("fmode_"))
async def start_flashcard(callback: CallbackQuery, redis: Redis):
    data = callback.data  # fmode_uz_en_Unit 5 yoki fmode_desc_en_Unit 5
    raw = data.removeprefix("fmode_")

    # mode va unit_id ni ajratish
    # format: uz_en_Unit 5 | en_uz_Unit 5 | desc_en_Unit 5
    if raw.startswith("desc_en_"):
        mode = "desc_en"
        unit_id_str = raw.removeprefix("desc_en_").strip()
    elif raw.startswith("uz_en_"):
        mode = "uz_en"
        unit_id_str = raw.removeprefix("uz_en_").strip()
    elif raw.startswith("en_uz_"):
        mode = "en_uz"
        unit_id_str = raw.removeprefix("en_uz_").strip()
    else:
        await callback.answer("❌ Noto'g'ri format.", show_alert=True)
        return

    user_id = callback.from_user.id

    raw_level = await redis.get(f"user:{user_id}:level")
    if isinstance(raw_level, bytes):
        raw_level = raw_level.decode()

    if not raw_level:
        await callback.answer("⚠️ Sessiya muddati tugagan.", show_alert=True)
        return

    level = "".join(filter(str.isalnum, raw_level)).lower()

    try:
        unit_num = int(unit_id_str.replace("Unit", "").replace("_", "").strip())
    except ValueError:
        await callback.answer("❌ Unit raqamini aniqlashda xatolik.", show_alert=True)
        return

    words = await get_unit_words(level, unit_num)

    if not words:
        await callback.answer(
            "❌ Bu unit uchun so'zlar topilmadi.", show_alert=True
        )
        return

    # Shuffle va Redis ga saqlash
    random.shuffle(words)
    flash_state = {
        "mode": mode,
        "unit_id": unit_id_str,
        "words": words,
        "current_index": 0,
    }

    await redis.set(
        f"flash_state:{user_id}", json.dumps(flash_state), ex=3600
    )

    await show_flash_card(callback, flash_state, user_id)
    await callback.answer()


# ==================== FLASH CARD KO'RSATISH ====================
async def show_flash_card(callback: CallbackQuery, state: dict, user_id: int):
    idx = state["current_index"]
    total = len(state["words"])
    mode = state["mode"]
    word_data = state["words"][idx]

    # Old tomon (savol)
    if mode == "uz_en":
        question = f"🇺🇿 <b>{word_data['uzbek']}</b>"
        hint = "Inglizcha tarjimasini topishga harakat qiling"
    elif mode == "en_uz":
        question = f"🇬🇧 <b>{word_data['word']}</b>"
        hint = "O'zbekcha tarjimasini topishga harakat qiling"
    else:  # desc_en
        question = f"📖 <i>{word_data.get('description', '—')}</i>"
        hint = "Qaysi so'z ekanini topishga harakat qiling"

    text = (
        f"🃏 <b>Flash Card</b> [{idx + 1}/{total}]\n\n"
        f"{question}\n\n"
        f"<i>{hint}</i>"
    )

    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(
            text="👀 Javobni ko'rish",
            callback_data=f"fshow_{user_id}",
            style="success",
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text=f"⏭ O'tkazish ({idx + 1}/{total})",
            callback_data=f"fnext_{user_id}",
        ),
    )
    ikb.row(
        InlineKeyboardButton(
            text="🔚 Tugatish",
            callback_data=f"fend_{user_id}",
            style="danger",
        )
    )

    try:
        await callback.message.edit_text(
            text, parse_mode="HTML", reply_markup=ikb.as_markup()
        )
    except TelegramBadRequest:
        pass


# ==================== JAVOBNI KO'RSATISH ====================
@router.callback_query(F.data.startswith("fshow_"))
async def show_flash_answer(callback: CallbackQuery, redis: Redis):
    user_id = callback.from_user.id

    state_raw = await redis.get(f"flash_state:{user_id}")
    if not state_raw:
        await callback.answer("⚠️ Sessiya topilmadi.", show_alert=True)
        return

    if isinstance(state_raw, bytes):
        state_raw = state_raw.decode()

    state = json.loads(state_raw)
    idx = state["current_index"]
    total = len(state["words"])
    mode = state["mode"]
    word_data = state["words"][idx]

    # Javob
    word = word_data.get("word", "—")
    uzbek = word_data.get("uzbek", "—")
    transcription = word_data.get("transcription", "")
    description = word_data.get("description", "")
    example = word_data.get("example", "")

    if mode == "uz_en":
        answer_text = (
            f"🇺🇿 {uzbek}\n\n"
            f"✅ 🇬🇧 <b>{word}</b>  <code>{transcription}</code>\n"
            f"📖 {description}\n"
            f"✏️ <i>{example}</i>"
        )
    elif mode == "en_uz":
        answer_text = (
            f"🇬🇧 <b>{word}</b>  <code>{transcription}</code>\n\n"
            f"✅ 🇺🇿 <b>{uzbek}</b>\n"
            f"📖 {description}\n"
            f"✏️ <i>{example}</i>"
        )
    else:  # desc_en
        answer_text = (
            f"📖 <i>{description}</i>\n\n"
            f"✅ 🇬🇧 <b>{word}</b>  <code>{transcription}</code>\n"
            f"🇺🇿 {uzbek}\n"
            f"✏️ <i>{example}</i>"
        )

    text = f"🃏 <b>Flash Card</b> [{idx + 1}/{total}]\n\n{answer_text}"

    ikb = InlineKeyboardBuilder()

    if idx + 1 < total:
        ikb.row(
            InlineKeyboardButton(
                text="➡️ Keyingi",
                callback_data=f"fnext_{user_id}",
                style="primary",
            )
        )
    else:
        ikb.row(
            InlineKeyboardButton(
                text="🎉 Tugatish",
                callback_data=f"fend_{user_id}",
                style="success",
            )
        )

    ikb.row(
        InlineKeyboardButton(
            text="🔚 Tugatish",
            callback_data=f"fend_{user_id}",
            style="danger",
        )
    )

    try:
        await callback.message.edit_text(
            text, parse_mode="HTML", reply_markup=ikb.as_markup()
        )
    except TelegramBadRequest:
        pass

    await callback.answer()


# ==================== KEYINGI CARD ====================
@router.callback_query(F.data.startswith("fnext_"))
async def next_flash_card(callback: CallbackQuery, redis: Redis):
    user_id = callback.from_user.id

    state_raw = await redis.get(f"flash_state:{user_id}")
    if not state_raw:
        await callback.answer("⚠️ Sessiya topilmadi.", show_alert=True)
        return

    if isinstance(state_raw, bytes):
        state_raw = state_raw.decode()

    state = json.loads(state_raw)
    state["current_index"] += 1

    if state["current_index"] >= len(state["words"]):
        # Tugadi
        total = len(state["words"])
        unit_id = state["unit_id"]

        ikb = InlineKeyboardBuilder()
        ikb.row(
            InlineKeyboardButton(
                text="🔄 Qayta boshlash",
                callback_data=f"flash_{unit_id}",
                style="primary",
            )
        )
        ikb.row(
            InlineKeyboardButton(
                text="⬅️ Unitga qaytish",
                callback_data=f"select_{unit_id}",
            )
        )

        try:
            await callback.message.edit_text(
                f"🎉 <b>Flash card tugadi!</b>\n\n"
                f"📊 Jami: <b>{total} ta</b> so'z ko'rib chiqildi.\n\n"
                f"Davom etasizmi?",
                parse_mode="HTML",
                reply_markup=ikb.as_markup(),
            )
        except TelegramBadRequest:
            pass

        await redis.delete(f"flash_state:{user_id}")
        await callback.answer()
        return

    await redis.set(f"flash_state:{user_id}", json.dumps(state), ex=3600)
    await show_flash_card(callback, state, user_id)
    await callback.answer()


# ==================== TUGATISH ====================
@router.callback_query(F.data.startswith("fend_"))
async def end_flashcard(callback: CallbackQuery, redis: Redis):
    user_id = callback.from_user.id

    state_raw = await redis.get(f"flash_state:{user_id}")
    unit_id = "Unit 1"

    if state_raw:
        if isinstance(state_raw, bytes):
            state_raw = state_raw.decode()
        state = json.loads(state_raw)
        unit_id = state.get("unit_id", "Unit 1")
        await redis.delete(f"flash_state:{user_id}")

    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(
            text="⬅️ Unitga qaytish",
            callback_data=f"select_{unit_id}",
        )
    )

    try:
        await callback.message.edit_text(
            "✅ Flash card sessiyasi tugatildi.",
            parse_mode="HTML",
            reply_markup=ikb.as_markup(),
        )
    except TelegramBadRequest:
        pass

    await callback.answer()
