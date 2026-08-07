from datetime import datetime

from aiogram import BaseMiddleware, types
from aiogram.enums import ChatType
from sqlalchemy import select

from bot.database.models.users import User
from bot.database.session import get_async_session_context
from bot.services.reminder_service import advance_reminder_for_unit


def _extract_unit_id_from_callback(data_str: str) -> int | None:
    prefixes = ("words_Unit_", "flash_Unit_", "test_Unit_", "rem_skip_")
    for prefix in prefixes:
        if data_str.startswith(prefix):
            suffix = data_str.removeprefix(prefix)
            if suffix.isdigit():
                return int(suffix)
    return None


class UserActivityMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: types.Message | types.CallbackQuery, data):
        if not isinstance(event, (types.Message, types.CallbackQuery)):
            return await handler(event, data)

        if not event.from_user:
            return await handler(event, data)

        chat = event.chat if isinstance(event, types.Message) else event.message.chat
        if chat and chat.type != ChatType.PRIVATE:
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

        handler_result = await handler(event, data)

        # Advance reminder ONLY if the user clicked learning words, flashcards, test, or completed button for that unit
        if isinstance(event, types.CallbackQuery) and event.data:
            unit_id = _extract_unit_id_from_callback(event.data)
            if unit_id is not None:
                await advance_reminder_for_unit(event.from_user.id, unit_id)

        return handler_result
