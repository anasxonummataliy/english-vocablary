from bot.database.base import Base
from bot.database.session import engine
from bot.database.models.users import User

def init_db():
    Base.metadata.create_all(engine)
