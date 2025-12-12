




class AddChannelStates(StatesGroup):
    channel = State()


# @router.message(Command("/add_channel"))
# async def add_channel(message: Message, state: FSMContext):
#     await state.set_state(AddChannelStates.channel)
#     await message.answer("Qo'shmoqchi bo'lgan kanalingiz id sini kiriting : ")
#
#
# @router.message(AddChannelStates.channel)
# async def channel_state(message: Message, state: FSMContext, bot: Bot):
#     channel_id = await message.text  # type:ignore
#     result = await bot.get_chat(channel_id)
#     await message.answer("...")
