import pytest

from bot.routers.keyboard import (
    ITEMS_PER_PAGE,
    create_units_keyboard,
    get_available_units,
    get_page_data,
)


def test_get_available_units_elementary():
    units = get_available_units("📗 Elementary")
    assert len(units) > 0
    assert units[0] == "Unit 1"
    assert all(u.startswith("Unit ") for u in units)


def test_get_available_units_preintermediate():
    units = get_available_units("📘 Pre-intermediate & Intermediate")
    assert len(units) > 0
    assert units[0] == "Unit 1"


def test_get_available_units_missing_level():
    units = get_available_units("📙 Upper intermediate")
    assert units == []


@pytest.mark.asyncio
async def test_get_page_data_first_page():
    page_data, current_page, total_pages = await get_page_data(
        0, "📗 Elementary"
    )
    assert current_page == 0
    assert total_pages >= 1
    assert len(page_data) <= ITEMS_PER_PAGE
    assert len(page_data) > 0


@pytest.mark.asyncio
async def test_get_page_data_empty_level():
    page_data, current_page, total_pages = await get_page_data(
        0, "📕 Advanced"
    )
    assert page_data == []
    assert current_page == 0
    assert total_pages == 0


@pytest.mark.asyncio
async def test_create_units_keyboard_structure():
    units = ["Unit 1", "Unit 2", "Unit 3"]
    keyboard = await create_units_keyboard(0, 1, units)

    assert len(keyboard.inline_keyboard) >= 2  # unitlar + navigatsiya
    nav_row = keyboard.inline_keyboard[-1]
    assert any(btn.callback_data == "current" for btn in nav_row)
