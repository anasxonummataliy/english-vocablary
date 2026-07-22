from aiogram import Router

from .start import router as start
from .help import router as help
from .message_to_admin import router as message_to_admin
from bot.filters.admin import isAdmin
from .level import router as level
from .get_words import router as get_words
from .test_router import router as test_router
from .review import router as review_router
from .flashcard import router as flashcard_router
from .reminder import router as reminder_router


user_router = Router()
user_router.message.filter(~isAdmin())
user_router.include_routers(
    flashcard_router, review_router, test_router, get_words, level, reminder_router, message_to_admin, help, start
)
