import os
import json

from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)


async def level_keyboard():
    kb = ReplyKeyboardBuilder()
    kb.button(text="📗 Elementary")
    kb.button(text="📘 Pre-intermediate & Intermediate")
    kb.button(text="📙 Upper intermediate")
    kb.button(text="📕 Advanced")
    kb.adjust(1)
    return kb


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
):
    keyboard = []

    for i in range(0, len(units), 2):
        row = []
        row.append(
            InlineKeyboardButton(
                text=units[i],
                callback_data=f"{select_prefix}{units[i]}",
            )
        )
        if i + 1 < len(units):
            row.append(
                InlineKeyboardButton(
                    text=units[i + 1],
                    callback_data=f"{select_prefix}{units[i + 1]}",
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

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
