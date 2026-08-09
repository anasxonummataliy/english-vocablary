from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.score_service import (
    get_unit_leaderboard,
    get_group_leaderboard,
    get_global_leaderboard,
)
from bot.routers.keyboard import get_available_levels, get_available_units

router = Router()


# ==================== /top KOMANDASI ====================
@router.message(Command("top", "leaderboard", "rating", "reyting"))
async def cmd_leaderboard(message: Message):
    text_args = message.text.split()[1:] if message.text else []

    # Agar arg berilgan bo'lsa: /top elementary 5
    if len(text_args) >= 2:
        level = text_args[0].lower()
        try:
            unit_num = int(text_args[1].replace("unit", "").strip())
            await _show_unit_leaderboard_msg(message, level, unit_num)
            return
        except ValueError:
            pass

    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(text="👥 Guruh Reytingi", callback_data="lb_group", style="success"),
        InlineKeyboardButton(text="🌍 Umumiy Reyting", callback_data="lb_global", style="primary"),
    )

    available_levels = get_available_levels()
    for title, code in available_levels:
        ikb.row(InlineKeyboardButton(text=title, callback_data=f"lb_lvl_{code}", style="primary"))

    await message.answer(
        "🏆 <b>REYTING JADVALI</b>\n\n"
        "Qaysi reytingni ko'rishni xohlaysiz?\n"
        "<i>(Har bir unit yoki jami ballar bo'yicha eng kuchli foydalanuvchilar)</i>",
        reply_markup=ikb.as_markup(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("lb_lvl_"))
async def select_leaderboard_level(callback: CallbackQuery):
    level = callback.data.removeprefix("lb_lvl_")

    units = get_available_units(level)

    ikb = InlineKeyboardBuilder()
    row = []
    for u_str in units:
        try:
            u_num = int(u_str.replace("Unit", "").strip())
        except ValueError:
            continue
        row.append(
            InlineKeyboardButton(
                text=u_str, callback_data=f"lb_unit_{level}_{u_num}", style="primary"
            )
        )
        if len(row) == 2:
            ikb.row(*row)
            row = []
    if row:
        ikb.row(*row)
    ikb.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="lb_main", style="danger"))

    await callback.message.edit_text(
        f"📖 Daraja: <b>{level.capitalize()}</b>\n"
        "🎯 <b>Qaysi Unit bo'yicha reytingni ko'rmoqchisiz?</b>",
        reply_markup=ikb.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "lb_main")
async def back_to_main_leaderboard(callback: CallbackQuery):
    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(text="👥 Guruh Reytingi", callback_data="lb_group", style="success"),
        InlineKeyboardButton(text="🌍 Umumiy Reyting", callback_data="lb_global", style="primary"),
    )
    available_levels = get_available_levels()
    for title, code in available_levels:
        ikb.row(InlineKeyboardButton(text=title, callback_data=f"lb_lvl_{code}", style="primary"))

    await callback.message.edit_text(
        "🏆 <b>REYTING JADVALI</b>\n\n"
        "Qaysi reytingni ko'rishni xohlaysiz?",
        reply_markup=ikb.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("lb_unit_"))
async def show_unit_leaderboard_cb(callback: CallbackQuery):
    raw = callback.data.removeprefix("lb_unit_")
    parts = raw.split("_")
    level = parts[0]
    unit_num = int(parts[1])

    rows = await get_unit_leaderboard(level, unit_num)

    ikb = InlineKeyboardBuilder()
    ikb.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"lb_lvl_{level}", style="danger"))

    text = f"🏆 <b>Unit {unit_num} ({level.capitalize()}) REYTINGI</b>\n\n"
    if not rows:
        text += "<i>Ushbu unit bo'yicha hali natijalar mavjud emas.</i>"
    else:
        medals = ["🥇", "🥈", "🥉"]
        for i, row in enumerate(rows):
            user_id, max_score, max_percent, first_name, username = row
            name = first_name or (f"@{username}" if username else f"User_{user_id}")
            medal = medals[i] if i < 3 else f"{i+1}."
            text += f"{medal} <b>{name}</b> — <b>{max_percent:.0f}%</b> ({max_score} ball)\n"

    await callback.message.edit_text(
        text, reply_markup=ikb.as_markup(), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "lb_group")
async def show_group_leaderboard_cb(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    rows = await get_group_leaderboard(chat_id)

    ikb = InlineKeyboardBuilder()
    ikb.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="lb_main", style="danger"))

    text = "👥 <b>GURUH REYTINGI (Jami Ballar)</b>\n\n"
    if not rows:
        text += "<i>Ushbu guruhda hali test yoki musobaqa o'tkazilmagan.</i>"
    else:
        medals = ["🥇", "🥈", "🥉"]
        for i, row in enumerate(rows):
            user_id, total_score, tests_count, first_name, username = row
            name = first_name or (f"@{username}" if username else f"User_{user_id}")
            medal = medals[i] if i < 3 else f"{i+1}."
            text += f"{medal} <b>{name}</b> — <b>{total_score} ball</b> ({tests_count} ta test)\n"

    await callback.message.edit_text(
        text, reply_markup=ikb.as_markup(), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "lb_global")
async def show_global_leaderboard_cb(callback: CallbackQuery):
    rows = await get_global_leaderboard()

    ikb = InlineKeyboardBuilder()
    ikb.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="lb_main", style="danger"))

    text = "🌍 <b>UMUMIY BOT REYTINGI</b>\n\n"
    if not rows:
        text += "<i>Hali umumiy natijalar mavjud emas.</i>"
    else:
        medals = ["🥇", "🥈", "🥉"]
        for i, row in enumerate(rows):
            user_id, total_score, tests_count, first_name, username = row
            name = first_name or (f"@{username}" if username else f"User_{user_id}")
            medal = medals[i] if i < 3 else f"{i+1}."
            text += f"{medal} <b>{name}</b> — <b>{total_score} ball</b> ({tests_count} ta test)\n"

    await callback.message.edit_text(
        text, reply_markup=ikb.as_markup(), parse_mode="HTML"
    )
    await callback.answer()


async def _show_unit_leaderboard_msg(message: Message, level: str, unit_num: int):
    rows = await get_unit_leaderboard(level, unit_num)
    text = f"🏆 <b>Unit {unit_num} ({level.capitalize()}) REYTINGI</b>\n\n"
    if not rows:
        text += "<i>Ushbu unit bo'yicha hali natijalar mavjud emas.</i>"
    else:
        medals = ["🥇", "🥈", "🥉"]
        for i, row in enumerate(rows):
            user_id, max_score, max_percent, first_name, username = row
            name = first_name or (f"@{username}" if username else f"User_{user_id}")
            medal = medals[i] if i < 3 else f"{i+1}."
            text += f"{medal} <b>{name}</b> — <b>{max_percent:.0f}%</b> ({max_score} ball)\n"

    await message.answer(text, parse_mode="HTML")
