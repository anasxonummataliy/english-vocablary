from functools import cache
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bot.config import settings


@cache
def get_async_engine():
    return create_async_engine(
        url=settings.db_url, pool_size=3, max_overflow=5, future=True
    )


@cache
def get_session_maker() -> async_sessionmaker[AsyncSession]:
    engine = get_async_engine()
    return async_sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )


@asynccontextmanager
async def get_async_session_context():
    session_maker = get_session_maker()
    async with session_maker() as new_session:
        try:
            yield new_session
        except Exception:
            await new_session.rollback()
            raise
        finally:
            await new_session.close()
