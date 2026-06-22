import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from bot.database.models.users import User
from bot.database.session import get_async_session_context
from bot.main import dp, bot, start_bot
from aiogram.types import Update
from contextlib import asynccontextmanager
from bot.database.base import redis_client

TEMPLATES_DIR = Path(__file__).parent / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_bot()
    yield
    await bot.close()


app = FastAPI(lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = TEMPLATES_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/api/users")
async def get_users_json():
    async with get_async_session_context() as session:
        stmt = select(User).order_by(User.id.desc())
        result = await session.execute(stmt)
        users = result.scalars().all()

    return [
        {
            "id": u.id,
            "tg_id": u.tg_id,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "username": u.username,
            "is_blocked": u.is_blocked,
            "last_activity": u.last_activity.isoformat() if u.last_activity else None,
        }
        for u in users
    ]


@app.post("/webhook")
async def webhook_handler(request: Request):
    try:
        data = await request.json()
        update = Update.model_validate(data, context={"bot": bot})
    except Exception as e:
        return {"status": "error", "message": str(e)}

    try:
        await dp.feed_update(bot, update, redis=redis_client)
    except Exception as e:
        logging.exception(f"Error processing update {update.update_id}: {e}")

    return {"status": "ok"}
