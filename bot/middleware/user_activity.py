from datetime import datetime
from aiogram import BaseMiddleware, types
from sqlalchemy import select

from bot.database.models.users import User
from bot.database.session import get_async_session_context

class UserActivityMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: types.Message, data):
        if isinstance(event, types.Message) and event.from_user:
            async with get_async_session_context() as session:
                result = await session.execute(
                    select(User).where(User.tg_id == event.from_user.id)
                )
                user = result.scalar_one_or_none()
                if user:
                    user.last_activity = datetime.now()
                    if user.is_blocked:
                        user.is_blocked = False
                    user.last_activity = datetime.now()
                    await session.commit()

        return await handler(event, data)