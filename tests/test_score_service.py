import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from bot.database.base import Base
import bot.services.score_service as score_service_module
from bot.services.score_service import (
    save_score,
    get_unit_leaderboard,
    get_group_leaderboard,
    get_global_leaderboard,
)


@pytest.mark.asyncio
async def test_save_score_and_leaderboards(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSessionLocal = async_sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False, class_=AsyncSession
    )

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_get_async_session_context():
        async with TestSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    monkeypatch.setattr(
        score_service_module, "get_async_session_context", mock_get_async_session_context
    )

    score1 = await save_score(
        user_id=1001,
        user_name="Ali",
        chat_id=-10012345,
        level="elementary",
        unit_num=5,
        test_mode="uz_en",
        score=9,
        total_questions=10,
    )
    assert score1.percentage == 90.0

    score2 = await save_score(
        user_id=1002,
        user_name="Vali",
        chat_id=-10012345,
        level="elementary",
        unit_num=5,
        test_mode="uz_en",
        score=10,
        total_questions=10,
    )
    assert score2.percentage == 100.0

    # Test unit leaderboard
    unit_lb = await get_unit_leaderboard("elementary", 5)
    assert len(unit_lb) >= 2
    assert unit_lb[0].user_id == 1002

    # Test group leaderboard
    group_lb = await get_group_leaderboard(-10012345)
    assert len(group_lb) >= 2

    # Test global leaderboard
    global_lb = await get_global_leaderboard()
    assert len(global_lb) >= 2

    await engine.dispose()
