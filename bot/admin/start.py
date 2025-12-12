import os

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from aiogram.filters import Filter, Command, CommandStart
from aiogram import Bot, Router
from dotenv import load_dotenv

from bot.admin.reply import router as reply_router

load_dotenv()
ADMIN = int(os.getenv('ADMIN') or "")


class isAdmin(Filter):
    async def __call__(self, message: Message):
        return message.from_user.id == ADMIN


router = Router()
router.message.filter(isAdmin())
router.include_router(reply_router)

class AddChannelStates(StatesGroup):
    channel = State()


@router.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(f"Salom {message.from_user.first_name}, Ahvolingiz yaxshimi?")


@router.message()
async def message_handler(message: Message):
    await message.answer('Mavjud bo\'lmagan command!')
