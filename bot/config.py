from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_url: str = 'postgresql://anasxonummataliyev:password@localhost:5432/english_vocablary'

settings = Settings()