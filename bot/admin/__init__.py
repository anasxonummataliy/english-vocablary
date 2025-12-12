
from aiogram import Router

from bot.admin.reply import isAdmin
from bot.admin.broadcast import router

admin_router = Router()
admin_router.message.filter(isAdmin())

admin_router.include_routers()
