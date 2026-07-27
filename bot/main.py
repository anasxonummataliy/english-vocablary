import sys
import logging
import os
import asyncio
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.exceptions import (
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)
from aiogram.types import BotCommandScopeAllPrivateChats, BotCommandScopeChat
from dotenv import load_dotenv

from bot.middleware.channel import IsJoinChannelMiddleware
from bot.middleware.user_activity import UserActivityMiddleware
from bot.middleware.saved_db import UserSaveMiddleware
from bot.routers import user_router
from bot.middleware.channel import router as middleware_router
from bot.admin import admin_router

from bot.admin.commands import admin_commands
from bot.routers.user_commands import user_command
from bot.database.base import create_db_and_tables
from bot.database.models import reminders  # noqa: F401
from bot.services.reminder_scheduler import reminder_scheduler_loop

load_dotenv()
TOKEN = os.getenv("TOKEN") or ""

logger = logging.getLogger(__name__)
dp = Dispatcher()
bot = Bot(TOKEN)
CHANNEL_ID = os.getenv("CHANNEL_ID") or ""
ADMIN = int(os.getenv("ADMIN"))
WEBHOOK_RETRY_ATTEMPTS = 5
WEBHOOK_RETRY_BASE_DELAY = 2
TELEGRAM_REQUEST_TIMEOUT = 10
telegram_bootstrap_task: asyncio.Task | None = None


async def _notify_admin_status(text: str) -> None:
    try:
        await bot.send_message(ADMIN, text, request_timeout=TELEGRAM_REQUEST_TIMEOUT)
    except Exception as exc:
        logger.warning("Admin xabar yuborilmadi: %s", exc)


async def _call_with_retry(title: str, action) -> bool:
    for attempt in range(1, WEBHOOK_RETRY_ATTEMPTS + 1):
        try:
            await action()
            if attempt > 1:
                logger.info("%s muvaffaqiyatli (urinish %s)", title, attempt)
            return True
        except TelegramRetryAfter as exc:
            delay = max(int(exc.retry_after), 1)
            logger.warning(
                "%s rate-limited (urinish %s/%s). %s s kutamiz.",
                title,
                attempt,
                WEBHOOK_RETRY_ATTEMPTS,
                delay,
            )
        except (TelegramServerError, TelegramNetworkError) as exc:
            delay = min(WEBHOOK_RETRY_BASE_DELAY * attempt, 15)
            logger.warning(
                "%s vaqtinchalik xatolik (urinish %s/%s): %s. %s s kutamiz.",
                title,
                attempt,
                WEBHOOK_RETRY_ATTEMPTS,
                exc,
                delay,
            )
        except Exception as exc:
            logger.exception("%s kutilmagan xatolik: %s", title, exc)
            return False

        if attempt < WEBHOOK_RETRY_ATTEMPTS:
            await asyncio.sleep(delay)

    logger.error("%s bajarilmadi: barcha urinishlar tugadi.", title)
    return False


async def _bootstrap_telegram() -> None:
    webhook_url = (os.getenv("WEBHOOK_URL") or "").strip()
    if not webhook_url:
        logger.error("WEBHOOK_URL bo'sh. Webhook sozlanmadi.")
        await _notify_admin_status("⚠️ Bot ishga tushdi, lekin WEBHOOK_URL bo'sh.")
        return

    await _call_with_retry(
        "delete_webhook",
        lambda: bot.delete_webhook(
            drop_pending_updates=True,
            request_timeout=TELEGRAM_REQUEST_TIMEOUT,
        ),
    )

    webhook_ok = await _call_with_retry(
        "set_webhook",
        lambda: bot.set_webhook(
            url=webhook_url,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True,
            max_connections=40,
            request_timeout=TELEGRAM_REQUEST_TIMEOUT,
        ),
    )

    if not webhook_ok:
        await _notify_admin_status("⚠️ Bot ishga tushdi, lekin webhook sozlanmadi.")
        return

    await _call_with_retry(
        "get_webhook_info",
        lambda: bot.get_webhook_info(request_timeout=TELEGRAM_REQUEST_TIMEOUT),
    )

    await _call_with_retry(
        "set_my_commands(admin)",
        lambda: bot.set_my_commands(
            admin_commands,
            scope=BotCommandScopeChat(chat_id=ADMIN),
            request_timeout=TELEGRAM_REQUEST_TIMEOUT,
        ),
    )
    await _call_with_retry(
        "set_my_commands(user)",
        lambda: bot.set_my_commands(
            user_command,
            scope=BotCommandScopeAllPrivateChats(),
            request_timeout=TELEGRAM_REQUEST_TIMEOUT,
        ),
    )

    await _notify_admin_status("Bot started ✅")


async def start_bot() -> None:
    global telegram_bootstrap_task

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    # Routerni qayta-qayta qo'shib yubormaslik uchun bitta startup jarayonida faqat bir marta sozlaymiz.
    if not getattr(dp, "_project_initialized", False):
        dp.message.middleware(UserSaveMiddleware())
        dp.message.middleware(IsJoinChannelMiddleware())
        dp.message.middleware(UserActivityMiddleware())
        dp.callback_query.middleware(UserSaveMiddleware())
        dp.callback_query.middleware(UserActivityMiddleware())
        dp.include_router(middleware_router)
        dp.include_router(admin_router)
        dp.include_router(user_router)
        dp._project_initialized = True

    await create_db_and_tables()
    asyncio.create_task(reminder_scheduler_loop(bot))

    # Telegram API vaqtincha sekin ishlasa ham FastAPI startup bloklanmasin.
    if not telegram_bootstrap_task or telegram_bootstrap_task.done():
        telegram_bootstrap_task = asyncio.create_task(_bootstrap_telegram())
    logger.info("Bot application startup yakunlandi. Telegram bootstrap fon rejimida.")


async def stop_bot() -> None:
    global telegram_bootstrap_task

    if telegram_bootstrap_task and not telegram_bootstrap_task.done():
        telegram_bootstrap_task.cancel()
        with suppress(asyncio.CancelledError):
            await telegram_bootstrap_task
    telegram_bootstrap_task = None

    await _notify_admin_status("Bot stopped ⛔️")
    await bot.close()


if __name__ == "__main__":
    asyncio.run(start_bot())
