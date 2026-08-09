import random
import json
import os
import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, PollAnswer
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.utils.keyboard import InlineKeyboardBuilder
from redis.asyncio import Redis

from bot.routers.get_words import get_unit_words, get_all_level_words
from bot.services.score_service import save_score
from bot.routers.keyboard import get_available_levels, get_available_units

router = Router()

TIMER_SECONDS = 15

gquiz_tasks: dict[int, asyncio.Task] = {}


def _to_str(value) -> str | None:
    if value is None:
        return None
    return value.decode() if isinstance(value, bytes) else str(value)


def _cancel_gquiz_task(chat_id: int):
    task = gquiz_tasks.pop(chat_id, None)
    if task and not task.done():
        task.cancel()


async def _is_group_admin_or_bot_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    bot_admin_id = int(os.getenv("ADMIN") or 0)
    if user_id == bot_admin_id:
        return True
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return member.status in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
        )
    except Exception:
        return False


# ==================== /quiz KOMANDASI ====================
@router.message(Command("quiz", "musobaqa"))
async def cmd_start_group_quiz(message: Message, redis: Redis):
    chat_id = message.chat.id

    # Tekshirish: aktiv musobaqa bor-yo'qligi
    existing = await redis.get(f"group_quiz:{chat_id}")
    if existing:
        quiz_data = json.loads(_to_str(existing) or "{}")
        is_paused = quiz_data.get("is_paused", False)

        ikb = InlineKeyboardBuilder()
        if is_paused:
            ikb.row(
                InlineKeyboardButton(
                    text="▶️ Musobaqani davom ettirish",
                    callback_data="gq_resume",
                    style="success",
                )
            )
        ikb.row(
            InlineKeyboardButton(
                text="🛑 Musobaqani to'xtatish", callback_data="gq_force_stop", style="danger"
            )
        )

        status_text = (
            "⏸ <b>Bu guruhda musobaqa pauza qilingan!</b>\n\n"
            "Davom ettirish uchun pastdagi tugmani bosing."
            if is_paused
            else "⚠️ <b>Bu guruhda allaqachon aktiv musobaqa ketmoqda!</b>\n\n"
            "Uning tugashini kuting yoki to'xtatish uchun pastdagi tugmani bosing yoki /stop_quiz yuboring."
        )

        await message.reply(
            status_text,
            reply_markup=ikb.as_markup(),
            parse_mode="HTML",
        )
        return

    ikb = InlineKeyboardBuilder()
    available_levels = get_available_levels()
    for title, code in available_levels:
        ikb.row(InlineKeyboardButton(text=title, callback_data=f"gq_lvl_{code}", style="primary"))

    await message.answer(
        "🏆 <b>Guruh musobaqasi!</b>\n\n"
        "Qaysi daraja (level) bo'yicha musobaqa o'tkazmoqchisiz?",
        reply_markup=ikb.as_markup(),
        parse_mode="HTML",
    )


# ==================== MUSOBAQANI PAUZADAN CHIQARISH (RESUME) ====================
@router.callback_query(F.data == "gq_resume")
async def resume_gquiz_callback(callback: CallbackQuery, redis: Redis, bot: Bot):
    chat_id = callback.message.chat.id
    raw = _to_str(await redis.get(f"group_quiz:{chat_id}"))
    if not raw:
        await callback.answer(
            "⚠️ Aktiv yoki pauza qilingan musobaqa topilmadi.", show_alert=True
        )
        return

    quiz_data = json.loads(raw)
    if not quiz_data.get("is_paused", False):
        await callback.answer("⚠️ Musobaqa allaqachon aktiv holatda!", show_alert=True)
        return

    # Paused holatini yechish va indexni oshirish
    quiz_data["is_paused"] = False
    quiz_data["unanswered_count"] = 0
    quiz_data["current_index"] += 1

    await redis.set(f"group_quiz:{chat_id}", json.dumps(quiz_data), ex=3600)

    try:
        await callback.message.delete()
    except Exception:
        pass

    user_name = callback.from_user.first_name or callback.from_user.username or "Foydalanuvchi"
    await callback.answer("▶️ Musobaqa qayta davom ettirilmoqda!")

    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"▶️ <b>Musobaqa {user_name} tomonidan davom ettirildi!</b>\n\n"
            "Navbatdagi savol yuborilmoqda..."
        ),
        parse_mode="HTML",
    )
    await asyncio.sleep(1)
    await send_next_gquiz_question(bot, chat_id, redis)


# ==================== MUSOBAQANI MAJBURIY TO'XTATISH ====================
@router.message(Command("stop_quiz", "stopquiz", "cancel_quiz", "stop"))
@router.callback_query(F.data == "gq_force_stop")
async def force_stop_gquiz(event: Message | CallbackQuery, redis: Redis, bot: Bot):
    chat = event.chat if isinstance(event, Message) else event.message.chat
    chat_id = chat.id
    user_id = event.from_user.id

    if chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        is_admin = await _is_group_admin_or_bot_admin(bot, chat_id, user_id)
        if not is_admin:
            warning_msg = "⚠️ Musobaqani faqat guruh adminlari to'xtata oladi!"
            if isinstance(event, CallbackQuery):
                await event.answer(warning_msg, show_alert=True)
            else:
                await event.reply(warning_msg)
            return

    _cancel_gquiz_task(chat_id)
    await redis.delete(f"group_quiz:{chat_id}")

    if isinstance(event, CallbackQuery):
        try:
            await event.message.delete()
        except Exception:
            pass
        await event.answer("🛑 Musobaqa to'xtatildi!")

    text = (
        "🛑 <b>Guruh musobaqasi admin tomonidan to'xtatildi.</b>\n\n"
        "Endi yangi musobaqa boshlashingiz mumkin (/quiz)."
    )
    await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")


from bot.routers.keyboard import (
    get_available_levels,
    get_available_units,
    get_page_data,
    create_units_keyboard,
)


@router.callback_query(F.data.startswith("gq_lvl_"))
async def select_gquiz_level(callback: CallbackQuery):
    level = callback.data.removeprefix("gq_lvl_")
    page_data, current_page, total_pages = await get_page_data(0, level)

    top_btn = [
        [
            InlineKeyboardButton(
                text="🔀 Mix (20 ta aralash savol)",
                callback_data=f"gq_start_{level}_mix",
                style="success",
            )
        ]
    ]

    kb = await create_units_keyboard(
        current_page=current_page,
        total_pages=total_pages,
        units=page_data,
        select_prefix=f"gq_start_{level}_",
        page_prefix=f"gq_page_{level}_",
        extra_top_buttons=top_btn,
        raw_number_payload=True,
    )

    await callback.message.edit_text(
        f"📖 Tanlangan daraja: <b>{level.capitalize()}</b>\n"
        "🎯 <b>Musobaqa turini yoki Unitni tanlang:</b>",
        reply_markup=kb,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("gq_page_"))
async def gquiz_pagination_handler(callback: CallbackQuery):
    raw = callback.data.removeprefix("gq_page_")
    parts = raw.split("_")
    level = parts[0]
    page = int(parts[1])

    page_data, current_page, total_pages = await get_page_data(page, level)
    top_btn = [
        [
            InlineKeyboardButton(
                text="🔀 Mix (20 ta aralash savol)",
                callback_data=f"gq_start_{level}_mix",
                style="success",
            )
        ]
    ]

    kb = await create_units_keyboard(
        current_page=current_page,
        total_pages=total_pages,
        units=page_data,
        select_prefix=f"gq_start_{level}_",
        page_prefix=f"gq_page_{level}_",
        extra_top_buttons=top_btn,
        raw_number_payload=True,
    )

    await callback.message.edit_text(
        f"📖 Tanlangan daraja: <b>{level.capitalize()}</b>\n"
        "🎯 <b>Musobaqa turini yoki Unitni tanlang:</b>",
        reply_markup=kb,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("gq_start_"))
async def start_gquiz_session(callback: CallbackQuery, redis: Redis, bot: Bot):
    raw = callback.data.removeprefix("gq_start_")
    parts = raw.split("_")
    if len(parts) < 2:
        await callback.answer("❌ Noto'g'ri format", show_alert=True)
        return

    level = parts[0]
    unit_param = parts[1]

    chat_id = callback.message.chat.id
    _cancel_gquiz_task(chat_id)

    if unit_param == "mix":
        words = await get_all_level_words(level)
        if not words or len(words) < 4:
            await callback.answer("⚠️ Ma'lumotlar topilmadi!", show_alert=True)
            return
        random.shuffle(words)
        selected_words = words[:20]  # Mix rejimida 20 ta savol
        unit_num = 0
        unit_display = "🔀 Mix (20 ta aralash savol)"
    else:
        try:
            unit_num = int(unit_param)
        except ValueError:
            await callback.answer("❌ Unit raqami xato", show_alert=True)
            return

        words = await get_unit_words(level, unit_num)
        if not words or len(words) < 4:
            await callback.answer(
                "⚠️ Bu unit uchun kamida 4 ta so'z bo'lishi kerak!", show_alert=True
            )
            return

        random.shuffle(words)
        selected_words = words  # Shu unitdagi barcha so'zlar
        unit_display = f"Unit {unit_num}"

    quiz_data = {
        "chat_id": chat_id,
        "level": level,
        "unit_num": unit_num,
        "unit_display": unit_display,
        "questions": selected_words,
        "current_index": 0,
        "unanswered_count": 0,
        "current_question_answered": False,
        "is_paused": False,
        "scores": {},  # user_id_str: {"name": str, "score": int}
        "current_poll_id": None,
        "correct_option_id": None,
    }

    try:
        await callback.message.delete()
    except Exception:
        pass

    await redis.set(f"group_quiz:{chat_id}", json.dumps(quiz_data), ex=3600)
    await callback.answer("🚀 Musobaqa boshlanmoqda!")

    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"🚀 <b>GURUH MUSOBAQASI BOSHLANDI!</b>\n\n"
            f"📚 Daraja: <b>{level.capitalize()}</b>\n"
            f"📖 Rejim: <b>{unit_display}</b>\n"
            f"❓ Jami savollar: <b>{len(selected_words)} ta</b>\n"
            f"⏱ Har bir savolga <b>{TIMER_SECONDS} soniya</b> beriladi!\n\n"
            "Tayyor bo'ling, birinchi savol yuborilmoqda..."
        ),
        parse_mode="HTML",
    )
    await asyncio.sleep(2)
    await send_next_gquiz_question(bot, chat_id, redis)


async def send_next_gquiz_question(bot: Bot, chat_id: int, redis: Redis):
    raw = _to_str(await redis.get(f"group_quiz:{chat_id}"))
    if not raw:
        return

    quiz_data = json.loads(raw)

    # Agar musobaqa pauza holatida bo'lsa, savol yubormaslik
    if quiz_data.get("is_paused", False):
        return

    idx = quiz_data["current_index"]
    questions = quiz_data["questions"]

    if idx >= len(questions):
        await finish_group_quiz(bot, chat_id, quiz_data, redis)
        return

    q = questions[idx]
    total = len(questions)

    # Uzbek -> English savol
    question_text = f"[{idx+1}/{total}] 🇺🇿 \"{q['uzbek']}\" so'zining inglizcha tarjimasi?"
    correct = q["word"]
    explanation = f"✅ {q['uzbek']} = {q['word']}"
    pool = [w["word"] for w in questions]
    wrong = [v for v in pool if v != correct]
    options = random.sample(wrong, min(3, len(wrong))) + [correct]
    random.shuffle(options)
    correct_idx = options.index(correct)

    poll_msg = await bot.send_poll(
        chat_id=chat_id,
        question=question_text[:255],
        options=options,
        type="quiz",
        correct_option_id=correct_idx,
        explanation=explanation,
        is_anonymous=False,
        open_period=TIMER_SECONDS,
    )

    poll_id = str(poll_msg.poll.id)
    quiz_data["current_poll_id"] = poll_id
    quiz_data["correct_option_id"] = correct_idx
    quiz_data["current_question_answered"] = False

    await redis.set(f"group_quiz:{chat_id}", json.dumps(quiz_data), ex=3600)
    await redis.set(f"gquiz_poll:{poll_id}", str(chat_id), ex=3600)

    # Savol vaqti tugagandan keyin keyingi savolga o'tish taski
    task = asyncio.create_task(
        _schedule_next_gquiz_step(bot, chat_id, idx, poll_id, redis)
    )
    gquiz_tasks[chat_id] = task


async def _schedule_next_gquiz_step(
    bot: Bot, chat_id: int, expected_idx: int, expected_poll_id: str, redis: Redis
):
    try:
        await asyncio.sleep(TIMER_SECONDS + 2)
        raw = _to_str(await redis.get(f"group_quiz:{chat_id}"))
        if not raw:
            return

        quiz_data = json.loads(raw)
        if quiz_data.get("is_paused", False):
            return
        if quiz_data["current_index"] != expected_idx:
            return

        # Ushbu savolga javob berildimi?
        if not quiz_data.get("current_question_answered", False):
            quiz_data["unanswered_count"] = quiz_data.get("unanswered_count", 0) + 1
        else:
            quiz_data["unanswered_count"] = 0

        # Ketma-ket 2 ta savolga javob berilmagan bo'lsa, musobaqani pauza qilish
        if quiz_data["unanswered_count"] >= 2:
            _cancel_gquiz_task(chat_id)
            quiz_data["is_paused"] = True
            await redis.set(f"group_quiz:{chat_id}", json.dumps(quiz_data), ex=3600)

            ikb = InlineKeyboardBuilder()
            ikb.row(
                InlineKeyboardButton(
                    text="▶️ Musobaqani davom ettirish",
                    callback_data="gq_resume",
                    style="success",
                )
            )
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "⏸ <b>Musobaqa pauza qilindi!</b>\n\n"
                    "⚠️ Ketma-ket <b>2 ta</b> savolga hech kim javob bermadi.\n\n"
                    "▶️ Istalgan foydalanuvchi tugmani bosib musobaqani davom ettirishi mumkin:"
                ),
                reply_markup=ikb.as_markup(),
                parse_mode="HTML",
            )
            return

        # Keyingi savolga o'tkazish
        quiz_data["current_index"] += 1
        await redis.set(f"group_quiz:{chat_id}", json.dumps(quiz_data), ex=3600)
        await send_next_gquiz_question(bot, chat_id, redis)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[GQUIZ TIMEOUT ERROR] Chat {chat_id}: {e}")


# ==================== POLL ANSWER HODISASI ====================
@router.poll_answer()
async def on_gquiz_poll_answer(poll_answer: PollAnswer, redis: Redis):
    poll_id = str(poll_answer.poll_id)
    chat_id_str = _to_str(await redis.get(f"gquiz_poll:{poll_id}"))
    if not chat_id_str:
        return

    chat_id = int(chat_id_str)
    raw = _to_str(await redis.get(f"group_quiz:{chat_id}"))
    if not raw:
        return

    quiz_data = json.loads(raw)
    if str(quiz_data.get("current_poll_id")) != poll_id:
        return

    user = poll_answer.user
    user_id_str = str(user.id)
    chosen_idx = poll_answer.option_ids[0] if poll_answer.option_ids else -1
    correct_idx = quiz_data.get("correct_option_id", -1)

    scores = quiz_data.setdefault("scores", {})
    if user_id_str not in scores:
        display_name = user.first_name or user.username or f"User_{user.id}"
        scores[user_id_str] = {"name": display_name, "score": 0}

    if chosen_idx == correct_idx:
        scores[user_id_str]["score"] += 1

    quiz_data["current_question_answered"] = True
    quiz_data["unanswered_count"] = 0

    await redis.set(f"group_quiz:{chat_id}", json.dumps(quiz_data), ex=3600)


# ==================== MUSOBAQANI YAKUNLASH ====================
async def finish_group_quiz(bot: Bot, chat_id: int, quiz_data: dict, redis: Redis):
    _cancel_gquiz_task(chat_id)
    try:
        scores = quiz_data.get("scores", {})
        total_q = len(quiz_data.get("questions", []))
        level = quiz_data.get("level", "elementary")
        raw_unit = quiz_data.get("unit_num", 1)
        try:
            unit_num = int(raw_unit)
        except (ValueError, TypeError):
            unit_num = 0

        unit_disp = quiz_data.get("unit_display", f"Unit {unit_num}")

        # Natijalarni bazaga saqlash va tartiblash
        sorted_players = sorted(
            scores.items(), key=lambda item: item[1]["score"], reverse=True
        )

        text = (
            f"🏆 <b>MUSOBAQA YAKUNLANDI!</b>\n\n"
            f"📚 Daraja: <b>{level.capitalize()}</b> | Rejim: <b>{unit_disp}</b>\n"
            f"❓ Jami savollar: <b>{total_q} ta</b>\n\n"
            f"🥇 <b>G'OLIBLAR VA REYTING:</b>\n"
        )

        if not sorted_players:
            text += "\n<i>Afsuski, hech kim musobaqada qatnashmadi.</i>"
        else:
            medals = ["🥇", "🥈", "🥉"]
            for i, (user_id_str, player_info) in enumerate(sorted_players):
                uid = int(user_id_str)
                p_score = player_info["score"]
                name = player_info["name"]
                medal = medals[i] if i < 3 else f"{i+1}."
                percent = (p_score / total_q * 100) if total_q > 0 else 0
                text += f"{medal} <b>{name}</b> — {p_score}/{total_q} ({percent:.0f}%)\n"

                # Bazaga saqlash
                try:
                    await save_score(
                        user_id=uid,
                        user_name=name,
                        chat_id=chat_id,
                        level=level,
                        unit_num=unit_num,
                        test_mode="group_quiz",
                        score=p_score,
                        total_questions=total_q,
                    )
                except Exception as e:
                    print(f"[GQUIZ SAVE SCORE ERROR] User {uid}: {e}")

        await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    except Exception as e:
        print(f"[GQUIZ FINISH ERROR] Chat {chat_id}: {e}")
    finally:
        await redis.delete(f"group_quiz:{chat_id}")
