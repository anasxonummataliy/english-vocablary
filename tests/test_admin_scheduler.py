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


@pytest.mark.asyncio
async def test_send_unit_to_channel_includes_finish_message():
    from api.services.channel_scheduler_service import send_unit_to_channel
    with patch("api.services.channel_scheduler_service.bot.send_message", new_callable=AsyncMock) as mock_send:
        with patch("api.services.channel_scheduler_service.bot.send_poll", new_callable=AsyncMock) as mock_poll:
            with patch("asyncio.sleep", new_callable=AsyncMock):
                sent = await send_unit_to_channel(
                    channel_id="@testchannel",
                    book_slug="essential1",
                    unit_num=1,
                    finish_message="Unit 1 tugadi!"
                )
                assert sent is True

            # Polls were sent for all 20 words in essential1 unit 1
            assert mock_poll.call_count == 20
            first_poll_kwargs = mock_poll.call_args_list[0].kwargs
            assert first_poll_kwargs["type"] == "quiz"
            assert "open_period" not in first_poll_kwargs  # No timer!
            assert first_poll_kwargs["is_anonymous"] is True
            assert len(first_poll_kwargs["options"]) == 4

            # Finish message sent at the end
            assert mock_send.call_count >= 2
            last_call_kwargs = mock_send.call_args_list[-1].kwargs
            assert last_call_kwargs["text"] == "Unit 1 tugadi!"
            assert last_call_kwargs["chat_id"] == "@testchannel"
