# --- BUILD STAGE: dependencies o'rnatamiz (multi-stage) ---
FROM python:3.11-slim AS builder

# Sistemdagi paketlar (poetry va build uchun kerakli paketlar)
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential curl git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Ish papkasi
WORKDIR /app

# pyproject va poetry.lock ni avvalo nusxa ko'chiramiz
# (bu qatlamlar keshlanishi uchun shu tartibda qilish kerak)
COPY pyproject.toml poetry.lock* /app/

# Poetry o'rnatish va virtualenv yaratishni o'chirish (container ichida tizimga to'g'ridan-to'g'ri o'rnatamiz)
RUN python -m pip install --upgrade pip \
 && pip install poetry \
 && poetry config virtualenvs.create false

# Dependensiyalarni o'rnatamiz (agar production uchun bo'lsa --no-dev qo'shing)
RUN poetry install --no-interaction --no-ansi --no-dev

# --- FINAL STAGE: kichikroq image yaratamiz ---
FROM python:3.11-slim

# Kerakli tizim paketlari (agar sizning botingizga kerak bo'lsa)
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Non-root user yaratish (xavfsizlik uchun)
RUN useradd --create-home --shell /bin/bash botuser

WORKDIR /app

# Build stage dan o'rnatilgan paketlarni nusxa ko'chirish
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Loyihaning qolgan fayllarini nusxa ko'chiramiz
# (masalan src/ papka yoki to'g'ridan-to'g'ri bot fayli)
COPY . /app

# Foydalanuvchini botuser ga o'zgartiramiz
USER botuser

# Agar entrypoint faylingiz misol uchun bot.py bo'lsa:
# (ENV orqali token yoki boshqa konfiguratsiyalar yuborish tavsiya etiladi)
ENV PYTHONUNBUFFERED=1

# Komanda: o'zingizning bot ishga tushirish faylingizni yozing
CMD ["python", "bot/main.py"]
