import os

from aiogram import Router, Bot
from aiogram.filters import Command, Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")
ADMIN = int(os.getenv("ADMIN"))


class isAdmin(Filter):
    async def __call__(self, message: Message):
        return message.from_user.id == ADMIN


router = Router()
router.message.filter(isAdmin())


class ReplyMessage(StatesGroup):
    id = State()
    message_to_user = State()


@router.message(Command("cancel"))
async def cancel_admin(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi")


@router.message(Command('reply'))
async def reply_message(message: Message, state: FSMContext):
    await message.answer("Yubormoqchi bo'lgan foydalanuvchi idsini kiriting.❗️")
    await state.set_state(ReplyMessage.id)


@router.message(ReplyMessage.id)
async def user_id_handler(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
        await message.answer(
            f"✅ User ID: <code>{user_id}</code>\n\n"
            f"Endi xabar matnini yuboring: \n(Bekor qilish uchun /cancel)",
            parse_mode="HTML"
        )
        await state.update_data(id=int(message.text))
        await state.set_state(ReplyMessage.message_to_user)
    except ValueError:
        await message.answer("❌ Noto'g'ri format! Faqat raqam yuboring.")


@router.message(ReplyMessage.message_to_user)
async def message_to_user(message: Message, bot: Bot, state: FSMContext):
    data = await state.get_data()
    user_id = (data.get('id'))
    try:
        await bot.send_message(
            user_id,
            f"📨 Admin javobi:\n\n{message.text}"
        )
        await message.answer(
            f"✅ Xabar yuborildi!\n"
            f"User ID: <code>{user_id}</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")
    await state.clear()
