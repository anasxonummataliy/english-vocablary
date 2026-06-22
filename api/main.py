import logging
import secrets
from pathlib import Path

from fastapi import FastAPI, Request, Response, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from bot.database.models.users import User
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
        error_html = '<div class="error">❌ Login yoki parol noto\'g\'ri</div>'

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
