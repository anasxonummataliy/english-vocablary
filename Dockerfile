FROM python:3.13-slim

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml ./

RUN uv pip install --system --no-cache \
    "aiogram[i18n]>=3.29.0,<4.0.0" \
    "python-dotenv>=1.0.0" \
    "babel>=2.17.0,<3.0.0" \
    "redis-dict>=3.2.5,<4.0.0" \
    "sqlalchemy>=2.0.45,<3.0.0" \
    "pydantic-settings>=2.12.0,<3.0.0" \
    "alembic>=1.17.2,<2.0.0" \
    "psycopg2-binary>=2.9.11,<3.0.0" \
    "aiosqlite>=0.22.0,<0.23.0" \
    "greenlet>=3.3.0,<4.0.0" \
    "fastapi>=0.115.0,<1.0.0" \
    "uvicorn>=0.40.0,<0.41.0" \
    "asyncpg>=0.31.0,<0.32.0" \
    "python-multipart>=0.0.18"

COPY . .

EXPOSE 8001

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001"]
