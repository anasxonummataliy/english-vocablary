from sqlalchemy import select
from aiogram import BaseMiddleware, Bot, Router, F
from aiogram.enums import ChatType, ChatMemberStatus
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery

from bot.database.models.channels import Channel
from bot.database.session import get_async_session_context
from dotenv import load_dotenv

load_dotenv()


async def get_channel_ids():
    async with get_async_session_context() as session:
        stmt = select(Channel.tg_id)
        result = await session.execute(stmt)
        return [row[0] for row in result.all()]


router = Router()


class IsJoinChannelMiddleware(BaseMiddleware):
    async def make_channel_buttons(self, bot: Bot, channel_list: list[int]):
        ikb = InlineKeyboardBuilder()
        for channel_id in channel_list:
            channel = await bot.get_chat(chat_id=channel_id)
            url = channel.invite_link or f"https://t.me/{channel.username}"
            ikb.row(InlineKeyboardButton(text=channel.title, url=url))
        ikb.row(InlineKeyboardButton(text="Tekshirish✅", callback_data="joined"))
        return ikb.as_markup()

    async def check_user_subscriptions(self, bot: Bot, user_id: int):
        unsubscribed_channels = []
        channel_list = await get_channel_ids()
        for channel_id in channel_list:
            try:
                chat_member = await bot.get_chat_member(
                    chat_id=channel_id, user_id=user_id
                )
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

    async def __call__(self, handler, event: Message, data):
        if isinstance(event, CallbackQuery):
            return await handler(event, data)

        if event.chat.type == ChatType.PRIVATE:
            bot: Bot = data["bot"]
            user_id = event.from_user.id
            unsubscribed_channels = await self.check_user_subscriptions(bot, user_id)

            if unsubscribed_channels:
                await event.answer(
                    "❗️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
                    reply_markup=await self.make_channel_buttons(
                        bot, unsubscribed_channels
                    ),
                )
                return
        if event.chat.type != ChatType.PRIVATE:
            await event.answer("❗️ Bot faqat private chatda ishlaydi")
            return
        return await handler(event, data)


@router.callback_query(F.data == "joined")
async def check_subscription(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id

    middleware_check = IsJoinChannelMiddleware()
    unsubscribed_channels = await middleware_check.check_user_subscriptions(
        bot, user_id
    )

    if unsubscribed_channels:
        await callback.answer(
            "❌ Siz hali barcha kanallarga obuna bo'lmadingiz!", show_alert=True
        )
    else:
        await callback.message.delete()
        await callback.message.answer(
            "✅ Tabriklaymiz! Siz barcha kanallarga obuna bo'ldingiz.\n"
            "Endi botdan foydalanishingiz mumkin!"
        )
        await callback.answer()
