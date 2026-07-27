import pytest
from sqlalchemy import MetaData, Table, Column, Integer, String, DateTime, Boolean, BigInteger, inspect
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.mark.asyncio
async def test_create_db_and_tables_adds_missing_reminder_columns(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    metadata = MetaData()
    Table(
        "reminders",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("tg_id", BigInteger, unique=True),
        Column("level", String),
        Column("current_unit", Integer),
        Column("interval_hours", Integer),
        Column("is_active", Boolean),
        Column("next_reminder_at", DateTime),
        Column("last_reminded_at", DateTime, nullable=True),
    )

    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)

    from bot.database import base as base_module

    monkeypatch.setattr(base_module, "get_async_engine", lambda: engine)
    await base_module.create_db_and_tables()

    async with engine.begin() as conn:
        columns = await conn.run_sync(lambda sync_conn: [c["name"] for c in inspect(sync_conn).get_columns("reminders")])

    assert "weekdays" in columns
    assert "reminder_times" in columns
