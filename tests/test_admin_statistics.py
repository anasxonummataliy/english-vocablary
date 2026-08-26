import pytest
from unittest.mock import AsyncMock, MagicMock
from bot.admin.statistics import (
    get_general_statistics_text,
    get_today_statistics_text,
    get_month_statistics_text,
    statistics_keyboard,
)


@pytest.mark.asyncio
async def test_admin_statistics_text_builders():
    mock_session = AsyncMock()
    # Mock scalar returns for queries
    mock_session.scalar.return_value = 10

    mock_result = MagicMock()
    mock_row = MagicMock()
    mock_row.user_name = "TestUser"
    mock_row.user_id = 12345
    mock_row.test_count = 5
    mock_row.avg_pct = 95.0
    mock_result.all.return_value = [mock_row]
    mock_session.execute.return_value = mock_result

    # 1. General statistics
    general_text = await get_general_statistics_text(mock_session)
    assert "Botning umumiy statistikasi" in general_text
    assert "Foydalanuvchilar" in general_text
    assert "Eslatmalar" in general_text
    assert "Savatchalar" in general_text
    assert "Test & Natijalar" in general_text

    # 2. Today statistics
    today_text = await get_today_statistics_text(mock_session)
    assert "Bugungi kunlik hisobot" in today_text
    assert "Bugungi faollik" in today_text
    assert "DAU" in today_text

    # 3. Monthly statistics
    month_text = await get_month_statistics_text(mock_session)
    assert "Oylik hisobot" in month_text
    assert "MAU" in month_text
    assert "TestUser" in month_text


def test_statistics_keyboard():
    kb_gen = statistics_keyboard("general").as_markup()
    assert len(kb_gen.inline_keyboard) == 2
    assert "Umumiy" in kb_gen.inline_keyboard[0][0].text

    kb_today = statistics_keyboard("today").as_markup()
    assert "Bugungi" in kb_today.inline_keyboard[0][1].text

    kb_month = statistics_keyboard("month").as_markup()
    assert "Oylik" in kb_month.inline_keyboard[0][2].text
