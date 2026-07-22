def test_bot_routers_import():
    import bot.routers.get_words  # noqa: F401
    import bot.routers.keyboard  # noqa: F401
    import bot.routers.level  # noqa: F401
    import bot.routers.flashcard  # noqa: F401
    import bot.routers.review  # noqa: F401
    import bot.routers.test_router  # noqa: F401


def test_config_settings():
    from bot.core.config import settings

    assert settings.redis_url.startswith("redis://")
    assert "postgresql+asyncpg://" in settings.postgres_dsn
