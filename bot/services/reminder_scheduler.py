import asyncio
import logging
from datetime import datetime

from aiogram import Bot
from sqlalchemy import select

from bot.database.base import redis_client
from bot.database.models.reminders import Reminder
from bot.database.session import get_async_session_context
from bot.services.reminder_service import postpone_reminder, send_unit_reminder

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60


async def process_due_reminders(bot: Bot) -> None:
    now = datetime.utcnow()
    async with get_async_session_context() as session:
        result = await session.execute(
            select(Reminder).where(
                Reminder.is_active.is_(True),
                Reminder.next_reminder_at <= now,
            )
        )
        due_reminders = result.scalars().all()

    for reminder in due_reminders:
        try:
            sent = await send_unit_reminder(
                bot,
                reminder.tg_id,
                reminder.level,
                reminder.current_unit,
                redis_client,
            )

            if not sent:
                logger.warning(
                    "Reminder unit topilmadi: user=%s level=%s unit=%s",
                    reminder.tg_id,
                    reminder.level,
                    reminder.current_unit,
                )
                continue

            await postpone_reminder(reminder.tg_id)
        except Exception:
            logger.exception(
                "Reminder yuborishda xatolik: user=%s", reminder.tg_id
            )


async def reminder_scheduler_loop(bot: Bot) -> None:
    logger.info("Reminder scheduler ishga tushdi")
    while True:
        try:
            await process_due_reminders(bot)
        except Exception:
            logger.exception("Reminder scheduler xatoligi")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
