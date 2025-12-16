from aiogram.filters import Command

from aiogram import Router
from aiogram.types import Message

from bot.database.session import session
from bot.database.models.users import User

router = Router()
@router.message(Command('users'))
async def get_users(message: Message):
    users = session.query(User).all()
    if not users:
        await message.answer("Hali foydalanuvchilar yo'q.")
        return
    users_list = "\n".join([f"{user.id}: {user.first_name} {user.last_name} @{user.username}" for user in users])
    await message.answer(users_list)