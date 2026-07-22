import os

# Bot va API modullarini import qilish uchun minimal muhit o'zgaruvchilari
os.environ.setdefault("TOKEN", "0000000000:TEST_TOKEN_FOR_CI")
os.environ.setdefault("ADMIN", "123456789")
os.environ.setdefault("WEBHOOK_URL", "https://example.com/webhook")
os.environ.setdefault("POSTGRES_DB", "test_db")
os.environ.setdefault("POSTGRES_USER", "test_user")
os.environ.setdefault("POSTGRES_PASSWORD", "test_password")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
