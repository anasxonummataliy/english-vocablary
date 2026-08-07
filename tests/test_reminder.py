import pytest
from datetime import datetime, timedelta, timezone

from bot.database.models.reminders import Reminder
from bot.services.reminder_service import (
    calculate_next_reminder,
    build_reminder_text,
    format_interval,
    format_user_time,
    format_weekdays,
    format_reminder_times,
    format_schedule_summary,
    get_next_unit,
    parse_unit_number,
    parse_reminder_times,
    parse_weekdays_input,
    split_long_text,
    should_auto_advance_reminder,
)


def test_parse_unit_number():
    assert parse_unit_number("Unit 5") == 5
    assert parse_unit_number("Unit 12") == 12


def test_get_next_unit():
    next_unit = get_next_unit("📗 Elementary", 1)
    assert next_unit == 2

    next_unit = get_next_unit("📗 Elementary", 2)
    assert next_unit == 3


def test_parse_reminder_times():
    assert parse_reminder_times("16:21") == ["16:21"]
    assert parse_reminder_times("08:00, 16:30") == ["08:00", "16:30"]
    assert parse_reminder_times("08:00; 16:30 21:15") == ["08:00", "16:30", "21:15"]
    with pytest.raises(ValueError):
        parse_reminder_times("invalid_time")


def test_parse_weekdays_input():
    assert parse_weekdays_input([0, 2, 4]) == [0, 2, 4]
    assert parse_weekdays_input("[0, 1, 3]") == [0, 1, 3]
    assert parse_weekdays_input("0, 2, 4") == [0, 2, 4]


def test_format_weekdays():
    assert format_weekdays([0, 2, 4]) == "Dush, Chor, Jum"
    assert format_weekdays([0, 1, 2, 3, 4, 5, 6]) == "Hamma kunlar"


def test_calculate_next_reminder_interval():
    base = datetime(2026, 1, 1, 12, 0, 0)
    result = calculate_next_reminder(9, from_time=base)
    assert result == base + timedelta(hours=9)

    result = calculate_next_reminder(24, from_time=base)
    assert result == base + timedelta(hours=24)


def test_calculate_next_reminder_schedule_multiple_times():
    # Thursday 2026-01-01 04:00 UTC = 09:00 Tashkent (UTC+5)
    base_utc = datetime(2026, 1, 1, 4, 0, 0)
    # Weekdays: Thursday (3). Times: 12:00, 16:00 (Tashkent time)
    # Target in Tashkent today: 12:00 (7:00 UTC)
    next_at = calculate_next_reminder(
        interval_hours=0,
        weekdays=[3],
        reminder_times=["12:00", "16:00"],
        from_time=base_utc,
    )
    assert next_at == datetime(2026, 1, 1, 7, 0, 0)


def test_format_interval():
    assert format_interval(9) == "9 soat"
    assert format_interval(24) == "1 kun"


def test_build_reminder_text():
    text = build_reminder_text("📗 Elementary", 1)

    assert "📚 <b>Kitob:</b> 📗 Elementary" in text
    assert "✅ <b>Tanlangan:</b> Unit 1" in text
    assert text.endswith("Ushbu unit bo'yicha nima qilmoqchisiz?")


def test_format_user_time_uses_asia_tashkent_offset():
    utc_time = datetime(2026, 7, 22, 6, 16, 0)
    assert format_user_time(utc_time) == "22.07.2026 11:16"


def test_split_long_text_short():
    text = "hello world"
    assert split_long_text(text) == ["hello world"]


def test_split_long_text_splits_on_separator():
    separator = f"\n{'─' * 18}\n\n"
    part_a = "A" * 2000
    part_b = "B" * 2000
    text = part_a + separator + part_b
    chunks = split_long_text(text)
    assert len(chunks) >= 2


def test_should_auto_advance_reminder_allows_first_activity_after_reminder():
    reminder = Reminder(
        tg_id=123,
        level="📗 Elementary",
        current_unit=1,
        interval_hours=9,
        is_active=True,
        next_reminder_at=datetime(2026, 1, 1, 12, 0, 0),
        last_reminded_at=datetime(2026, 1, 1, 11, 0, 0),
    )

    assert should_auto_advance_reminder(reminder, None) is True


def test_should_auto_advance_reminder_blocks_repeated_activity():
    reminder = Reminder(
        tg_id=123,
        level="📗 Elementary",
        current_unit=1,
        interval_hours=9,
        is_active=True,
        next_reminder_at=datetime(2026, 1, 1, 12, 0, 0),
        last_reminded_at=datetime(2026, 1, 1, 11, 0, 0),
    )

    previous_last_activity = datetime(2026, 1, 1, 11, 5, 0)

    assert should_auto_advance_reminder(reminder, previous_last_activity) is False
