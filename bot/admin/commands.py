from aiogram.types import BotCommand

admin_commands = [
    BotCommand(command='/start', description='Boshlash🏁'),
    BotCommand(command='/statistics', description='User list📚'),
    BotCommand(command='/channels', description='Channel list📢'),
    BotCommand(command='/add_channel', description="Majburiy kanal qo'shish➕"),
    BotCommand(command='/broadcast', description='Hamma userlar uchun xabar yuborish📢'),
    BotCommand(command='/reply', description='Bitta userga xabar yuborish'),
    BotCommand(command='/cancel', description='State tozalash'),
    BotCommand(command='/users', description='Userlar')
]
