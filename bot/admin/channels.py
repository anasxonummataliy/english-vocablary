from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from bot.database.models.channels import Channel
from bot.database.session import get_async_session_context


class AddChannelStates(StatesGroup):
    channel = State()


router = Router()


@router.message(Command("channels"))
async def get_channels(message: Message):
    async with get_async_session_context() as session:
        stmt = select(Channel)
        result = await session.execute(stmt)
        channels = result.scalars().all()
    if not channels:
        await message.answer("Kanallar mavjud emas❗️")
        return
    await message.answer(channels)


@router.message(Command("/add_channel"))
async def add_channel(message: Message, state: FSMContext):
    await state.set_state(AddChannelStates.channel)
    await message.answer("Qo'shmoqchi bo'lgan kanalingiz id sini kiriting : ")


@router.message(AddChannelStates.channel)
async def channel_state(message: Message, state: FSMContext, bot: Bot):
    channel_id = await message.text
    result = await bot.get_chat(channel_id)
    await message.answer("...")
