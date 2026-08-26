from aiogram import Router

from .start import router as start
from .help import router as help
from .message_to_admin import router as message_to_admin
from .level import router as level
from .get_words import router as get_words
from .test_router import router as test_router
from .review import router as review_router
from .flashcard import router as flashcard_router
from .reminder import router as reminder_router
from .group_quiz import router as group_quiz_router
from .leaderboard import router as leaderboard_router
from .basket import router as basket_router


user_router = Router()
user_router.include_routers(
    group_quiz_router,
    leaderboard_router,
    basket_router,
    flashcard_router,
    review_router,
    test_router,
    get_words,
    level,
    reminder_router,
    message_to_admin,
    start,
    help,
)
