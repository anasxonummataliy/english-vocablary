import html
import json
import random
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
from redis.asyncio import Redis

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.services.basket_service import (
    get_user_baskets,
    get_basket_by_id,
    get_basket_words,
    remove_word_from_basket,
    set_active_basket,
    delete_basket,
    rename_basket,
    add_word_to_basket,
    MAX_BASKET_SIZE,
)


class BasketRenameState(StatesGroup):
    waiting_for_new_name = State()

router = Router()


def _format_basket_words_text(words: list, basket_name: str, start_index: int = 1) -> str:
    text = (
        f"🧺 <b>{html.escape(basket_name)}</b> — So'zlar ro'yxati\n"
        f"📊 Jami: <b>{len(words)} ta so'z</b>\n\n"
        f"{'━' * 20}\n\n"
    )
    for i, word in enumerate(words, start=start_index):
        word_str = html.escape(word.get("word", ""))
        transcription = html.escape(word.get("transcription", ""))
        pos = html.escape(word.get("part_of_speech", ""))
        uzbek = html.escape(word.get("uzbek", "—"))
        description = html.escape(word.get("description", ""))
        example = html.escape(word.get("example", ""))
        text += (
            f"<b>{i}. {word_str}</b>  <code>{transcription}</code>\n"
            f"   🇺🇿 <b>{uzbek}</b>\n"
        )
        if pos or description:
            text += f"   📖 <i>{pos}</i> — {description}\n"
        if example:
            text += f"   ✏️ <i>{example}</i>\n"

        if i < start_index + len(words) - 1:
            text += f"\n{'─' * 18}\n\n"
    return text


@router.message(Command("savat", "basket", "savatcha"))
async def cmd_basket(message: Message):
    user_id = message.from_user.id
    baskets = await get_user_baskets(user_id)

    if not baskets:
        ikb = InlineKeyboardBuilder()
        ikb.row(
            InlineKeyboardButton(
                text="🏠 Asosiy menyu (Kitoblar)",
                callback_data="menu_main",
                style="primary",
            )
        )
        text = (
            "🧺 <b>Sizning Savatchangiz bo'sh!</b>\n\n"
            "So'zlarni o'rganish, Flash card yoki Test ishlash vaqtida bilmagan so'zlaringizni "
            "<b>'🛒 Savatga qo'shish'</b> tugmasi orqali saqlab borishingiz mumkin.\n\n"
            f"Har bir savatchaga ko'pi bilan <b>{MAX_BASKET_SIZE} ta so'z</b> sig'adi."
        )
        await message.answer(text, reply_markup=ikb.as_markup(), parse_mode="HTML")
        return

    ikb = InlineKeyboardBuilder()
    for b in baskets:
        active_mark = " (⭐️ Faol)" if b["is_active"] else ""
        btn_text = f"🧺 {b['name']} ({b['word_count']}/{MAX_BASKET_SIZE}){active_mark}"
        ikb.row(
            InlineKeyboardButton(
                text=btn_text,
                callback_data=f"bview_{b['id']}",
                style="primary",
            )
        )
    ikb.row(
        InlineKeyboardButton(
            text="🏠 Asosiy menyu (Kitoblar)",
            callback_data="menu_main",
            style="danger",
        )
    )

    text = (
        "🧺 <b>SIZNING SAVATCHALARINGIZ:</b>\n\n"
        "Kerakli savatchani tanlang va undagi so'zlarni o'rganing, flash card qiling yoki test topshiring:"
    )
    await message.answer(text, reply_markup=ikb.as_markup(), parse_mode="HTML")


@router.callback_query(F.data == "baskets_list")
async def callback_baskets_list(callback: CallbackQuery):
    user_id = callback.from_user.id
    baskets = await get_user_baskets(user_id)

    if not baskets:
        ikb = InlineKeyboardBuilder()
        ikb.row(
            InlineKeyboardButton(
                text="🏠 Asosiy menyu (Kitoblar)",
                callback_data="menu_main",
                style="primary",
            )
        )
        try:
            await callback.message.edit_text(
                "🧺 <b>Sizning Savatchangiz bo'sh!</b>\n\n"
                "So'zlarni o'rganish yoki test vaqtida <b>'🛒 Savatga qo'shish'</b> tugmasini bosing.",
                reply_markup=ikb.as_markup(),
                parse_mode="HTML",
            )
        except TelegramBadRequest:
            pass
        await callback.answer()
        return

    ikb = InlineKeyboardBuilder()
    for b in baskets:
        active_mark = " (⭐️ Faol)" if b["is_active"] else ""
        btn_text = f"🧺 {b['name']} ({b['word_count']}/{MAX_BASKET_SIZE}){active_mark}"
        ikb.row(
            InlineKeyboardButton(
                text=btn_text,
                callback_data=f"bview_{b['id']}",
                style="primary",
            )
        )
    ikb.row(
        InlineKeyboardButton(
            text="🏠 Asosiy menyu (Kitoblar)",
            callback_data="menu_main",
            style="danger",
        )
    )

    text = (
        "🧺 <b>SIZNING SAVATCHALARINGIZ:</b>\n\n"
        "Kerakli savatchani tanlang:"
    )
    try:
        await callback.message.edit_text(text, reply_markup=ikb.as_markup(), parse_mode="HTML")
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("bview_"))
async def callback_view_basket(callback: CallbackQuery, state: FSMContext = None):
    if state:
        await state.clear()
    basket_id = int(callback.data.removeprefix("bview_"))
    user_id = callback.from_user.id

    basket = await get_basket_by_id(basket_id, user_id=user_id)
    if not basket:
        await callback.answer("❌ Savatcha topilmadi.", show_alert=True)
        return

    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(
            text="📖 So'zlarni ko'rish",
            callback_data=f"bwords_{basket_id}_1",
            style="primary",
        ),
    )
    ikb.row(
        InlineKeyboardButton(
            text="🃏 Flash card qilish",
            callback_data=f"bflash_{basket_id}",
            style="primary",
        ),
    )
    ikb.row(
        InlineKeyboardButton(
            text="📝 Test yechish",
            callback_data=f"btest_{basket_id}",
            style="success",
        ),
    )

    ikb.row(
        InlineKeyboardButton(
            text="✏️ Nomini o'zgartirish",
            callback_data=f"brename_{basket_id}",
            style="primary",
        )
    )

    if not basket["is_active"]:
        ikb.row(
            InlineKeyboardButton(
                text="⭐️ Faol savat qilish (Yangi so'zlar uchun)",
                callback_data=f"bsetactive_{basket_id}",
                style="success",
            )
        )

    ikb.row(
        InlineKeyboardButton(
            text="🗑 Savatchani o'chirish",
            callback_data=f"bdelconfirm_{basket_id}",
            style="danger",
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text="⬅️ Savatchalar ro'yxatiga",
            callback_data="baskets_list",
            style="danger",
        ),
        InlineKeyboardButton(
            text="🏠 Asosiy menyu",
            callback_data="menu_main",
            style="primary",
        ),
    )

    status_str = "⭐️ <b>Hozirgi faol savat</b> (yangi so'zlar shu yerga tushadi)" if basket["is_active"] else "Oddiy savat"
    text = (
        f"🧺 <b>{html.escape(basket['name'])}</b>\n"
        f"📊 So'zlar soni: <b>{basket['word_count']}/{MAX_BASKET_SIZE} ta</b>\n"
        f"📌 Holati: {status_str}\n\n"
        f"Ushbu savatcha bilan nima qilmoqchisiz?"
    )

    try:
        await callback.message.edit_text(text, reply_markup=ikb.as_markup(), parse_mode="HTML")
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("brename_"))
async def callback_start_rename_basket(callback: CallbackQuery, state: FSMContext):
    basket_id = int(callback.data.removeprefix("brename_"))
    user_id = callback.from_user.id

    basket = await get_basket_by_id(basket_id, user_id=user_id)
    if not basket:
        await callback.answer("❌ Savatcha topilmadi.", show_alert=True)
        return

    await state.set_state(BasketRenameState.waiting_for_new_name)
    await state.update_data(basket_id=basket_id, old_name=basket["name"])

    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(
            text="❌ Bekor qilish",
            callback_data=f"bview_{basket_id}",
            style="danger",
        )
    )

    text = (
        f"✏️ <b>{html.escape(basket['name'])}</b> savatchasi uchun yangi nom yozib yuboring:\n\n"
        "<i>(Masalan: Qiyin so'zlar, IELTS lug'at, Unit 5 xatolari...)</i>"
    )
    try:
        await callback.message.edit_text(text, reply_markup=ikb.as_markup(), parse_mode="HTML")
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.message(BasketRenameState.waiting_for_new_name)
async def message_save_new_basket_name(message: Message, state: FSMContext):
    new_name = (message.text or "").strip()
    if not new_name:
        await message.answer("⚠️ Iltimos, savatcha uchun yangi nom yozing:")
        return

    data = await state.get_data()
    basket_id = data.get("basket_id")
    user_id = message.from_user.id
    await state.clear()

    success, msg = await rename_basket(user_id, basket_id, new_name)
    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(
            text="🧺 Savatchani ko'rish",
            callback_data=f"bview_{basket_id}",
            style="primary",
        ),
        InlineKeyboardButton(
            text="⬅️ Savatchalar ro'yxatiga",
            callback_data="baskets_list",
            style="danger",
        ),
    )
    await message.answer(msg, reply_markup=ikb.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("bdelconfirm_"))
async def callback_confirm_delete_basket(callback: CallbackQuery):
    basket_id = int(callback.data.removeprefix("bdelconfirm_"))
    user_id = callback.from_user.id

    basket = await get_basket_by_id(basket_id, user_id=user_id)
    if not basket:
        await callback.answer("❌ Savatcha topilmadi.", show_alert=True)
        return

    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(
            text="✅ Ha, o'chirilsin",
            callback_data=f"bdel_{basket_id}",
            style="danger",
        ),
        InlineKeyboardButton(
            text="❌ Bekor qilish",
            callback_data=f"bview_{basket_id}",
            style="success",
        ),
    )

    text = (
        f"⚠️ <b>{html.escape(basket['name'])}</b> savatchasini va undagi barcha ({basket['word_count']} ta) so'zlarni "
        "o'chirib tashlamoqchimisiz?\n\n"
        "<i>Bu amalni ortga qaytarib bo'lmaydi.</i>"
    )
    try:
        await callback.message.edit_text(text, reply_markup=ikb.as_markup(), parse_mode="HTML")
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("bsetactive_"))
async def callback_set_active_basket(callback: CallbackQuery):
    basket_id = int(callback.data.removeprefix("bsetactive_"))
    user_id = callback.from_user.id
    success = await set_active_basket(user_id, basket_id)
    if success:
        await callback.answer("⭐️ Savatcha asosiy (faol) qilib belgilandi!", show_alert=True)
    else:
        await callback.answer("❌ Xatolik yuz berdi.", show_alert=True)
    await callback_view_basket(callback)


@router.callback_query(F.data.startswith("bdel_"))
async def callback_delete_basket(callback: CallbackQuery):
    basket_id = int(callback.data.removeprefix("bdel_"))
    user_id = callback.from_user.id

    success, msg = await delete_basket(user_id, basket_id)
    await callback.answer(msg.replace("<b>", "").replace("</b>", ""), show_alert=True)
    await callback_baskets_list(callback)


@router.callback_query(F.data.startswith("bwords_"))
async def callback_basket_words_view(callback: CallbackQuery):
    parts = callback.data.split("_")
    basket_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 1

    user_id = callback.from_user.id
    basket = await get_basket_by_id(basket_id, user_id=user_id)
    if not basket:
        await callback.answer("❌ Savatcha topilmadi.", show_alert=True)
        return

    words = await get_basket_words(basket_id)
    if not words:
        await callback.answer("ℹ️ Savatchada hali so'zlar yo'q.", show_alert=True)
        return

    start_idx = (page - 1) * 7
    end_idx = page * 7
    preview_words = words[start_idx:end_idx]

    if not preview_words:
        page = 1
        start_idx = 0
        end_idx = 7
        preview_words = words[start_idx:end_idx]

    text = _format_basket_words_text(preview_words, basket["name"], start_index=start_idx + 1)
    page_total = (len(words) + 6) // 7
    text += f"\n📄 Sahifa: <b>{page}/{page_total}</b>\n"
    text += "<i>So'zni savatdan o'chirish uchun pastdagi 🗑 [Raqam] tugmasini bosing:</i>"

    ikb = InlineKeyboardBuilder()

    # O'chirish tugmalari qatori (shu sahifadagi so'zlar uchun)
    del_row = []
    for i, w in enumerate(preview_words, start=start_idx + 1):
        del_row.append(
            InlineKeyboardButton(
                text=f"🗑 {i}",
                callback_data=f"bdelw_{basket_id}_{w['id']}_{page}",
                style="danger",
            )
        )
    if del_row:
        # 4 tadan qilib joylaymiz
        ikb.row(*del_row[:4])
        if len(del_row) > 4:
            ikb.row(*del_row[4:])

    # Navigatsiya
    nav_row = []
    if page > 1:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Oldingisi",
                callback_data=f"bwords_{basket_id}_{page - 1}",
                style="success",
            )
        )
    if len(words) > page * 7:
        nav_row.append(
            InlineKeyboardButton(
                text="Keyingisi ➡️",
                callback_data=f"bwords_{basket_id}_{page + 1}",
                style="success",
            )
        )
    if nav_row:
        ikb.row(*nav_row)

    ikb.row(
        InlineKeyboardButton(
            text="⬅️ Savatchaga qaytish",
            callback_data=f"bview_{basket_id}",
            style="danger",
        ),
        InlineKeyboardButton(
            text="🏠 Asosiy menyu",
            callback_data="menu_main",
            style="primary",
        ),
    )

    try:
        await callback.message.edit_text(text, reply_markup=ikb.as_markup(), parse_mode="HTML")
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("bdelw_"))
async def callback_delete_word_from_basket(callback: CallbackQuery):
    parts = callback.data.split("_")
    basket_id = int(parts[1])
    word_id = int(parts[2])
    page = int(parts[3]) if len(parts) > 3 else 1

    success, msg = await remove_word_from_basket(basket_id, word_id)
    await callback.answer(msg.replace("<b>", "").replace("</b>", ""), show_alert=False)

    # Sahifani yangilaymiz
    words = await get_basket_words(basket_id)
    if not words:
        await callback_view_basket(callback)
        return

    # Yangi sahifani hisoblaymiz
    page_total = (len(words) + 6) // 7
    if page > page_total:
        page = max(1, page_total)

    callback.data = f"bwords_{basket_id}_{page}"
    await callback_basket_words_view(callback)


# ==================== SAVAT FLASH CARD ====================
@router.callback_query(F.data.startswith("bflash_"))
async def callback_basket_flash_start(callback: CallbackQuery, redis: Redis):
    basket_id = int(callback.data.removeprefix("bflash_"))
    user_id = callback.from_user.id

    basket = await get_basket_by_id(basket_id, user_id=user_id)
    words = await get_basket_words(basket_id)

    if not words:
        await callback.answer("❌ Bu savatchada so'zlar yo'q.", show_alert=True)
        return

    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(
            text="🇺🇿 O'zbekcha → 🇬🇧 Inglizcha",
            callback_data=f"bfmode_uz_en_{basket_id}",
            style="primary",
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text="🇬🇧 Inglizcha → 🇺🇿 O'zbekcha",
            callback_data=f"bfmode_en_uz_{basket_id}",
            style="primary",
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text="📖 Ta'rif → 🇬🇧 Inglizcha",
            callback_data=f"bfmode_desc_en_{basket_id}",
            style="primary",
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text="⬅️ Orqaga",
            callback_data=f"bview_{basket_id}",
            style="danger",
        )
    )

    text = (
        f"🃏 <b>{html.escape(basket['name'])} — Flash Card</b>\n\n"
        "Mashg'ulot turini tanlang:"
    )
    try:
        await callback.message.edit_text(text, reply_markup=ikb.as_markup(), parse_mode="HTML")
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("bfmode_"))
async def callback_start_basket_flash_session(callback: CallbackQuery, redis: Redis):
    raw = callback.data.removeprefix("bfmode_")
    # Format: uz_en_{basket_id} | en_uz_{basket_id} | desc_en_{basket_id}
    if raw.startswith("desc_en_"):
        mode = "desc_en"
        basket_id = int(raw.removeprefix("desc_en_"))
    elif raw.startswith("uz_en_"):
        mode = "uz_en"
        basket_id = int(raw.removeprefix("uz_en_"))
    elif raw.startswith("en_uz_"):
        mode = "en_uz"
        basket_id = int(raw.removeprefix("en_uz_"))
    else:
        await callback.answer("❌ Noto'g'ri format.", show_alert=True)
        return

    user_id = callback.from_user.id
    words = await get_basket_words(basket_id)
    if not words:
        await callback.answer("❌ Savatchada so'zlar yo'q.", show_alert=True)
        return

    random.shuffle(words)
    flash_state = {
        "mode": mode,
        "unit_id": f"Basket {basket_id}",
        "words": words,
        "current_index": 0,
        "is_basket": True,
        "basket_id": basket_id,
    }

    await redis.set(f"flash_state:{user_id}", json.dumps(flash_state), ex=3600)
    from bot.routers.flashcard import show_flash_card
    await show_flash_card(callback, flash_state, user_id)
    await callback.answer()


# ==================== SAVAT TEST ====================
@router.callback_query(F.data.startswith("btest_"))
async def callback_basket_test_start(callback: CallbackQuery):
    basket_id = int(callback.data.removeprefix("btest_"))
    user_id = callback.from_user.id

    basket = await get_basket_by_id(basket_id, user_id=user_id)
    words = await get_basket_words(basket_id)

    if not words or len(words) < 4:
        await callback.answer(
            f"⚠️ Test yechish uchun savatchada kamida 4 ta so'z bo'lishi kerak! (Hozir: {len(words)} ta)",
            show_alert=True,
        )
        return

    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(
            text="🇺🇿 O'zbekcha → 🇬🇧 Inglizcha",
            callback_data=f"btmode_uz_en_{basket_id}",
            style="primary",
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text="🇬🇧 Inglizcha → 🇺🇿 O'zbekcha",
            callback_data=f"btmode_en_uz_{basket_id}",
            style="primary",
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text="📖 Ta'rifdan so'zni top",
            callback_data=f"btmode_desc_{basket_id}",
            style="primary",
        )
    )
    ikb.row(
        InlineKeyboardButton(
            text="⬅️ Orqaga",
            callback_data=f"bview_{basket_id}",
            style="danger",
        )
    )

    text = (
        f"📝 <b>{html.escape(basket['name'])} — Test yechish</b>\n\n"
        "Test turini tanlang:\n"
        "⏱ Har bir savolga <b>15 soniya</b> beriladi."
    )
    try:
        await callback.message.edit_text(text, reply_markup=ikb.as_markup(), parse_mode="HTML")
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("btmode_"))
async def callback_start_basket_test_session(callback: CallbackQuery, redis: Redis, bot: Bot):
    raw = callback.data.removeprefix("btmode_")
    if raw.startswith("desc_"):
        mode = "desc"
        basket_id = int(raw.removeprefix("desc_"))
    elif raw.startswith("uz_en_"):
        mode = "uz_en"
        basket_id = int(raw.removeprefix("uz_en_"))
    elif raw.startswith("en_uz_"):
        mode = "en_uz"
        basket_id = int(raw.removeprefix("en_uz_"))
    else:
        await callback.answer("❌ Noto'g'ri format.", show_alert=True)
        return

    user_id = callback.from_user.id
    words = await get_basket_words(basket_id)
    if not words or len(words) < 4:
        await callback.answer("⚠️ Kamida 4 ta so'z kerak!", show_alert=True)
        return

    random.shuffle(words)
    test_data = {
        "mode": mode,
        "unit_id": f"Savatcha",
        "questions": words,
        "current_index": 0,
        "score": 0,
        "skips": 0,
        "paused": False,
        "poll_id": None,
        "chat_id": callback.message.chat.id,
        "is_basket": True,
        "basket_id": basket_id,
    }

    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    from bot.routers.test_router import _cancel_timeout, send_quiz_poll
    _cancel_timeout(user_id)

    await redis.set(f"test_state:{user_id}", json.dumps(test_data), ex=3600)
    await send_quiz_poll(bot, user_id, test_data, redis)
    await callback.answer("✅ Test boshlandi!")
