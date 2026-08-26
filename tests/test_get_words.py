import pytest

from bot.routers.get_words import (
    format_words_text,
    get_unit_info,
    get_unit_words,
)


@pytest.mark.asyncio
async def test_get_unit_words_elementary_unit_1():
    words = await get_unit_words("elementary", 1)
    assert words is not None
    assert len(words) >= 4
    assert words[0]["word"] == "mother"
    assert "uzbek" in words[0]


@pytest.mark.asyncio
async def test_get_unit_words_preintermediate():
    words = await get_unit_words("preintermediateintermediate", 1)
    assert words is not None
    assert len(words) >= 4
    assert words[0]["word"] == "routine"


@pytest.mark.asyncio
async def test_get_unit_words_essential_words():
    words = await get_unit_words("4000essentialenglishwords1", 1)
    assert words is not None
    assert len(words) == 20
    assert words[0]["word"] == "afraid"
    assert words[0]["uzbek"] == "qo'rqqan, cho'chigan"


@pytest.mark.asyncio
async def test_get_unit_words_missing_file():
    words = await get_unit_words("nonexistentlevel", 1)
    assert words is None


@pytest.mark.asyncio
async def test_get_unit_words_missing_unit():
    words = await get_unit_words("elementary", 9999)
    assert words is None


@pytest.mark.asyncio
async def test_get_unit_info():
    info = await get_unit_info("elementary", 1)
    assert info is not None
    assert info["title"] == "The family"
    assert "Family" in info["topic"]


def test_format_words_text_contains_key_fields():
    words = [
        {
            "word": "mother",
            "transcription": "/ˈmʌðər/",
            "part_of_speech": "noun",
            "uzbek": "ona",
            "description": "A woman who has children",
            "example": "My mother works as a teacher.",
        }
    ]
    unit_info = {"title": "The family", "topic": "Family members"}

    text = format_words_text(words, 1, unit_info, "elementary")

    assert "Elementary" in text
    assert "Unit 1" in text
    assert "mother" in text
    assert "ona" in text
    assert "The family" in text


def test_format_words_text_can_continue_numbering():
    words = [
        {
            "word": "second",
            "transcription": "",
            "part_of_speech": "noun",
            "uzbek": "ikkinchi",
            "description": "desc",
            "example": "ex",
        }
    ]
    unit_info = {"title": "The family", "topic": "Family members"}

    text = format_words_text(words, 1, unit_info, "elementary", start_index=11)

    assert "11. second" in text


def test_format_words_text_escapes_html():
    words = [
        {
            "word": "<script>",
            "transcription": "",
            "part_of_speech": "noun",
            "uzbek": "test & value",
            "description": "desc",
            "example": "ex",
        }
    ]
    unit_info = {"title": "Title <b>", "topic": "Topic"}

    text = format_words_text(words, 1, unit_info, "elementary")

    assert "<script>" not in text
    assert "&lt;script&gt;" in text
    assert "&amp;" in text


def test_preview_shows_only_first_ten_words_with_remaining_note():
    words = [
        {
            "word": f"word{i}",
            "transcription": "",
            "part_of_speech": "noun",
            "uzbek": f"uzbek{i}",
            "description": f"desc{i}",
            "example": f"example{i}",
        }
        for i in range(1, 13)
    ]
    unit_info = {"title": "The family", "topic": "Family members"}

    text = format_words_text(words[:10], 1, unit_info, "elementary")

    assert "word10" in text
    assert "word11" not in text
    assert "word12" not in text


