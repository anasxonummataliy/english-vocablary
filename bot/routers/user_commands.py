from aiogram.types import BotCommand

user_command = [
    BotCommand(command="start", description="Boshlash"),
    BotCommand(command="level", description="Level tanlash"),
    BotCommand(command="top", description="Reytinglar (Leaderboard)"),
    BotCommand(command="reminder", description="Eslatma sozlash"),
    BotCommand(command="help", description="Yordam"),
    BotCommand(command="admin", description="Adminga xabar yozish"),
]

group_command = [
    BotCommand(command="quiz", description="Guruhda musobaqa boshlash"),
    BotCommand(command="stop_quiz", description="Aktiv musobaqani to'xtatish"),
    BotCommand(command="top", description="Reytinglar jadvalini ko'rish"),
    BotCommand(command="help", description="Guruh bot qo'llanmasi"),
]
