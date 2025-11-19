import sys
import logging
import os
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.enums import ChatMemberStatus
from aiogram.filters import Filter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from aiogram.types import BotCommandScopeChat, BotCommandScopeAllPrivateChats, InlineKeyboardButton

from commands import *
from router.start import router as start_router
from commands import router as command_router


load_dotenv()
TOKEN = os.getenv("TOKEN") or ""
ADMIN = os.getenv("ADMIN") or ""

dp = Dispatcher()
bot = Bot(TOKEN)
CHANNEL_ID = os.getenv("CHANNEL_ID") or ""

class IsJoinChannel(Filter):
    def __init__(self, channel_id):
        self.channel_id = channel_id

    async def __call__(self, message: Message, bot:Bot):
        chat_member = await bot.get_chat_member(self.channel_id, message.from_user.id) # type: ignore
        return chat_member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR, ChatMemberStatus.MEMBER)


@dp.startup()
async def start_message(bot: Bot) -> None:
    admin_commands = [
        BotCommand(command='/start', description='Boshlash🏁'),
        BotCommand(command='/users', description='User list📚'),
        BotCommand(command='/check', description='Botni tekshirish☑️')
    ]
    user_command = [
        BotCommand(command='start', description='Boshlash'),  # type: ignore
        BotCommand(command='help', description='Yordam'),  # type:ignore
    ]
    await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=ADMIN))
    await bot.set_my_commands(user_command, scope=BotCommandScopeAllPrivateChats())
    await bot.send_message(ADMIN, 'Bot ishga tushdi✅')
@dp.shutdown()
async def shotdown_message(bot: Bot) -> None:
    await bot.send_message(ADMIN, "Bot to'xtatildi❌")


@dp.message(IsJoinChannel(CHANNEL_ID))
async def join_handler(message: Message):
    channel = await bot.get_chat(CHANNEL_ID)
    ikb = InlineKeyboardBuilder()
    ikb.add(
        InlineKeyboardButton(text='Enlgish Vocablary', url=channel.invite_link)
    )
    await message.answer(text="❗️ Botdan foydalanish uchun kanalga obuna bo‘ling va qaytadan /start buyrug‘ini bosing!", reply_markup=ikb.as_markup())



async def main() -> None:
    dp.include_router(command_router)
    dp.include_router(start_router)
    await intilize_settings(bot)
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
