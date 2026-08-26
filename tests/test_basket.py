import pytest
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from bot.database.base import Base
import bot.services.basket_service as basket_service_module
from bot.services.basket_service import (
    add_word_to_basket,
    get_user_baskets,
    get_basket_by_id,
    get_basket_words,
    remove_word_from_basket,
    set_active_basket,
    delete_basket,
    MAX_BASKET_SIZE,
)


@pytest.fixture
async def setup_test_db(monkeypatch):
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    test_sessionmaker = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def mock_get_async_session_context():
        async with test_sessionmaker() as session:
            yield session

    monkeypatch.setattr(
        basket_service_module, "get_async_session_context", mock_get_async_session_context
    )

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_add_word_and_auto_create_basket(setup_test_db):
    user_id = 999001
    sample_word = {
        "word": "challenge",
        "transcription": "/ˈtʃalɪndʒ/",
        "part_of_speech": "noun",
        "uzbek": "qiyinchilik, sinov",
        "description": "A difficult task",
        "example": "This was a challenge.",
    }

    success, msg, basket_name, count = await add_word_to_basket(user_id, sample_word)
    assert success is True
    assert "challenge" in msg
    assert basket_name == "Savatcha 1"
    assert count == 1

    baskets = await get_user_baskets(user_id)
    assert len(baskets) == 1
    assert baskets[0]["name"] == "Savatcha 1"
    assert baskets[0]["word_count"] == 1
    assert baskets[0]["is_active"] is True


@pytest.mark.asyncio
async def test_add_duplicate_word_in_basket(setup_test_db):
    user_id = 999002
    sample_word = {
        "word": "arrive",
        "transcription": "/əˈraɪv/",
        "part_of_speech": "verb",
        "uzbek": "yetib kelmoq",
        "description": "To reach a place",
        "example": "The train arrived on time.",
    }

    success1, _, _, count1 = await add_word_to_basket(user_id, sample_word)
    assert success1 is True
    assert count1 == 1

    # Attempt duplicate
    success2, msg2, _, count2 = await add_word_to_basket(user_id, sample_word)
    assert success2 is False
    assert "allaqachon" in msg2
    assert count2 == 1


@pytest.mark.asyncio
async def test_auto_create_next_basket_when_full(setup_test_db):
    user_id = 999003

    # Add 20 words to fill Savatcha 1
    for i in range(1, 21):
        w = {
            "word": f"word_{i}",
            "transcription": f"/w_{i}/",
            "part_of_speech": "noun",
            "uzbek": f"so'z_{i}",
            "description": f"desc_{i}",
            "example": f"ex_{i}",
        }
        success, _, b_name, count = await add_word_to_basket(user_id, w)
        assert success is True
        assert b_name == "Savatcha 1"
        assert count == i

    baskets = await get_user_baskets(user_id)
    assert len(baskets) == 1
    assert baskets[0]["word_count"] == 20

    # Add 21st word -> should auto-create Savatcha 2
    w_21 = {
        "word": "word_21",
        "transcription": "/w_21/",
        "part_of_speech": "noun",
        "uzbek": "so'z_21",
        "description": "desc_21",
        "example": "ex_21",
    }
    success21, msg21, b_name21, count21 = await add_word_to_basket(user_id, w_21)
    assert success21 is True
    assert b_name21 == "Savatcha 2"
    assert count21 == 1

    baskets_after = await get_user_baskets(user_id)
    assert len(baskets_after) == 2
    assert baskets_after[0]["is_active"] is False
    assert baskets_after[1]["name"] == "Savatcha 2"
    assert baskets_after[1]["is_active"] is True
    assert baskets_after[1]["word_count"] == 1


@pytest.mark.asyncio
async def test_get_basket_words_and_remove(setup_test_db):
    user_id = 999004
    w = {
        "word": "unique",
        "transcription": "/juːˈniːk/",
        "part_of_speech": "adjective",
        "uzbek": "noyob",
        "description": "Not like others",
        "example": "She has a unique style.",
    }
    await add_word_to_basket(user_id, w)

    baskets = await get_user_baskets(user_id)
    basket_id = baskets[0]["id"]

    words = await get_basket_words(basket_id)
    assert len(words) == 1
    assert words[0]["word"] == "unique"
    word_id = words[0]["id"]

    # Remove word
    ok, del_msg = await remove_word_from_basket(basket_id, word_id)
    assert ok is True
    assert "unique" in del_msg

    words_after = await get_basket_words(basket_id)
    assert len(words_after) == 0


@pytest.mark.asyncio
async def test_set_active_and_delete_basket(setup_test_db):
    user_id = 999005

    # Fill Savatcha 1 and create Savatcha 2
    for i in range(1, 22):
        w = {
            "word": f"term_{i}",
            "transcription": "",
            "part_of_speech": "",
            "uzbek": f"tarjima_{i}",
            "description": "",
            "example": "",
        }
        await add_word_to_basket(user_id, w)

    baskets = await get_user_baskets(user_id)
    assert len(baskets) == 2
    b1_id = baskets[0]["id"]
    b2_id = baskets[1]["id"]

    # Set Savatcha 1 as active
    await set_active_basket(user_id, b1_id)
    baskets_updated = await get_user_baskets(user_id)
    assert baskets_updated[0]["is_active"] is True
    assert baskets_updated[1]["is_active"] is False

    # Delete Savatcha 1
    ok, del_msg = await delete_basket(user_id, b1_id)
    assert ok is True
    assert "Savatcha 1" in del_msg

    baskets_remaining = await get_user_baskets(user_id)
    assert len(baskets_remaining) == 1
    assert baskets_remaining[0]["id"] == b2_id
    assert baskets_remaining[0]["is_active"] is True
