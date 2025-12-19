from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from bot.database.base import Base


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(Integer)
    channel_link: Mapped[str] = mapped_column(String, nullable=True)
    channel_username: Mapped[str] = mapped_column(String, nullable=True)
    channel_title: Mapped[str] = mapped_column(String, nullable=False)
    is_active :Mapped[bool] = mapped_column(Boolean, default=True)
    
