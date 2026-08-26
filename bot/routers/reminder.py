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
    INTERVAL_OPTIONS,
    LEVEL_OPTIONS,
    SETUP_TTL,
    disable_reminder,
    enable_reminder,
    format_interval,
    format_schedule,
    format_schedule_summary,
    format_user_time,
    format_reminder_times,
    format_weekdays,
    get_user_reminder,
    parse_unit_number,
    parse_reminder_times,
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
    status = "✅ Yoqilgan" if reminder.is_active else "⏸ O'chirilgan"
    next_at = format_user_time(reminder.next_reminder_at)
    schedule = format_schedule(reminder)
    return (
        "⏰ <b>Eslatma sozlamalari</b>\n\n"
        f"📚 Kitob: <b>{reminder.level}</b>\n"
        f"🎯 Joriy unit: <b>Unit {reminder.current_unit}</b>\n"
        f"{schedule}\n"
        f"📅 Keyingi eslatma: <b>{next_at}</b>\n"
        f"📌 Holat: {status}"
    )


def _mode_selection_keyboard() -> InlineKeyboardBuilder:
    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(
            text="⏱ Interval bo'yicha (har X soatda)",
            callback_data="rem_mode_interval",
            style="primary",
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text="📅 Kunlar va vaqtlar bo'yicha",
            callback_data="rem_mode_schedule",
            style="primary",
        )
    )
    ikb.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="rem_back", style="danger"))
    return ikb


def _interval_selection_keyboard() -> InlineKeyboardBuilder:
    ikb = InlineKeyboardBuilder()
    options = [1, 2, 3, 4, 6, 8, 9, 12, 24]
    buttons = []
    for h in options:
        label = "1 kun" if h == 24 else f"{h} soat"
        buttons.append(
            InlineKeyboardButton(
                text=label,
                callback_data=f"rem_int_{h}",
                style="primary",
            )
        )
    for idx in range(0, len(buttons), 3):
        ikb.row(*buttons[idx : idx + 3])
    ikb.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="rem_setup", style="danger"))
    return ikb


def _weekday_keyboard(selected_days: list[int]) -> InlineKeyboardBuilder:
    ikb = InlineKeyboardBuilder()
    selected = set(selected_days)
    buttons = []
    weekday_labels = [
        (0, "Dush"),
        (1, "Sesh"),
        (2, "Chor"),
        (3, "Pay"),
        (4, "Jum"),
        (5, "Shan"),
        (6, "Yak"),
    ]

    for day_index, short_label in weekday_labels:
        prefix = "✅ " if day_index in selected else ""
        btn_style = "success" if day_index in selected else "primary"
        buttons.append(
            InlineKeyboardButton(
                text=f"{prefix}{short_label}",
                callback_data=f"rem_day_{day_index}",
                style=btn_style,
            )
        )

    for idx in range(0, len(buttons), 2):
        ikb.row(*buttons[idx : idx + 2])

    ikb.row(
        InlineKeyboardButton(text="✅ Davom etish", callback_data="rem_days_next", style="success"),
    )
    ikb.row(
        InlineKeyboardButton(text="📅 Hamma kunlar", callback_data="rem_days_all", style="primary"),
        InlineKeyboardButton(text="🔄 Tozalash", callback_data="rem_days_clear", style="danger"),
    )
    ikb.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="rem_setup", style="danger"))
    return ikb


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
                style="primary",
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
            "Siz eslatmalarni <b>Interval (har X soatda)</b> yoki "
            "<b>Kunlar va bir nechta vaqtlar</b> bo'yicha sozlamalishingiz mumkin."
        )
        keyboard = _main_menu_keyboard(False, False)

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=keyboard.as_markup(),
    )


@router.callback_query(F.data == "rem_setup")
async def setup_start(callback: CallbackQuery, redis: Redis):
    await _save_setup(
        redis,
        callback.from_user.id,
        {"step": "choose_mode"},
    )

    await callback.message.edit_text(
        "⚙️ <b>Eslatish rejimini tanlang:</b>\n\n"
        "1. <b>Interval bo'yicha:</b> Har X soatda eslatish (masalan: har 9 soatda, 1 kunda).\n"
        "2. <b>Kunlar va vaqtlar bo'yicha:</b> Hafta kunlari va kun davomidagi aniq vaqtlarda (masalan: Dush, Chor 08:00, 16:30).",
        parse_mode="HTML",
        reply_markup=_mode_selection_keyboard().as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data == "rem_mode_interval")
async def setup_mode_interval(callback: CallbackQuery, redis: Redis):
    user_id = callback.from_user.id
    setup = await _get_setup(redis, user_id) or {}
    setup["mode"] = "interval"
    setup["step"] = "choose_interval"
    await _save_setup(redis, user_id, setup)

    await callback.message.edit_text(
        "⏱ <b>Eslatma intervalini tanlang:</b>\n\n"
        "Har qancha vaqtda eslatish kerakligini tanlang.",
        parse_mode="HTML",
        reply_markup=_interval_selection_keyboard().as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rem_int_"))
async def setup_interval_select(callback: CallbackQuery, redis: Redis):
    hours = int(callback.data.removeprefix("rem_int_"))
    user_id = callback.from_user.id
    setup = await _get_setup(redis, user_id) or {}
    setup["mode"] = "interval"
    setup["interval_hours"] = hours
    setup["selected_days"] = None
    setup["reminder_times"] = None
    setup["step"] = "choose_level"
    await _save_setup(redis, user_id, setup)

    levels = _available_levels()
    if not levels:
        await callback.message.edit_text("❌ Hozircha hech qaysi kitob yuklanmagan.")
        return

    ikb = InlineKeyboardBuilder()
    for idx, level in levels:
        ikb.row(
            InlineKeyboardButton(
                text=level,
                callback_data=f"rem_lvl_{idx}",
                style="primary",
            )
        )
    ikb.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="rem_setup", style="danger"))

    await callback.message.edit_text(
        "📚 <b>Qaysi kitobdan eslatish kerak?</b>\n\n"
        f"🕐 Interval: <b>{format_interval(hours)}</b>",
        parse_mode="HTML",
        reply_markup=ikb.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data == "rem_mode_schedule")
async def setup_mode_schedule(callback: CallbackQuery, redis: Redis):
    user_id = callback.from_user.id
    setup = await _get_setup(redis, user_id) or {}
    setup["mode"] = "schedule"
    setup["interval_hours"] = 0
    setup["selected_days"] = []
    setup["step"] = "choose_days"
    await _save_setup(redis, user_id, setup)

    await callback.message.edit_text(
        "📅 <b>Eslatma kunlarini tanlang:</b>\n\n"
        "Kunlarni bittadan tanlang, so'ng davom eting.",
        parse_mode="HTML",
        reply_markup=_weekday_keyboard([]).as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rem_day_"))
async def setup_day_toggle(callback: CallbackQuery, redis: Redis):
    day_index = int(callback.data.removeprefix("rem_day_"))
    user_id = callback.from_user.id
    setup = await _get_setup(redis, user_id)

    if not setup or setup.get("step") != "choose_days":
        await callback.answer("⚠️ Sessiya tugadi. Qaytadan sozlang.", show_alert=True)
        return

    selected_days = setup.get("selected_days", [])
    if day_index in selected_days:
        selected_days = [day for day in selected_days if day != day_index]
    else:
        selected_days.append(day_index)

    setup["selected_days"] = sorted(selected_days)
    await _save_setup(redis, user_id, setup)

    await callback.message.edit_reply_markup(
        reply_markup=_weekday_keyboard(setup["selected_days"]).as_markup()
    )
    await callback.answer()


@router.callback_query(F.data == "rem_days_clear")
async def setup_days_clear(callback: CallbackQuery, redis: Redis):
    user_id = callback.from_user.id
    setup = await _get_setup(redis, user_id)

    if not setup or setup.get("step") != "choose_days":
        await callback.answer("⚠️ Sessiya tugadi. Qaytadan sozlang.", show_alert=True)
        return

    setup["selected_days"] = []
    await _save_setup(redis, user_id, setup)
    await callback.message.edit_reply_markup(
        reply_markup=_weekday_keyboard([]).as_markup()
    )
    await callback.answer("🧹 Tozalandi")


@router.callback_query(F.data == "rem_days_all")
async def setup_days_all(callback: CallbackQuery, redis: Redis):
    user_id = callback.from_user.id
    setup = await _get_setup(redis, user_id)

    if not setup or setup.get("step") != "choose_days":
        await callback.answer("⚠️ Sessiya tugadi. Qaytadan sozlang.", show_alert=True)
        return

    setup["selected_days"] = [0, 1, 2, 3, 4, 5, 6]
    await _save_setup(redis, user_id, setup)
    await callback.message.edit_reply_markup(
        reply_markup=_weekday_keyboard([0, 1, 2, 3, 4, 5, 6]).as_markup()
    )
    await callback.answer("📅 Barcha kunlar tanlandi")


@router.callback_query(F.data == "rem_days_next")
async def setup_days_next(callback: CallbackQuery, redis: Redis):
    user_id = callback.from_user.id
    setup = await _get_setup(redis, user_id)

    if not setup or setup.get("step") != "choose_days":
        await callback.answer("⚠️ Sessiya tugadi. Qaytadan sozlang.", show_alert=True)
        return

    selected_days = setup.get("selected_days", [])
    if not selected_days:
        await callback.answer("❌ Kamida bitta kun tanlang.", show_alert=True)
        return

    setup["step"] = "await_times"
    setup["selected_days"] = sorted(selected_days)
    await _save_setup(redis, user_id, setup)

    back_keyboard = InlineKeyboardBuilder()
    back_keyboard.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="rem_setup", style="danger"))

    await callback.message.edit_text(
        "🕐 <b>Eslatma vaqtlarini yuboring:</b>\n\n"
        "Format: <b>16:21</b> yoki <b>08:00, 16:30</b> (bir nechta vaqtlarni vergul bilan ajratib yuboring).\n"
        "Noto'g'ri format yuborsangiz, qayta kiritishingiz so'raladi.",
        parse_mode="HTML",
        reply_markup=back_keyboard.as_markup(),
    )
    await callback.answer()


async def _is_awaiting_times(message: Message, redis: Redis) -> bool:
    if not message.from_user:
        return False
    setup = await _get_setup(redis, message.from_user.id)
    return setup is not None and setup.get("step") == "await_times"


@router.message(F.text, _is_awaiting_times)
async def setup_times_input(message: Message, redis: Redis):
    if not message.from_user:
        return

    user_id = message.from_user.id
    setup = await _get_setup(redis, user_id)
    if not setup:
        return

    try:
        reminder_times = parse_reminder_times(message.text)
        if not reminder_times:
            raise ValueError("Kiritilgan vaqt bo'sh")
    except ValueError:
        await message.answer(
            "❌ Noto'g'ri formatda kiritdingiz.\n"
            "Vaqtni <b>16:21</b> yoki <b>08:00, 16:30</b> ko'rinishida yuboring.",
            parse_mode="HTML",
        )
        return

    setup["reminder_times"] = reminder_times
    setup["step"] = "choose_level"
    await _save_setup(redis, user_id, setup)

    levels = _available_levels()
    if not levels:
        await message.answer("❌ Hozircha hech qaysi kitob yuklanmagan.")
        return

    ikb = InlineKeyboardBuilder()
    for idx, level in levels:
        ikb.row(
            InlineKeyboardButton(
                text=level,
                callback_data=f"rem_lvl_{idx}",
                style="primary",
            )
        )
    ikb.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="rem_setup", style="danger"))

    await message.answer(
        "📚 <b>Qaysi kitobdan eslatish kerak?</b>\n\n"
        f"📅 Kunlar: <b>{format_weekdays(setup.get('selected_days', []))}</b>\n"
        f"🕐 Vaqtlar: <b>{format_reminder_times(reminder_times)}</b>",
        parse_mode="HTML",
        reply_markup=ikb.as_markup(),
    )


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
    setup["step"] = "choose_unit"
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
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("rem_sel_"))
async def setup_unit_select(callback: CallbackQuery, redis: Redis):
    unit_label = callback.data.removeprefix("rem_sel_")
    user_id = callback.from_user.id
    setup = await _get_setup(redis, user_id)

    if not setup or "level" not in setup:
        await callback.answer("⚠️ Sessiya tugadi. Qaytadan sozlang.", show_alert=True)
        return

    unit_num = parse_unit_number(unit_label)
    setup["start_unit"] = unit_num
    await _save_setup(redis, user_id, setup)

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
            style="danger",
        ),
    )

    await callback.message.edit_text(
        "✅ <b>Sozlamalarni tasdiqlang:</b>\n\n"
        f"📚 Kitob: <b>{setup['level']}</b>\n"
        f"🎯 Boshlang'ich unit: <b>Unit {unit_num}</b>\n"
        f"{format_schedule_summary(setup.get('selected_days'), setup.get('reminder_times'), setup.get('interval_hours'))}\n\n"
        "Tasdiqlangandan so'ng eslatmalar avtomatik yuboriladi.",
        parse_mode="HTML",
        reply_markup=ikb.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data == "rem_confirm")
async def setup_confirm(callback: CallbackQuery, redis: Redis):
    user_id = callback.from_user.id
    setup = await _get_setup(redis, user_id)

    if not setup or not all(k in setup for k in ("level", "start_unit")):
        await callback.answer("⚠️ Sessiya tugadi. Qaytadan sozlang.", show_alert=True)
        return

    reminder = await save_reminder(
        tg_id=user_id,
        level=setup["level"],
        start_unit=setup["start_unit"],
        interval_hours=setup.get("interval_hours", 24),
        weekdays=setup.get("selected_days"),
        reminder_times=setup.get("reminder_times"),
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
async def skip_from_reminder(callback: CallbackQuery):
    completed_unit = callback.data.removeprefix("rem_skip_")
    user_id = callback.from_user.id
    ok, message = await skip_to_next_unit(user_id)

    if not ok:
        await callback.answer(message, show_alert=True)
        return

    reminder = await get_user_reminder(user_id)
    if reminder and reminder.is_active:
        text = (
            f"✅ <b>Unit {completed_unit} bajarildi!</b>\n\n"
            f"🎯 Keyingi unit: <b>Unit {reminder.current_unit}</b>\n"
            f"📅 Keyingi eslatma: <b>{format_user_time(reminder.next_reminder_at)}</b>"
        )
        await callback.message.edit_text(text, parse_mode="HTML")
        await callback.answer("✅ Bajarildi!")
    else:
        await callback.message.edit_text(message, parse_mode="HTML")
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
