import os
import logging
import secrets
from datetime import timedelta
from pathlib import Path

from fastapi import FastAPI, Request, Response, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from bot.database.models.users import User
from bot.database.models.reminders import Reminder
from bot.database.session import get_async_session_context
from bot.main import dp, bot, start_bot, stop_bot
from aiogram.types import Update
from contextlib import asynccontextmanager
from bot.database.base import redis_client
from api.database import init_sqlite_db
from api.services.channel_scheduler_service import channel_scheduler_loop
from api.database import (
    get_all_channel_schedulers,
    get_channel_scheduler,
    save_channel_scheduler,
    update_channel_scheduler_status,
    delete_channel_scheduler,
)
from api.services.vocab_service import vocab_service
from api.services.channel_scheduler_service import send_unit_to_channel
import asyncio

TEMPLATES_DIR = Path(__file__).parent / "templates"

# Session tokenlari saqlanadi (oddiy in-memory)
active_sessions: set[str] = set()


def verify_credentials(login: str, password: str) -> bool:
    admin_login = os.getenv("ADMIN_LOGIN", "anasxon")
    admin_password = os.getenv("ADMIN_PASSWORD", "muslim1306")
    return login == admin_login and password == admin_password


def is_authenticated(session_token: str | None) -> bool:
    return session_token is not None and session_token in active_sessions


ALLOWED_UPDATES = [
    "message",
    "callback_query",
    "inline_query",
    "poll",
    "poll_answer",
]


async def webhook_watchdog_loop(webhook_url: str):
    """Periodic check to ensure Telegram webhook always points to our server."""
    if not webhook_url:
        return
    while True:
        try:
            await asyncio.sleep(120)  # Check every 2 minutes
            info = await bot.get_webhook_info()
            if info.url != webhook_url:
                logging.warning(
                    f"⚠️ Webhook URL mismatch detected! Current: '{info.url}', Expected: '{webhook_url}'. Restoring..."
                )
                await bot.set_webhook(
                    url=webhook_url,
                    allowed_updates=ALLOWED_UPDATES,
                    drop_pending_updates=False,
                    max_connections=40,
                )
                logging.info("✅ Webhook successfully restored by watchdog.")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.warning(f"Webhook watchdog error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_sqlite_db()
    channel_sched_task = asyncio.create_task(channel_scheduler_loop())
    webhook_url = os.getenv("WEBHOOK_URL") or ""
    watchdog_task = None
    try:
        await start_bot()
    except Exception as e:
        logging.warning(f"Bot startup warning: {e}")
    finally:
        if webhook_url:
            try:
                await bot.set_webhook(
                    url=webhook_url,
                    allowed_updates=ALLOWED_UPDATES,
                    drop_pending_updates=True,
                    max_connections=40,
                )
                logging.info("Webhook set with all required updates (message, callback_query, etc.)")
            except Exception as e:
                logging.warning(f"Webhook configuration warning: {e}")
            watchdog_task = asyncio.create_task(webhook_watchdog_loop(webhook_url))
    yield
    channel_sched_task.cancel()
    if watchdog_task:
        watchdog_task.cancel()
    try:
        await stop_bot()
    except Exception:
        pass


app = FastAPI(lifespan=lifespan, docs_url="/docs", redoc_url=None, openapi_url="/openapi.json")


@app.get("/login", response_class=HTMLResponse)
async def login_page(error: str = ""):
    error_html = ""
    if error:
        error_html = "<div class=\"error\">❌ Login yoki parol noto'g'ri</div>"

    html = f"""<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login — English Vocabulary Admin</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #090d0b;
            color: #e2e8f0;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }}
        .login-card {{
            background: #111a14;
            border: 1px solid rgba(16, 185, 129, 0.2);
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 4px 30px rgba(0,0,0,0.5);
            width: 100%;
            max-width: 380px;
        }}
        .login-card h1 {{
            text-align: center;
            margin-bottom: 8px;
            font-size: 1.5rem;
            color: #10b981;
        }}
        .login-card p {{
            text-align: center;
            color: #94a3b8;
            margin-bottom: 24px;
            font-size: 0.9rem;
        }}
        .form-group {{
            margin-bottom: 16px;
        }}
        .form-group label {{
            display: block;
            margin-bottom: 6px;
            font-weight: 500;
            color: #cbd5e1;
            font-size: 0.9rem;
        }}
        .form-group input {{
            width: 100%;
            padding: 12px 14px;
            background: #090d0b;
            color: #fff;
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 8px;
            font-size: 0.95rem;
            outline: none;
            transition: border-color 0.2s;
        }}
        .form-group input:focus {{ border-color: #10b981; box-shadow: 0 0 10px rgba(16, 185, 129, 0.3); }}
        .btn {{
            width: 100%;
            padding: 12px;
            background: #10b981;
            color: #052e16;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 700;
            cursor: pointer;
            margin-top: 8px;
            transition: all 0.2s;
        }}
        .btn:hover {{ background: #34d399; transform: translateY(-1px); }}
        .error {{
            background: rgba(239, 68, 68, 0.2);
            border: 1px solid rgba(239, 68, 68, 0.4);
            color: #f87171;
            padding: 10px 14px;
            border-radius: 8px;
            margin-bottom: 16px;
            font-size: 0.9rem;
            text-align: center;
        }}
        .back-link {{
            display: block;
            text-align: center;
            margin-top: 16px;
            color: #10b981;
            text-decoration: none;
            font-size: 0.85rem;
        }}
    </style>
</head>
<body>
    <div class="login-card">
        <h1>🔐 Admin Panel</h1>
        <p>English Vocabulary Bot</p>
        {error_html}
        <form method="POST" action="/login">
            <div class="form-group">
                <label for="login">Login</label>
                <input type="text" id="login" name="login" required autocomplete="username">
            </div>
            <div class="form-group">
                <label for="password">Parol</label>
                <input type="password" id="password" name="password" required autocomplete="current-password">
            </div>
            <button type="submit" class="btn">Kirish</button>
            <a href="/" class="back-link">← Web App ga qaytish</a>
        </form>
    </div>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    login = form.get("login", "")
    password = form.get("password", "")

    if verify_credentials(login, password):
        token = secrets.token_hex(32)
        active_sessions.add(token)
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            max_age=86400,  # 24 soat
            samesite="lax",
        )
        return response
    else:
        return RedirectResponse(url="/login?error=1", status_code=303)


@app.get("/logout")
async def logout(session_token: str | None = Cookie(default=None)):
    if session_token:
        active_sessions.discard(session_token)
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session_token")
    return response


@app.get("/")
async def root():
    return RedirectResponse(url="/admin", status_code=303)


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(session_token: str | None = Cookie(default=None)):
    if not is_authenticated(session_token):
        return RedirectResponse(url="/login", status_code=303)

    html_path = TEMPLATES_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/api/users")
async def get_users_json(session_token: str | None = Cookie(default=None)):
    if not is_authenticated(session_token):
        return Response(status_code=401, content="Unauthorized")

    async with get_async_session_context() as session:
        stmt = select(User).order_by(User.id.desc())
        result = await session.execute(stmt)
        users = result.scalars().all()
        reminder_result = await session.execute(select(Reminder.tg_id))
        reminder_tg_ids = set(reminder_result.scalars().all())

    TZ5 = timedelta(hours=5)
    return [
        {
            "id": u.id,
            "tg_id": u.tg_id,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "username": u.username,
            "is_blocked": u.is_blocked,
            "has_reminder": u.tg_id in reminder_tg_ids,
            "last_activity": (
                (u.last_activity + TZ5).isoformat() if u.last_activity else None
            ),
            "created_at": (u.created_at + TZ5).isoformat() if u.created_at else None,
        }
        for u in users
    ]


@app.get("/api/stats")
async def get_stats_json(session_token: str | None = Cookie(default=None)):
    if not is_authenticated(session_token):
        return Response(status_code=401, content="Unauthorized")

    from datetime import datetime
    from sqlalchemy import func
    from bot.database.models.channels import Channel

    TZ_OFFSET = timedelta(hours=5)
    now_utc = datetime.utcnow()
    now_tashkent = now_utc + TZ_OFFSET

    # Toshkent vaqtida kunning boshlari, lekin bazaga saqlash UTC sifatida bo'lgani uchun
    # SQL so'rovlarda UTC chegaralarini ishlatamiz
    week_dow = now_tashkent.weekday()  # 0=Monday

    today_start = (
        datetime(now_tashkent.year, now_tashkent.month, now_tashkent.day) - TZ_OFFSET
    )
    week_start = (
        datetime(now_tashkent.year, now_tashkent.month, now_tashkent.day)
        - timedelta(days=week_dow)
        - TZ_OFFSET
    )
    month_start = datetime(now_tashkent.year, now_tashkent.month, 1) - TZ_OFFSET

    async with get_async_session_context() as session:
        total = (await session.execute(select(func.count(User.id)))).scalar() or 0
        active = (
            await session.execute(
                select(func.count(User.id)).where(User.is_blocked == False)
            )
        ).scalar() or 0
        blocked = (
            await session.execute(
                select(func.count(User.id)).where(User.is_blocked == True)
            )
        ).scalar() or 0
        today_active = (
            await session.execute(
                select(func.count(User.id)).where(User.last_activity >= today_start)
            )
        ).scalar() or 0
        week_active = (
            await session.execute(
                select(func.count(User.id)).where(User.last_activity >= week_start)
            )
        ).scalar() or 0
        month_active = (
            await session.execute(
                select(func.count(User.id)).where(User.last_activity >= month_start)
            )
        ).scalar() or 0
        today_new = (
            await session.execute(
                select(func.count(User.id)).where(User.created_at >= today_start)
            )
        ).scalar() or 0
        week_new = (
            await session.execute(
                select(func.count(User.id)).where(User.created_at >= week_start)
            )
        ).scalar() or 0
        reminder_users = (
            await session.execute(select(func.count(Reminder.id)))
        ).scalar() or 0

        # Oxirgi 7 kun (Toshkent kunlari bo'yicha)
        daily_stats = []
        for i in range(6, -1, -1):
            day_tashkent = now_tashkent - timedelta(days=i)
            day_start_utc = (
                datetime(day_tashkent.year, day_tashkent.month, day_tashkent.day)
                - TZ_OFFSET
            )
            day_end_utc = day_start_utc + timedelta(days=1)
            count = (
                await session.execute(
                    select(func.count(User.id)).where(
                        User.last_activity >= day_start_utc,
                        User.last_activity < day_end_utc,
                    )
                )
            ).scalar() or 0
            daily_stats.append(
                {
                    "date": day_tashkent.strftime("%d/%m"),
                    "count": count,
                }
            )

        # Channels
        channels_result = await session.execute(select(Channel))
        channels = channels_result.scalars().all()

        channels_data = []
        for ch in channels:
            added_at = (
                ch.created_at if hasattr(ch, "created_at") and ch.created_at else None
            )
            users_at_join = (
                ch.users_at_join
                if hasattr(ch, "users_at_join") and ch.users_at_join is not None
                else None
            )

            if users_at_join is not None:
                before_count = users_at_join
                after_count = total - users_at_join
            elif added_at:
                before_count = (
                    await session.execute(
                        select(func.count(User.id)).where(User.created_at < added_at)
                    )
                ).scalar() or 0
                after_count = total - before_count
            else:
                before_count = 0
                after_count = total

            channels_data.append(
                {
                    "id": ch.id,
                    "tg_id": ch.tg_id,
                    "title": ch.channel_title,
                    "username": ch.channel_username,
                    "link": ch.channel_link,
                    "is_active": ch.is_active,
                    "added_at": added_at.isoformat() if added_at else None,
                    "users_before": before_count,
                    "users_after": max(after_count, 0),
                }
            )

    return {
        "total": total,
        "active": active,
        "blocked": blocked,
        "today_active": today_active,
        "week_active": week_active,
        "month_active": month_active,
        "today_new": today_new,
        "week_new": week_new,
        "reminder_users": reminder_users,
        "daily_stats": daily_stats,
        "channels": channels_data,
    }


@app.get("/api/channels")
async def get_channels_json(session_token: str | None = Cookie(default=None)):
    if not is_authenticated(session_token):
        return Response(status_code=401, content="Unauthorized")

    from bot.database.models.channels import Channel
    from sqlalchemy import func

    async with get_async_session_context() as session:
        total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
        channels_result = await session.execute(select(Channel))
        channels = channels_result.scalars().all()

    result = []
    for ch in channels:
        # Real kanal a'zolari soni
        try:
            member_count = await bot.get_chat_member_count(ch.tg_id)
        except Exception:
            member_count = None

        added_at = (
            ch.created_at if hasattr(ch, "created_at") and ch.created_at else None
        )
        users_at_join = (
            ch.users_at_join
            if hasattr(ch, "users_at_join") and ch.users_at_join is not None
            else None
        )

        if users_at_join is not None:
            before_count = users_at_join
            after_count = max(total_users - users_at_join, 0)
        else:
            before_count = 0
            after_count = total_users

        result.append(
            {
                "id": ch.id,
                "tg_id": ch.tg_id,
                "title": ch.channel_title,
                "username": ch.channel_username,
                "link": ch.channel_link,
                "is_active": ch.is_active,
                "added_at": added_at.isoformat() if added_at else None,
                "member_count": member_count,
                "bot_users_before": before_count,
                "bot_users_after": after_count,
                "bot_users_total": total_users,
            }
        )

    return result


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


# ─── Channel Scheduler Admin API ──────────────────────────────────────────────

@app.get("/api/channel-scheduler")
async def api_get_channel_schedulers(session_token: str | None = Cookie(default=None)):
    """List all channel scheduler configs."""
    if not is_authenticated(session_token):
        return Response(status_code=401, content="Unauthorized")
    schedulers = await get_all_channel_schedulers()
    # Enrich with book info
    for s in schedulers:
        book = vocab_service.books.get(s.get("book_slug", ""), {})
        s["book_title"] = book.get("short_title", s.get("book_slug", "—"))
        s["total_units"] = book.get("total_units", 0)
    return schedulers


@app.get("/api/channel-scheduler/books")
async def api_get_scheduler_books(session_token: str | None = Cookie(default=None)):
    """List all available books with their units for the scheduler dropdown."""
    if not is_authenticated(session_token):
        return Response(status_code=401, content="Unauthorized")
    result = []
    for slug, book in vocab_service.books.items():
        units = [{
            "unit_num": u["unit_num"],
            "title": u["title"],
            "word_count": u["word_count"],
        } for u in book["units"]]
        result.append({
            "slug": slug,
            "title": book["title"],
            "short_title": book["short_title"],
            "icon": book["icon"],
            "total_units": book["total_units"],
            "total_words": book["total_words"],
            "units": units,
        })
    return result


@app.post("/api/channel-scheduler")
async def api_save_channel_scheduler(request: Request, session_token: str | None = Cookie(default=None)):
    """Create or update a channel scheduler config."""
    if not is_authenticated(session_token):
        return Response(status_code=401, content="Unauthorized")
    data = await request.json()
    channel_id = str(data.get("channel_id") or os.getenv("CHANNEL_ID", ""))
    if not channel_id:
        return {"status": "error", "message": "Channel ID is required"}

    result = await save_channel_scheduler(
        channel_id=channel_id,
        book_slug=data.get("book_slug", "essential1"),
        start_unit=int(data.get("start_unit", 1)),
        send_time=data.get("send_time", "09:00"),
        is_active=bool(data.get("is_active", True)),
        finish_message=data.get("finish_message") or None,
    )
    return {"status": "ok", "scheduler": result}


@app.post("/api/channel-scheduler/toggle")
async def api_toggle_channel_scheduler(request: Request, session_token: str | None = Cookie(default=None)):
    """Toggle active/inactive status."""
    if not is_authenticated(session_token):
        return Response(status_code=401, content="Unauthorized")
    data = await request.json()
    channel_id = str(data.get("channel_id", ""))
    is_active = bool(data.get("is_active", False))
    await update_channel_scheduler_status(channel_id, is_active)
    return {"status": "ok"}


@app.delete("/api/channel-scheduler/{channel_id}")
async def api_delete_channel_scheduler(channel_id: str, session_token: str | None = Cookie(default=None)):
    """Delete a channel scheduler config."""
    if not is_authenticated(session_token):
        return Response(status_code=401, content="Unauthorized")
    await delete_channel_scheduler(channel_id)
    return {"status": "ok"}


@app.post("/api/channel-scheduler/test-send")
async def api_test_send_unit(request: Request, session_token: str | None = Cookie(default=None)):
    """Manually trigger a test send of the current unit to the channel."""
    if not is_authenticated(session_token):
        return Response(status_code=401, content="Unauthorized")
    data = await request.json()
    channel_id = str(data.get("channel_id") or os.getenv("CHANNEL_ID", ""))
    book_slug = data.get("book_slug", "essential1")
    unit_num = int(data.get("unit_num", 1))

    sched = await get_channel_scheduler(channel_id)
    finish_msg = data.get("finish_message") or (sched.get("finish_message") if sched else None)

    asyncio.create_task(
        send_unit_to_channel(channel_id, book_slug, unit_num, finish_message=finish_msg)
    )
    return {
        "status": "ok",
        "message": f"Unit {unit_num} savollari har 1 daqiqa oralig'ida kanalga jo'natilishi boshlandi!"
    }
