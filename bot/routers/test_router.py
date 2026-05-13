import random
import json
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from redis.asyncio import Redis
from sqlalchemy import delete

from bot.routers.get_words import get_unit_words
from bot.routers.level import pagination_handler, section_selection_handler


router = Router()


@router.callback_query(F.data.startswith("test_"))
async def test_type_selection(callback: CallbackQuery):
    unit_id = callback.data.replace("test_", "")

    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(
            text="🇺🇿 UZ - 🇬🇧 EN", callback_data=f"tmode_uz_en_{unit_id}"
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text="🇬🇧 EN - 🇺🇿 UZ", callback_data=f"tmode_en_uz_{unit_id}"
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text="📖 Description", callback_data=f"tmode_desc_{unit_id}"
        )
    )
    ikb.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"select_{unit_id}"))

    await callback.message.edit_text(
        "🎯 <b>Test turini tanlang:</b>\n\n"
        "• <b>UZ-EN:</b> O'zbekcha so'zga inglizcha javob topish.\n"
        "• <b>EN-UZ:</b> Inglizcha so'zga o'zbekcha javob topish.\n"
        "• <b>Description:</b> Inglizcha ta'rifga mos so'zni topish.",
        reply_markup=ikb.as_markup(),
        parse_mode="HTML",
    )


# 2. Tanlangan rejimga qarab testni boshlash
@router.callback_query(F.data.startswith("tmode_"))
async def start_test_by_mode(callback: CallbackQuery, redis: Redis):
    parts = callback.data.split("_")

    if len(parts) == 4:
        mode = f"{parts[1]}_{parts[2]}"
    else:
        mode = parts[1]  # desc

    unit_id_str = parts[-1]  # "Unit 1"
    unit_num = int(unit_id_str.replace("Unit ", ""))

    user_id = callback.from_user.id
    user_level_raw = await redis.get(f"user:{user_id}:level")
    if not user_level_raw:
        await callback.answer("Sessiya muddati tugagan!", show_alert=True)
        return

    clean_level = user_level_raw.split()[-1].lower()

    # So'zlarni JSON dan o'qish
    words = await get_unit_words(clean_level, unit_num)

    if not words or len(words) < 4:
        await callback.answer(
            "⚠️ Test uchun kamida 4 ta so'z bo'lishi kerak!", show_alert=True
        )
        return

    # Test holatini tayyorlash
    random.shuffle(words)
    test_data = {
        "mode": mode,
        "unit_id": unit_id_str,
        "questions": words[:10],  # Maksimal 10 ta savol
        "current_index": 0,
        "score": 0,
    }

    # Redisga saqlash (30 daqiqa muddat bilan)
    await redis.set(f"test_state:{user_id}", json.dumps(test_data), ex=1800)
    await send_question(callback, test_data)


# 3. Savolni ekranga chiqarish funksiyasi
async def send_question(callback: CallbackQuery, test_data: dict):
    idx = test_data["current_index"]
    mode = test_data["mode"]
    q = test_data["questions"][idx]

    # Rejimga qarab Savol va To'g'ri javobni aniqlash
    if mode == "uz_en":
        question_text = f"🇺🇿 O'zbekcha: <b>{q['uzbek']}</b>"
        correct = q["word"]
        all_variants = [w["word"] for w in test_data["questions"]]
    elif mode == "en_uz":
        question_text = f"🇬🇧 Inglizcha: <b>{q['word']}</b>"
        correct = q["uzbek"]
        all_variants = [w["uzbek"] for w in test_data["questions"]]
    else:  # desc
        question_text = f"📖 Ta'rif: <i>{q['description']}</i>"
        correct = q["word"]
        all_variants = [w["word"] for w in test_data["questions"]]

    # Variantlarni shakllantirish (1 to'g'ri + 3 noto'g'ri)
    wrong_options = [v for v in all_variants if v != correct]
    # Agar unitda so'z kam bo'lsa xato bermasligi uchun min() ishlatamiz
    options = random.sample(wrong_options, min(3, len(wrong_options))) + [correct]
    random.shuffle(options)

    ikb = InlineKeyboardBuilder()
    for opt in options:
        # callback_data: ans_Tanlangan_To'g'ri_UnitID
        # Telegram callback_data limiti 64 byte, shuning uchun ID ni qisqa saqlaymiz
        ikb.row(
            InlineKeyboardButton(
                text=opt, callback_data=f"ans_{opt[:20]}_{correct[:20]}"
            )
        )

    text = f"❓ <b>Savol {idx + 1}/{len(test_data['questions'])}</b>\n\n{question_text}"
    await callback.message.edit_text(
        text, reply_markup=ikb.as_markup(), parse_mode="HTML"
    )


# 4. Javobni tekshirish
@router.callback_query(F.data.startswith("ans_"))
async def check_answer(callback: CallbackQuery, redis: Redis):
    user_id = callback.from_user.id
    state_raw = await redis.get(f"test_state:{user_id}")

    if not state_raw:
        await callback.answer("Sessiya yopilgan. Qayta boshlang.")
        return

    data = json.loads(state_raw)
    _, selected, correct = callback.data.split("_")

    if selected == correct:
        data["score"] += 1
        await callback.answer("✅ To'g'ri!")
    else:
        await callback.answer(
            f"❌ Noto'g'ri! To'g'ri javob: {correct}", show_alert=False
        )

    data["current_index"] += 1

    if data["current_index"] < len(data["questions"]):
        await redis.set(f"test_state:{user_id}", json.dumps(data), ex=1800)
        await send_question(callback, data)
    else:
        # Test natijasi
        score = data["score"]
        total = len(data["questions"])
        unit_id = data["unit_id"]

        await callback.message.edit_text(
            f"🏁 <b>Test yakunlandi!</b>\n\n"
            f"📊 Natijangiz: <b>{score}/{total}</b>\n"
            f"📚 Unit: <b>{unit_id}</b>\n\n"
            "Yana o'rganishni davom ettirasizmi?",
            reply_markup=InlineKeyboardBuilder()
            .row(
                InlineKeyboardButton(
                    text="🔄 Qayta topshirish", callback_data=f"test_{unit_id}"
                ),
                InlineKeyboardButton(
                    text="📕 Unitlar ro'yxati", callback_data="back_to_units"
                ),  # bu callbackni o'zingizga moslang
            )
            .as_markup(),
            parse_mode="HTML",
        )
        await redis.delete(f"test_state:{user_id}")


@router.callback_query(F.data == "back_to_units")
async def back_to_units(callback: CallbackQuery, redis: Redis):
    await callback.message.delete()
    await section_selection_handler(callback.message, redis)
