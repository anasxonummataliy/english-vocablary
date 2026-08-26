import pytest
from unittest.mock import AsyncMock, MagicMock
from bot.routers.keyboard import (
    VOCABULARY_IN_USE_LEVELS,
    ESSENTIAL_WORDS_LEVELS,
    LEVEL_DEFINITIONS,
    normalize_level_code,
    get_available_units,
)
from bot.routers.get_words import get_unit_words, get_unit_info, show_words_handler
from bot.routers.flashcard import start_flashcard
from bot.routers.test_router import start_test_by_mode
from bot.routers.review import review_handler


def test_normalize_level_code_all_variants():
    """Barcha kitoblar va ularning emojili variantlari to'g'ri kodga aylanishini tekshirish."""
    test_cases = [
        ("📗 Elementary", "elementary"),
        ("📘 Pre-intermediate & Intermediate", "preintermediateintermediate"),
        ("📙 Upper intermediate", "upperintermediate"),
        ("📕 Advanced", "advanced"),
        ("📗 Essential Words 1", "4000essentialenglishwords1"),
        ("📘 Essential Words 2", "4000essentialenglishwords2"),
        ("📙 Essential Words 3", "4000essentialenglishwords3"),
        ("📕 Essential Words 4", "4000essentialenglishwords4"),
        ("📔 Essential Words 5", "4000essentialenglishwords5"),
        ("📓 Essential Words 6", "4000essentialenglishwords6"),
        ("🔵 4000 Essential English Words 1", "4000essentialenglishwords1"),
    ]
    for raw_level, expected_code in test_cases:
        assert normalize_level_code(raw_level) == expected_code, f"Failed for {raw_level}"


@pytest.mark.asyncio
async def test_all_essential_words_books_load_successfully():
    """Barcha 6 ta Essential Words kitoblarining har bir unit so'zlari to'g'ri yuklanishini tekshirish."""
    for title, code in ESSENTIAL_WORDS_LEVELS:
        units = get_available_units(title)
        assert len(units) == 30, f"{title} da 30 ta unit bo'lishi kerak"

        # Har bir kitobning 1-uniti va oxirgi 30-uniti so'zlarini tekshirish
        for u_id in [1, 15, 30]:
            words = await get_unit_words(title, u_id)
            assert words is not None and len(words) == 20, f"{title} unit {u_id} so'zlari topilmadi"
            info = await get_unit_info(title, u_id)
            assert info is not None and "title" in info, f"{title} unit {u_id} ma'lumotlari topilmadi"


@pytest.mark.asyncio
async def test_show_words_handler_with_essential_words():
    """show_words_handler emojili level bilan so'zlarni to'g'ri ko'rsatishini tekshirish."""
    callback = AsyncMock()
    callback.data = "words_Unit_1"
    callback.from_user = MagicMock(id=123456)
    callback.message = AsyncMock()
    callback.answer = AsyncMock()

    redis = AsyncMock()
    redis.get.return_value = "📗 Essential Words 1"

    await show_words_handler(callback, redis)

    # callback.answer alert xatosi bermasligi kerak
    if callback.answer.called:
        for call_arg in callback.answer.call_args_list:
            assert "topilmadi" not in str(call_arg)


@pytest.mark.asyncio
async def test_start_flashcard_with_essential_words():
    """start_flashcard emojili level bilan xatosiz ishga tushishini tekshirish."""
    callback = AsyncMock()
    callback.data = "fmode_uz_en_Unit 1"
    callback.from_user = MagicMock(id=123456)
    callback.message = AsyncMock()
    callback.answer = AsyncMock()

    redis = AsyncMock()
    redis.get.return_value = "📗 Essential Words 1"

    await start_flashcard(callback, redis)

    # Redis ga saqlangan bo'lishi kerak
    assert redis.set.called


@pytest.mark.asyncio
async def test_start_test_with_essential_words():
    """start_test_by_mode emojili level bilan xatosiz ishga tushishini tekshirish."""
    callback = AsyncMock()
    callback.data = "tmode_uz_en_Unit_1"
    callback.from_user = MagicMock(id=123456)
    callback.message = AsyncMock()
    callback.message.chat = MagicMock(id=123456)
    callback.answer = AsyncMock()

    redis = AsyncMock()
    redis.get.return_value = "📗 Essential Words 1"

    bot = AsyncMock()
    await start_test_by_mode(callback, redis, bot)

    assert redis.set.called
