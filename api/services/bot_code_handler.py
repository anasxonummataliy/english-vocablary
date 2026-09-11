import os
import random
import logging
from pathlib import Path
from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message
from api.database import save_login_code

logger = logging.getLogger(__name__)

bot_code_router = Router(name="bot_code_router")
AVATARS_DIR = Path(__file__).resolve().parent.parent / "static" / "avatars"


@bot_code_router.message(Command("code"))
async def handle_code_command(message: Message, bot: Bot):
    user = message.from_user
    if not user:
        return

    tg_id = user.id
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    username = user.username or ""

    # Fetch user's profile photo
    photo_url = ""
    try:
        photos = await bot.get_user_profile_photos(tg_id, limit=1)
        if photos and photos.total_count > 0:
            file_id = photos.photos[0][-1].file_id
            file_info = await bot.get_file(file_id)
            if file_info.file_path:
                os.makedirs(AVATARS_DIR, exist_ok=True)
                avatar_filename = f"{tg_id}.jpg"
                avatar_path = AVATARS_DIR / avatar_filename
                await bot.download_file(file_info.file_path, avatar_path)
                photo_url = f"/static/avatars/{avatar_filename}"
    except Exception as e:
        logger.warning(f"Could not download user profile photo for {tg_id}: {e}")

    # Generate 6-digit code
    code = f"{random.randint(100000, 999999)}"

    await save_login_code(
        code=code,
        tg_id=tg_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        photo_url=photo_url,
        duration_minutes=10
    )

    text = (
        f"🔐 <b>Web App ga kirish kodingiz:</b>\n\n"
        f"👉 <code>{code}</code> 👈\n\n"
        f"⏳ Ushbu maxsus kod <b>10 daqiqa</b> davomida amal qiladi.\n"
        f"Uni Web App sahifasidagi <b>'Kodni kiritish'</b> maydoniga yozing."
    )

    await message.answer(text, parse_mode="HTML")
