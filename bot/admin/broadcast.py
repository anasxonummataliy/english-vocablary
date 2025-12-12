@router.message(Command("broadcast"))
async def broadcast_handler(message: Message, bot: Bot):
    await message.answer("")
