import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.enums import ChatType
from bot.routers.help import help_handler, fallback_user_message_handler


@pytest.mark.asyncio
async def test_help_handler_private():
    message = AsyncMock()
    message.chat = MagicMock(type=ChatType.PRIVATE)
    message.answer = AsyncMock()

    await help_handler(message)
    message.answer.assert_called_once()
    called_text = message.answer.call_args[0][0]
    assert "Botdan qanday foydalanish mumkin?" in called_text


@pytest.mark.asyncio
async def test_help_handler_group():
    message = AsyncMock()
    message.chat = MagicMock(type=ChatType.GROUP)
    message.answer = AsyncMock()

    await help_handler(message)
    message.answer.assert_called_once()
    called_text = message.answer.call_args[0][0]
    assert "Guruhda botdan foydalanish" in called_text


@pytest.mark.asyncio
async def test_fallback_user_message_handler():
    message = AsyncMock()
    message.chat = MagicMock(type=ChatType.PRIVATE)
    message.answer = AsyncMock()

    await fallback_user_message_handler(message)
    message.answer.assert_called_once()
    called_text = message.answer.call_args[0][0]
    assert "Sizga qanday yordam bera olaman?" in called_text
    assert "English Vocabulary in Use" in called_text
