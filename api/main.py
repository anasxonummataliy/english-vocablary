import asyncio
from fastapi import FastAPI, Request
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


@app.post("/webhook")
async def webhook_handler(request: Request):
    try:
        data = await request.json()
        update = Update.model_validate(data, context={"bot": bot})
    except Exception as e:
        return {"status": "error", "message": str(e)}

    await dp.feed_update(bot, update, redis=redis_client)
    return {"status": "ok"}
