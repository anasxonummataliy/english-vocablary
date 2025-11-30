from optparse import Option

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from aiogram.filters import Filter, Command, IS_ADMIN, CommandStart
from aiogram import Bot, Router
from os import getenv
from dotenv import load_dotenv

load_dotenv()
ADMIN = getenv("ADMIN")
print(ADMIN)

router = Router()


class AddChannelStates(StatesGroup):
    channel = State()


class isAdmin(Filter):
    async def __call__(self, message: Message):
        return message.from_user.id == int(ADMIN)


@router.message(CommandStart(), isAdmin())
async def start_handler(message: Message):
    await message.answer(f"Salom {message.from_user.first_name}, Ahvolingiz yaxshimi?")


@router.message(Command("/add_channel"), isAdmin())
async def add_channel(message: Message, state: FSMContext):
    await state.set_state(AddChannelStates.channel)
    await message.answer("Qo'shmoqchi bo'lgan kanalingiz id sini kiriting : ")


@router.message(AddChannelStates.channel, isAdmin())
async def channel_state(message: Message, state: FSMContext, bot: Bot):
    channel_id: Option[str | None] = await message.text
    result = await bot.get_chat(channel_id)
    await message.answer("...")


@router.message(Command('channels'), isAdmin())
async def get_channels(message: Message, state: FSMContext, bot: Bot):
    await message.answer(f"Channels : Kanal bor edi")


@router.message(isAdmin())
async def msg_handler(message: Message):
    await message.answer("salom")
