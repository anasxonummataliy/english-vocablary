import pytest
from datetime import datetime, timedelta

from bot.database.models.reminders import Reminder
from bot.services.reminder_service import (
    calculate_next_reminder,
    build_reminder_text,
    format_interval,
    format_reminder_times,
    format_schedule,
    format_schedule_summary,
    format_user_time,
    format_weekdays,
    get_next_unit,
    parse_unit_number,
    parse_reminder_times,
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


def test_get_next_unit_returns_none_at_end():
    units = []
    from bot.routers.keyboard import get_available_units

    level = "📗 Elementary"
    available = get_available_units(level)
    last = parse_unit_number(available[-1])
    assert get_next_unit(level, last) is None


def test_calculate_next_reminder():
    from datetime import datetime, timedelta

    base = datetime(2026, 1, 1, 12, 0, 0)
    result = calculate_next_reminder(9, base)
    assert result == base + timedelta(hours=9)

    result = calculate_next_reminder(24, base)
    assert result == base + timedelta(hours=24)


def test_format_interval():
    assert format_interval(9) == "9 soat"
    assert format_interval(24) == "1 kun"


def test_parse_reminder_times():
    assert parse_reminder_times("16:21") == ["16:21"]
    assert parse_reminder_times("08:00, 16:30") == ["08:00", "16:30"]


def test_parse_reminder_times_rejects_bad_format():
    with pytest.raises(ValueError):
        parse_reminder_times("16-21")


def test_format_weekdays_and_times():
    assert format_weekdays([0, 2, 4]) == "Dushanba, Chorshanba, Juma"
    assert format_reminder_times(["08:00", "16:30"]) == "08:00, 16:30"


def test_build_reminder_text():
    text = build_reminder_text("📗 Elementary", 1)

    assert "📚 <b>Kitob:</b> 📗 Elementary" in text
    assert "✅ <b>Tanlangan:</b> Unit 1" in text
    assert text.endswith("Ushbu unit bo'yicha nima qilmoqchisiz?")


def test_format_user_time_uses_asia_tashkent_offset():
    from datetime import datetime

    utc_time = datetime(2026, 7, 22, 6, 16, 0)
    assert format_user_time(utc_time) == "22.07.2026 11:16"


def test_format_schedule_helpers():
    class DummyReminder:
        weekdays = "[0, 2, 4]"
        reminder_times = '["08:00", "16:30"]'

    text = format_schedule(DummyReminder())
    assert "Dushanba, Chorshanba, Juma" in text
    assert "08:00, 16:30" in text

    summary = format_schedule_summary([0, 2, 4], ["08:00", "16:30"])
    assert "Kunlar" in summary
    assert "Vaqtlar" in summary


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
