from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.enums import ChatType
from aiogram.types import (
    InlineKeyboardButton,
    Message,
    ReplyKeyboardRemove,
    CallbackQuery,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from redis.asyncio import Redis

from bot.routers.keyboard import (
    main_menu_keyboard,
    main_menu_inline_keyboard,
    vocabulary_in_use_keyboard,
    vocabulary_in_use_inline_keyboard,
    essential_words_keyboard,
    essential_words_inline_keyboard,
    level_keyboard,
    get_page_data,
    create_units_keyboard,
    get_available_units,
    BOOK_VOCABULARY_IN_USE,
    BOOK_ESSENTIAL_WORDS,
    MAIN_MENU_BASKET,
    BTN_BACK_MAIN,
    LEVEL_DEFINITIONS,
    VOCABULARY_IN_USE_LEVELS,
    ESSENTIAL_WORDS_LEVELS,
)

router = Router()


def _decode(value) -> str | None:
    """Redis qiymatini stringga aylantirish."""
    if value is None:
        return None
    return value.decode() if isinstance(value, bytes) else str(value)


async def get_user_context(user_id: int, redis: Redis) -> str | None:
    """Redisdan foydalanuvchi tanlagan kitobni olish uchun"""
    raw = await redis.get(f"user:{user_id}:level")
    return _decode(raw)


@router.message(Command("level"))
async def level_handler(message: Message):
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer(
            "👥 Guruhda musobaqa va viktorina o'tkazish uchun <b>/quiz</b> buyrug'idan foydalaning!\n"
            "Reytinglarni ko'rish uchun <b>/top</b> buyrug'ini bosing.",
            parse_mode="HTML",
        )
        return
    kb = await main_menu_keyboard()
    await message.answer(
        "📚 <b>Kitoblar va Savatcha</b>\n\nQaysi bo'limdan boshlamoqchisiz?",
        reply_markup=kb.as_markup(resize_keyboard=True),
        parse_mode="HTML",
    )


# ==================== INLINE ASOSIY MENYU HANDLERLARI ====================

@router.callback_query(F.data == "menu_main")
async def callback_menu_main(callback: CallbackQuery):
    kb = await main_menu_keyboard()
    await callback.message.answer(
        "🏠 <b>Asosiy menyu</b>\n\nQaysi bo'limdan boshlamoqchisiz?",
        reply_markup=kb.as_markup(resize_keyboard=True),
        parse_mode="HTML",
    )
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data == "menu_vocab_in_use")
async def callback_menu_vocab_in_use(callback: CallbackQuery):
    ikb = await vocabulary_in_use_inline_keyboard()
    try:
        await callback.message.edit_text(
            "📘 <b>English Vocabulary in Use</b>\n\nKerakli darajani tanlang:",
            reply_markup=ikb,
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data == "menu_essential_words")
async def callback_menu_essential_words(callback: CallbackQuery):
    ikb = await essential_words_inline_keyboard()
    try:
        await callback.message.edit_text(
            "🔵 <b>Essential Words</b>\n\nKerakli kitobni tanlang:",
            reply_markup=ikb,
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("lvl_sel_"))
async def callback_level_select(callback: CallbackQuery, redis: Redis):
    code = callback.data.removeprefix("lvl_sel_")
    level_title = None
    for title, c in LEVEL_DEFINITIONS:
        if c == code:
            level_title = title
            break
    if not level_title:
        level_title = code

    user_id = callback.from_user.id
    await redis.set(f"user:{user_id}:level", level_title, ex=86400)

    available_units = get_available_units(level_title)
    if not available_units:
        await callback.answer(
            f"⚠️ {level_title} kitobidagi so'zlar hali yuklanmagan.",
            show_alert=True,
        )
        return

    page_data, current_page, total_pages = await get_page_data(0, level_title)
    back_target = (
        "menu_vocab_in_use"
        if any(c == code for _, c in VOCABULARY_IN_USE_LEVELS)
        else "menu_essential_words"
    )
    extra_bottom = [
        [
            InlineKeyboardButton(
                text="⬅️ Kitoblar ro'yxatiga",
                callback_data=back_target,
                style="danger",
            )
        ]
    ]

    keyboard = await create_units_keyboard(
        current_page,
        total_pages,
        page_data,
        extra_bottom_buttons=extra_bottom,
    )

    text = f"📖 Kitob: <b>{level_title}</b>\n"
    text += "🎯 <b>Unit tanlang:</b>\n\n"
    text += f"📊 Jami: {len(available_units)} ta unit mavjud"

    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except TelegramBadRequest:
        pass
    await callback.answer()


# ==================== KITOBLAR VA ASOSIY MENYU TUGMALARI ====================

@router.message(F.text.in_({BOOK_VOCABULARY_IN_USE, "📚 English Vocabulary in Use", "📘 English Vocabulary in Use", "English Vocabulary in Use", "Vocabulary in Use"}))
async def handle_vocabulary_in_use_selection(message: Message):
    kb = await vocabulary_in_use_keyboard()
    await message.answer(
        "📘 <b>English Vocabulary in Use</b>\n\nKerakli darajani tanlang:",
        reply_markup=kb.as_markup(resize_keyboard=True),
        parse_mode="HTML",
    )


@router.message(F.text.in_({BOOK_ESSENTIAL_WORDS, "📗 4000 Essential English Words", "📖 4000 Essential English Words", "🔵 4000 Essential English Words", "4000 Essential English Words", "Essential Words"}))
async def handle_essential_words_selection(message: Message):
    kb = await essential_words_keyboard()
    await message.answer(
        "📗 <b>4000 Essential English Words</b>\n\nKerakli kitobni tanlang:",
        reply_markup=kb.as_markup(resize_keyboard=True),
        parse_mode="HTML",
    )


@router.message(F.text.in_({MAIN_MENU_BASKET, "🧺 Mening savatcham", "🧺 Savatcham", "🛒 Mening savatcham", "🛒 Savatcham", "🟢 Mening savatcham", "Mening savatcham", "Savatcham"}))
async def handle_basket_button(message: Message):
    from bot.routers.basket import cmd_basket
    await cmd_basket(message)


@router.message(F.text.in_({BTN_BACK_MAIN, "🔴 Asosiy menyu", "⬅️ Asosiy menyu", "⬅️ Bosh menyu", "⬅️ Orqaga", "Asosiy menyu"}))
async def handle_back_to_main_menu(message: Message):
    kb = await main_menu_keyboard()
    await message.answer(
        "🏠 <b>Asosiy menyu</b>\n\nQaysi bo'limdan boshlamoqchisiz?",
        reply_markup=kb.as_markup(resize_keyboard=True),
        parse_mode="HTML",
    )


VALID_LEVEL_BUTTONS = {
    # English Vocabulary in Use
    "📘 Elementary",
    "📗 Elementary",
    "🟢 Elementary",
    "📘 Pre-intermediate & Intermediate",
    "📘 Pre-Intermediate & Intermediate",
    "🔵 Pre-intermediate & Intermediate",
    "🔵 Pre-Intermediate & Intermediate",
    "📘 Upper intermediate",
    "📘 Upper Intermediate",
    "📙 Upper intermediate",
    "📙 Upper Intermediate",
    "📘 Advanced",
    "📕 Advanced",
    "🔴 Advanced",
    # 4000 Essential English Words / Essential Words
    "📗 Essential Words 1",
    "📘 Essential Words 2",
    "📙 Essential Words 3",
    "📕 Essential Words 4",
    "📔 Essential Words 5",
    "📓 Essential Words 6",
    "🔵 Essential Words 1",
    "🔵 Essential Words 2",
    "🔵 Essential Words 3",
    "🔵 Essential Words 4",
    "🔵 Essential Words 5",
    "🔵 Essential Words 6",
    "Essential Words 1",
    "Essential Words 2",
    "Essential Words 3",
    "Essential Words 4",
    "Essential Words 5",
    "Essential Words 6",
    "🔵 4000 Essential English Words 1",
    "🔵 4000 Essential English Words 2",
    "🔵 4000 Essential English Words 3",
    "🔵 4000 Essential English Words 4",
    "🔵 4000 Essential English Words 5",
    "🔵 4000 Essential English Words 6",
    "📕 4000 Essential English Words 1",
    "📗 4000 Essential English Words 2",
    "📘 4000 Essential English Words 3",
    "📙 4000 Essential English Words 4",
    "📓 4000 Essential English Words 5",
    "📔 4000 Essential English Words 6",
    "📚 4000 Essential English Words 1",
    "📚 4000 Essential English Words 2",
    "📚 4000 Essential English Words 3",
    "📚 4000 Essential English Words 4",
    "📚 4000 Essential English Words 5",
    "📚 4000 Essential English Words 6",
    "4000 Essential English Words 1",
    "4000 Essential English Words 2",
    "4000 Essential English Words 3",
    "4000 Essential English Words 4",
    "4000 Essential English Words 5",
    "4000 Essential English Words 6",
}


@router.message(F.text.in_(VALID_LEVEL_BUTTONS))
async def section_selection_handler(message: Message, redis: Redis):
    level_name = message.text
    user_id = message.from_user.id

    await redis.set(f"user:{user_id}:level", level_name, ex=86400)

    # Avval bu level uchun unitlar mavjudligini tekshiramiz
    available_units = get_available_units(level_name)
    if not available_units:
        await message.answer(
            f"⚠️ <b>{level_name}</b> kitobidagi so'zlar hali yuklanmagan.\n\n"
            "Tez orada qo'shiladi! Boshqa darajani tanlang.",
            parse_mode="HTML",
        )
        return

    page_data, current_page, total_pages = await get_page_data(0, level_name)

    text = f"📖 Kitob: <b>{level_name}</b>\n"
    text += "🎯 <b>Unit tanlang:</b>\n\n"
    text += f"📊 Jami: {len(available_units)} ta unit mavjud"

    extra_bottom = [
        [
            InlineKeyboardButton(
                text="🏠 Asosiy menyu",
                callback_data="menu_main",
                style="danger",
            )
        ]
    ]

    keyboard = await create_units_keyboard(
        current_page,
        total_pages,
        page_data,
        extra_bottom_buttons=extra_bottom,
    )

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("page_"))
async def pagination_handler(callback: CallbackQuery, redis: Redis):
    user_id = callback.from_user.id
    page = int(callback.data.split("_")[1])

    user_level = await get_user_context(user_id, redis)

    if not user_level:
        await callback.answer(
            "⚠️ Sessiya muddati tugagan. Qaytadan darajani tanlang.", show_alert=True
        )
        return

    page_data, current_page, total_pages = await get_page_data(page, user_level)

    if not page_data:
        await callback.answer("❌ Bu sahifada ma'lumot yo'q.", show_alert=True)
        return

    text = f"📖 Kitob: <b>{user_level}</b>\n"
    text += "🎯 <b>Unit tanlang:</b>\n\n"
    text += f"📊 Sahifa: {current_page + 1}/{total_pages}"

    extra_bottom = [
        [
            InlineKeyboardButton(
                text="🏠 Asosiy menyu",
                callback_data="menu_main",
                style="danger",
            )
        ]
    ]

    keyboard = await create_units_keyboard(
        current_page,
        total_pages,
        page_data,
        extra_bottom_buttons=extra_bottom,
    )

    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except TelegramBadRequest:
        pass

    await callback.answer()


@router.callback_query(F.data.startswith("select_"))
async def select_handler(callback: CallbackQuery, redis: Redis):
    selected_unit = callback.data.replace("select_", "")  # "Unit 3"
    selected_unit_safe = selected_unit.replace(" ", "_")   # "Unit_3" — callback_data uchun
    user_id = callback.from_user.id

    user_level = await get_user_context(user_id, redis)

    if not user_level:
        await callback.answer("⚠️ Sessiya muddati tugagan.", show_alert=True)
        return

    ikb = InlineKeyboardBuilder()
    ikb.row(
        InlineKeyboardButton(
            text="📖 So'zlarni o'rganish",
            callback_data=f"words_{selected_unit_safe}",
            style="primary",
        ),
    )
    ikb.row(
        InlineKeyboardButton(
            text="🃏 Flash card",
            callback_data=f"flash_{selected_unit_safe}",
            style="primary",
        ),
    )
    ikb.row(
        InlineKeyboardButton(
            text="📝 Test yechish",
            callback_data=f"test_{selected_unit_safe}",
            style="success",
        ),
    )

    ikb.row(
        InlineKeyboardButton(
            text="⬅️ Unitlar ro'yxatiga qaytish",
            callback_data="page_0",
            style="danger",
        )
    )

    text = f"📚 <b>Kitob:</b> {user_level}\n"
    text += f"✅ <b>Tanlangan:</b> {selected_unit}\n\n"
    text += "Ushbu unit bo'yicha nima qilmoqchisiz?"

    try:
        await callback.message.edit_text(
            text, parse_mode="HTML", reply_markup=ikb.as_markup()
        )
    except TelegramBadRequest:
        pass

    await callback.answer()


@router.callback_query(F.data == "current")
async def current_page_handler(callback: CallbackQuery):
    await callback.answer("Siz hozirgi sahifadasiz", show_alert=False)
