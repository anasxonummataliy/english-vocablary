from sqlalchemy.orm import DeclarativeBase

from bot.database import session


class Base(DeclarativeBase):
    pass

Base.metadata(session)