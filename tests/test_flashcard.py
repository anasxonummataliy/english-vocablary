import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from bot.routers.flashcard import show_flash_card, show_flash_answer, next_flash_card, end_flashcard


@pytest.mark.asyncio
async def test_show_flash_card_and_answer():
    callback = AsyncMock()
    callback.message = AsyncMock()
    callback.from_user = MagicMock(id=12345)

    sample_words = [
        {
            "word": "apple",
            "uzbek": "olma",
            "transcription": "/ˈæp.əl/",
            "description": "a round fruit",
            "example": "I ate an apple.",
        },
        {
            "word": "book",
            "uzbek": "kitob",
            "transcription": "/bʊk/",
            "description": "written work",
            "example": "He reads a book.",
        },
    ]

    state = {
        "mode": "en_uz",
        "unit_id": "Unit 1",
        "words": sample_words,
        "current_index": 0,
    }

    # 1. Savol ko'rsatish
    await show_flash_card(callback, state, 12345)
    callback.message.edit_text.assert_called()
    called_text = callback.message.edit_text.call_args[0][0]
    assert "apple" in called_text

    # 2. Redis mock
    redis = AsyncMock()
    redis.get.return_value = json.dumps(state).encode()

    # 3. Javobni ko'rsatish
    await show_flash_answer(callback, redis)
    answer_text = callback.message.edit_text.call_args[0][0]
    assert "olma" in answer_text
    assert "apple" in answer_text
