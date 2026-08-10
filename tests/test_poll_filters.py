import pytest
from unittest.mock import AsyncMock
from aiogram.types import PollAnswer
from bot.routers.group_quiz import _is_gquiz_poll
from bot.routers.test_router import _is_test_poll


@pytest.mark.asyncio
async def test_is_gquiz_poll():
    poll_answer = AsyncMock(spec=PollAnswer)
    poll_answer.poll_id = "12345"

    redis = AsyncMock()

    redis.exists.return_value = 1
    assert await _is_gquiz_poll(poll_answer, redis) is True
    redis.exists.assert_called_with("gquiz_poll:12345")

    redis.exists.return_value = 0
    assert await _is_gquiz_poll(poll_answer, redis) is False


@pytest.mark.asyncio
async def test_is_test_poll():
    poll_answer = AsyncMock(spec=PollAnswer)
    poll_answer.poll_id = "67890"

    redis = AsyncMock()

    redis.exists.return_value = 1
    assert await _is_test_poll(poll_answer, redis) is True
    redis.exists.assert_called_with("poll_user:67890")

    redis.exists.return_value = 0
    assert await _is_test_poll(poll_answer, redis) is False
