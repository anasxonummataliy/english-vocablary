FROM python:3.13-slim


RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app


RUN pip install --upgrade pip && pip install "poetry==1.8.3"


COPY pyproject.toml poetry.lock ./


RUN poetry config virtualenvs.create false \
    && poetry install --no-root --only main -v


COPY . .

EXPOSE 8001

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001"]
