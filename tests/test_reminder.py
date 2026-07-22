import pytest

from bot.services.reminder_service import (
    calculate_next_reminder,
    format_interval,
    get_next_unit,
    parse_unit_number,
    split_long_text,
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
