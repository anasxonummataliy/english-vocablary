from datetime import datetime, timezone, timedelta
from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from sqlalchemy import select, func

from bot.database.models.users import User
from bot.database.models.reminders import Reminder
from bot.database.models.baskets import Basket, BasketWord
from bot.database.models.scores import TestScore
from bot.database.session import get_async_session_context

router = Router()


def get_tashkent_time_bounds():
    tz = timezone(timedelta(hours=5))
    now = datetime.now(tz)

    today_start_local = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_utc = today_start_local.astimezone(timezone.utc).replace(tzinfo=None)

    month_start_local = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_start_utc = month_start_local.astimezone(timezone.utc).replace(tzinfo=None)

    return now.strftime("%d.%m.%Y %H:%M"), today_start_utc, month_start_utc


def statistics_keyboard(current_section: str = "general") -> InlineKeyboardBuilder:
    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(
            text="📊 Umumiy" if current_section != "general" else "• 📊 Umumiy •",
            callback_data="admin_stat_general",
            style="primary" if current_section != "general" else "success",
        ),
        InlineKeyboardButton(
            text="📅 Bugungi" if current_section != "today" else "• 📅 Bugungi •",
            callback_data="admin_stat_today",
            style="primary" if current_section != "today" else "success",
        ),
        InlineKeyboardButton(
            text="📆 Oylik" if current_section != "month" else "• 📆 Oylik •",
            callback_data="admin_stat_month",
            style="primary" if current_section != "month" else "success",
        ),
    )
    ikb.row(
        InlineKeyboardButton(
            text="🔄 Yangilash",
            callback_data=f"admin_stat_{current_section}",
            style="primary",
        )
    )
    return ikb


async def get_general_statistics_text(session) -> str:
    now_str, _, _ = get_tashkent_time_bounds()

    total_users = (await session.scalar(select(func.count(User.id)))) or 0
    blocked_users = (
        await session.scalar(select(func.count(User.id)).where(User.is_blocked == True))
    ) or 0
    active_users = total_users - blocked_users

    total_reminders = (await session.scalar(select(func.count(Reminder.id)))) or 0
    active_reminders = (
        await session.scalar(
            select(func.count(Reminder.id)).where(Reminder.is_active == True)
        )
    ) or 0

    total_baskets = (await session.scalar(select(func.count(Basket.id)))) or 0
    total_basket_words = (
        await session.scalar(select(func.count(BasketWord.id)))
    ) or 0

    total_tests = (await session.scalar(select(func.count(TestScore.id)))) or 0
    avg_test_score = (
        await session.scalar(select(func.avg(TestScore.percentage)))
    ) or 0.0

    return (
        f"📊 <b>Botning umumiy statistikasi</b>\n"
        f"🕒 <i>Holat: {now_str}</i>\n\n"
        f"👥 <b>Foydalanuvchilar:</b>\n"
        f"  ├ Jami: <b>{total_users}</b> ta\n"
        f"  ├ Faol: <b>{active_users}</b> ta\n"
        f"  └ Bloklagan: <b>{blocked_users}</b> ta\n\n"
        f"⏰ <b>Eslatmalar (Reminder):</b>\n"
        f"  ├ Jami sozlangan: <b>{total_reminders}</b> ta\n"
        f"  └ Hozir faol: <b>{active_reminders}</b> ta\n\n"
        f"🛒 <b>Savatchalar (Lug'at):</b>\n"
        f"  ├ Jami savatchalar: <b>{total_baskets}</b> ta\n"
        f"  └ Saqlangan so'zlar: <b>{total_basket_words}</b> ta\n\n"
        f"📝 <b>Test & Natijalar:</b>\n"
        f"  ├ Jami yechilgan testlar: <b>{total_tests}</b> ta\n"
        f"  └ O'rtacha natija: <b>{avg_test_score:.1f}%</b>"
    )


async def get_today_statistics_text(session) -> str:
    now_str, today_start_utc, _ = get_tashkent_time_bounds()

    today_active = (
        await session.scalar(
            select(func.count(User.id)).where(User.last_activity >= today_start_utc)
        )
    ) or 0

    today_tests = (
        await session.scalar(
            select(func.count(TestScore.id)).where(
                TestScore.created_at >= today_start_utc
            )
        )
    ) or 0

    today_avg_score = (
        await session.scalar(
            select(func.avg(TestScore.percentage)).where(
                TestScore.created_at >= today_start_utc
            )
        )
    ) or 0.0

    today_basket_words = (
        await session.scalar(
            select(func.count(BasketWord.id)).where(
                BasketWord.created_at >= today_start_utc
            )
        )
    ) or 0

    return (
        f"📅 <b>Bugungi kunlik hisobot</b>\n"
        f"🕒 <i>Sana: {now_str}</i>\n\n"
        f"🟢 <b>Bugungi faollik:</b>\n"
        f"  ├ Bugun kirgan foydalanuvchilar (DAU): <b>{today_active}</b> ta\n"
        f"  ├ Bugun yechilgan testlar: <b>{today_tests}</b> ta\n"
        f"  ├ Bugungi o'rtacha test balli: <b>{today_avg_score:.1f}%</b>\n"
        f"  └ Savatga qo'shilgan so'zlar: <b>{today_basket_words}</b> ta"
    )


async def get_month_statistics_text(session) -> str:
    now_str, _, month_start_utc = get_tashkent_time_bounds()

    month_active = (
        await session.scalar(
            select(func.count(User.id)).where(User.last_activity >= month_start_utc)
        )
    ) or 0

    month_tests = (
        await session.scalar(
            select(func.count(TestScore.id)).where(
                TestScore.created_at >= month_start_utc
            )
        )
    ) or 0

    month_avg_score = (
        await session.scalar(
            select(func.avg(TestScore.percentage)).where(
                TestScore.created_at >= month_start_utc
            )
        )
    ) or 0.0

    month_basket_words = (
        await session.scalar(
            select(func.count(BasketWord.id)).where(
                BasketWord.created_at >= month_start_utc
            )
        )
    ) or 0

    # Top 5 monthly users
    top_query = (
        select(
            TestScore.user_name,
            TestScore.user_id,
            func.count(TestScore.id).label("test_count"),
            func.avg(TestScore.percentage).label("avg_pct"),
        )
        .where(TestScore.created_at >= month_start_utc)
        .group_by(TestScore.user_id, TestScore.user_name)
        .order_by(func.count(TestScore.id).desc())
        .limit(5)
    )
    top_rows = (await session.execute(top_query)).all()

    top_text = ""
    if top_rows:
        top_text = "\n\n🏆 <b>Shu oyning eng faol foydalanuvchilari:</b>\n"
        for i, row in enumerate(top_rows, 1):
            name = row.user_name or f"User {row.user_id}"
            top_text += f"  {i}. {name} — <b>{row.test_count}</b> ta test ({row.avg_pct:.1f}%)\n"

    return (
        f"📆 <b>Oylik hisobot</b>\n"
        f"🕒 <i>Holat: {now_str}</i>\n\n"
        f"📈 <b>Shu oydagi ko'rsatkichlar:</b>\n"
        f"  ├ Oylik faol foydalanuvchilar (MAU): <b>{month_active}</b> ta\n"
        f"  ├ Shu oyda yechilgan testlar: <b>{month_tests}</b> ta\n"
        f"  ├ Oylik o'rtacha natija: <b>{month_avg_score:.1f}%</b>\n"
        f"  └ Savatga qo'shilgan so'zlar: <b>{month_basket_words}</b> ta"
        f"{top_text}"
    )


@router.message(Command("statistics", "stats"))
async def statistics_handler(message: Message):
    async with get_async_session_context() as session:
        text = await get_general_statistics_text(session)

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=statistics_keyboard("general").as_markup(),
    )


@router.callback_query(F.data == "admin_stat_general")
async def callback_stat_general(callback: CallbackQuery):
    async with get_async_session_context() as session:
        text = await get_general_statistics_text(session)

    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=statistics_keyboard("general").as_markup(),
        )
    except TelegramBadRequest:
        pass
    await callback.answer("📊 Umumiy statistika yangilandi")


@router.callback_query(F.data == "admin_stat_today")
async def callback_stat_today(callback: CallbackQuery):
    async with get_async_session_context() as session:
        text = await get_today_statistics_text(session)

    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=statistics_keyboard("today").as_markup(),
        )
    except TelegramBadRequest:
        pass
    await callback.answer("📅 Bugungi hisobot yangilandi")


@router.callback_query(F.data == "admin_stat_month")
async def callback_stat_month(callback: CallbackQuery):
    async with get_async_session_context() as session:
        text = await get_month_statistics_text(session)

    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=statistics_keyboard("month").as_markup(),
        )
    except TelegramBadRequest:
        pass
    await callback.answer("📆 Oylik hisobot yangilandi")
