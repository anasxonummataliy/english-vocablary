from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, BigInteger, Boolean, DateTime, ForeignKey
from bot.database.base import Base


class Basket(Base):
    __tablename__ = "baskets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    name: Mapped[str] = mapped_column(String, default="Savatcha 1")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    words: Mapped[List["BasketWord"]] = relationship(
        "BasketWord", back_populates="basket", cascade="all, delete-orphan"
    )


class BasketWord(Base):
    __tablename__ = "basket_words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    basket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("baskets.id", ondelete="CASCADE"), index=True
    )
    word: Mapped[str] = mapped_column(String, index=True)
    transcription: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    part_of_speech: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    uzbek: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    example: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    basket: Mapped["Basket"] = relationship("Basket", back_populates="words")
