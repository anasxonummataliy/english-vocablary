from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_url: str = "sqlite:///./bot/database.db"

settings = Settings()
