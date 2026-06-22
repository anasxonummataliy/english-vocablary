import random
import json
import asyncio
from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton, PollAnswer
from aiogram.utils.keyboard import InlineKeyboardBuilder
from redis.asyncio import Redis

from bot.routers.get_words import get_unit_words

router = Router()

TIMER_SECONDS = 15
MAX_SKIPS = 2


timeout_tasks: dict[int, asyncio.Task] = {}


def _to_str(value) -> str | None:
    if value is None:
        return None
    return value.decode() if isinstance(value, bytes) else str(value)


def _cancel_timeout(user_id: int):
    """Foydalanuvchining timeout taskini bekor qilish."""
    task = timeout_tasks.pop(user_id, None)
    if task and not task.done():
        task.cancel()
        print(f"[DEBUG] Timeout bekor qilindi → User {user_id}")


@router.callback_query(F.data.startswith("test_"))
async def test_type_selection(callback: CallbackQuery):
    unit_id = callback.data.replace("test_", "")
    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(
            text="🇺🇿 O'zbekcha → 🇬🇧 Inglizcha",
            callback_data=f"tmode_uz_en_{unit_id}",
            style="success",
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text="🇬🇧 Inglizcha → 🇺🇿 O'zbekcha",
            callback_data=f"tmode_en_uz_{unit_id}",
            style="success",
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text="📖 Ta'rifdan so'zni top",
            callback_data=f"tmode_desc_{unit_id}",
            style="primary",
        )
    )
    ikb.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"select_{unit_id}"))

    try:
        await callback.message.edit_text(
            "🎯 <b>Test turini tanlang:</b>\n\n"
            f"⏱ Har bir savolga <b>{TIMER_SECONDS} soniya</b> vaqt beriladi\n"
            f"⚠️ Ketma-ket <b>{MAX_SKIPS} ta</b> savolga javob berilmasa — test to'xtatiladi",
            reply_markup=ikb.as_markup(),
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


# ==================== TEST BOSHLASH ====================
@router.callback_query(F.data.startswith("tmode_"))
async def start_test_by_mode(callback: CallbackQuery, redis: Redis, bot: Bot):
    parts = callback.data.split("_")
    mode = f"{parts[1]}_{parts[2]}" if len(parts) >= 4 else parts[1]
    unit_id_str = parts[-1]
    unit_num = int(unit_id_str.replace("Unit ", ""))

    user_id = callback.from_user.id
    _cancel_timeout(user_id)

    user_level_raw = _to_str(await redis.get(f"user:{user_id}:level"))
    if not user_level_raw:
        await callback.answer(
            "⚠️ Sessiya muddati tugagan. Qaytadan boshlang!", show_alert=True
        )
        return

    words = await get_unit_words(user_level_raw.split()[-1].lower(), unit_num)
    if not words:
        await callback.answer(
            "❌ Bu unit uchun so'zlar topilmadi. Boshqa unitni tanlang.",
            show_alert=True,
        )
        return
    if len(words) < 4:
        await callback.answer(
            "⚠️ Bu unitda kamida 4 ta so'z bo'lishi kerak!", show_alert=True
        )
        return

    random.shuffle(words)

    test_data = {
        "mode": mode,
        "unit_id": unit_id_str,
        "questions": words,  # unitdagi barcha so'zlar
        "current_index": 0,
        "score": 0,
        "skips": 0,
        "paused": False,
        "poll_id": None,
        "chat_id": callback.message.chat.id,
    }

    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    await redis.set(f"test_state:{user_id}", json.dumps(test_data), ex=3600)
    await send_quiz_poll(bot, user_id, test_data, redis)
    await callback.answer("✅ Test boshlandi!")


# ==================== SAVOL YUBORISH ====================
async def send_quiz_poll(bot: Bot, user_id: int, test_data: dict, redis: Redis):

    if test_data.get("paused"):
        return

    idx = test_data["current_index"]
    mode = test_data["mode"]
    q = test_data["questions"][idx]
    total = len(test_data["questions"])
    chat_id = test_data["chat_id"]

    if mode == "uz_en":
        question = (
            f"[{idx+1}/{total}] 🇺🇿 \"{q['uzbek']}\" so'zining inglizcha tarjimasi?"
        )
        correct = q["word"]
        explanation = f"✅ {q['uzbek']} = {q['word']}"
        pool = [w["word"] for w in test_data["questions"]]
    elif mode == "en_uz":
        question = (
            f"[{idx+1}/{total}] 🇬🇧 \"{q['word']}\" so'zining o'zbekcha tarjimasi?"
        )
        correct = q["uzbek"]
        explanation = f"✅ {q['word']} = {q['uzbek']}"
        pool = [w["uzbek"] for w in test_data["questions"]]
    else:
        question = (
            f"[{idx+1}/{total}] 📖 Ta'rifga mos so'zni toping:\n{q['description']}"
        )
        correct = q["word"]
        explanation = f"✅ To'g'ri javob: {q['word']}"
        pool = [w["word"] for w in test_data["questions"]]

    wrong = [v for v in pool if v != correct]
    options = random.sample(wrong, min(3, len(wrong))) + [correct]
    random.shuffle(options)
    correct_idx = options.index(correct)

    poll_msg = await bot.send_poll(
        chat_id=chat_id,
        question=question[:255],
        options=options,
        type="quiz",
        correct_option_id=correct_idx,
        explanation=explanation,
        is_anonymous=False,
        open_period=TIMER_SECONDS,
    )

    pid = str(poll_msg.poll.id)  # har doim str

    await redis.set(f"poll_correct_idx:{pid}", str(correct_idx), ex=3600)
    await redis.set(f"poll_user:{pid}", str(user_id), ex=3600)

    test_data["poll_id"] = pid
    await redis.set(f"test_state:{user_id}", json.dumps(test_data), ex=3600)

    task = asyncio.create_task(
        _check_after_timeout(bot, user_id, idx, pid, redis, chat_id)
    )
    timeout_tasks[user_id] = task


# ==================== TIMEOUT ====================
async def _check_after_timeout(
    bot: Bot,
    user_id: int,
    expected_index: int,
    expected_poll_id: str,
    redis: Redis,
    chat_id: int,
):
    try:
        await asyncio.sleep(TIMER_SECONDS + 3)

        state_raw = _to_str(await redis.get(f"test_state:{user_id}"))
        if not state_raw:
            return

        data = json.loads(state_raw)

        current_idx = data["current_index"]
        current_poll = str(data.get("poll_id", ""))
        is_paused = data.get("paused", False)

        if is_paused:
            return

        if current_idx != expected_index:
            # Index o'zgardi — biror javob berildi
            return

        if current_poll != expected_poll_id:
            # Boshqa poll — bu eski timeout
            return

        # Javob berilmadi
        data["skips"] += 1
        data["current_index"] += 1

        if data["skips"] >= MAX_SKIPS:

            data["paused"] = True
            await redis.set(f"test_state:{user_id}", json.dumps(data), ex=3600)
            await _send_pause(bot, chat_id, data)
            return

        await redis.set(f"test_state:{user_id}", json.dumps(data), ex=3600)

        if data["current_index"] >= len(data["questions"]):
            await _send_result(bot, chat_id, user_id, data, redis)
            return

        await send_quiz_poll(bot, user_id, data, redis)

    except asyncio.CancelledError:
        pass  # Javob berilganda yoki yangi savol chiqqanda bekor qilinadi
    except Exception as e:
        print(f"[Timeout ERROR] User {user_id}: {e}")


# ==================== POLL JAVOBI ====================
@router.poll_answer()
async def on_poll_answer(poll_answer: PollAnswer, redis: Redis, bot: Bot):
    user_id = poll_answer.user.id
    poll_id = str(poll_answer.poll_id)  # str sifatida

    # 1) Poll bu foydalanuvchiga tegishlimi?
    mapped = _to_str(await redis.get(f"poll_user:{poll_id}"))
    if not mapped or int(mapped) != user_id:
        return

    # 2) Test state mavjudmi?
    state_raw = _to_str(await redis.get(f"test_state:{user_id}"))
    if not state_raw:
        return

    data = json.loads(state_raw)

    # 3) Pauzadadami?
    if data.get("paused"):
        return

    # 4) Joriy savolning pollimi? (vaqti o'tgan eski poll javobini bloklash)
    current_poll_id = str(data.get("poll_id", ""))
    if current_poll_id != poll_id:
        print(
            f"[POLL ANSWER] Eski poll javobi → bekor | {poll_id} != {current_poll_id}"
        )
        return

    # Timeout bekor qilish
    _cancel_timeout(user_id)

    # Javobni baholash
    chosen = poll_answer.option_ids[0] if poll_answer.option_ids else -1
    correct_raw = _to_str(await redis.get(f"poll_correct_idx:{poll_id}"))
    correct_idx = int(correct_raw) if correct_raw else -1
    is_correct = chosen == correct_idx

    if is_correct:
        data["score"] += 1

    # Har qanday javobda (to'g'ri yoki noto'g'ri) skips nollanadi
    # Pauza faqat javob BERILMAGAN hollarda (timeout) ishga tushadi
    data["skips"] = 0

    data["current_index"] += 1

    await redis.delete(f"poll_user:{poll_id}")
    await redis.delete(f"poll_correct_idx:{poll_id}")
    await redis.set(f"test_state:{user_id}", json.dumps(data), ex=3600)

    # Pauza faqat timeout orqali ishga tushadi (ketma-ket javobsiz qolish)
    # Noto'g'ri javob pauza qilmaydi

    await _next_step(bot, user_id, data, redis)


async def _next_step(bot: Bot, user_id: int, data: dict, redis: Redis):
    if data["current_index"] >= len(data["questions"]):
        await _send_result(bot, data["chat_id"], user_id, data, redis)
    else:
        await send_quiz_poll(bot, user_id, data, redis)


# ==================== PAUZA ====================
async def _send_pause(bot: Bot, chat_id: int, data: dict):

    ikb = InlineKeyboardBuilder()
    ikb.row(InlineKeyboardButton(text="▶️ Davom ettirish", callback_data="resume_test", style="success"))
    ikb.row(
        InlineKeyboardButton(
            text="🔄 Qayta boshlash",
            callback_data=f"test_{data['unit_id']}",
            style="primary",
        ),
        InlineKeyboardButton(text="📕 Unitlar", callback_data="back_to_units"),
    )

    answered = data["current_index"]
    total = len(data["questions"])
    remaining = total - answered

    await bot.send_message(
        chat_id=chat_id,
        text=(
            "⏸ <b>Test to'xtatildi!</b>\n\n"
            f"⚠️ Ketma-ket <b>{MAX_SKIPS} ta</b> savolga javob berilmadi.\n\n"
            f"📊 Hozirgi natija: <b>{data['score']}/{answered}</b>\n"
            f"📝 Qolgan savollar: <b>{remaining} ta</b>\n\n"
            "Nima qilmoqchisiz?"
        ),
        reply_markup=ikb.as_markup(),
        parse_mode="HTML",
    )


# ==================== DAVOM ETTIRISH ====================
@router.callback_query(F.data == "resume_test")
async def resume_test(callback: CallbackQuery, redis: Redis, bot: Bot):
    user_id = callback.from_user.id

    state_raw = _to_str(await redis.get(f"test_state:{user_id}"))
    if not state_raw:
        await callback.answer("⚠️ Test sessiyasi topilmadi!", show_alert=True)
        return

    data = json.loads(state_raw)
    data["paused"] = False
    data["skips"] = 0

    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    await redis.set(f"test_state:{user_id}", json.dumps(data), ex=3600)
    await send_quiz_poll(bot, user_id, data, redis)
    await callback.answer("▶️ Test davom ettirildi!")


# ==================== NATIJA ====================
async def _send_result(bot: Bot, chat_id: int, user_id: int, data: dict, redis: Redis):
    score = data["score"]
    total = len(data["questions"])
    percent = score / total if total > 0 else 0

    if percent == 1.0:
        emoji, comment = "🏆", "Mukammal natija! Zo'r!"
    elif percent >= 0.8:
        emoji, comment = "🥇", "A'lo! Juda yaxshi!"
    elif percent >= 0.6:
        emoji, comment = "🥈", "Yaxshi! Davom eting!"
    elif percent >= 0.4:
        emoji, comment = "🥉", "O'rtacha. Ko'proq mashq qiling!"
    else:
        emoji, comment = "📚", "Ko'proq takrorlash kerak."

    filled = round(percent * 10)
    bar = "🟩" * filled + "⬜" * (10 - filled)

    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(
            text="🔄 Qayta topshirish",
            callback_data=f"test_{data['unit_id']}",
            style="primary",
        ),
        InlineKeyboardButton(text="📕 Unitlar", callback_data="back_to_units"),
    )

    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"{emoji} <b>Test yakunlandi!</b>\n\n"
            f"{bar}\n"
            f"📊 Natija: <b>{score}/{total}</b> ({percent:.0%})\n"
            f"💬 {comment}"
        ),
        parse_mode="HTML",
        reply_markup=ikb.as_markup(),
    )
    await redis.delete(f"test_state:{user_id}")


# ==================== UNITLARGA QAYTISH ====================
@router.callback_query(F.data == "back_to_units")
async def back_to_units(callback: CallbackQuery, redis: Redis):
    user_id = callback.from_user.id
    user_level = _to_str(await redis.get(f"user:{user_id}:level"))

    if not user_level:
        await callback.answer("⚠️ Sessiya muddati tugagan.", show_alert=True)
        return

    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    # section_selection_handler o'rniga to'g'ridan-to'g'ri unitlar sahifasiga yo'naltiramiz
    from bot.routers.keyboard import get_page_data, create_units_keyboard, get_available_units

    available_units = get_available_units(user_level)
    if not available_units:
        await callback.message.answer(
            f"⚠️ <b>{user_level}</b> kitobidagi so'zlar hali yuklanmagan.",
            parse_mode="HTML",
        )
        await callback.answer()
        return

    page_data, current_page, total_pages = await get_page_data(0, user_level)

    text = f"📖 Kitob: <b>{user_level}</b>\n"
    text += "🎯 <b>Unit tanlang:</b>\n\n"
    text += f"📊 Jami: {len(available_units)} ta unit mavjud"

    keyboard = await create_units_keyboard(current_page, total_pages, page_data)
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()
