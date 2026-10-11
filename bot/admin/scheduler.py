import os
import re
import html
from typing import Optional
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from api.database import (
    get_all_channel_schedulers,
    get_channel_scheduler,
    save_channel_scheduler,
    update_channel_scheduler_status,
    update_channel_scheduler_unit,
    delete_channel_scheduler,
)
from api.services.vocab_service import vocab_service

router = Router()


class SchedulerSetup(StatesGroup):
    channel_id = State()
    book_slug = State()
    start_unit = State()
    send_time = State()
    finish_message = State()


def get_book_info(book_slug: str):
    book = vocab_service.books.get(book_slug, {})
    title = book.get("title", book_slug)
    total_units = len(book.get("units", []))
    return title, total_units


def render_scheduler_card(s: dict) -> tuple[str, InlineKeyboardMarkup]:
    channel_id = s.get("channel_id", "")
    book_slug = s.get("book_slug", "essential1")
    current_unit = s.get("current_unit", 1)
    send_time = s.get("send_time", "09:00")
    is_active = bool(s.get("is_active", 1))
    last_sent = s.get("last_sent_date") or "Hali jo'natilmagan"
    finish_msg = s.get("finish_message") or "Mavjud emas (ixtiyoriy)"
    
    book_title, total_units = get_book_info(book_slug)

    status_icon = "🟢 FAOL" if is_active else "⏸ TO'XTATILGAN"
    toggle_text = "⏸ To'xtatish" if is_active else "▶️ Faollashtirish"

    text = (
        f"📬 <b>Kanal Scheduler Boshqaruvi</b>\n\n"
        f"📢 <b>Kanal:</b> <code>{html.escape(str(channel_id))}</code>\n"
        f"📚 <b>Kitob:</b> {html.escape(book_title)}\n"
        f"📖 <b>Hozirgi Unit:</b> <b>{current_unit}</b> / {total_units}\n"
        f"⏰ <b>Yuborish vaqti:</b> <code>{send_time}</code> (Har kuni)\n"
        f"📊 <b>Holati:</b> {status_icon}\n"
        f"📅 <b>Oxirgi jo'natilgan:</b> {last_sent}\n"
        f"🏁 <b>Unitdan keyingi xabar:</b> <i>{html.escape(str(finish_msg))}</i>\n"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=toggle_text, callback_data=f"sched:toggle:{channel_id}"),
                InlineKeyboardButton(text="🚀 Test jo'natish", callback_data=f"sched:test:{channel_id}"),
            ],
            [
                InlineKeyboardButton(text="⏮ Oldingi unit", callback_data=f"sched:prev:{channel_id}"),
                InlineKeyboardButton(text="⏭ Keyingi unit", callback_data=f"sched:next:{channel_id}"),
            ],
            [
                InlineKeyboardButton(text="⚙️ Qayta sozlash", callback_data=f"sched:setup:{channel_id}"),
                InlineKeyboardButton(text="🔄 Yangilash", callback_data=f"sched:refresh:{channel_id}"),
            ],
        ]
    )
    return text, kb


@router.message(Command("scheduler", "channel_scheduler"))
async def cmd_scheduler(message: Message, state: FSMContext):
    await state.clear()
    schedulers = await get_all_channel_schedulers()

    if schedulers:
        # Eng birinchi scheduler ma'lumotini ko'rsatamiz
        s = schedulers[0]
        text, kb = render_scheduler_card(s)
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        default_channel = os.getenv("CHANNEL_ID", "")
        text = (
            "📬 <b>Kanal Scheduler hali sozlanmagan!</b>\n\n"
            "Kanalga har kuni belgilangan vaqtda lug'at so'zlarini avtomatik jo'natish "
            "uchun sozlashni boshlang.\n"
        )
        if default_channel:
            text += f"\n📌 Default kanal: <code>{default_channel}</code>"

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ Kanal Scheduler sozlash", callback_data="sched:setup:new")]
            ]
        )
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("sched:refresh:"))
async def cb_refresh(call: CallbackQuery):
    channel_id = call.data.split(":", 2)[2]
    s = await get_channel_scheduler(channel_id)
    if not s:
        await call.answer("Scheduler topilmadi!", show_alert=True)
        return
    text, kb = render_scheduler_card(s)
    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await call.answer("Yangilandi ✅")


@router.callback_query(F.data.startswith("sched:toggle:"))
async def cb_toggle(call: CallbackQuery):
    channel_id = call.data.split(":", 2)[2]
    s = await get_channel_scheduler(channel_id)
    if not s:
        await call.answer("Scheduler topilmadi!", show_alert=True)
        return

    new_status = not bool(s.get("is_active", 1))
    await update_channel_scheduler_status(channel_id, new_status)
    s["is_active"] = 1 if new_status else 0

    text, kb = render_scheduler_card(s)
    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass

    msg = "Scheduler faollashtirildi ✅" if new_status else "Scheduler to'xtatildi ⏸"
    await call.answer(msg)


@router.callback_query(F.data.startswith("sched:test:"))
async def cb_test_send(call: CallbackQuery):
    channel_id = call.data.split(":", 2)[2]
    s = await get_channel_scheduler(channel_id)
    if not s:
        await call.answer("Scheduler topilmadi!", show_alert=True)
        return

    book_slug = s.get("book_slug", "essential1")
    unit_num = s.get("current_unit", 1)
    finish_msg = s.get("finish_message")

    from api.services.channel_scheduler_service import send_unit_to_channel
    asyncio.create_task(
        send_unit_to_channel(channel_id, book_slug, unit_num, finish_message=finish_msg)
    )

    await call.message.answer(
        f"🚀 <b>Unit {unit_num}</b> ({book_slug}) savollari har 1 daqiqa oralig'ida kanalga jo'natilishi boshlandi!\n"
        f"<i>(Jami testlar har minutda bittadan tashlanadi va oxirida yakuniy xabar yuboriladi)</i>",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("sched:next:"))
async def cb_next_unit(call: CallbackQuery):
    channel_id = call.data.split(":", 2)[2]
    s = await get_channel_scheduler(channel_id)
    if not s:
        await call.answer("Scheduler topilmadi!", show_alert=True)
        return

    book_slug = s.get("book_slug", "essential1")
    _, total_units = get_book_info(book_slug)
    curr = s.get("current_unit", 1)

    if curr >= total_units:
        await call.answer(f"Oxirgi unitdasiz ({total_units})!", show_alert=True)
        return

    s = await update_channel_scheduler_unit(channel_id, curr + 1)
    text, kb = render_scheduler_card(s)
    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await call.answer(f"Unit {curr + 1} ga o'tkazildi ⏭")


@router.callback_query(F.data.startswith("sched:prev:"))
async def cb_prev_unit(call: CallbackQuery):
    channel_id = call.data.split(":", 2)[2]
    s = await get_channel_scheduler(channel_id)
    if not s:
        await call.answer("Scheduler topilmadi!", show_alert=True)
        return

    curr = s.get("current_unit", 1)
    if curr <= 1:
        await call.answer("1-unitdasiz!", show_alert=True)
        return

    s = await update_channel_scheduler_unit(channel_id, curr - 1)
    text, kb = render_scheduler_card(s)
    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await call.answer(f"Unit {curr - 1} ga qaytarildi ⏮")


# ─── Scheduler Setup Wizard (FSM) ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("sched:setup:"))
async def start_setup_wizard(call: CallbackQuery, state: FSMContext):
    await state.clear()
    default_ch = os.getenv("CHANNEL_ID", "")

    buttons = []
    if default_ch:
        buttons.append([InlineKeyboardButton(text=f"📌 Default: {default_ch}", callback_data=f"sched:set_ch:{default_ch}")])
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="sched:cancel")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await state.set_state(SchedulerSetup.channel_id)
    await call.message.answer(
        "📝 <b>1/5. Kanal ID yoki username kiriting</b>\n\n"
        "Masalan: <code>@mening_kanalim</code> yoki <code>-1001234567890</code>\n"
        "<i>(Bot ushbu kanalda xabar yozish huquqiga ega bo'lgan admin bo'lishi shart!)</i>",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.startswith("sched:set_ch:"))
async def cb_set_default_channel(call: CallbackQuery, state: FSMContext):
    channel_id = call.data.split(":", 2)[2]
    await state.update_data(channel_id=channel_id)
    await prompt_book_selection(call.message, state)
    await call.answer()


@router.message(SchedulerSetup.channel_id)
async def process_channel_id(message: Message, state: FSMContext):
    ch_input = message.text.strip()
    await state.update_data(channel_id=ch_input)
    await prompt_book_selection(message, state)


async def prompt_book_selection(message: Message, state: FSMContext):
    await state.set_state(SchedulerSetup.book_slug)

    buttons = []
    # Books list from vocab service
    for slug, b in vocab_service.books.items():
        title = b.get("short_title", b.get("title", slug))
        units_count = len(b.get("units", []))
        buttons.append([InlineKeyboardButton(text=f"📚 {title} ({units_count} unit)", callback_data=f"sched:pick_book:{slug}")])

    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="sched:cancel")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(
        "📚 <b>2/5. Qaysi kitobdan so'zlar yuborilsin?</b>",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("sched:pick_book:"))
async def process_book_selection(call: CallbackQuery, state: FSMContext):
    book_slug = call.data.split(":", 2)[2]
    await state.update_data(book_slug=book_slug)

    title, total_units = get_book_info(book_slug)
    await state.set_state(SchedulerSetup.start_unit)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Unit 1", callback_data="sched:pick_unit:1"),
                InlineKeyboardButton(text="Unit 5", callback_data="sched:pick_unit:5"),
                InlineKeyboardButton(text="Unit 10", callback_data="sched:pick_unit:10"),
            ],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="sched:cancel")]
        ]
    )

    await call.message.answer(
        f"📖 <b>3/5. Boshlang'ich Unit raqamini kiriting:</b>\n\n"
        f"Tanlangan kitob: <b>{title}</b> (Jami: {total_units} ta unit)\n"
        f"1 dan {total_units} gacha son yozing yoki tugmalardan tanlang:",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.startswith("sched:pick_unit:"))
async def cb_pick_unit(call: CallbackQuery, state: FSMContext):
    unit_num = int(call.data.split(":", 2)[2])
    await state.update_data(start_unit=unit_num)
    await prompt_send_time(call.message, state)
    await call.answer()


@router.message(SchedulerSetup.start_unit)
async def process_start_unit(message: Message, state: FSMContext):
    try:
        unit_num = int(message.text.strip())
        if unit_num < 1:
            await message.answer("Unit raqami 1 dan kichik bo'lishi mumkin emas. Qaytadan kiriting:")
            return
    except ValueError:
        await message.answer("Iltimos, faqat butun son kiriting (masalan: 1):")
        return

    await state.update_data(start_unit=unit_num)
    await prompt_send_time(message, state)


async def prompt_send_time(message: Message, state: FSMContext):
    await state.set_state(SchedulerSetup.send_time)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="08:00", callback_data="sched:pick_time:08:00"),
                InlineKeyboardButton(text="09:00", callback_data="sched:pick_time:09:00"),
                InlineKeyboardButton(text="10:00", callback_data="sched:pick_time:10:00"),
            ],
            [
                InlineKeyboardButton(text="18:00", callback_data="sched:pick_time:18:00"),
                InlineKeyboardButton(text="20:00", callback_data="sched:pick_time:20:00"),
                InlineKeyboardButton(text="21:00", callback_data="sched:pick_time:21:00"),
            ],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="sched:cancel")]
        ]
    )

    await message.answer(
        "⏰ <b>4/5. Har kuni qaysi vaqtda jo'natilsin?</b> (Toshkent vaqti, UTC+5)\n\n"
        "Format: <code>HH:MM</code> (masalan: <code>09:00</code> yoki <code>20:30</code>):",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("sched:pick_time:"))
async def cb_pick_time(call: CallbackQuery, state: FSMContext):
    time_str = call.data.split(":", 2)[2]
    await state.update_data(send_time=time_str)
    await prompt_finish_message(call.message, state)
    await call.answer()


@router.message(SchedulerSetup.send_time)
async def process_send_time(message: Message, state: FSMContext):
    time_str = message.text.strip()
    if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", time_str):
        await message.answer("⚠️ Vaqt formati noto'g'ri! Iltimos, <code>09:00</code> yoki <code>20:30</code> ko'rinishida yozing:", parse_mode="HTML")
        return

    await state.update_data(send_time=time_str)
    await prompt_finish_message(message, state)


async def prompt_finish_message(message: Message, state: FSMContext):
    await state.set_state(SchedulerSetup.finish_message)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ O'tkazib yuborish (Matnsiz)", callback_data="sched:skip_finish")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="sched:cancel")],
        ]
    )

    await message.answer(
        "🏁 <b>5/5. Har bir unit so'zlari tashlangandan so'ng kanalga qanday xabar yuborilsin?</b>\n\n"
        "Masalan: <i>💬 Bugungi unit so'zlari shulardan iborat edi. Yod oling va takrorlang!</i>\n\n"
        "Agar xabar kerak bo'lmasa, 'O'tkazib yuborish' tugmasini bosing:",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "sched:skip_finish")
async def cb_skip_finish(call: CallbackQuery, state: FSMContext):
    await save_and_finalize_scheduler(call.message, state, finish_msg=None)
    await call.answer()


@router.message(SchedulerSetup.finish_message)
async def process_finish_message(message: Message, state: FSMContext):
    await save_and_finalize_scheduler(message, state, finish_msg=message.text.strip())


async def save_and_finalize_scheduler(message: Message, state: FSMContext, finish_msg: Optional[str]):
    data = await state.get_data()
    channel_id = data.get("channel_id")
    book_slug = data.get("book_slug", "essential1")
    start_unit = int(data.get("start_unit", 1))
    send_time = data.get("send_time", "09:00")

    result = await save_channel_scheduler(
        channel_id=channel_id,
        book_slug=book_slug,
        start_unit=start_unit,
        send_time=send_time,
        is_active=True,
        finish_message=finish_msg,
    )

    await state.clear()

    await message.answer("🎉 <b>Kanal Scheduler muvaffaqiyatli saqlandi!</b>", parse_mode="HTML")
    text, kb = render_scheduler_card(result)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "sched:cancel")
async def cb_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer("❌ Kanal Scheduler sozlash bekor qilindi.")
    await call.answer()
