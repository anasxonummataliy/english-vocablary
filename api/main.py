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
from bot.main import dp, bot, start_bot
from aiogram.types import Update
from contextlib import asynccontextmanager
from bot.database.base import redis_client

TEMPLATES_DIR = Path(__file__).parent / "templates"

# Session tokenlari saqlanadi (oddiy in-memory)
active_sessions: set[str] = set()


def verify_credentials(login: str, password: str) -> bool:
    return login == "anasxon" and password == "muslim1306"


def is_authenticated(session_token: str | None) -> bool:
    return session_token is not None and session_token in active_sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_bot()
    yield
    await bot.close()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


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
    <title>Login — English Vocabulary Bot</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f0f2f5;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }}
        .login-card {{
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 380px;
        }}
        .login-card h1 {{
            text-align: center;
            margin-bottom: 8px;
            font-size: 1.5rem;
            color: #16213e;
        }}
        .login-card p {{
            text-align: center;
            color: #666;
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
            color: #333;
            font-size: 0.9rem;
        }}
        .form-group input {{
            width: 100%;
            padding: 12px 14px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 0.95rem;
            outline: none;
            transition: border-color 0.2s;
        }}
        .form-group input:focus {{ border-color: #2980b9; }}
        .btn {{
            width: 100%;
            padding: 12px;
            background: #16213e;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            margin-top: 8px;
            transition: background 0.2s;
        }}
        .btn:hover {{ background: #0f3460; }}
        .error {{
            background: #fdecea;
            color: #e74c3c;
            padding: 10px 14px;
            border-radius: 8px;
            margin-bottom: 16px;
            font-size: 0.9rem;
            text-align: center;
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
        response = RedirectResponse(url="/", status_code=303)
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


@app.get("/", response_class=HTMLResponse)
async def index(session_token: str | None = Cookie(default=None)):
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
