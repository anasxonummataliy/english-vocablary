from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy import select, func

from bot.database.models.users import User
from bot.database.session import get_async_session_context

router = Router()


@router.message(Command("statistics"))
async def statistics_handler(message: Message):
    async with get_async_session_context() as session:
        total_users = await session.scalar(select(func.count(User.id)))

        blocked_users = await session.scalar(
            select(func.count(User.id)).where(User.is_blocked == True)
        ) or 0

        active_users = total_users - blocked_users
    await message.answer(
        f"📊 <b>Bot statistikasi</b>\n\n"
        f"👥 Jami foydalanuvchilar: {total_users}\n"
        f"✅ Aktiv: {active_users}\n"
        f"❌ Bloklagan: {blocked_users}", parse_mode='HTML'
    )
