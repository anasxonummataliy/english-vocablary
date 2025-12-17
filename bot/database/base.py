from bot.database.session import get_async_engine
from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import DeclarativeBase, declared_attr


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
