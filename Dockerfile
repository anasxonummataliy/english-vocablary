FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml poetry.lock* /app/

RUN pip install --upgrade pip \
    && pip install poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-root --only main

COPY . /app

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
