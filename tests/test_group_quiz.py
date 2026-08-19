import json
import pytest
from unittest.mock import AsyncMock
from bot.routers.user_commands import user_command, group_command
from bot.routers.group_quiz import _schedule_next_gquiz_step


def test_command_definitions():
    user_cmds = [c.command for c in user_command]
    group_cmds = [c.command for c in group_command]

    assert "start" in user_cmds
    assert "top" in user_cmds

    assert "quiz" in group_cmds
    assert "top" in group_cmds
    assert "help" in group_cmds


@pytest.mark.asyncio
async def test_schedule_next_gquiz_step_pauses_on_2_unanswered(monkeypatch):
    import asyncio
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())

    bot = AsyncMock()
    redis = AsyncMock()

    quiz_data = {
        "current_index": 1,
        "current_poll_id": "poll123",
        "is_paused": False,
        "current_question_answered": False,
        "unanswered_count": 1,
        "questions": [{"uzbek": "test", "word": "test"}],
    }

    redis.get.return_value = json.dumps(quiz_data).encode()

    await _schedule_next_gquiz_step(bot, 12345, 1, "poll123", redis)

    bot.send_message.assert_called_once()
    call_args = bot.send_message.call_args[1]
    assert "Musobaqa pauza qilindi" in call_args["text"]
    assert "Ketma-ket <b>2 ta</b> savolga hech kim javob bermadi" in call_args["text"]


@pytest.mark.asyncio
async def test_cmd_start_group_quiz_in_private_chat():
    from bot.routers.group_quiz import cmd_start_group_quiz
    from aiogram.enums import ChatType
    from unittest.mock import MagicMock

    message = AsyncMock()
    message.chat = MagicMock()
    message.chat.type = ChatType.PRIVATE
    redis = AsyncMock()

    await cmd_start_group_quiz(message, redis)

    message.answer.assert_called_once()
    args, kwargs = message.answer.call_args
    assert "Bu buyruq faqat guruhlarda ishlaydi" in args[0]
    redis.get.assert_not_called()


@pytest.mark.asyncio
async def test_force_stop_gquiz_in_private_chat():
    from bot.routers.group_quiz import force_stop_gquiz
    from aiogram.enums import ChatType
    from unittest.mock import MagicMock

    message = AsyncMock()
    message.chat = MagicMock()
    message.chat.type = ChatType.PRIVATE
    message.chat.id = 123
    message.from_user.id = 456
    redis = AsyncMock()
    bot = AsyncMock()

    await force_stop_gquiz(message, redis, bot)

    message.answer.assert_called_once()
    args, kwargs = message.answer.call_args
    assert "Bu buyruq faqat guruhlarda ishlaydi" in args[0]
    redis.delete.assert_not_called()

