from aiogram.types import BotCommand

admin_commands = [
    BotCommand(command='/start', description='🏁 Botni ishga tushirish'),
    BotCommand(command='/statistics', description='📊 Bot statistikasi'),
    BotCommand(command='/users', description='👥 Foydalanuvchilar ro\'yxati'),
    BotCommand(command='/broadcast', description='📢 Ommaviy xabar yuborish'),
    BotCommand(command='/reply', description='💬 Userga xabar yuborish'),
    BotCommand(command='/channels', description='📺 Kanallar ro\'yxati'),
    BotCommand(command='/add_channel', description='➕ Majburiy kanal qo\'shish'),
    BotCommand(command='/clear', description='❌ Stateni tozalash'),
]