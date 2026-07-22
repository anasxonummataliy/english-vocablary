from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.base import Base


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    level: Mapped[str] = mapped_column(String)
    current_unit: Mapped[int] = mapped_column(Integer)
    interval_hours: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    next_reminder_at: Mapped[datetime] = mapped_column(DateTime)
    last_reminded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
