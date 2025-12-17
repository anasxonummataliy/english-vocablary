from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from bot.config import settings

async_engine = create_async_engine(settings.db_url)

SessionLocal = async_sessionmaker(
    async_engine, expire_on_commit=False, class_=AsyncSession
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


@asynccontextmanager
async def get_async_context_session() -> AsyncGenerator[AsyncSession, None]:
    session_maker = SessionLocal()
    async with session_maker as new_session:
        yield new_session
