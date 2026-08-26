import pytest
from unittest.mock import AsyncMock, MagicMock
from contextlib import asynccontextmanager

import bot.services.basket_service as basket_service_module
from bot.database.models.baskets import Basket, BasketWord
from bot.services.basket_service import (
    add_word_to_basket,
    get_user_baskets,
    get_basket_by_id,
    get_basket_words,
    remove_word_from_basket,
    set_active_basket,
    delete_basket,
    rename_basket,
)


@pytest.mark.asyncio
async def test_add_word_to_new_basket(monkeypatch):
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    @asynccontextmanager
    async def mock_get_async_session_context():
        yield mock_session

    monkeypatch.setattr(
        basket_service_module, "get_async_session_context", mock_get_async_session_context
    )

    sample_word = {
        "word": "challenge",
        "transcription": "/ˈtʃalɪndʒ/",
        "part_of_speech": "noun",
        "uzbek": "qiyinchilik, sinov",
        "description": "A difficult task",
        "example": "This was a challenge.",
    }

    success, msg, basket_name, count = await add_word_to_basket(1001, sample_word)
    assert success is True
    assert "challenge" in msg
    assert basket_name == "Savatcha 1"
    assert count == 1
    mock_session.commit.assert_called()


@pytest.mark.asyncio
async def test_add_duplicate_word_in_basket(monkeypatch):
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.flush = AsyncMock()

    existing_word = BasketWord(
        id=1,
        basket_id=1,
        word="arrive",
        transcription="/əˈraɪv/",
        part_of_speech="verb",
        uzbek="yetib kelmoq",
        description="",
        example="",
    )
    existing_basket = Basket(id=1, user_id=1002, name="Savatcha 1", is_active=True, words=[existing_word])

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [existing_basket]
    mock_session.execute.return_value = mock_result

    @asynccontextmanager
    async def mock_get_async_session_context():
        yield mock_session

    monkeypatch.setattr(
        basket_service_module, "get_async_session_context", mock_get_async_session_context
    )

    duplicate_word = {
        "word": "arrive",
        "transcription": "/əˈraɪv/",
        "part_of_speech": "verb",
        "uzbek": "yetib kelmoq",
        "description": "",
        "example": "",
    }

    success, msg, basket_name, count = await add_word_to_basket(1002, duplicate_word)
    assert success is False
    assert "allaqachon" in msg
    assert basket_name == "Savatcha 1"
    assert count == 1


@pytest.mark.asyncio
async def test_auto_create_next_basket_when_full(monkeypatch):
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()

    # 20 ta so'zli to'la savat
    words_20 = [
        BasketWord(id=i, basket_id=1, word=f"word_{i}", uzbek=f"tarjima_{i}")
        for i in range(1, 21)
    ]
    full_basket = Basket(id=1, user_id=1003, name="Savatcha 1", is_active=True, words=words_20)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [full_basket]
    mock_session.execute.return_value = mock_result

    @asynccontextmanager
    async def mock_get_async_session_context():
        yield mock_session

    monkeypatch.setattr(
        basket_service_module, "get_async_session_context", mock_get_async_session_context
    )

    w_21 = {
        "word": "word_21",
        "transcription": "/w_21/",
        "part_of_speech": "noun",
        "uzbek": "so'z_21",
        "description": "desc_21",
        "example": "ex_21",
    }

    success, msg, basket_name, count = await add_word_to_basket(1003, w_21)
    assert success is True
    assert basket_name == "Savatcha 2"
    assert count == 1
    assert full_basket.is_active is False


@pytest.mark.asyncio
async def test_get_user_baskets(monkeypatch):
    mock_session = AsyncMock()
    words = [BasketWord(id=1, basket_id=10, word="test", uzbek="test")]
    basket = Basket(id=10, user_id=1004, name="Savatcha 1", is_active=True, words=words)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [basket]
    mock_session.execute.return_value = mock_result

    @asynccontextmanager
    async def mock_get_async_session_context():
        yield mock_session

    monkeypatch.setattr(
        basket_service_module, "get_async_session_context", mock_get_async_session_context
    )

    baskets = await get_user_baskets(1004)
    assert len(baskets) == 1
    assert baskets[0]["id"] == 10
    assert baskets[0]["name"] == "Savatcha 1"
    assert baskets[0]["word_count"] == 1


@pytest.mark.asyncio
async def test_get_basket_words_and_remove(monkeypatch):
    mock_session = AsyncMock()
    mock_session.delete = AsyncMock()
    mock_session.commit = AsyncMock()

    word = BasketWord(
        id=55,
        basket_id=12,
        word="unique",
        transcription="/juːˈniːk/",
        part_of_speech="adj.",
        uzbek="noyob",
        description="special",
        example="sample",
    )

    mock_res_words = MagicMock()
    mock_res_words.scalars.return_value.all.return_value = [word]

    mock_res_one = MagicMock()
    mock_res_one.scalar_one_or_none.return_value = word

    mock_session.execute.side_effect = [mock_res_words, mock_res_one]

    @asynccontextmanager
    async def mock_get_async_session_context():
        yield mock_session

    monkeypatch.setattr(
        basket_service_module, "get_async_session_context", mock_get_async_session_context
    )

    words = await get_basket_words(12)
    assert len(words) == 1
    assert words[0]["word"] == "unique"
    assert words[0]["uzbek"] == "noyob"

    ok, del_msg = await remove_word_from_basket(12, 55)
    assert ok is True
    assert "unique" in del_msg
    mock_session.delete.assert_called_once_with(word)
    mock_session.commit.assert_called()


@pytest.mark.asyncio
async def test_set_active_and_delete_basket(monkeypatch):
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.delete = AsyncMock()

    mock_update_res = MagicMock()
    mock_update_res.rowcount = 1

    basket = Basket(id=20, user_id=1005, name="Savatcha 1", is_active=True)
    mock_select_res = MagicMock()
    mock_select_res.scalar_one_or_none.return_value = basket

    other_basket = Basket(id=21, user_id=1005, name="Savatcha 2", is_active=False)
    mock_other_res = MagicMock()
    mock_other_res.scalar_one_or_none.return_value = other_basket

    mock_session.execute.side_effect = [mock_update_res, mock_update_res, mock_select_res, mock_other_res]

    @asynccontextmanager
    async def mock_get_async_session_context():
        yield mock_session

    monkeypatch.setattr(
        basket_service_module, "get_async_session_context", mock_get_async_session_context
    )

    active_ok = await set_active_basket(1005, 20)
    assert active_ok is True

    del_ok, del_msg = await delete_basket(1005, 20)
    assert del_ok is True
    assert "Savatcha 1" in del_msg
    assert other_basket.is_active is True


@pytest.mark.asyncio
async def test_rename_basket(monkeypatch):
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()

    mock_update_res = MagicMock()
    mock_update_res.rowcount = 1
    mock_session.execute.return_value = mock_update_res

    @asynccontextmanager
    async def mock_get_async_session_context():
        yield mock_session

    monkeypatch.setattr(
        basket_service_module, "get_async_session_context", mock_get_async_session_context
    )

    ok, msg = await rename_basket(1006, 15, "IELTS Lug'at")
    assert ok is True
    assert "IELTS Lug'at" in msg
    mock_session.commit.assert_called_once()
