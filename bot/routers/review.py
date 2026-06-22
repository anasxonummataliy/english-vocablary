import random

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from redis.asyncio import Redis

from bot.routers.get_words import get_unit_words

router = Router()


@router.callback_query(F.data.startswith("review_"))
async def review_handler(callback: CallbackQuery, redis: Redis):

    unit_id = int(callback.data.removeprefix("review_"))

    user_id = callback.from_user.id
    raw_level = await redis.get(f"user:{user_id}:level")

    if isinstance(raw_level, bytes):
        raw_level = raw_level.decode()

    if not raw_level:
        await callback.answer(
            "⚠️ Sessiya muddati tugagan. Qaytadan boshlang.", show_alert=True
        )
        return

    level = "".join(filter(str.isalnum, raw_level)).lower()

    words = await get_unit_words(level, unit_id)

    if not words:
        await callback.answer(
            "❌ Bu unit uchun so'zlar topilmadi. Boshqa unitni tanlang.",
            show_alert=True,
        )
        return

    word = random.choice(words)

    word_text = word.get("word", "")
    uzbek = word.get("uzbek", "")

    ikb = InlineKeyboardBuilder()

    ikb.row(
        InlineKeyboardButton(
            text="👀 Javob",
            callback_data=f"show_review_{unit_id}_{word_text}",
            style="success",
        )
    )

    try:
        await callback.message.edit_text(
            f"🇬🇧 <b>{word_text}</b>",
            parse_mode="HTML",
            reply_markup=ikb.as_markup(),
        )
    except TelegramBadRequest:
        pass

    await redis.set(
        f"review:{user_id}:{word_text}",
        uzbek,
    )

    await callback.answer()


@router.callback_query(F.data.startswith("show_review_"))
async def show_review_answer(callback: CallbackQuery, redis: Redis):

    data = callback.data.split("_")

    unit_id = data[2]
    word_text = "_".join(data[3:])  # so'z ichida _ bo'lishi mumkin

    user_id = callback.from_user.id

    uzbek = await redis.get(f"review:{user_id}:{word_text}")

    if isinstance(uzbek, bytes):
        uzbek = uzbek.decode()

    if not uzbek:
        await callback.answer("❌ Ma'lumot topilmadi.", show_alert=True)
        return

    ikb = InlineKeyboardBuilder()

    ikb.row(
        InlineKeyboardButton(
            text="➡️ Keyingi",
            callback_data=f"review_{unit_id}",
            style="primary",
        )
    )

    try:
        await callback.message.edit_text(
            f"🇬🇧 <b>{word_text}</b>\n\n" f"🇺🇿 <b>{uzbek}</b>",
            parse_mode="HTML",
            reply_markup=ikb.as_markup(),
        )
    except TelegramBadRequest:
        pass

    await callback.answer()
