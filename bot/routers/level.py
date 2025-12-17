from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from bot.routers.keyboard import (
    level_keyboard,
    get_page_data,
    create_units_keyboard,
    ALL_UNITS,
)


router = Router()


@router.message(Command("level"))
async def level_handler(message: Message):
    kb = await level_keyboard()
    await message.answer(
        "📚 English Vocablary in Use Kitobni qaysi qismidan boshlamoqchisiz?",
        reply_markup=kb.as_markup(resize_keyboard=True),
    )


@router.message(F.text == "📗 Elementary")
async def section_elem(message: Message):
    loading_msg = await message.answer(
        "⏳ Yuklanmoqda...", reply_markup=ReplyKeyboardRemove()
    )
    page_data, current_page, total_pages = await get_page_data(0)

    text = "🎯 <b>Unit tanlang:</b>\n\n"
    text += f"📊 Jami: {len(ALL_UNITS)} ta unit mavjud"

    keyboard = await create_units_keyboard(current_page, total_pages, page_data)
    loading_msg.delete()
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(F.text == "📘 Pre-intermediate & Intermediate")
async def section_pre_int(message: Message):
    page_data, current_page, total_pages = await get_page_data(0)

    text = "🎯 <b>Unit tanlang:</b>\n\n"
    text += f"📊 Jami: {len(ALL_UNITS)} ta unit mavjud"

    keyboard = await create_units_keyboard(current_page, total_pages, page_data)
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(F.text == "📙 Upper intermediate")
async def section_upper_int(message: Message):
    page_data, current_page, total_pages = await get_page_data(0)

    text = "🎯 <b>Unit tanlang:</b>\n\n"
    text += f"📊 Jami: {len(ALL_UNITS)} ta unit mavjud"

    keyboard = await create_units_keyboard(current_page, total_pages, page_data)
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(F.text == "📕 Advanced")
async def section_advanced(message: Message):
    page_data, current_page, total_pages = await get_page_data(0)

    text = "🎯 <b>Unit tanlang:</b>\n\n"
    text += f"📊 Jami: {len(ALL_UNITS)} ta unit mavjud"

    keyboard = await create_units_keyboard(current_page, total_pages, page_data)
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("page_"))
async def pagination_handler(callback: CallbackQuery):
    page = int(callback.data.split("_")[1])
    page_data, current_page, total_pages = await get_page_data(page)

    text = "🎯 <b>Unit tanlang:</b>\n\n"
    text += f"📊 Jami: {len(ALL_UNITS)} ta unit mavjud"

    keyboard = await create_units_keyboard(current_page, total_pages, page_data)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "current")
async def current_page_handler(callback: CallbackQuery):
    await callback.answer("Siz hozirgi sahifadasiz", show_alert=False)


@router.callback_query(F.data.startswith("select_"))
async def select_handler(callback: CallbackQuery):
    selected_unit = callback.data.replace("select_", "")
    await callback.answer(f"✅ Siz {selected_unit} tanladingiz!", show_alert=True)

    text = f"✅ <b>Tanlangan:</b> {selected_unit}\n\n"
    text += f"Bu yerda {selected_unit} uchun ma'lumotlar ko'rsatiladi.\n\n"
    text += "Yana tanlash uchun /level bosing"

    await callback.message.edit_text(text, parse_mode="HTML")
