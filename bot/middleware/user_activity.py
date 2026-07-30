from datetime import datetime

from aiogram import BaseMiddleware, types
from aiogram.enums import ChatType
from sqlalchemy import select

from bot.database.models.users import User
from bot.database.session import get_async_session_context


class UserActivityMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: types.Message, data):
        if not isinstance(event, (types.Message, types.CallbackQuery)):
            return await handler(event, data)

        if not event.from_user:
            return await handler(event, data)

        chat = event.chat if isinstance(event, types.Message) else event.message.chat
        if chat.type != ChatType.PRIVATE:
            return await handler(event, data)

        async with get_async_session_context() as session:
            result = await session.execute(
                select(User).where(User.tg_id == event.from_user.id)
            )
            user = result.scalar_one_or_none()
            if user:
                user.last_activity = datetime.utcnow()
                if user.is_blocked:
                    user.is_blocked = False
                await session.commit()

        return await handler(event, data)

