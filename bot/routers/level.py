from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    Message,
    ReplyKeyboardRemove,
    CallbackQuery,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from redis.asyncio import Redis

from bot.routers.keyboard import (
    level_keyboard,
    get_page_data,
    create_units_keyboard,
    ALL_UNITS,
)

router = Router()


async def get_user_context(user_id: int, redis: Redis):
    """Redisdan foydalanuvchi tanlagan kitobni olish uchun"""
    return await redis.get(f"user:{user_id}:level")


@router.message(Command("level"))
async def level_handler(message: Message):
    kb = await level_keyboard()
    await message.answer(
        "📚 <b>English Vocabulary in Use</b>\n\nQaysi darajadagi kitobdan boshlamoqchisiz?",
        reply_markup=kb.as_markup(resize_keyboard=True),
        parse_mode="HTML",
    )


@router.message(
    F.text.in_(
        {
            "📗 Elementary",
            "📘 Pre-intermediate & Intermediate",
            "📙 Upper intermediate",
            "📕 Advanced",
        }
    )
)
async def section_selection_handler(message: Message, redis: Redis):
    level_name = message.text
    user_id = message.from_user.id

    await redis.set(f"user:{user_id}:level", level_name, ex=86400)

    loading_msg = await message.answer(
        "⏳ Unitlar ro‘yxati yuklanmoqda...", reply_markup=ReplyKeyboardRemove()
    )

    page_data, current_page, total_pages = await get_page_data(0)

    text = f"📖 Kitob: <b>{level_name}</b>\n"
    text += "🎯 <b>Unit tanlang:</b>\n\n"
    text += f"📊 Jami: {len(ALL_UNITS)} ta unit mavjud"

    keyboard = await create_units_keyboard(current_page, total_pages, page_data)

    await loading_msg.delete()
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("page_"))
async def pagination_handler(callback: CallbackQuery, redis: Redis):
    user_id = callback.from_user.id
    page = int(callback.data.split("_")[1])

    user_level = await get_user_context(user_id, redis)

    if not user_level:
        await callback.answer(
            "⚠️ Sessiya muddati tugagan. Qaytadan darajani tanlang.", show_alert=True
        )
        return

    page_data, current_page, total_pages = await get_page_data(page)

    text = f"📖 Kitob: <b>{user_level}</b>\n"
    text += "🎯 <b>Unit tanlang:</b>\n\n"
    text += f"📊 Sahifa: {current_page + 1}/{total_pages}"

    keyboard = await create_units_keyboard(current_page, total_pages, page_data)

    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        pass

    await callback.answer()


@router.callback_query(F.data.startswith("select_"))
async def select_handler(callback: CallbackQuery, redis: Redis):
    selected_unit = callback.data.replace("select_", "")
    user_id = callback.from_user.id

    user_level = await get_user_context(user_id, redis)

    if not user_level:
        await callback.answer("⚠️ Sessiya muddati tugagan.", show_alert=True)
        return

    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(
            text="📖 So‘zlarni o‘rganish", callback_data=f"words_{selected_unit}"
        ),
    )
    ikb.row(
        InlineKeyboardButton(
            text="📝 Test yechish", callback_data=f"test_{selected_unit}"
        ),
    )

    ikb.row(
        InlineKeyboardButton(
            text="⬅️ Unitlar ro'yxatiga qaytish", callback_data="page_0"
        )
    )

    text = f"📚 <b>Kitob:</b> {user_level}\n"
    text += f"✅ <b>Tanlangan:</b> {selected_unit}\n\n"
    text += "Ushbu unit bo‘yicha nima qilmoqchisiz?"

    await callback.message.edit_text(
        text, parse_mode="HTML", reply_markup=ikb.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data == "current")
async def current_page_handler(callback: CallbackQuery):
    await callback.answer("Siz hozirgi sahifadasiz", show_alert=False)
