import logging
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from redis.asyncio import Redis
from sqlalchemy import select

from bot.database.models.reminders import Reminder
from bot.database.session import get_async_session_context
from bot.routers.get_words import format_words_text, get_unit_info, get_unit_words
from bot.routers.keyboard import get_available_units

logger = logging.getLogger(__name__)

INTERVAL_OPTIONS = {
    9: "9 soat",
    24: "1 kun",
}

LEVEL_OPTIONS = [
    "📗 Elementary",
    "📘 Pre-intermediate & Intermediate",
    "📙 Upper intermediate",
    "📕 Advanced",
]

MAX_MESSAGE_LEN = 4000
SETUP_TTL = 3600


def parse_unit_number(unit_label: str) -> int:
    return int(unit_label.replace("Unit", "").strip())


def get_next_unit(level: str, current_unit: int) -> int | None:
    units = get_available_units(level)
    if not units:
        return None

    unit_numbers = sorted(parse_unit_number(u) for u in units)
    for unit_num in unit_numbers:
        if unit_num > current_unit:
            return unit_num
    return None


def calculate_next_reminder(interval_hours: int, from_time: datetime | None = None) -> datetime:
    base = from_time or datetime.utcnow()
    return base + timedelta(hours=interval_hours)


def format_interval(interval_hours: int) -> str:
    return INTERVAL_OPTIONS.get(interval_hours, f"{interval_hours} soat")


def build_action_keyboard(unit_id: int) -> InlineKeyboardBuilder:
    unit_safe = f"Unit_{unit_id}"
    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(
            text="📖 So'zlarni o'rganish",
            callback_data=f"words_{unit_safe}",
            style="success",
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text="🃏 Flash card",
            callback_data=f"flash_{unit_safe}",
            style="success",
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text="📝 Test yechish",
            callback_data=f"test_{unit_safe}",
            style="primary",
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text="⏭ Keyingi unitga o'tish",
            callback_data=f"rem_skip_{unit_id}",
        )
    )
    return ikb


def split_long_text(text: str) -> list[str]:
    if len(text) <= MAX_MESSAGE_LEN:
        return [text]

    separator = f"\n{'─' * 18}\n\n"
    parts = text.split(separator)
    chunks: list[str] = []
    current = ""

    for part in parts:
        extra = len(separator) if current else 0
        if len(current) + len(part) + extra > MAX_MESSAGE_LEN:
            if current:
                chunks.append(current.rstrip())
            current = part
        elif current:
            current += separator + part
        else:
            current = part

    if current:
        chunks.append(current.rstrip())
    return chunks


async def send_unit_reminder(
    bot: Bot,
    chat_id: int,
    level: str,
    unit_id: int,
    redis: Redis,
    *,
    intro: str | None = None,
) -> bool:
    clean_level = "".join(filter(str.isalnum, level)).lower()
    unit_info = await get_unit_info(clean_level, unit_id)
    words = await get_unit_words(clean_level, unit_id)

    if not words or not unit_info:
        return False

    await redis.set(f"user:{chat_id}:level", level, ex=86400)

    intro_text = intro or (
        "⏰ <b>Eslatma!</b>\n"
        "Bugun navbatdagi unitni ishlang 👇\n\n"
    )
    text = intro_text + format_words_text(words, unit_id, unit_info, clean_level)
    chunks = split_long_text(text)
    keyboard = build_action_keyboard(unit_id).as_markup()

    await bot.send_message(
        chat_id,
        chunks[0],
        parse_mode="HTML",
        reply_markup=keyboard if len(chunks) == 1 else None,
    )
    for idx, chunk in enumerate(chunks[1:], start=1):
        is_last = idx == len(chunks) - 1
        await bot.send_message(
            chat_id,
            chunk,
            parse_mode="HTML",
            reply_markup=keyboard if is_last else None,
        )
    return True


async def get_user_reminder(tg_id: int) -> Reminder | None:
    async with get_async_session_context() as session:
        result = await session.execute(
            select(Reminder).where(Reminder.tg_id == tg_id)
        )
        return result.scalar_one_or_none()


async def save_reminder(
    tg_id: int,
    level: str,
    start_unit: int,
    interval_hours: int,
) -> Reminder:
    next_at = calculate_next_reminder(interval_hours)
    async with get_async_session_context() as session:
        result = await session.execute(
            select(Reminder).where(Reminder.tg_id == tg_id)
        )
        reminder = result.scalar_one_or_none()

        if reminder:
            reminder.level = level
            reminder.current_unit = start_unit
            reminder.interval_hours = interval_hours
            reminder.is_active = True
            reminder.next_reminder_at = next_at
            reminder.last_reminded_at = None
        else:
            reminder = Reminder(
                tg_id=tg_id,
                level=level,
                current_unit=start_unit,
                interval_hours=interval_hours,
                is_active=True,
                next_reminder_at=next_at,
            )
            session.add(reminder)

        await session.commit()
        await session.refresh(reminder)
        return reminder


async def disable_reminder(tg_id: int) -> bool:
    async with get_async_session_context() as session:
        result = await session.execute(
            select(Reminder).where(Reminder.tg_id == tg_id)
        )
        reminder = result.scalar_one_or_none()
        if not reminder:
            return False
        reminder.is_active = False
        await session.commit()
        return True


async def enable_reminder(tg_id: int) -> Reminder | None:
    async with get_async_session_context() as session:
        result = await session.execute(
            select(Reminder).where(Reminder.tg_id == tg_id)
        )
        reminder = result.scalar_one_or_none()
        if not reminder:
            return None
        reminder.is_active = True
        reminder.next_reminder_at = calculate_next_reminder(reminder.interval_hours)
        await session.commit()
        await session.refresh(reminder)
        return reminder


async def advance_reminder_unit(reminder: Reminder) -> Reminder:
    next_unit = get_next_unit(reminder.level, reminder.current_unit)
    async with get_async_session_context() as session:
        result = await session.execute(
            select(Reminder).where(Reminder.id == reminder.id)
        )
        db_reminder = result.scalar_one()

        if next_unit is None:
            db_reminder.is_active = False
        else:
            db_reminder.current_unit = next_unit
            db_reminder.next_reminder_at = calculate_next_reminder(
                db_reminder.interval_hours
            )

        db_reminder.last_reminded_at = datetime.utcnow()
        await session.commit()
        await session.refresh(db_reminder)
        return db_reminder


async def skip_to_next_unit(tg_id: int) -> tuple[bool, str]:
    async with get_async_session_context() as session:
        result = await session.execute(
            select(Reminder).where(Reminder.tg_id == tg_id)
        )
        reminder = result.scalar_one_or_none()
        if not reminder or not reminder.is_active:
            return False, "Eslatma topilmadi yoki o'chirilgan."

        next_unit = get_next_unit(reminder.level, reminder.current_unit)
        if next_unit is None:
            reminder.is_active = False
            await session.commit()
            return True, "🎉 Barcha unitlar tugadi! Eslatma o'chirildi."

        reminder.current_unit = next_unit
        reminder.next_reminder_at = calculate_next_reminder(reminder.interval_hours)
        await session.commit()
        return True, f"✅ Keyingi unit: <b>Unit {next_unit}</b>"
