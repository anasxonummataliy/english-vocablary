from datetime import datetime

from aiogram import BaseMiddleware, Bot, types
from aiogram.enums import ChatType
from sqlalchemy import select
from redis.asyncio import Redis

from bot.database.models.users import User
from bot.database.session import get_async_session_context
from bot.services.reminder_service import (
    auto_advance_reminder_on_activity,
    format_user_time,
    send_unit_reminder,
)


def _is_reminder_management_action(event: types.Message | types.CallbackQuery) -> bool:
    if isinstance(event, types.Message):
        return bool(event.text and event.text.startswith("/reminder"))

    return bool(event.data and event.data.startswith("rem_"))


class UserActivityMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: types.Message, data):
        if not isinstance(event, (types.Message, types.CallbackQuery)):
            return await handler(event, data)

        if not event.from_user:
            return await handler(event, data)

        if _is_reminder_management_action(event):
            return await handler(event, data)

        chat = event.chat if isinstance(event, types.Message) else event.message.chat
        if chat.type != ChatType.PRIVATE:
            return await handler(event, data)

        bot: Bot = data["bot"]
        redis: Redis | None = data.get("redis")

        async with get_async_session_context() as session:
            result = await session.execute(
                select(User).where(User.tg_id == event.from_user.id)
            )
            user = result.scalar_one_or_none()
            previous_last_activity = user.last_activity if user else None
            if user:
                user.last_activity = datetime.utcnow()
                if user.is_blocked:
                    user.is_blocked = False
                await session.commit()

        handler_result = await handler(event, data)

        if not redis or not user:
            return handler_result

        reminder = await auto_advance_reminder_on_activity(
            event.from_user.id,
            previous_last_activity,
            activity_at=datetime.utcnow(),
        )
        if reminder and reminder.is_active:
            await send_unit_reminder(
                bot,
                event.from_user.id,
                reminder.level,
                reminder.current_unit,
                redis,
                intro=(
                    "✅ Siz botda faollik ko'rsatdingiz. Keyingi unit:\n"
                    f"🕐 Keyingi eslatma: <b>{format_user_time(reminder.next_reminder_at)}</b>\n\n"
                ),
            )

        return handler_result
