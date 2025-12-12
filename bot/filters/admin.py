class isAdmin(Filter):
    async def __call__(self, message: Message):
        return message.from_user.id == ADMIN
