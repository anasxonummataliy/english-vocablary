"""
Channel Scheduler Service
─────────────────────────
Background loop that posts vocabulary words to a Telegram channel on a
daily schedule.  For each active scheduler, at the configured send_time
(Tashkent UTC+5) it:

1. Reads all words from the current unit of the selected book.
2. Formats them into a clean channel message (split across multiple
   Telegram messages when the text exceeds 4000 chars).
3. Sends the messages to the channel.
4. Advances to the next unit.
5. When all units are exhausted, optionally sends a finish_message
   and deactivates the scheduler.
"""

import asyncio
import html as html_lib
import logging
from datetime import datetime, timedelta, timezone

from bot.main import bot
from api.database import (
    get_due_channel_schedulers,
    advance_channel_scheduler,
    finish_channel_scheduler,
)
from api.services.vocab_service import vocab_service

logger = logging.getLogger(__name__)

MAX_TG_MESSAGE_LEN = 4000


def format_word_card(idx: int, w: dict) -> str:
    """Format a single word into a channel-friendly HTML block."""
    word = html_lib.escape(w.get("word", ""))
    transcription = html_lib.escape(w.get("transcription", ""))
    pos = html_lib.escape(w.get("part_of_speech", ""))
    uzbek = html_lib.escape(w.get("uzbek", ""))
    description = html_lib.escape(w.get("description", ""))
    example = html_lib.escape(w.get("example", ""))

    lines = [f"<b>{idx}. {word}</b>  {transcription}"]
    if pos:
        lines[0] += f"  <i>({pos})</i>"
    if uzbek:
        lines.append(f"    🇺🇿 {uzbek}")
    if description:
        lines.append(f"    📖 {description}")
    if example:
        lines.append(f"    💬 <i>{example}</i>")

    return "\n".join(lines)


def build_unit_messages(book_slug: str, unit_num: int) -> list[str]:
    """
    Build a list of Telegram messages for one unit's words.
    Splits automatically if the text exceeds MAX_TG_MESSAGE_LEN.
    """
    unit_data = vocab_service.get_words(book_slug, unit_num)
    words = unit_data.get("words", [])
    if not words:
        return []

    book_info = vocab_service.books.get(book_slug, {})
    book_title = book_info.get("short_title", book_slug)
    unit_title = unit_data.get("title", f"Unit {unit_num}")

    header = (
        f"📚 <b>{html_lib.escape(book_title)}</b>\n"
        f"📖 <b>{html_lib.escape(unit_title)}</b>  •  "
        f"{len(words)} ta so'z\n"
        f"{'─' * 24}\n\n"
    )

    separator = f"\n{'─' * 18}\n\n"
    word_blocks = [format_word_card(i + 1, w) for i, w in enumerate(words)]

    # Greedily pack blocks into messages, each ≤ MAX_TG_MESSAGE_LEN
    messages: list[str] = []
    current = header

    for block in word_blocks:
        candidate = current + separator + block if current != header else current + block
        if len(candidate) > MAX_TG_MESSAGE_LEN and current != header:
            messages.append(current.rstrip())
            current = block
        else:
            current = candidate

    if current:
        messages.append(current.rstrip())

    return messages


async def send_unit_to_channel(channel_id: str, book_slug: str, unit_num: int) -> bool:
    """Send all word cards for a unit to the channel. Returns True on success."""
    messages = build_unit_messages(book_slug, unit_num)
    if not messages:
        logger.warning(
            "No words found for book=%s unit=%d — skipping send", book_slug, unit_num
        )
        return False

    target_chat: int | str = int(channel_id) if channel_id.lstrip("-").isdigit() else channel_id
    for msg in messages:
        try:
            await bot.send_message(
                chat_id=target_chat,
                text=msg,
                parse_mode="HTML",
            )
            await asyncio.sleep(0.5)          # small delay between messages
        except Exception as e:
            logger.error(
                "Failed to send message to channel %s: %s", channel_id, e
            )
            return False

    return True


async def send_finish_message(channel_id: str, finish_text: str) -> bool:
    """Send the optional finish message after all units are done."""
    target_chat: int | str = int(channel_id) if channel_id.lstrip("-").isdigit() else channel_id
    try:
        await bot.send_message(
            chat_id=target_chat,
            text=finish_text,
            parse_mode="HTML",
        )
        return True
    except Exception as e:
        logger.error("Failed to send finish message to %s: %s", channel_id, e)
        return False


async def process_due_channel_schedulers() -> None:
    """Check for any due schedulers and send the scheduled unit."""
    tz_tashkent = timezone(timedelta(hours=5))
    now = datetime.now(tz_tashkent)
    current_hhmm = now.strftime("%H:%M")
    today_str = now.strftime("%Y-%m-%d")

    due_list = await get_due_channel_schedulers(current_hhmm, today_str)

    for sched in due_list:
        channel_id = sched["channel_id"]
        book_slug = sched["book_slug"]
        current_unit = sched["current_unit"]

        # Determine how many units exist in this book
        book = vocab_service.books.get(book_slug)
        if not book:
            logger.warning("Book %s not found for scheduler on channel %s", book_slug, channel_id)
            continue

        all_units = sorted(u["unit_num"] for u in book["units"])
        if current_unit not in all_units:
            logger.warning(
                "Unit %d not in book %s for channel %s — finishing",
                current_unit, book_slug, channel_id,
            )
            finish_msg = sched.get("finish_message")
            if finish_msg:
                await send_finish_message(channel_id, finish_msg)
            await finish_channel_scheduler(channel_id, today_str)
            continue

        # --- Send the unit ---
        sent = await send_unit_to_channel(channel_id, book_slug, current_unit)
        if not sent:
            logger.error(
                "Sending unit %d to channel %s failed — will retry next loop",
                current_unit, channel_id,
            )
            continue

        logger.info(
            "✅ Channel %s: sent book=%s unit=%d",
            channel_id, book_slug, current_unit,
        )

        # --- Determine next unit ---
        idx = all_units.index(current_unit)
        if idx + 1 < len(all_units):
            next_unit = all_units[idx + 1]
            await advance_channel_scheduler(channel_id, next_unit, today_str)
        else:
            # All units exhausted
            finish_msg = sched.get("finish_message")
            if finish_msg:
                await send_finish_message(channel_id, finish_msg)
            await finish_channel_scheduler(channel_id, today_str)
            logger.info("🏁 Channel %s: all units finished for book=%s", channel_id, book_slug)


async def channel_scheduler_loop() -> None:
    """Main background loop — checks every 60 seconds."""
    logger.info("Channel scheduler background loop started")
    while True:
        try:
            await process_due_channel_schedulers()
        except Exception:
            logger.exception("Error in channel scheduler loop")
        await asyncio.sleep(60)
