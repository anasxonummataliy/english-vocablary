from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

class AddChannelStates(StatesGroup):
    channel = State()

router = Router()
@router.message(Command("/add_channel"))
async def add_channel(message: Message, state: FSMContext):
    await state.set_state(AddChannelStates.channel)
    await message.answer("Qo'shmoqchi bo'lgan kanalingiz id sini kiriting : ")


@router.message(AddChannelStates.channel)
async def channel_state(message: Message, state: FSMContext, bot: Bot):
    channel_id = await message.text
    result = await bot.get_chat(channel_id)
    await message.answer("...")
