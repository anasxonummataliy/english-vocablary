"""
Channel Scheduler Service
─────────────────────────
Background loop that posts vocabulary words to a Telegram channel on a
daily schedule. For each active scheduler, at the configured send_time
(Tashkent UTC+5) it:

1. Reads all words from the current unit of the selected book.
2. Sends each word as a Telegram Quiz Poll (no countdown timer).
3. Right after the unit's polls, sends the optional completion message.
4. Advances to the next unit.
5. When all units are completed, deactivates the scheduler.
"""

import asyncio
import html as html_lib
import logging
import random
from datetime import datetime, timedelta, timezone

from bot.main import bot
from api.database import (
    get_due_channel_schedulers,
    advance_channel_scheduler,
    finish_channel_scheduler,
)
from api.services.vocab_service import vocab_service

logger = logging.getLogger(__name__)


def build_unit_polls(book_slug: str, unit_num: int) -> list[dict]:
    """
    Build a list of Quiz Poll data dicts for every word in the unit.
    Each poll contains:
      - question: e.g. "[1/20] 🇬🇧 afraid /ə'freɪd/ (adjective)\nTo'g'ri tarjimasini toping:"
      - options: list of 4 unique options (1 correct Uzbek translation + 3 wrong candidates)
      - correct_option_id: index of the correct answer
      - explanation: definition and example sentence popup
    """
    unit_data = vocab_service.get_words(book_slug, unit_num)
    words = unit_data.get("words", [])
    if not words:
        return []

    book = vocab_service.books.get(book_slug, {})
    all_book_words = [w for u in book.get("units", []) for w in u.get("words", [])]

    polls = []
    total = len(words)

    for idx, w in enumerate(words, start=1):
        word = w.get("word", "").strip()
        transcription = w.get("transcription", "").strip()
        pos = w.get("part_of_speech", "").strip()
        correct_uzbek = w.get("uzbek", "").strip()[:100]

        if not word or not correct_uzbek:
            continue

        header = f"{word} {transcription}".strip()
        if pos:
            header += f" ({pos})"
        question = f"[{idx}/{total}] 🇬🇧 {header}\nTo'g'ri tarjimasini toping:"
        if len(question) > 255:
            question = question[:252] + "..."

        # Wrong options pool (first try same unit, fallback to entire book)
        wrong_candidates = [
            o.get("uzbek", "").strip()[:100]
            for o in words
            if o.get("uzbek", "").strip() and o.get("uzbek", "").strip() != correct_uzbek
        ]
        unique_wrong = list(set(wrong_candidates))

        if len(unique_wrong) < 3:
            more_candidates = [
                o.get("uzbek", "").strip()[:100]
                for o in all_book_words
                if o.get("uzbek", "").strip() and o.get("uzbek", "").strip() != correct_uzbek
            ]
            unique_wrong = list(set(unique_wrong + more_candidates))

        selected_wrong = random.sample(unique_wrong, min(3, len(unique_wrong)))
        options = [correct_uzbek] + selected_wrong
        random.shuffle(options)
        correct_idx = options.index(correct_uzbek)

        # Explanation shown upon answering in Telegram Quiz (max 200 chars)
        explanation_parts = []
        if w.get("description"):
            explanation_parts.append(f"📖 {w['description'].strip()}")
        if w.get("example"):
            explanation_parts.append(f"💬 {w['example'].strip()}")
        explanation = "\n".join(explanation_parts) if explanation_parts else f"✅ {word} = {correct_uzbek}"
        if len(explanation) > 200:
            explanation = explanation[:197] + "..."

        polls.append({
            "question": question,
            "options": options,
            "correct_option_id": correct_idx,
            "explanation": explanation,
        })

    return polls


async def send_unit_to_channel(
    channel_id: str,
    book_slug: str,
    unit_num: int,
    finish_message: str | None = None,
) -> bool:
    """Send all words of a unit as Quiz Polls to the channel."""
    polls = build_unit_polls(book_slug, unit_num)
    if not polls:
        logger.warning(
            "No words found for book=%s unit=%d — skipping send", book_slug, unit_num
        )
        return False

    unit_data = vocab_service.get_words(book_slug, unit_num)
    book_info = vocab_service.books.get(book_slug, {})
    book_title = book_info.get("short_title", book_slug)
    unit_title = unit_data.get("title", f"Unit {unit_num}")

    target_chat: int | str = int(channel_id) if channel_id.lstrip("-").isdigit() else channel_id

    # 1. Send Unit intro header message
    intro_text = (
        f"📚 <b>{html_lib.escape(book_title)}</b>\n"
        f"📖 <b>Unit {unit_num}:</b> {html_lib.escape(unit_title)}\n"
        f"🎯 Jami: <b>{len(polls)} ta test</b>\n\n"
        f"👇 So'zlarni yod oling va to'g'ri javoblarni belgilang:"
    )
    try:
        await bot.send_message(
            chat_id=target_chat,
            text=intro_text,
            parse_mode="HTML",
        )
        await asyncio.sleep(1.0)
    except Exception as e:
        logger.error("Failed to send intro message to channel %s: %s", channel_id, e)
        return False

    # 2. Send each word as a Quiz Poll (no timer / open_period)
    for p in polls:
        try:
            await bot.send_poll(
                chat_id=target_chat,
                question=p["question"],
                options=p["options"],
                type="quiz",
                correct_option_id=p["correct_option_id"],
                explanation=p["explanation"],
                is_anonymous=True,  # In channels, anonymous polls allow private voting
            )
            await asyncio.sleep(1.2)  # Delay between polls for Telegram rate limit safety
        except Exception as e:
            logger.error("Failed to send poll to channel %s: %s", channel_id, e)
            return False

    # 3. Send completion message immediately after all unit polls
    if finish_message:
        try:
            await asyncio.sleep(1.0)
            formatted_msg = (
                finish_message
                .replace("{unit}", str(unit_num))
                .replace("{book}", str(book_title))
            )
            await send_finish_message(channel_id, formatted_msg)
        except Exception as e:
            logger.error("Failed to send unit completion message to %s: %s", channel_id, e)

    return True


async def send_finish_message(channel_id: str, finish_text: str) -> bool:
    """Send the completion message after unit polls are sent."""
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
            await finish_channel_scheduler(channel_id, today_str)
            continue

        # --- Send the unit as Quiz Polls + completion message ---
        finish_msg = sched.get("finish_message")
        sent = await send_unit_to_channel(
            channel_id, book_slug, current_unit, finish_message=finish_msg
        )
        if not sent:
            logger.error(
                "Sending unit %d polls to channel %s failed — will retry next loop",
                current_unit, channel_id,
            )
            continue

        logger.info(
            "✅ Channel %s: sent book=%s unit=%d polls with completion message",
            channel_id, book_slug, current_unit,
        )

        # --- Determine next unit ---
        idx = all_units.index(current_unit)
        if idx + 1 < len(all_units):
            next_unit = all_units[idx + 1]
            await advance_channel_scheduler(channel_id, next_unit, today_str)
        else:
            # All units exhausted
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
