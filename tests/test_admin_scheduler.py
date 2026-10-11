import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from bot.admin.scheduler import get_book_info, render_scheduler_card, cmd_scheduler
from bot.admin.commands import admin_commands


def test_admin_commands_includes_scheduler():
    command_names = [c.command for c in admin_commands]
    assert "scheduler" in command_names


def test_get_book_info():
    title, units = get_book_info("essential1")
    assert "4000 Essential English Words 1" in title
    assert units == 30


def test_render_scheduler_card():
    mock_data = {
        "channel_id": "-1001234567890",
        "book_slug": "essential1",
        "current_unit": 3,
        "send_time": "09:00",
        "is_active": 1,
        "last_sent_date": "2026-10-11",
        "finish_message": "Tugadi!",
    }
    text, kb = render_scheduler_card(mock_data)
    assert "Kanal Scheduler Boshqaruvi" in text
    assert "-1001234567890" in text
    assert "4000 Essential English Words 1" in text
    assert "3</b> / 30" in text
    assert "09:00" in text
    assert "🟢 FAOL" in text

    # Check button callbacks
    callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "sched:toggle:-1001234567890" in callbacks
    assert "sched:test:-1001234567890" in callbacks
    assert "sched:next:-1001234567890" in callbacks
    assert "sched:prev:-1001234567890" in callbacks
    assert "sched:setup:-1001234567890" in callbacks
    assert "sched:refresh:-1001234567890" in callbacks


@pytest.mark.asyncio
async def test_cmd_scheduler_renders_card():
    mock_sched = {
        "channel_id": "@mychannel",
        "book_slug": "essential1",
        "current_unit": 1,
        "send_time": "09:00",
        "is_active": 1,
    }
    with patch("bot.admin.scheduler.get_all_channel_schedulers", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = [mock_sched]
        message = AsyncMock()
        state = AsyncMock()

        await cmd_scheduler(message, state)

        state.clear.assert_awaited_once()
        message.answer.assert_awaited_once()
        args, kwargs = message.answer.call_args
        assert "@mychannel" in args[0]
