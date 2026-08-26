import pytest

from bot.routers.keyboard import (
    ITEMS_PER_PAGE,
    create_units_keyboard,
    get_available_units,
    get_page_data,
)


def test_get_available_units_elementary():
    units = get_available_units("📘 Elementary")
    assert len(units) > 0
    assert units[0] == "Unit 1"
    assert all(u.startswith("Unit ") for u in units)


def test_get_available_units_preintermediate():
    units = get_available_units("📘 Pre-intermediate & Intermediate")
    assert len(units) > 0
    assert units[0] == "Unit 1"


def test_get_available_units_missing_level():
    units = get_available_units("📘 Upper intermediate")
    assert units == []


def test_get_available_units_essential_words():
    for book_num in range(1, 7):
        units = get_available_units(f"🔵 4000 Essential English Words {book_num}")
        assert len(units) == 30
        assert units[0] == "Unit 1"
        assert units[-1] == "Unit 30"


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


@pytest.mark.asyncio
async def test_main_menu_and_sub_keyboards():
    from bot.routers.keyboard import (
        main_menu_keyboard,
        vocabulary_in_use_keyboard,
        essential_words_keyboard,
        BOOK_VOCABULARY_IN_USE,
        BOOK_ESSENTIAL_WORDS,
        MAIN_MENU_BASKET,
        BTN_BACK_MAIN,
    )

    main_kb = await main_menu_keyboard()
    main_buttons = [btn.text for row in main_kb.export() for btn in row]
    assert BOOK_VOCABULARY_IN_USE in main_buttons
    assert BOOK_ESSENTIAL_WORDS in main_buttons
    assert MAIN_MENU_BASKET in main_buttons

    vocab_kb = await vocabulary_in_use_keyboard()
    vocab_buttons = [btn.text for row in vocab_kb.export() for btn in row]
    assert "📘 Elementary" in vocab_buttons
    assert "📘 Advanced" in vocab_buttons
    assert BTN_BACK_MAIN in vocab_buttons

    ess_kb = await essential_words_keyboard()
    ess_buttons = [btn.text for row in ess_kb.export() for btn in row]
    assert "🔵 4000 Essential English Words 1" in ess_buttons
    assert "🔵 4000 Essential English Words 6" in ess_buttons
    assert BTN_BACK_MAIN in ess_buttons
