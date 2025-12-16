from aiogram import Router

from bot.filters.admin import isAdmin
from bot.admin.broadcast import router as broadcast
from bot.admin.channels import router as channels
from bot.admin.reply import router as reply
from bot.admin.statistics import router as statistics
from bot.admin.start import router as start
from bot.admin.users import router as user

admin_router = Router()
admin_router.message.filter(isAdmin())

admin_router.include_routers(user, broadcast, channels, reply, statistics, start)
