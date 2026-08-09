from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, BigInteger, Float, DateTime
from bot.database.base import Base


class TestScore(Base):
    __tablename__ = "test_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    level: Mapped[str] = mapped_column(String, index=True)
    unit_num: Mapped[int] = mapped_column(Integer, index=True)
    test_mode: Mapped[str] = mapped_column(String, default="uz_en")
    score: Mapped[int] = mapped_column(Integer)
    total_questions: Mapped[int] = mapped_column(Integer)
    percentage: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
