import os

from aiogram import Bot, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.enums import ChatAction
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from dotenv import load_dotenv

load_dotenv()
router = Router()
ADMIN = os.getenv("ADMIN") or ""


class MessageToAdmin(StatesGroup):
    message = State()



def level_keyboard():
    kb = ReplyKeyboardBuilder()
    kb.button(text='📗 Elementary')
    kb.button(text='📘 Pre-intermediate & Intermediate')
    kb.button(text='📙 Upper intermediate')
    kb.button(text='📕 Advanced')
    kb.adjust(1)
    return kb

@router.message(CommandStart())
async def start_handler(message: Message, bot: Bot):
    await bot.send_chat_action(
            chat_id=message.from_user.id, action=ChatAction.TYPING
        )
    kb = level_keyboard()
    await message.answer(
        f"Assalomu alaykum {message.from_user.first_name} bizning botimizga hush kelibsiz! \n 📚 English Vocablary in Use Kitobni qaysi qismidan boshlamoqchisiz?",reply_markup=kb.as_markup(resize_keyboard=True))


@router.message(F.text.in_(['📗 Elementary', '📘 Pre-intermediate & Intermediate', '📙 Upper intermediate', '📕 Advanced']))
async def level_selected(message: Message):
    selected_level = message.text

    await message.answer(
        f"✅ Siz {selected_level} darajasini tanladingiz!",
        reply_markup=ReplyKeyboardRemove()  # ✅ Klaviaturani o'chiradi
    )

@router.message(Command('level'))
async def level_handler(message: Message):
    kb = level_keyboard()
    await message.answer("📚 English Vocablary in Use Kitobni qaysi qismidan boshlamoqchisiz?",
                         reply_markup=kb.as_markup(resize_keyboard=True))


@router.message(Command("admin"))
async def admin_handler(message: Message, bot: Bot, state: FSMContext):
    await bot.send_chat_action(chat_id=message.from_user.id, action=ChatAction.TYPING)
    if message.from_user.id == ADMIN:
        await message.answer("Siz adminsiz! O'zingizga xabar yozib bo'lmaydi.")
        return
    await state.set_state(MessageToAdmin.message)
    await message.answer(
        "✍️ Adminga xabaringizni yozing:\n"
        "(Bekor qilish uchun /cancel)"
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
        await message.answer("✅ Xabaringiz adminga yuborildi!\n Tez orada javob beramiz.")
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {e}")
    finally:
        await state.clear()


@router.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(
        "Buyruqlar: \n 1. /start - botni boshlash uchun \n"
        " 2. /level - English Vocablary in Use kitobining qismlari"
        " 3. /help - botning buyruqlari haqida \n"
        " 4. /admin - adminga bot haqida muammo yoki taklif bo'lsa yozish uchun."
    )
