from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from bot.database.models.channels import Channel
from bot.database.session import get_async_session_context


class AddChannelStates(StatesGroup):
    channel_link = State()


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
    text = "📢 Saqlangan kanallar:\n\n"
    for i, ch in enumerate(channels, start=1):
        identifier = (
            f"@{ch.channel_username}" if ch.channel_username else ch.channel_link
        )
        text += f"{i}. {ch.channel_title}\n   ID: {ch.tg_id}\n   Link/Username: {identifier}\n\n"

    await message.answer(text)


@router.message(Command("add_channel"))
async def add_channel(message: Message, state: FSMContext):
    await state.set_state(AddChannelStates.channel_link)
    await message.answer(
        "Avval botni kanalga admin qiling❗️\n"
        "Admin qilganingizdan keyin kanal linki yoki username ni yuboring."
    )


@router.message(AddChannelStates.channel_link)
async def channel_state(message: Message, state: FSMContext, bot: Bot):
    user_input = message.text.strip()
    result = await bot.get_chat(user_input)
    try:
        chat = await bot.get_chat(user_input)
    except Exception as e:
        await message.answer(f"Kanalni olishda xatolik: {e}")
        return
    if chat.username:
        channel_username = chat.username
        channel_link = None
    else:
        channel_username = None
        channel_link = user_input

    channel_data = {
        "tg_id": chat.id,
        "channel_link": channel_link,
        "channel_username": channel_username,
        "channel_title": chat.title,
    }
    async with get_async_session_context() as session:
        stmt = select(Channel).where(Channel.tg_id == chat.id)
        result = await session.execute(stmt)
        existing_channel = result.scalar_one_or_none()
        if existing_channel:
            existing_channel.channel_link = channel_link
            existing_channel.channel_username = channel_username
            existing_channel.channel_title = chat.title
        else:
            session.add(Channel(**channel_data))
        await session.commit()
        await message.answer(f"Kanal saqlandi: {chat.title}")
        await state.clear()
