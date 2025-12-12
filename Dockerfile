FROM python:3.13

WORKDIR /app

COPY pyproject.toml poetry.lock* /app/

RUN python -m pip install --upgrade pip \
 && pip install poetry \
 && poetry config virtualenvs.create false

RUN poetry install --no-root

COPY . /app

CMD ["python", "-m", "bot.main"]
