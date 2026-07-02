from sqlalchemy import BigInteger, String, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from bot.database.base import Base


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger)
    channel_link: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    channel_username: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    channel_title: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    users_at_join: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
