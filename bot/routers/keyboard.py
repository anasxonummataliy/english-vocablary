import os
import json

from aiogram.enums import ButtonStyle
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import (
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)


# Main menu categories
BOOK_VOCABULARY_IN_USE = "📘 English Vocabulary in Use"
BOOK_ESSENTIAL_WORDS = "📗 4000 Essential English Words"
MAIN_MENU_BASKET = "🧺 Mening savatcham"
BTN_BACK_MAIN = "🏠 Asosiy menyu"

VOCABULARY_IN_USE_LEVELS = [
    ("📗 Elementary", "elementary"),
    ("📘 Pre-intermediate & Intermediate", "preintermediateintermediate"),
    ("📙 Upper intermediate", "upperintermediate"),
    ("📕 Advanced", "advanced"),
]

ESSENTIAL_WORDS_LEVELS = [
    ("📗 Essential Words 1", "4000essentialenglishwords1"),
    ("📘 Essential Words 2", "4000essentialenglishwords2"),
    ("📙 Essential Words 3", "4000essentialenglishwords3"),
    ("📕 Essential Words 4", "4000essentialenglishwords4"),
    ("📔 Essential Words 5", "4000essentialenglishwords5"),
    ("📓 Essential Words 6", "4000essentialenglishwords6"),
]

LEVEL_DEFINITIONS = VOCABULARY_IN_USE_LEVELS + ESSENTIAL_WORDS_LEVELS


def normalize_level_code(level: str) -> str:
    """Level nomidan data fayli nomini aniqlaydi."""
    clean = "".join(filter(str.isalnum, level)).lower()
    if clean.startswith("essentialwords"):
        suffix = clean.replace("essentialwords", "")
        return f"4000essentialenglishwords{suffix}"
    if clean.startswith("essentialenglishwords"):
        suffix = clean.replace("essentialenglishwords", "")
        return f"4000essentialenglishwords{suffix}"
    if clean == "preintermediate":
        return "preintermediateintermediate"
    return clean


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
    """Bosh menyu: 2 ta kitob (PRIMARY) va Savatcha (SUCCESS)"""
    kb = ReplyKeyboardBuilder()
    kb.button(text=BOOK_VOCABULARY_IN_USE, style=ButtonStyle.PRIMARY)
    kb.button(text=BOOK_ESSENTIAL_WORDS, style=ButtonStyle.PRIMARY)
    kb.button(text=MAIN_MENU_BASKET, style=ButtonStyle.SUCCESS)
    kb.adjust(2, 1)
    return kb


async def main_menu_inline_keyboard() -> InlineKeyboardMarkup:
    """Bosh menyu: 2 ta kitob (ko'k) va Savatcha (yashil)"""
    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(
            text=BOOK_VOCABULARY_IN_USE,
            callback_data="menu_vocab_in_use",
            style="primary",
        ),
        InlineKeyboardButton(
            text="🔵 Essential Words",
            callback_data="menu_essential_words",
            style="primary",
        ),
    )
    ikb.row(
        InlineKeyboardButton(
            text=MAIN_MENU_BASKET,
            callback_data="baskets_list",
            style="success",
        )
    )
    return ikb.as_markup()


async def vocabulary_in_use_keyboard():
    """English Vocabulary in Use kitoblari levellari (PRIMARY) va Asosiy menyu (DANGER)"""
    kb = ReplyKeyboardBuilder()
    for title, _ in VOCABULARY_IN_USE_LEVELS:
        kb.button(text=title, style=ButtonStyle.PRIMARY)
    kb.button(text=BTN_BACK_MAIN, style=ButtonStyle.DANGER)
    kb.adjust(2, 2, 1)
    return kb


async def vocabulary_in_use_inline_keyboard() -> InlineKeyboardMarkup:
    ikb = InlineKeyboardBuilder()
    for title, code in VOCABULARY_IN_USE_LEVELS:
        ikb.button(
            text=title,
            callback_data=f"lvl_sel_{code}",
            style="primary",
        )
    ikb.adjust(2)
    ikb.row(
        InlineKeyboardButton(
            text="⬅️ Asosiy menyu",
            callback_data="menu_main",
            style="danger",
        )
    )
    return ikb.as_markup()


async def essential_words_keyboard():
    """4000 Essential English Words kitoblari levellari (PRIMARY) va Asosiy menyu (DANGER)"""
    kb = ReplyKeyboardBuilder()
    for title, _ in ESSENTIAL_WORDS_LEVELS:
        kb.button(text=title, style=ButtonStyle.PRIMARY)
    kb.button(text=BTN_BACK_MAIN, style=ButtonStyle.DANGER)
    kb.adjust(2, 2, 2, 1)
    return kb


async def essential_words_inline_keyboard() -> InlineKeyboardMarkup:
    ikb = InlineKeyboardBuilder()
    for title, code in ESSENTIAL_WORDS_LEVELS:
        ikb.button(
            text=title,
            callback_data=f"lvl_sel_{code}",
            style="primary",
        )
    ikb.adjust(2)
    ikb.row(
        InlineKeyboardButton(
            text="⬅️ Asosiy menyu",
            callback_data="menu_main",
            style="danger",
        )
    )
    return ikb.as_markup()


async def level_keyboard():
    """Default bosh menyu klaviaturasi"""
    return await main_menu_keyboard()


ALL_UNITS = [f"Unit {i}" for i in range(1, 61)]
ITEMS_PER_PAGE = 8


def get_available_units(level: str) -> list[str]:
    """Berilgan level uchun data faylidan mavjud unitlarni qaytaradi."""
    clean_level = normalize_level_code(level)
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
                text="◀️",
                callback_data=f"{page_prefix}{current_page - 1}",
                style="success",
            )
        )

    nav_buttons.append(
        InlineKeyboardButton(
            text=f"{current_page + 1}/{total_pages}",
            callback_data="current",
            style="success",
        )
    )
    if current_page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="▶️",
                callback_data=f"{page_prefix}{current_page + 1}",
                style="success",
            )
        )

    keyboard.append(nav_buttons)

    if extra_bottom_buttons:
        keyboard.extend(extra_bottom_buttons)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
