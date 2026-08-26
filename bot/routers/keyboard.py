import os
import json

from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)


# Main menu categories
BOOK_VOCABULARY_IN_USE = "📚 English Vocabulary in Use"
BOOK_ESSENTIAL_WORDS = "📖 4000 Essential English Words"
MAIN_MENU_BASKET = "🧺 Mening savatcham"
BTN_BACK_MAIN = "⬅️ Asosiy menyu"

VOCABULARY_IN_USE_LEVELS = [
    ("📘 Elementary", "elementary"),
    ("📘 Pre-intermediate & Intermediate", "preintermediateintermediate"),
    ("📘 Upper intermediate", "upperintermediate"),
    ("📘 Advanced", "advanced"),
]

ESSENTIAL_WORDS_LEVELS = [
    ("🔵 4000 Essential English Words 1", "4000essentialenglishwords1"),
    ("🔵 4000 Essential English Words 2", "4000essentialenglishwords2"),
    ("🔵 4000 Essential English Words 3", "4000essentialenglishwords3"),
    ("🔵 4000 Essential English Words 4", "4000essentialenglishwords4"),
    ("🔵 4000 Essential English Words 5", "4000essentialenglishwords5"),
    ("🔵 4000 Essential English Words 6", "4000essentialenglishwords6"),
]

LEVEL_DEFINITIONS = VOCABULARY_IN_USE_LEVELS + ESSENTIAL_WORDS_LEVELS


def get_available_levels(only_with_words: bool = False) -> list[tuple[str, str]]:
    """Kitoblar darajasini qaytaradi.
    Agar only_with_words=True bo'lsa, faqat so'zlari bor kitoblarni qaytaradi.
    Aks holda barcha kitoblar ro'yxatini qaytaradi.
    """
    if not only_with_words:
        return list(LEVEL_DEFINITIONS)
    result = []
    for title, code in LEVEL_DEFINITIONS:
        file_path = f"data/{code}.json"
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("units") and any(u.get("words") for u in data.get("units", [])):
                    result.append((title, code))
            except Exception:
                pass
    return result


async def main_menu_keyboard():
    """Bosh menyu: 2 ta kitob va Savatcha"""
    kb = ReplyKeyboardBuilder()
    kb.button(text=BOOK_VOCABULARY_IN_USE)
    kb.button(text=BOOK_ESSENTIAL_WORDS)
    kb.button(text=MAIN_MENU_BASKET)
    kb.adjust(1, 1, 1)
    return kb


async def vocabulary_in_use_keyboard():
    """English Vocabulary in Use kitoblari levellari"""
    kb = ReplyKeyboardBuilder()
    for title, _ in VOCABULARY_IN_USE_LEVELS:
        kb.button(text=title)
    kb.button(text=BTN_BACK_MAIN)
    kb.adjust(2, 2, 1)
    return kb


async def essential_words_keyboard():
    """4000 Essential English Words kitoblari levellari"""
    kb = ReplyKeyboardBuilder()
    for title, _ in ESSENTIAL_WORDS_LEVELS:
        kb.button(text=title)
    kb.button(text=BTN_BACK_MAIN)
    kb.adjust(2, 2, 2, 1)
    return kb


async def level_keyboard():
    """Default bosh menyu klaviaturasi"""
    return await main_menu_keyboard()


ALL_UNITS = [f"Unit {i}" for i in range(1, 61)]
ITEMS_PER_PAGE = 8


def get_available_units(level: str) -> list[str]:
    """Berilgan level uchun data faylidan mavjud unitlarni qaytaradi."""
    clean_level = "".join(filter(str.isalnum, level)).lower()
    file_path = f"data/{clean_level}.json"

    if not os.path.exists(file_path):
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        units = data.get("units", [])
        return [f"Unit {unit['unit']}" for unit in units if unit.get("words")]
    except (json.JSONDecodeError, KeyError):
        return []


async def get_page_data(page: int = 0, level: str | None = None):
    if level:
        units = get_available_units(level)
    else:
        units = ALL_UNITS

    if not units:
        return [], 0, 0

    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_data = units[start:end]
    total_pages = (len(units) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    return page_data, page, total_pages


async def create_units_keyboard(
    current_page: int,
    total_pages: int,
    units: list,
    *,
    select_prefix: str = "select_",
    page_prefix: str = "page_",
    extra_top_buttons: list | None = None,
    extra_bottom_buttons: list | None = None,
    btn_style: str = "primary",
    raw_number_payload: bool = False,
):
    keyboard = []

    if extra_top_buttons:
        keyboard.extend(extra_top_buttons)

    for i in range(0, len(units), 2):
        row = []
        val1 = units[i].replace("Unit ", "") if raw_number_payload else units[i]
        row.append(
            InlineKeyboardButton(
                text=units[i],
                callback_data=f"{select_prefix}{val1}",
                style=btn_style,
            )
        )
        if i + 1 < len(units):
            val2 = units[i + 1].replace("Unit ", "") if raw_number_payload else units[i + 1]
            row.append(
                InlineKeyboardButton(
                    text=units[i + 1],
                    callback_data=f"{select_prefix}{val2}",
                    style=btn_style,
                )
            )
        keyboard.append(row)

    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="◀️", callback_data=f"{page_prefix}{current_page - 1}"
            )
        )

    nav_buttons.append(
        InlineKeyboardButton(
            text=f"{current_page + 1}/{total_pages}", callback_data="current"
        )
    )
    if current_page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="▶️", callback_data=f"{page_prefix}{current_page + 1}"
            )
        )

    keyboard.append(nav_buttons)

    if extra_bottom_buttons:
        keyboard.extend(extra_bottom_buttons)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
