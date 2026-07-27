from bot.database.session import get_async_engine
from sqlalchemy import Column, DateTime, func, inspect
from sqlalchemy.orm import DeclarativeBase, declared_attr
from redis.asyncio import Redis
from bot.core.config import settings

redis_client = Redis(
    host=settings.redis_host, port=settings.redis_port, decode_responses=True
)


class Base(DeclarativeBase):
    @declared_attr
    def created_at(cls):
        return Column(DateTime, default=func.now())

    @declared_attr
    def updated_at(cls):
        return Column(DateTime, default=func.now(), onupdate=func.now())


async def create_db_and_tables():
    async with get_async_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def _ensure_reminder_columns(sync_conn):
            inspector = inspect(sync_conn)
            if "reminders" not in inspector.get_table_names():
                return

            existing_columns = {
                column["name"] for column in inspector.get_columns("reminders")
            }
            for column_name in ("weekdays", "reminder_times"):
                if column_name not in existing_columns:
                    sync_conn.exec_driver_sql(
                        f"ALTER TABLE reminders ADD COLUMN {column_name} VARCHAR"
                    )

        await conn.run_sync(_ensure_reminder_columns)
