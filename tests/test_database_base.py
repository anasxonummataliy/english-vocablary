import pytest
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    inspect,
)


@pytest.mark.asyncio
async def test_create_db_and_tables_adds_missing_reminder_columns(monkeypatch):
    sync_engine = create_engine("sqlite:///:memory:")

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

    metadata.create_all(sync_engine)

    class FakeBeginContext:
        def __init__(self, connection):
            self.connection = connection

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def run_sync(self, fn):
            return fn(self.connection)

    class FakeAsyncEngine:
        def __init__(self, connection):
            self.connection = connection

        def begin(self):
            return FakeBeginContext(self.connection)

    connection = sync_engine.connect()
    fake_engine = FakeAsyncEngine(connection)

    from bot.database import base as base_module

    monkeypatch.setattr(base_module, "get_async_engine", lambda: fake_engine)
    await base_module.create_db_and_tables()

    columns = [c["name"] for c in inspect(connection).get_columns("reminders")]
    connection.close()

    assert "weekdays" in columns
    assert "reminder_times" in columns
