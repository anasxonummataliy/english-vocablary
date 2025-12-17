from aiogram.filters import Command

from aiogram import Router
from sqlalchemy import select
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.utils.markdown import hbold, hcode, text

from bot.database.models.users import User
from bot.database.session import get_async_session_context


router = Router()


@router.message(Command("users"))
async def get_users(message: Message):
    async with get_async_session_context() as session:
        smtm = select(User)
        result = await session.execute(smtm)
        users = result.scalars().all()
        if not users:
            await message.answer("Hali foydalanuvchilar yo'q.")
            return
    users_lines = []
    header = 'USERS\n\n'
    for i, user in enumerate(users, start=1):
        line = text(
            hcode(f"ID: {user.id}"),
            hbold(f"Fullname: {user.first_name} {user.last_name or ''}"),
            f"Username: (@{user.username or 'username yo‘q'})",
            hcode(f"Telegram ID: {user.tg_id}"),
            sep="\n",
        )
        users_lines.append(line)

    users_message = "\n\n".join(users_lines)
    await message.answer(header+users_message, parse_mode="HTML")
