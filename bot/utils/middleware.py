import os
from aiogram import BaseMiddleware, Bot, Router
from aiogram.types import Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ChatType, ChatMemberStatus

from dotenv import load_dotenv

load_dotenv()


CHANNELS = os.getenv("CHANNELS", "")
CHANNELS = [int(x) for x in CHANNELS.split(",") if x.strip()]

router = Router()


class IsJoinChannelMiddleware(BaseMiddleware):
    async def make_channel_buttons(self, bot: Bot, channel_list: list[int]):
        ikb = InlineKeyboardBuilder()
        for channel_id in channel_list:
            channel = await bot.get_chat(chat_id=channel_id)
            ikb.row(
                InlineKeyboardButton(text=channel.title, url=channel.invite_link)  # type: ignore
            )
        return ikb.as_markup()

    async def __call__(self, handler, event: Message, data):
        if event.event.chat.type != ChatType.PRIVATE: 
            return await handler(event, data)
        bot: Bot = data["bot"]
        user_id = event.event.from_user.id
        unsubscribed_channels = []
        for channel_id in CHANNELS:  
            chat_member = await bot.get_chat_member(channel_id, user_id)
            if chat_member.status not in (
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.CREATOR,
                ChatMemberStatus.ADMINISTRATOR,
            ):
                unsubscribed_channels.append(channel_id)
        if unsubscribed_channels:
            await event.message.answer("❗️ Botdan foydalanish uchun kanalga obuna bo‘ling", reply_markup=await self.make_channel_buttons(bot, unsubscribed_channels))  # type: ignore
            return
        return await handler(event, data)
