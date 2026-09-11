import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from bot.main import bot
from api.database import get_due_reminders, mark_reminder_sent
from api.services.vocab_service import vocab_service

logger = logging.getLogger(__name__)

# Base URL for Web App
WEBAPP_URL = os.getenv("WEBHOOK_URL", "").replace("/webhook", "")
if not WEBAPP_URL or "http" not in WEBAPP_URL:
    WEBAPP_URL = "https://game-english.anasxonummataliy.dev"


async def send_telegram_reminder_notification(
    tg_id: int,
    user_name: str = "O'quvchi",
    book_slug: str = "elementary",
    unit_num: int = 1,
    is_test: bool = False
) -> bool:
    try:
        # Get sample words from the chosen unit
        unit_data = vocab_service.get_words(book_slug, unit_num)
        book_info = vocab_service.books.get(book_slug, {})
        book_title = book_info.get("short_title", "English Vocabulary")
        unit_title = unit_data.get("title", f"Unit {unit_num}")
        words = unit_data.get("words", [])

        # Pick 3 words to display
        sample_words = words[:3] if len(words) >= 3 else words

        words_text = ""
        for w in sample_words:
            words_text += (
                f"• <b>{w['word']}</b> {w.get('transcription', '')} — <i>{w['uzbek']}</i>\n"
            )

        test_badge = "🧪 <b>TEST ESLATMA</b>\n" if is_test else "⏰ <b>KUNDALIK LUG'AT ESLATMASI</b>\n"

        text = (
            f"{test_badge}\n"
            f"Assalomu alaykum, <b>{user_name}</b>!\n"
            f"Bugun ingliz tili lug'at boyligingizni oshirish vaqti keldi 🚀\n\n"
            f"📖 <b>Kitob:</b> {book_title}\n"
            f"🎯 <b>Mavzu:</b> Unit {unit_num} — {unit_title}\n\n"
            f"<b>Bugungi kalit so'zlar:</b>\n"
            f"{words_text}\n"
            f"💡 <i>Web Appda to'liq kartochkalarni ko'rib chiqing va 60 soniyalik testni topshiring!</i>"
        )

        webapp_button_url = f"{WEBAPP_URL}/app"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📱 Web Appda mashq qilish",
                        web_app=WebAppInfo(url=webapp_button_url)
                    )
                ]
            ]
        )

        await bot.send_message(
            chat_id=tg_id,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        logger.info(f"Telegram notification sent to user {tg_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send telegram notification to {tg_id}: {e}")
        return False


async def reminder_scheduler_loop():
    """Checks every 60 seconds if any reminders are due in Tashkent time (UTC+5)."""
    logger.info("Starting webapp reminder scheduler background loop...")
    while True:
        try:
            # Tashkent time UTC+5
            tz_tashkent = timezone(timedelta(hours=5))
            now = datetime.now(tz_tashkent)
            current_hhmm = now.strftime("%H:%M")
            today_str = now.strftime("%Y-%m-%d")

            due_list = await get_due_reminders(current_hhmm, today_str)
            for r in due_list:
                tg_id = r["tg_id"]
                name = r.get("first_name") or r.get("username") or "O'quvchi"
                book_slug = r.get("book_slug") or "elementary"
                unit_num = r.get("unit_num") or 1

                sent = await send_telegram_reminder_notification(
                    tg_id=tg_id,
                    user_name=name,
                    book_slug=book_slug,
                    unit_num=unit_num,
                    is_test=False
                )
                if sent:
                    await mark_reminder_sent(r["id"], today_str)

        except Exception as e:
            logger.error(f"Error in reminder scheduler loop: {e}")

        await asyncio.sleep(60)
