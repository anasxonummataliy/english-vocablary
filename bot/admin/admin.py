import os

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from aiogram.filters import Filter, Command, CommandStart
from aiogram import Bot, Router
from dotenv import load_dotenv

load_dotenv()
ADMIN = int(os.getenv('ADMIN') or "")


class isAdmin(Filter):
    async def __call__(self, message: Message):
        return message.from_user.id == ADMIN


router = Router()
router.message.filter(isAdmin())


class AddChannelStates(StatesGroup):
    channel = State()


@router.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(f"Salom {message.from_user.first_name}, Ahvolingiz yaxshimi?")


#
# @router.message(Command("/add_channel"))
# async def add_channel(message: Message, state: FSMContext):
#     await state.set_state(AddChannelStates.channel)
#     await message.answer("Qo'shmoqchi bo'lgan kanalingiz id sini kiriting : ")
#
#
# @router.message(AddChannelStates.channel)
# async def channel_state(message: Message, state: FSMContext, bot: Bot):
#     channel_id = await message.text  # type:ignore
#     result = await bot.get_chat(channel_id)
#     await message.answer("...")

@router.message(Command("broadcast"))
async def broadcast_handler(message: Message, bot: Bot):
    await message.answer("")

