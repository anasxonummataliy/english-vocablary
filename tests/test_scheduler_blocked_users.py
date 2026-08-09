import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import SendMessage

from bot.database.models.reminders import Reminder
from bot.database.models.users import User
from bot.services.reminder_scheduler import (
    handle_blocked_user,
    process_due_reminders,
)


@pytest.mark.asyncio
async def test_handle_blocked_user_deactivates_reminder_and_marks_user_blocked():
    tg_id = 123456789
    reminder = Reminder(
        tg_id=tg_id,
        level="📗 Elementary",
        current_unit=1,
        interval_hours=24,
        is_active=True,
    )
    user = User(tg_id=tg_id, is_blocked=False)

    mock_session = AsyncMock()

    def mock_execute(stmt):
        stmt_str = str(stmt)
        res = MagicMock()
        if "FROM reminders" in stmt_str or "reminders" in stmt_str:
            res.scalar_one_or_none.return_value = reminder
        elif "FROM users" in stmt_str or "users" in stmt_str:
            res.scalar_one_or_none.return_value = user
        else:
            res.scalar_one_or_none.return_value = None
        return res

    mock_session.execute.side_effect = mock_execute

    class FakeSessionContext:
        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, exc_type, exc, tb):
            return None

    with patch(
        "bot.services.reminder_scheduler.get_async_session_context",
        return_value=FakeSessionContext(),
    ):
        await handle_blocked_user(tg_id)

    assert reminder.is_active is False
    assert user.is_blocked is True
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_process_due_reminders_catches_forbidden_error():
    tg_id = 1825357821
    reminder = Reminder(
        tg_id=tg_id,
        level="📗 Elementary",
        current_unit=1,
        interval_hours=24,
        is_active=True,
        next_reminder_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )

    mock_session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [reminder]
    mock_session.execute.return_value = mock_res

    class FakeSessionContext:
        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, exc_type, exc, tb):
            return None

    forbidden_exc = TelegramForbiddenError(
        method=SendMessage(chat_id=tg_id, text="test"),
        message="Forbidden: bot was blocked by the user",
    )

    mock_bot = AsyncMock()

    with patch(
        "bot.services.reminder_scheduler.get_async_session_context",
        return_value=FakeSessionContext(),
    ), patch(
        "bot.services.reminder_scheduler.send_unit_reminder",
        side_effect=forbidden_exc,
    ), patch(
        "bot.services.reminder_scheduler.handle_blocked_user",
        new_callable=AsyncMock,
    ) as mock_handle_blocked:
        await process_due_reminders(mock_bot)

        mock_handle_blocked.assert_called_once_with(tg_id)
