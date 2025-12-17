import os
from aiogram import BaseMiddleware, Bot, Router, F
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery
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
            ikb.row(InlineKeyboardButton(text=channel.title, url=channel.invite_link))
        ikb.row(InlineKeyboardButton(text='Tekshirish✅', callback_data='joined'))
        return ikb.as_markup()

    async def check_user_subscriptions(self, bot: Bot, user_id: int):
        unsubscribed_channels = []
        for channel_id in CHANNELS:
            try:
                chat_member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
                if chat_member.status not in (
                        ChatMemberStatus.MEMBER,
                        ChatMemberStatus.CREATOR,
                        ChatMemberStatus.ADMINISTRATOR,
                ):
                    unsubscribed_channels.append(channel_id)
            except Exception as e:
                print(f"Kanal tekshirishda xatolik {channel_id}: {e}")
                unsubscribed_channels.append(channel_id)
        return unsubscribed_channels

    async def __call__(self, handler, event, data):
        if isinstance(event, CallbackQuery):
            return await handler(event, data)

        if event.chat.type != ChatType.PRIVATE:
            return await handler(event, data)
        bot: Bot = data["bot"]
        user_id = event.from_user.id
        unsubscribed_channels = await self.check_user_subscriptions(bot, user_id)

        if unsubscribed_channels:
            await event.answer(
                "❗️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
                reply_markup=await self.make_channel_buttons(bot, unsubscribed_channels)
            )
            return
        return await handler(event, data)


@router.callback_query(F.data == 'joined')
async def check_subscription(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id

    middleware_check = IsJoinChannelMiddleware()
    unsubscribed_channels = await middleware_check.check_user_subscriptions(bot, user_id)

    if unsubscribed_channels:
        await callback.answer(
            "❌ Siz hali barcha kanallarga obuna bo'lmadingiz!",
            show_alert=True
        )
    else:
        await callback.message.delete()
        await callback.message.answer(
            "✅ Tabriklaymiz! Siz barcha kanallarga obuna bo'ldingiz.\n"
            "Endi botdan foydalanishingiz mumkin!"
        )
        await callback.answer()

