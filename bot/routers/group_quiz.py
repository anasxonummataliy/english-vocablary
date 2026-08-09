import random
import json
import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, PollAnswer
from aiogram.utils.keyboard import InlineKeyboardBuilder
from redis.asyncio import Redis

from bot.routers.get_words import get_unit_words, get_all_level_words
from bot.services.score_service import save_score

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


# ==================== /quiz KOMANDASI ====================
@router.message(Command("quiz", "musobaqa"))
async def cmd_start_group_quiz(message: Message, redis: Redis):
    chat_id = message.chat.id

    # Tekshirish: aktiv musobaqa bor-yo'qligi
    existing = await redis.get(f"group_quiz:{chat_id}")
    if existing:
        await message.reply(
            "⚠️ <b>Bu guruhda allaqachon aktiv musobaqa ketmoqda!</b>\n"
            "Uning tugashini kuting yoki navbatdagi savollarga javob bering.",
            parse_mode="HTML",
        )
        return

    ikb = InlineKeyboardBuilder()
    levels = [
        ("🟢 Elementary", "gq_lvl_elementary"),
        ("🔵 Pre-Intermediate", "gq_lvl_preintermediate"),
        ("🟡 Intermediate", "gq_lvl_intermediate"),
        ("🟠 Upper-Intermediate", "gq_lvl_upperintermediate"),
        ("🔴 Advanced", "gq_lvl_advanced"),
    ]
    for name, code in levels:
        ikb.row(InlineKeyboardButton(text=name, callback_data=code))

    await message.answer(
        "🏆 <b>Guruh musobaqasi!</b>\n\n"
        "Qaysi daraja (level) bo'yicha musobaqa o'tkazmoqchisiz?",
        reply_markup=ikb.as_markup(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("gq_lvl_"))
async def select_gquiz_level(callback: CallbackQuery):
    level = callback.data.removeprefix("gq_lvl_")

    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(
            text="🔀 Mix (20 ta aralash savol)", callback_data=f"gq_start_{level}_mix"
        )
    )
    # Har bir level uchun 1-10 unitlar
    row = []
    for u in range(1, 11):
        row.append(
            InlineKeyboardButton(
                text=f"Unit {u}", callback_data=f"gq_start_{level}_{u}"
            )
        )
        if len(row) == 5:
            ikb.row(*row)
            row = []
    if row:
        ikb.row(*row)

    await callback.message.edit_text(
        f"📖 Tanlangan daraja: <b>{level.capitalize()}</b>\n"
        "🎯 <b>Musobaqa turini yoki Unitni tanlang:</b>",
        reply_markup=ikb.as_markup(),
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
        selected_words = words[:10]  # Standard unit uchun 10-20 ta savol
        unit_display = f"Unit {unit_num}"

    quiz_data = {
        "chat_id": chat_id,
        "level": level,
        "unit_num": unit_num,
        "unit_display": unit_display,
        "questions": selected_words,
        "current_index": 0,
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
        if quiz_data["current_index"] != expected_idx:
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

    await redis.set(f"group_quiz:{chat_id}", json.dumps(quiz_data), ex=3600)


# ==================== MUSOBAQANI YAKUNLASH ====================
async def finish_group_quiz(bot: Bot, chat_id: int, quiz_data: dict, redis: Redis):
    _cancel_gquiz_task(chat_id)
    scores = quiz_data.get("scores", {})
    total_q = len(quiz_data.get("questions", []))
    level = quiz_data.get("level", "elementary")
    unit_num = quiz_data.get("unit_num", 1)

    # Natijalarni bazaga saqlash va tartiblash
    sorted_players = sorted(
        scores.items(), key=lambda item: item[1]["score"], reverse=True
    )

    text = (
        f"🏆 <b>MUSOBAQA YAKUNLANDI!</b>\n\n"
        f"📚 Daraja: <b>{level.capitalize()}</b> | Unit: <b>Unit {unit_num}</b>\n"
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
    await redis.delete(f"group_quiz:{chat_id}")
