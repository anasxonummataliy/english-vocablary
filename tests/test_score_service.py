import pytest
from unittest.mock import AsyncMock, MagicMock
import bot.services.score_service as score_service_module
from bot.services.score_service import (
    save_score,
    get_unit_leaderboard,
    get_group_leaderboard,
    get_global_leaderboard,
)


@pytest.mark.asyncio
async def test_save_score(monkeypatch):
    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_get_async_session_context():
        yield mock_session

    monkeypatch.setattr(
        score_service_module, "get_async_session_context", mock_get_async_session_context
    )

    result = await save_score(
        user_id=1001,
        user_name="Ali",
        chat_id=-10012345,
        level="elementary",
        unit_num=5,
        test_mode="uz_en",
        score=9,
        total_questions=10,
    )

    assert result.user_id == 1001
    assert result.percentage == 90.0
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_leaderboard_queries(monkeypatch):
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = [
        (1002, 10, 100.0, "Vali", "vali_username"),
        (1001, 9, 90.0, "Ali", "ali_username"),
    ]
    mock_session.execute.return_value = mock_result

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_get_async_session_context():
        yield mock_session

    monkeypatch.setattr(
        score_service_module, "get_async_session_context", mock_get_async_session_context
    )

    unit_lb = await get_unit_leaderboard("elementary", 5)
    assert len(unit_lb) == 2
    assert unit_lb[0][0] == 1002

    group_lb = await get_group_leaderboard(-10012345)
    assert len(group_lb) == 2

    global_lb = await get_global_leaderboard()
    assert len(global_lb) == 2
