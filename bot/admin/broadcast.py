from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message

from bot.database.session import get_async_session_context

router = Router()


@router.message(Command("broadcast"))
async def broadcast_handler(message: Message, bot: Bot):
    async with get_async_session_context() as session:  
        pass