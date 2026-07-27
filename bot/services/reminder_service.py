import json
import html
import logging
import re
import asyncio
from datetime import datetime, timedelta, timezone, time

from aiogram import Bot
from aiogram.exceptions import (
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from redis.asyncio import Redis
from sqlalchemy import select

from bot.database.models.reminders import Reminder
from bot.database.session import get_async_session_context

logger = logging.getLogger(__name__)

INTERVAL_OPTIONS = {
    hour: "1 kun" if hour == 24 else f"{hour} soat" for hour in range(1, 25)
}

WEEKDAY_OPTIONS = [
    (0, "Dushanba"),
    (1, "Seshanba"),
    (2, "Chorshanba"),
    (3, "Payshanba"),
    (4, "Juma"),
    (5, "Shanba"),
    (6, "Yakshanba"),
]

WEEKDAY_LABELS = {index: label for index, label in WEEKDAY_OPTIONS}
LOCAL_TIMEZONE = timezone(timedelta(hours=5))
TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")

LEVEL_OPTIONS = [
    "📗 Elementary",
    "📘 Pre-intermediate & Intermediate",
    "📙 Upper intermediate",
    "📕 Advanced",
]

MAX_MESSAGE_LEN = 4000
SETUP_TTL = 3600
SEND_RETRY_ATTEMPTS = 4
SEND_RETRY_BASE_DELAY = 2
SEND_REQUEST_TIMEOUT = 10


def parse_unit_number(unit_label: str) -> int:
    return int(unit_label.replace("Unit", "").strip())


def dump_schedule_values(values: list) -> str:
    return json.dumps(values, ensure_ascii=False)


def load_schedule_values(raw: str | None) -> list:
    if not raw:
        return []
    if isinstance(raw, bytes):
        raw = raw.decode()
    try:
        values = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return values if isinstance(values, list) else []


def parse_reminder_times(raw_text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"[,;\n]+", raw_text) if part.strip()]
    if not parts:
        raise ValueError("Vaqt kiritilmadi.")

    normalized: list[str] = []
    for part in parts:
        if not TIME_PATTERN.fullmatch(part):
            raise ValueError(f"Noto'g'ri vaqt formati: {part}")
        if part not in normalized:
            normalized.append(part)
    return normalized


def format_weekdays(values: list[int] | None) -> str:
    if not values:
        return "Tanlanmagan"
    ordered = [
        WEEKDAY_LABELS[index]
        for index in sorted(set(values))
        if index in WEEKDAY_LABELS
    ]
    return ", ".join(ordered) if ordered else "Tanlanmagan"


def format_reminder_times(values: list[str] | None) -> str:
    if not values:
        return "Tanlanmagan"
    return ", ".join(values)


def _to_local_time(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(LOCAL_TIMEZONE)


def _to_utc_naive(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def calculate_next_scheduled_reminder(
    weekdays: list[int], reminder_times: list[str], from_time: datetime | None = None
) -> datetime:
    local_now = _to_local_time(from_time or datetime.utcnow())
    normalized_days = sorted({day for day in weekdays if 0 <= day <= 6})
    normalized_times = sorted(
        {
            time_value
            for time_value in reminder_times
            if TIME_PATTERN.fullmatch(time_value)
        },
        key=lambda value: (int(value[:2]), int(value[3:])),
    )

    if not normalized_days or not normalized_times:
        return calculate_next_reminder(24, from_time)

    for day_offset in range(0, 15):
        candidate_date = local_now.date() + timedelta(days=day_offset)
        if candidate_date.weekday() not in normalized_days:
            continue

        for time_value in normalized_times:
            hour, minute = map(int, time_value.split(":"))
            candidate_local = datetime.combine(
                candidate_date,
                time(hour=hour, minute=minute, tzinfo=LOCAL_TIMEZONE),
            )
            if candidate_local > local_now:
                return _to_utc_naive(candidate_local)

    first_day = normalized_days[0]
    first_time = normalized_times[0]
    hour, minute = map(int, first_time.split(":"))
    days_ahead = (first_day - local_now.date().weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    candidate_date = local_now.date() + timedelta(days=days_ahead)
    candidate_local = datetime.combine(
        candidate_date,
        time(hour=hour, minute=minute, tzinfo=LOCAL_TIMEZONE),
    )
    return _to_utc_naive(candidate_local)


def calculate_next_reminder_time(
    reminder, from_time: datetime | None = None
) -> datetime:
    weekdays = [int(day) for day in load_schedule_values(reminder.weekdays)]
    reminder_times = [
        str(value) for value in load_schedule_values(reminder.reminder_times)
    ]
    if weekdays and reminder_times:
        return calculate_next_scheduled_reminder(weekdays, reminder_times, from_time)
    return calculate_next_reminder(reminder.interval_hours, from_time)


def _advance_reminder_state(
    reminder: Reminder, *, now: datetime | None = None
) -> int | None:
    next_unit = get_next_unit(reminder.level, reminder.current_unit)
    current_time = now or datetime.utcnow()

    reminder.last_reminded_at = current_time
    if next_unit is None:
        reminder.is_active = False
        return None

    reminder.current_unit = next_unit
    reminder.next_reminder_at = calculate_next_reminder_time(reminder, current_time)
    return next_unit


def get_next_unit(level: str, current_unit: int) -> int | None:
    from bot.routers.keyboard import get_available_units

    units = get_available_units(level)
    if not units:
        return None

    unit_numbers = sorted(parse_unit_number(u) for u in units)
    for unit_num in unit_numbers:
        if unit_num > current_unit:
            return unit_num
    return None


def calculate_next_reminder(
    interval_hours: int, from_time: datetime | None = None
) -> datetime:
    base = from_time or datetime.utcnow()
    return base + timedelta(hours=interval_hours)


def format_interval(interval_hours: int) -> str:
    return INTERVAL_OPTIONS.get(interval_hours, f"{interval_hours} soat")


def format_user_time(value: datetime) -> str:
    tz = timezone(timedelta(hours=5))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(tz).strftime("%d.%m.%Y %H:%M")


def format_schedule(reminder) -> str:
    weekdays = load_schedule_values(reminder.weekdays)
    reminder_times = load_schedule_values(reminder.reminder_times)
    days_text = format_weekdays([int(day) for day in weekdays])
    times_text = format_reminder_times([str(value) for value in reminder_times])
    return f"📅 Kunlar: <b>{days_text}</b>\n🕐 Vaqtlar: <b>{times_text}</b>"


def format_schedule_summary(weekdays: list[int], reminder_times: list[str]) -> str:
    days_text = format_weekdays(weekdays)
    times_text = format_reminder_times(reminder_times)
    return f"📅 Kunlar: <b>{days_text}</b>\n🕐 Vaqtlar: <b>{times_text}</b>"


def build_reminder_text(level: str, unit_id: int) -> str:
    return (
        f"📚 <b>Kitob:</b> {html.escape(level)}\n"
        f"✅ <b>Tanlangan:</b> Unit {unit_id}\n\n"
        "Ushbu unit bo'yicha nima qilmoqchisiz?"
    )


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
            text="✅ Bajarildi",
            callback_data=f"rem_skip_{unit_id}",
        ),
        InlineKeyboardButton(
            text="📕 Unitlar ro'yxatiga qaytish",
            callback_data="back_to_units",
        ),
    )
    return ikb


def should_auto_advance_reminder(
    reminder: Reminder,
    previous_last_activity: datetime | None,
) -> bool:
    if not reminder.is_active or reminder.last_reminded_at is None:
        return False

    if previous_last_activity is None:
        return True

    return previous_last_activity < reminder.last_reminded_at


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
    async def _send_message_with_retry(*, text_chunk: str, reply_markup=None) -> bool:
        for attempt in range(1, SEND_RETRY_ATTEMPTS + 1):
            try:
                await bot.send_message(
                    chat_id,
                    text_chunk,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                    request_timeout=SEND_REQUEST_TIMEOUT,
                )
                return True
            except TelegramRetryAfter as exc:
                delay = max(int(exc.retry_after), 1)
                logger.warning(
                    "Reminder send rate-limited: user=%s urinish=%s/%s kutish=%ss",
                    chat_id,
                    attempt,
                    SEND_RETRY_ATTEMPTS,
                    delay,
                )
            except (TelegramServerError, TelegramNetworkError) as exc:
                delay = min(SEND_RETRY_BASE_DELAY * attempt, 10)
                logger.warning(
                    "Reminder send vaqtinchalik xatolik: user=%s urinish=%s/%s xato=%s kutish=%ss",
                    chat_id,
                    attempt,
                    SEND_RETRY_ATTEMPTS,
                    exc,
                    delay,
                )
            except Exception as exc:
                logger.warning(
                    "Reminder send yakuniy xatolik: user=%s xato=%s",
                    chat_id,
                    exc,
                )
                return False

            if attempt < SEND_RETRY_ATTEMPTS:
                await asyncio.sleep(delay)

        logger.error("Reminder yuborilmadi: user=%s barcha urinish tugadi", chat_id)
        return False

    await redis.set(f"user:{chat_id}:level", level, ex=86400)

    intro_text = intro or "⏰ <b>Eslatma!</b>\n\n"
    text = intro_text + build_reminder_text(level, unit_id)
    chunks = split_long_text(text)
    keyboard = build_action_keyboard(unit_id).as_markup()

    first_sent = await _send_message_with_retry(
        text_chunk=chunks[0],
        reply_markup=keyboard if len(chunks) == 1 else None,
    )
    if not first_sent:
        return False

    for idx, chunk in enumerate(chunks[1:], start=1):
        is_last = idx == len(chunks) - 1
        chunk_sent = await _send_message_with_retry(
            text_chunk=chunk,
            reply_markup=keyboard if is_last else None,
        )
        if not chunk_sent:
            return False

    return True


async def postpone_reminder(tg_id: int) -> Reminder | None:
    now = datetime.utcnow()
    async with get_async_session_context() as session:
        result = await session.execute(select(Reminder).where(Reminder.tg_id == tg_id))
        reminder = result.scalar_one_or_none()
        if not reminder:
            return None

        reminder.next_reminder_at = calculate_next_reminder_time(reminder, now)
        reminder.last_reminded_at = now
        await session.commit()
        await session.refresh(reminder)
        return reminder


async def get_user_reminder(tg_id: int) -> Reminder | None:
    async with get_async_session_context() as session:
        result = await session.execute(select(Reminder).where(Reminder.tg_id == tg_id))
        return result.scalar_one_or_none()


async def save_reminder(
    tg_id: int,
    level: str,
    start_unit: int,
    interval_hours: int,
    *,
    weekdays: list[int] | None = None,
    reminder_times: list[str] | None = None,
) -> Reminder:
    next_at = (
        calculate_next_scheduled_reminder(weekdays or [], reminder_times or [])
        if weekdays and reminder_times
        else calculate_next_reminder(interval_hours)
    )
    async with get_async_session_context() as session:
        result = await session.execute(select(Reminder).where(Reminder.tg_id == tg_id))
        reminder = result.scalar_one_or_none()

        if reminder:
            reminder.level = level
            reminder.current_unit = start_unit
            reminder.interval_hours = interval_hours
            reminder.weekdays = (
                dump_schedule_values(weekdays or []) if weekdays else None
            )
            reminder.reminder_times = (
                dump_schedule_values(reminder_times or []) if reminder_times else None
            )
            reminder.is_active = True
            reminder.next_reminder_at = next_at
            reminder.last_reminded_at = None
        else:
            reminder = Reminder(
                tg_id=tg_id,
                level=level,
                current_unit=start_unit,
                interval_hours=interval_hours,
                weekdays=dump_schedule_values(weekdays or []) if weekdays else None,
                reminder_times=(
                    dump_schedule_values(reminder_times or [])
                    if reminder_times
                    else None
                ),
                is_active=True,
                next_reminder_at=next_at,
            )
            session.add(reminder)

        await session.commit()
        await session.refresh(reminder)
        return reminder


async def disable_reminder(tg_id: int) -> bool:
    async with get_async_session_context() as session:
        result = await session.execute(select(Reminder).where(Reminder.tg_id == tg_id))
        reminder = result.scalar_one_or_none()
        if not reminder:
            return False
        reminder.is_active = False
        await session.commit()
        return True


async def enable_reminder(tg_id: int) -> Reminder | None:
    async with get_async_session_context() as session:
        result = await session.execute(select(Reminder).where(Reminder.tg_id == tg_id))
        reminder = result.scalar_one_or_none()
        if not reminder:
            return None
        reminder.is_active = True
        reminder.next_reminder_at = calculate_next_reminder_time(reminder)
        await session.commit()
        await session.refresh(reminder)
        return reminder


async def advance_reminder_unit(reminder: Reminder) -> Reminder:
    async with get_async_session_context() as session:
        result = await session.execute(
            select(Reminder).where(Reminder.id == reminder.id)
        )
        db_reminder = result.scalar_one()

        _advance_reminder_state(db_reminder)
        await session.commit()
        await session.refresh(db_reminder)
        return db_reminder


async def auto_advance_reminder_on_activity(
    tg_id: int,
    previous_last_activity: datetime | None,
    *,
    activity_at: datetime | None = None,
) -> Reminder | None:
    now = activity_at or datetime.utcnow()
    async with get_async_session_context() as session:
        result = await session.execute(select(Reminder).where(Reminder.tg_id == tg_id))
        reminder = result.scalar_one_or_none()
        if not reminder or not should_auto_advance_reminder(
            reminder, previous_last_activity
        ):
            return None

        _advance_reminder_state(reminder, now=now)
        await session.commit()
        await session.refresh(reminder)
        return reminder


async def skip_to_next_unit(tg_id: int) -> tuple[bool, str]:
    async with get_async_session_context() as session:
        result = await session.execute(select(Reminder).where(Reminder.tg_id == tg_id))
        reminder = result.scalar_one_or_none()
        if not reminder or not reminder.is_active:
            return False, "Eslatma topilmadi yoki o'chirilgan."

        next_unit = _advance_reminder_state(reminder)
        if next_unit is None:
            await session.commit()
            return True, "🎉 Barcha mavjud unitlar tugadi. Eslatma o'chirildi."

        await session.commit()
        return (
            True,
            f"✅ Keyingi unit: <b>Unit {next_unit}</b>\n"
            f"🕐 Keyingi eslatma: <b>{format_user_time(reminder.next_reminder_at)}</b>",
        )
