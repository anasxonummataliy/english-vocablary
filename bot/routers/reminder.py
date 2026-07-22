import json

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from redis.asyncio import Redis

from bot.routers.keyboard import (
    create_units_keyboard,
    get_available_units,
    get_page_data,
)
from bot.services.reminder_service import (
    SETUP_TTL,
    disable_reminder,
    enable_reminder,
    format_interval,
    get_user_reminder,
    parse_unit_number,
    save_reminder,
    skip_to_next_unit,
)

router = Router()


def _setup_key(user_id: int) -> str:
    return f"reminder_setup:{user_id}"


async def _get_setup(redis: Redis, user_id: int) -> dict | None:
    raw = await redis.get(_setup_key(user_id))
    if not raw:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode()
    return json.loads(raw)


async def _save_setup(redis: Redis, user_id: int, data: dict) -> None:
    await redis.set(_setup_key(user_id), json.dumps(data), ex=SETUP_TTL)


async def _clear_setup(redis: Redis, user_id: int) -> None:
    await redis.delete(_setup_key(user_id))


def _available_levels() -> list[tuple[int, str]]:
    return [
        (idx, level)
        for idx, level in enumerate(LEVEL_OPTIONS)
        if get_available_units(level)
    ]


def _status_text(reminder) -> str:
    interval = format_interval(reminder.interval_hours)
    status = "✅ Yoqilgan" if reminder.is_active else "⏸ O'chirilgan"
    next_at = reminder.next_reminder_at.strftime("%d.%m.%Y %H:%M")
    return (
        "⏰ <b>Eslatma sozlamalari</b>\n\n"
        f"📚 Kitob: <b>{reminder.level}</b>\n"
        f"🎯 Joriy unit: <b>Unit {reminder.current_unit}</b>\n"
        f"🕐 Interval: <b>{interval}</b>\n"
        f"📅 Keyingi eslatma: <b>{next_at}</b>\n"
        f"📌 Holat: {status}"
    )


def _main_menu_keyboard(has_reminder: bool, is_active: bool) -> InlineKeyboardBuilder:
    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(
            text="⚙️ Sozlash",
            callback_data="rem_setup",
            style="primary",
        )
    )
    if has_reminder:
        if is_active:
            ikb.row(
                InlineKeyboardButton(
                    text="⏸ O'chirish",
                    callback_data="rem_disable",
                    style="danger",
                )
            )
        else:
            ikb.row(
                InlineKeyboardButton(
                    text="▶️ Yoqish",
                    callback_data="rem_enable",
                    style="success",
                )
            )
        ikb.row(
            InlineKeyboardButton(
                text="⏭ Keyingi unitga o'tish",
                callback_data="rem_skip",
            )
        )
    return ikb


@router.message(Command("reminder"))
async def reminder_command(message: Message, redis: Redis):
    user_id = message.from_user.id
    reminder = await get_user_reminder(user_id)

    if reminder:
        text = _status_text(reminder)
        keyboard = _main_menu_keyboard(True, reminder.is_active)
    else:
        text = (
            "⏰ <b>Eslatma xizmati</b>\n\n"
            "Bot sizga tanlangan kitob va unit bo'yicha "
            "muntazam eslatmalar yuboradi.\n\n"
            "Siz kitob, boshlang'ich unit va intervalni "
            "(9 soat yoki 1 kun) o'zingiz tanlaysiz."
        )
        keyboard = _main_menu_keyboard(False, False)

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=keyboard.as_markup(),
    )


@router.callback_query(F.data == "rem_setup")
async def setup_start(callback: CallbackQuery, redis: Redis):
    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(text="🕘 9 soat", callback_data="rem_int_9", style="success"),
        InlineKeyboardButton(text="📅 1 kun", callback_data="rem_int_24", style="success"),
    )
    ikb.row(
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data="rem_back"),
    )

    await callback.message.edit_text(
        "⏰ <b>Eslatma intervalini tanlang:</b>\n\n"
        "Bot shu vaqt oralig'ida keyingi unitni "
        "ishlashingizni eslatib turadi.",
        parse_mode="HTML",
        reply_markup=ikb.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rem_int_"))
async def setup_interval(callback: CallbackQuery, redis: Redis):
    interval_hours = int(callback.data.removeprefix("rem_int_"))
    user_id = callback.from_user.id

    await _save_setup(redis, user_id, {"interval_hours": interval_hours})

    levels = _available_levels()
    if not levels:
        await callback.answer("❌ Hozircha hech qaysi kitob yuklanmagan.", show_alert=True)
        return

    ikb = InlineKeyboardBuilder()
    for idx, level in levels:
        ikb.row(
            InlineKeyboardButton(
                text=level,
                callback_data=f"rem_lvl_{idx}",
            )
        )
    ikb.row(
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data="rem_setup"),
    )

    await callback.message.edit_text(
        "📚 <b>Qaysi kitobdan eslatish kerak?</b>",
        parse_mode="HTML",
        reply_markup=ikb.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rem_lvl_"))
async def setup_level(callback: CallbackQuery, redis: Redis):
    level_idx = int(callback.data.removeprefix("rem_lvl_"))
    levels = _available_levels()
    level_map = {idx: level for idx, level in levels}

    if level_idx not in level_map:
        await callback.answer("❌ Kitob topilmadi.", show_alert=True)
        return

    level = level_map[level_idx]
    user_id = callback.from_user.id
    setup = await _get_setup(redis, user_id) or {}
    setup["level"] = level
    setup["level_idx"] = level_idx
    await _save_setup(redis, user_id, setup)

    page_data, current_page, total_pages = await get_page_data(0, level)
    keyboard = await create_units_keyboard(
        current_page,
        total_pages,
        page_data,
        select_prefix="rem_sel_",
        page_prefix="rem_page_",
    )

    await callback.message.edit_text(
        f"📖 Kitob: <b>{level}</b>\n"
        "🎯 <b>Qaysi unitdan boshlaysiz?</b>\n\n"
        "Bot shu unitdan boshlab ketma-ket eslatib boradi.",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rem_page_"))
async def setup_unit_page(callback: CallbackQuery, redis: Redis):
    page = int(callback.data.removeprefix("rem_page_"))
    user_id = callback.from_user.id
    setup = await _get_setup(redis, user_id)

    if not setup or "level" not in setup:
        await callback.answer("⚠️ Sessiya tugadi. Qaytadan sozlang.", show_alert=True)
        return

    level = setup["level"]
    page_data, current_page, total_pages = await get_page_data(page, level)

    if not page_data:
        await callback.answer("❌ Bu sahifada unit yo'q.", show_alert=True)
        return

    keyboard = await create_units_keyboard(
        current_page,
        total_pages,
        page_data,
        select_prefix="rem_sel_",
        page_prefix="rem_page_",
    )

    text = (
        f"📖 Kitob: <b>{level}</b>\n"
        "🎯 <b>Qaysi unitdan boshlaysiz?</b>\n\n"
        f"📊 Sahifa: {current_page + 1}/{total_pages}"
    )

    try:
        await callback.message.edit_text(
            text, parse_mode="HTML", reply_markup=keyboard
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("rem_sel_"))
async def setup_unit_select(callback: CallbackQuery, redis: Redis):
    unit_label = callback.data.removeprefix("rem_sel_")
    user_id = callback.from_user.id
    setup = await _get_setup(redis, user_id)

    if not setup or "level" not in setup or "interval_hours" not in setup:
        await callback.answer("⚠️ Sessiya tugadi. Qaytadan sozlang.", show_alert=True)
        return

    unit_num = parse_unit_number(unit_label)
    setup["start_unit"] = unit_num
    await _save_setup(redis, user_id, setup)

    interval = format_interval(setup["interval_hours"])
    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(
            text="✅ Tasdiqlash",
            callback_data="rem_confirm",
            style="success",
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text="⬅️ Orqaga",
            callback_data=f"rem_lvl_{setup.get('level_idx', 0)}",
        ),
    )

    await callback.message.edit_text(
        "✅ <b>Sozlamalarni tasdiqlang:</b>\n\n"
        f"📚 Kitob: <b>{setup['level']}</b>\n"
        f"🎯 Boshlang'ich unit: <b>Unit {unit_num}</b>\n"
        f"🕐 Interval: <b>{interval}</b>\n\n"
        "Tasdiqlangandan so'ng eslatmalar avtomatik yuboriladi.",
        parse_mode="HTML",
        reply_markup=ikb.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data == "rem_confirm")
async def setup_confirm(callback: CallbackQuery, redis: Redis):
    user_id = callback.from_user.id
    setup = await _get_setup(redis, user_id)

    if not setup or not all(k in setup for k in ("level", "interval_hours", "start_unit")):
        await callback.answer("⚠️ Sessiya tugadi. Qaytadan sozlang.", show_alert=True)
        return

    reminder = await save_reminder(
        tg_id=user_id,
        level=setup["level"],
        start_unit=setup["start_unit"],
        interval_hours=setup["interval_hours"],
    )
    await _clear_setup(redis, user_id)

    await callback.message.edit_text(
        _status_text(reminder) + "\n\n✅ Eslatma muvaffaqiyatli sozlandi!",
        parse_mode="HTML",
        reply_markup=_main_menu_keyboard(True, True).as_markup(),
    )
    await callback.answer("✅ Eslatma yoqildi!")


@router.callback_query(F.data == "rem_disable")
async def disable_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    disabled = await disable_reminder(user_id)

    if not disabled:
        await callback.answer("❌ Eslatma topilmadi.", show_alert=True)
        return

    reminder = await get_user_reminder(user_id)
    await callback.message.edit_text(
        _status_text(reminder),
        parse_mode="HTML",
        reply_markup=_main_menu_keyboard(True, False).as_markup(),
    )
    await callback.answer("⏸ Eslatma o'chirildi")


@router.callback_query(F.data == "rem_enable")
async def enable_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    reminder = await enable_reminder(user_id)

    if not reminder:
        await callback.answer("❌ Eslatma topilmadi.", show_alert=True)
        return

    await callback.message.edit_text(
        _status_text(reminder),
        parse_mode="HTML",
        reply_markup=_main_menu_keyboard(True, True).as_markup(),
    )
    await callback.answer("✅ Eslatma yoqildi")


@router.callback_query(F.data == "rem_skip")
async def skip_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    ok, message = await skip_to_next_unit(user_id)

    if not ok:
        await callback.answer(message, show_alert=True)
        return

    reminder = await get_user_reminder(user_id)
    if reminder and reminder.is_active:
        text = _status_text(reminder) + f"\n\n{message}"
        keyboard = _main_menu_keyboard(True, True)
    else:
        text = message
        keyboard = _main_menu_keyboard(False, False)

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rem_skip_"))
async def skip_from_reminder(callback: CallbackQuery, bot: Bot, redis: Redis):
    user_id = callback.from_user.id
    ok, message = await skip_to_next_unit(user_id)

    if not ok:
        await callback.answer(message, show_alert=True)
        return

    reminder = await get_user_reminder(user_id)
    if reminder and reminder.is_active:
        from bot.services.reminder_service import send_unit_reminder

        await send_unit_reminder(
            bot,
            user_id,
            reminder.level,
            reminder.current_unit,
            redis,
            intro=f"✅ {message}\n\n",
        )
        await callback.answer("Keyingi unit yuborildi!")
    else:
        await callback.message.answer(message, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data == "rem_back")
async def back_to_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    reminder = await get_user_reminder(user_id)

    if reminder:
        text = _status_text(reminder)
        keyboard = _main_menu_keyboard(True, reminder.is_active)
    else:
        text = (
            "⏰ <b>Eslatma xizmati</b>\n\n"
            "Bot sizga tanlangan kitob va unit bo'yicha "
            "muntazam eslatmalar yuboradi."
        )
        keyboard = _main_menu_keyboard(False, False)

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard.as_markup(),
    )
    await callback.answer()
