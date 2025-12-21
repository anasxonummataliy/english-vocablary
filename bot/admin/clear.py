
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.filters import Command

clear_router = Router()

@clear_router.message(Command('clear'))
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Amal bekor qilindi.")



