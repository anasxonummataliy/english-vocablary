from sqlalchemy import select, func, desc
from bot.database.models.scores import TestScore
from bot.database.models.users import User
from bot.database.session import get_async_session_context


async def save_score(
    user_id: int,
    user_name: str | None,
    chat_id: int | None,
    level: str,
    unit_num: int,
    test_mode: str,
    score: int,
    total_questions: int,
) -> TestScore:
    percentage = (score / total_questions * 100.0) if total_questions > 0 else 0.0
    async with get_async_session_context() as session:
        score_record = TestScore(
            user_id=user_id,
            user_name=user_name,
            chat_id=chat_id,
            level=level.lower(),
            unit_num=unit_num,
            test_mode=test_mode,
            score=score,
            total_questions=total_questions,
            percentage=percentage,
        )
        session.add(score_record)
        await session.commit()
        return score_record


async def get_unit_leaderboard(level: str, unit_num: int, limit: int = 10):
    """
    Unit bo'yicha eng yuqori natijaga erishgan foydalanuvchilar (High Scores).
    """
    async with get_async_session_context() as session:
        subquery = (
            select(
                TestScore.user_id,
                func.max(TestScore.percentage).label("max_percentage"),
                func.max(TestScore.score).label("max_score"),
            )
            .where(
                func.lower(TestScore.level) == level.lower(),
                TestScore.unit_num == unit_num,
            )
            .group_by(TestScore.user_id)
            .subquery()
        )

        stmt = (
            select(
                subquery.c.user_id,
                subquery.c.max_score,
                subquery.c.max_percentage,
                User.first_name,
                User.username,
            )
            .outerjoin(User, User.tg_id == subquery.c.user_id)
            .order_by(desc(subquery.c.max_percentage), desc(subquery.c.max_score))
            .limit(limit)
        )

        result = await session.execute(stmt)
        return result.all()


async def get_group_leaderboard(chat_id: int, limit: int = 10):
    """
    Guruh bo'yicha eng ko'p ball to'plgan aktiv foydalanuvchilar.
    """
    async with get_async_session_context() as session:
        subquery = (
            select(
                TestScore.user_id,
                func.sum(TestScore.score).label("total_score"),
                func.count(TestScore.id).label("tests_count"),
            )
            .where(TestScore.chat_id == chat_id)
            .group_by(TestScore.user_id)
            .subquery()
        )

        stmt = (
            select(
                subquery.c.user_id,
                subquery.c.total_score,
                subquery.c.tests_count,
                User.first_name,
                User.username,
            )
            .outerjoin(User, User.tg_id == subquery.c.user_id)
            .order_by(desc(subquery.c.total_score))
            .limit(limit)
        )

        result = await session.execute(stmt)
        return result.all()


async def get_global_leaderboard(limit: int = 10):
    """
    Umumiy barcha testlar va musobaqalar bo'yicha top foydalanuvchilar.
    """
    async with get_async_session_context() as session:
        subquery = (
            select(
                TestScore.user_id,
                func.sum(TestScore.score).label("total_score"),
                func.count(TestScore.id).label("tests_count"),
            )
            .group_by(TestScore.user_id)
            .subquery()
        )

        stmt = (
            select(
                subquery.c.user_id,
                subquery.c.total_score,
                subquery.c.tests_count,
                User.first_name,
                User.username,
            )
            .outerjoin(User, User.tg_id == subquery.c.user_id)
            .order_by(desc(subquery.c.total_score))
            .limit(limit)
        )

        result = await session.execute(stmt)
        return result.all()
