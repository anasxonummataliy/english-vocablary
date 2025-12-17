from aiogram.filters import Command

from aiogram import Router
from sqlalchemy import select
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.users import User
from bot.database.session import get_async_context_session


router = Router()
@router.message(Command('users'))
async def get_users(message: Message):
    async with get_async_context_session() as session:
        smtm = select(User)
        result = await session.execute(smtm)
        users = result.scalars().all()
        if not users:
            await message.answer("Hali foydalanuvchilar yo'q.")
            return
    users_list = "\n".join([f"{user.id}: {user.first_name} {user.last_name} @{user.username}" for user in users])
    await message.answer(users_list)
