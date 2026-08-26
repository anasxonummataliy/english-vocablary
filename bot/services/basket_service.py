import logging
import re
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, func, update, delete
from sqlalchemy.orm import selectinload

from bot.database.models.baskets import Basket, BasketWord
from bot.database.session import get_async_session_context

logger = logging.getLogger(__name__)

MAX_BASKET_SIZE = 20


def _extract_basket_number(name: str) -> int:
    match = re.search(r'\d+', name)
    return int(match.group()) if match else 1


async def get_or_create_active_basket(session, user_id: int) -> Tuple[Basket, int]:
    """Foydalanuvchining faol savatchasini oladi yoki yangisini yaratadi."""
    # Barcha savatchalarni yuklash
    stmt = (
        select(Basket)
        .where(Basket.user_id == user_id)
        .options(selectinload(Basket.words))
        .order_by(Basket.id)
    )
    result = await session.execute(stmt)
    baskets = result.scalars().all()

    if not baskets:
        new_basket = Basket(user_id=user_id, name="Savatcha 1", is_active=True)
        session.add(new_basket)
        await session.flush()
        await session.refresh(new_basket, ["words"])
        return new_basket, 0

    # Faol savatchani topamiz
    active_basket = next((b for b in baskets if b.is_active), None)
    if not active_basket:
        active_basket = baskets[-1]
        active_basket.is_active = True

    word_count = len(active_basket.words)

    # Agar faol savat to'lgan bo'lsa (>= 20), keyingi savatchani ochamiz
    if word_count >= MAX_BASKET_SIZE:
        active_basket.is_active = False
        max_num = max(_extract_basket_number(b.name) for b in baskets)
        next_num = max(len(baskets) + 1, max_num + 1)
        new_basket = Basket(
            user_id=user_id,
            name=f"Savatcha {next_num}",
            is_active=True
        )
        session.add(new_basket)
        await session.flush()
        await session.refresh(new_basket, ["words"])
        return new_basket, 0

    return active_basket, word_count


async def add_word_to_basket(user_id: int, word_data: Dict[str, Any]) -> Tuple[bool, str, str, int]:
    """So'zni faol savatchaga qo'shadi."""
    word_str = word_data.get("word", "").strip()
    if not word_str:
        return False, "❌ Noto'g'ri so'z ma'lumoti.", "", 0

    async with get_async_session_context() as session:
        basket, word_count = await get_or_create_active_basket(session, user_id)

        # Duplikatni tekshiramiz
        existing = any(
            w.word.lower().strip() == word_str.lower()
            for w in basket.words
        )
        if existing:
            return False, f"ℹ️ <b>'{word_str}'</b> allaqachon {basket.name}da mavjud!", basket.name, word_count

        basket_word = BasketWord(
            basket_id=basket.id,
            word=word_str,
            transcription=word_data.get("transcription", ""),
            part_of_speech=word_data.get("part_of_speech", ""),
            uzbek=word_data.get("uzbek", ""),
            description=word_data.get("description", ""),
            example=word_data.get("example", ""),
        )
        session.add(basket_word)
        await session.commit()
        new_count = word_count + 1
        return True, f"✅ <b>'{word_str}'</b> {basket.name}ga qo'shildi! ({new_count}/{MAX_BASKET_SIZE})", basket.name, new_count


async def get_user_baskets(user_id: int) -> List[Dict[str, Any]]:
    """Foydalanuvchining barcha savatchalarini qaytaradi."""
    async with get_async_session_context() as session:
        stmt = (
            select(Basket)
            .where(Basket.user_id == user_id)
            .options(selectinload(Basket.words))
            .order_by(Basket.id)
        )
        result = await session.execute(stmt)
        baskets = result.scalars().all()
        return [
            {
                "id": b.id,
                "name": b.name,
                "is_active": b.is_active,
                "word_count": len(b.words),
                "created_at": b.created_at,
            }
            for b in baskets
        ]


async def get_basket_by_id(basket_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Savatcha ma'lumotlarini ID bo'yicha oladi."""
    async with get_async_session_context() as session:
        stmt = select(Basket).where(Basket.id == basket_id).options(selectinload(Basket.words))
        if user_id is not None:
            stmt = stmt.where(Basket.user_id == user_id)
        result = await session.execute(stmt)
        basket = result.scalar_one_or_none()
        if not basket:
            return None
        return {
            "id": basket.id,
            "user_id": basket.user_id,
            "name": basket.name,
            "is_active": basket.is_active,
            "word_count": len(basket.words),
            "created_at": basket.created_at,
        }


async def get_basket_words(basket_id: int) -> List[Dict[str, Any]]:
    """Savatchadagi barcha so'zlarni standart formatda qaytaradi."""
    async with get_async_session_context() as session:
        stmt = (
            select(BasketWord)
            .where(BasketWord.basket_id == basket_id)
            .order_by(BasketWord.id)
        )
        result = await session.execute(stmt)
        words = result.scalars().all()
        return [
            {
                "id": w.id,
                "word": w.word,
                "transcription": w.transcription or "",
                "part_of_speech": w.part_of_speech or "",
                "uzbek": w.uzbek,
                "description": w.description or "",
                "example": w.example or "",
            }
            for w in words
        ]


async def remove_word_from_basket(basket_id: int, word_id: int) -> Tuple[bool, str]:
    """Savatchadan bitta so'zni o'chiradi."""
    async with get_async_session_context() as session:
        stmt = select(BasketWord).where(
            BasketWord.basket_id == basket_id,
            BasketWord.id == word_id
        )
        result = await session.execute(stmt)
        word = result.scalar_one_or_none()
        if not word:
            return False, "❌ So'z topilmadi."
        word_text = word.word
        await session.delete(word)
        await session.commit()
        return True, f"🗑 <b>'{word_text}'</b> savatchadan o'chirildi."


async def set_active_basket(user_id: int, basket_id: int) -> bool:
    """Foydalanuvchining faol savatchasini o'zgartiradi."""
    async with get_async_session_context() as session:
        # Barchasini nofaol qilish
        await session.execute(
            update(Basket)
            .where(Basket.user_id == user_id)
            .values(is_active=False)
        )
        # Tanlanganni faol qilish
        result = await session.execute(
            update(Basket)
            .where(Basket.user_id == user_id, Basket.id == basket_id)
            .values(is_active=True)
        )
        await session.commit()
        return result.rowcount > 0


async def delete_basket(user_id: int, basket_id: int) -> Tuple[bool, str]:
    """Savatchani o'chiradi."""
    async with get_async_session_context() as session:
        stmt = select(Basket).where(Basket.user_id == user_id, Basket.id == basket_id)
        result = await session.execute(stmt)
        basket = result.scalar_one_or_none()
        if not basket:
            return False, "❌ Savatcha topilmadi."
        name = basket.name
        was_active = basket.is_active
        await session.delete(basket)

        # Agar faol bo'lgan bo'lsa, qolganlardan birini faol qilamiz
        if was_active:
            other_stmt = select(Basket).where(Basket.user_id == user_id).order_by(Basket.id.desc())
            other_res = await session.execute(other_stmt)
            other_basket = other_res.scalar_one_or_none()
            if other_basket:
                other_basket.is_active = True

        await session.commit()
        return True, f"🗑 <b>{name}</b> muvaffaqiyatli o'chirildi."
