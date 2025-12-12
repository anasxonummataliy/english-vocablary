from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_url: str = 'postgres://anasxonummataliy:password@localhost:5432/english_vocablary'

settings = Settings()