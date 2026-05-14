from fastapi import FastAPI, Request
from sqlalchemy import select
from bot.database.models.users import User
from bot.database.session import get_async_session_context
from bot.main import dp, bot, start_bot
from aiogram.types import Update
from contextlib import asynccontextmanager
from bot.database.base import redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_bot()
    yield
    await bot.close()


app = FastAPI(lifespan=lifespan)


@app.get("/users")
async def get_users():
    async with get_async_session_context() as session:
        stmt = select(User)
        result = await session.execute(stmt)
    return result.scalars().all()


@app.post("/webhook")
async def webhook_handler(request: Request):
    try:
        data = await request.json()
        update = Update.model_validate(data, context={"bot": bot})
    except Exception as e:
        return {"status": "error", "message": str(e)}

    await dp.feed_update(bot, update, redis=redis_client)
    return {"status": "ok"}
