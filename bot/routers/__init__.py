from aiogram import Router

from bot.routers.start import router as start
from bot.routers.help import router as help
from bot.routers.message_to_admin import router as message_to_admin
from bot.routers.level import router as level


user_router = Router()
user_router.include_routers(level, message_to_admin, help, start)