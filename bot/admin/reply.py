import re
from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message


router = Router()


@router.message(Command("cancel"))
async def cancel_admin(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi")


@router.message(F.reply_to_message)
async def reply_to_user(message: Message, bot: Bot):
    replied = message.reply_to_message
    if not replied or not replied.text:
        return

    match = re.search(
        r"ID:\s*`?(\d+)`?|ID:</b>\s*<code>(\d+)</code>|ID: (\d+)", replied.text
    )
    if not match:
        return

    user_id = int(match.group(1) or match.group(2) or match.group(3))

    try:
        await bot.send_message(
            user_id,
            f"📩 <b>Admin javobi:</b>\n\n{message.text}",
            parse_mode="HTML",
        )
        await message.answer("✅ Foydalanuvchiga yuborildi!")
    except Exception as e:
        await message.answer(f"❌ Yuborib bo'lmadi: {e}")
