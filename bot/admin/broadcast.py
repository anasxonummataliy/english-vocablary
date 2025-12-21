import asyncio

from aiogram import Router, Bot, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from sqlalchemy import select

from bot.database.models.users import User
from bot.database.session import get_async_session_context

router = Router()


class MsgToUser(StatesGroup):
    message_to_user = State()


@router.message(Command('broadcast'))
async def broadcast(message: Message, state: FSMContext):
    async with get_async_session_context() as session:
        stmt = select(User)
        result = await session.execute(stmt)
        users = result.scalars().all()
        if not users:
            await message.answer("Hali foydalanuvchilar yo'q.")
            return
    await state.set_state(MsgToUser.message_to_user)
    await message.answer("Yubormoqchi bo'lgan xabaringizni kiriting.")


@router.message(MsgToUser.message_to_user)
async def broadcast_handler(message: Message, bot: Bot, state: FSMContext):
    async with get_async_session_context() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

    success = 0
    failed = 0
    status_msg = await message.answer("Xabarlar yuborilmoqda...")

    for user in users:
        try:
            await bot.send_message(user.tg_id, message.text)
            success += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed += 1
            print(e)
            continue

    await state.clear()

    await status_msg.edit_text(
        f"📢 Broadcast yakunlandi\n\n"
        f"✅ Yuborildi: {success}\n"
        f"❌ Yuborilmadi: {failed}"
    )
