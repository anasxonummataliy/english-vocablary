import os
from aiogram import Bot, Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
from aiogram.enums import ChatAction
from dotenv import load_dotenv
load_dotenv()
router = Router()
ADMIN = int(os.getenv("ADMIN"))

class MessageToAdmin(StatesGroup):
    message = State()


@router.message(Command("admin"))
async def admin_handler(message: Message, bot: Bot, state: FSMContext):
    await bot.send_chat_action(chat_id=message.from_user.id, action=ChatAction.TYPING)
    if message.from_user.id == ADMIN:
        await message.answer("Siz adminsiz! O'zingizga xabar yozib bo'lmaydi.")
        return
    await state.set_state(MessageToAdmin.message)
    await message.answer(
        "✍️ Adminga xabaringizni yozing:\n" "(Bekor qilish uchun /cancel)"
    )


@router.message(Command("cancel"), MessageToAdmin.message)
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi.")


@router.message(MessageToAdmin.message)
async def message_handler(message: Message, bot: Bot, state: FSMContext):
    try:
        user_info = f"👤 Foydalanuvchi: {message.from_user.full_name}\n"
        user_info += f"🆔 ID: {message.from_user.id}\n"
        if message.from_user.username:
            user_info += f"📱 Username: @{message.from_user.username}\n"
        user_info += f"\n📩 Xabar:\n{message.text}"
        await bot.send_message(int(ADMIN), user_info)
        await message.answer(
            "✅ Xabaringiz adminga yuborildi!\n Tez orada javob beramiz."
        )
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {e}")
    finally:
        await state.clear()
