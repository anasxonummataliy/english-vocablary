import html
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from aiogram import Bot
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

LEVEL_OPTIONS = [
    "📗 Elementary",
    "📘 Pre-intermediate & Intermediate",
    "📙 Upper intermediate",
    "📕 Advanced",
    "📕 4000 Essential English Words 1",
    "📗 4000 Essential English Words 2",
    "📘 4000 Essential English Words 3",
    "📙 4000 Essential English Words 4",
    "📓 4000 Essential English Words 5",
    "📔 4000 Essential English Words 6",
]

WEEKDAY_LABELS = {
    0: "Dush",
    1: "Sesh",
    2: "Chor",
    3: "Pay",
    4: "Jum",
    5: "Shan",
    6: "Yak",
}

MAX_MESSAGE_LEN = 4000
SETUP_TTL = 3600


def parse_unit_number(unit_label: str) -> int:
    return int(unit_label.replace("Unit", "").strip())


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


def parse_weekdays_input(val: Any) -> list[int]:
    if isinstance(val, list):
        return sorted([int(x) for x in val if 0 <= int(x) <= 6])
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return []
        if val.startswith("["):
            try:
                parsed = json.loads(val)
                return sorted([int(x) for x in parsed if 0 <= int(x) <= 6])
            except Exception:
                pass
        return sorted(
            [
                int(x.strip())
                for x in val.split(",")
                if x.strip().isdigit() and 0 <= int(x.strip()) <= 6
            ]
        )
    return []


def parse_reminder_times(text: Any) -> list[str]:
    if not text:
        return []
    if isinstance(text, list):
        items = text
    elif isinstance(text, str):
        text = text.strip()
        if text.startswith("["):
            try:
                items = json.loads(text)
            except Exception:
                items = text.split(",")
        else:
            items = text.replace(";", ",").replace(" ", ",").split(",")
    else:
        return []

    valid_times = []
    for item in items:
        item_str = str(item).strip()
        if not item_str:
            continue
        parts = item_str.split(":")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            hh, mm = int(parts[0]), int(parts[1])
            if 0 <= hh <= 23 and 0 <= mm <= 59:
                valid_times.append(f"{hh:02d}:{mm:02d}")

    seen = set()
    result = []
    for t in valid_times:
        if t not in seen:
            seen.add(t)
            result.append(t)

    if not result and text:
        raise ValueError("Noto'g'ri vaqt formati")

    return result


def format_weekdays(weekdays: Any) -> str:
    parsed = parse_weekdays_input(weekdays)
    if not parsed:
        return "Har kuni"
    if len(parsed) == 7:
        return "Hamma kunlar"
    return ", ".join(WEEKDAY_LABELS[d] for d in parsed if d in WEEKDAY_LABELS)


def format_reminder_times(reminder_times: Any) -> str:
    parsed = parse_reminder_times(reminder_times)
    if not parsed:
        return "Vaqt belgilanmagan"
    return ", ".join(parsed)


def format_interval(interval_hours: int) -> str:
    return INTERVAL_OPTIONS.get(interval_hours, f"{interval_hours} soat")


def format_schedule_summary(
    selected_days: Any = None,
    reminder_times: Any = None,
    interval_hours: int | None = None,
) -> str:
    days_list = parse_weekdays_input(selected_days)
    times_list = parse_reminder_times(reminder_times)

    if days_list and times_list:
        return (
            f"📅 Kunlar: <b>{format_weekdays(days_list)}</b>\n"
            f"🕐 Vaqtlar: <b>{format_reminder_times(times_list)}</b>"
        )
    elif interval_hours and interval_hours > 0 and not times_list:
        return f"🕐 Interval: <b>{format_interval(interval_hours)}</b>"
    elif times_list:
        return (
            f"📅 Kunlar: <b>{format_weekdays(days_list)}</b>\n"
            f"🕐 Vaqtlar: <b>{format_reminder_times(times_list)}</b>"
        )
    return "🕐 Sozlama: Belgilanmagan"


def format_schedule(reminder: Reminder) -> str:
    days_list = parse_weekdays_input(reminder.weekdays)
    times_list = parse_reminder_times(reminder.reminder_times)
    if days_list and times_list:
        return format_schedule_summary(days_list, times_list)
    return f"🕐 Interval: <b>{format_interval(reminder.interval_hours or 24)}</b>"


def calculate_next_reminder(
    interval_hours: int = 24,
    weekdays: Any = None,
    reminder_times: Any = None,
    from_time: datetime | None = None,
) -> datetime:
    base_utc = from_time or datetime.utcnow()
    if base_utc.tzinfo is None:
        base_utc = base_utc.replace(tzinfo=timezone.utc)

    days_list = parse_weekdays_input(weekdays)
    times_list = parse_reminder_times(reminder_times)

    if days_list and times_list:
        tz_tashkent = timezone(timedelta(hours=5))
        base_local = base_utc.astimezone(tz_tashkent)

        candidates = []
        parsed_times = []
        for t_str in times_list:
            hh, mm = map(int, t_str.split(":"))
            parsed_times.append((hh, mm))

        for day_offset in range(15):
            candidate_date = base_local.date() + timedelta(days=day_offset)
            candidate_weekday = candidate_date.weekday()
            if candidate_weekday in days_list:
                for hh, mm in parsed_times:
                    cand_dt = datetime(
                        candidate_date.year,
                        candidate_date.month,
                        candidate_date.day,
                        hh,
                        mm,
                        0,
                        tzinfo=tz_tashkent,
                    )
                    if cand_dt > base_local:
                        candidates.append(cand_dt)

        if candidates:
            next_local = min(candidates)
            next_utc = next_local.astimezone(timezone.utc)
            return next_utc.replace(tzinfo=None)

    eff_interval = interval_hours if interval_hours > 0 else 24
    res = base_utc + timedelta(hours=eff_interval)
    return res.replace(tzinfo=None)


def format_user_time(value: datetime) -> str:
    tz = timezone(timedelta(hours=5))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(tz).strftime("%d.%m.%Y %H:%M")


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
            style="primary",
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text="🃏 Flash card",
            callback_data=f"flash_{unit_safe}",
            style="primary",
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
            style="success",
        ),
        InlineKeyboardButton(
            text="📕 Unitlar ro'yxatiga qaytish",
            callback_data="back_to_units",
            style="danger",
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
    await redis.set(f"user:{chat_id}:level", level, ex=86400)

    intro_text = intro or "⏰ <b>Eslatma!</b>\n\n"
    text = intro_text + build_reminder_text(level, unit_id)
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


async def postpone_reminder(tg_id: int) -> Reminder | None:
    now = datetime.utcnow()
    async with get_async_session_context() as session:
        result = await session.execute(select(Reminder).where(Reminder.tg_id == tg_id))
        reminder = result.scalar_one_or_none()
        if not reminder:
            return None

        reminder.next_reminder_at = calculate_next_reminder(
            interval_hours=reminder.interval_hours or 24,
            weekdays=reminder.weekdays,
            reminder_times=reminder.reminder_times,
            from_time=now,
        )
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
    interval_hours: int = 24,
    weekdays: list[int] | str | None = None,
    reminder_times: list[str] | str | None = None,
) -> Reminder:
    days_json = (
        json.dumps(parse_weekdays_input(weekdays))
        if weekdays is not None
        else None
    )
    times_json = (
        json.dumps(parse_reminder_times(reminder_times))
        if reminder_times
        else None
    )

    next_at = calculate_next_reminder(
        interval_hours=interval_hours,
        weekdays=weekdays,
        reminder_times=reminder_times,
    )

    async with get_async_session_context() as session:
        result = await session.execute(select(Reminder).where(Reminder.tg_id == tg_id))
        reminder = result.scalar_one_or_none()

        if reminder:
            reminder.level = level
            reminder.current_unit = start_unit
            reminder.interval_hours = interval_hours
            reminder.weekdays = days_json
            reminder.reminder_times = times_json
            reminder.is_active = True
            reminder.next_reminder_at = next_at
            reminder.last_reminded_at = None
        else:
            reminder = Reminder(
                tg_id=tg_id,
                level=level,
                current_unit=start_unit,
                interval_hours=interval_hours,
                weekdays=days_json,
                reminder_times=times_json,
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
        reminder.next_reminder_at = calculate_next_reminder(
            interval_hours=reminder.interval_hours or 24,
            weekdays=reminder.weekdays,
            reminder_times=reminder.reminder_times,
        )
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
                interval_hours=db_reminder.interval_hours or 24,
                weekdays=db_reminder.weekdays,
                reminder_times=db_reminder.reminder_times,
            )

        db_reminder.last_reminded_at = datetime.utcnow()
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

        next_unit = get_next_unit(reminder.level, reminder.current_unit)
        if next_unit is None:
            reminder.is_active = False
        else:
            reminder.current_unit = next_unit
            reminder.next_reminder_at = calculate_next_reminder(
                interval_hours=reminder.interval_hours or 24,
                weekdays=reminder.weekdays,
                reminder_times=reminder.reminder_times,
                from_time=now,
            )

        reminder.last_reminded_at = now
        await session.commit()
        await session.refresh(reminder)
        return reminder


async def skip_to_next_unit(tg_id: int) -> tuple[bool, str]:
    async with get_async_session_context() as session:
        result = await session.execute(select(Reminder).where(Reminder.tg_id == tg_id))
        reminder = result.scalar_one_or_none()
        if not reminder or not reminder.is_active:
            return False, "Eslatma topilmadi yoki o'chirilgan."

        next_unit = get_next_unit(reminder.level, reminder.current_unit)
        if next_unit is None:
            reminder.is_active = False
            await session.commit()
            return True, "🎉 Barcha unitlar tugadi! Eslatma o'chirildi."

        reminder.current_unit = next_unit
        reminder.next_reminder_at = calculate_next_reminder(
            interval_hours=reminder.interval_hours or 24,
            weekdays=reminder.weekdays,
            reminder_times=reminder.reminder_times,
        )
        await session.commit()
        return True, f"✅ Keyingi unit: <b>Unit {next_unit}</b>"


async def advance_reminder_for_unit(tg_id: int, unit_id: int) -> Reminder | None:
    now = datetime.utcnow()
    async with get_async_session_context() as session:
        result = await session.execute(select(Reminder).where(Reminder.tg_id == tg_id))
        reminder = result.scalar_one_or_none()
        if not reminder or not reminder.is_active:
            return None

        if reminder.current_unit != unit_id:
            return None

        next_unit = get_next_unit(reminder.level, reminder.current_unit)
        if next_unit is None:
            reminder.is_active = False
        else:
            reminder.current_unit = next_unit
            reminder.next_reminder_at = calculate_next_reminder(
                interval_hours=reminder.interval_hours or 24,
                weekdays=reminder.weekdays,
                reminder_times=reminder.reminder_times,
                from_time=now,
            )

        reminder.last_reminded_at = now
        await session.commit()
        await session.refresh(reminder)
        return reminder

