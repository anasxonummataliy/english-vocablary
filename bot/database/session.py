from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from bot.config import settings

engine = create_engine(settings.db_url)

session = sessionmaker(engine)()

