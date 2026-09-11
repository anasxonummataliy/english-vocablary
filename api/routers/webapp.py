from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional
from api.services.vocab_service import vocab_service
from api.services.notification_service import send_telegram_reminder_notification
from api.database import (
    save_or_update_telegram_user,
    verify_login_code,
    sync_user_activity,
    get_user_profile,
    get_all_registered_users,
    set_or_update_reminder,
    get_user_reminder,
    mark_word_progress,
    toggle_save_word,
    get_user_saved_words,
    save_quiz_score,
    get_user_stats,
)

router = APIRouter(prefix="/api/webapp", tags=["webapp"])


@router.get("/books")
async def get_books():
    return vocab_service.get_books_list()


@router.get("/units")
async def get_units(book: str = Query(..., description="Book slug e.g. elementary")):
    units = vocab_service.get_units(book)
    if not units:
        raise HTTPException(status_code=404, detail="Book not found")
    return units


@router.get("/words")
async def get_words(
    book: str = Query(..., description="Book slug"),
    unit: int = Query(..., description="Unit number")
):
    data = vocab_service.get_words(book, unit)
    if not data["words"] and data["unit"] is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    return data


@router.get("/search")
async def search_words(q: str = Query("", description="Search term in English or Uzbek")):
    return vocab_service.search(q, limit=50)


@router.get("/quiz")
async def get_quiz(
    book: str = Query(..., description="Book slug"),
    unit: Optional[int] = Query(None, description="Optional unit number"),
    count: int = Query(10, ge=3, le=50),
    mode: str = Query("en_uz", pattern="^(en_uz|uz_en)$")
):
    questions = vocab_service.generate_quiz(book, unit, count, mode)
    return questions


@router.get("/speed-match")
async def get_speed_match(
    book: str = Query(..., description="Book slug"),
    unit: Optional[int] = Query(None, description="Optional unit number"),
    count: int = Query(6, ge=4, le=12)
):
    pairs = vocab_service.generate_speed_match(book, unit, count)
    return pairs


@router.post("/auth/telegram")
async def auth_telegram(payload: dict = Body(...)):
    """Registers or logs in a user via Telegram WebApp or Telegram Login."""
    tg_id_raw = payload.get("tg_id") or payload.get("id")
    if not tg_id_raw:
        raise HTTPException(status_code=400, detail="Telegram ID is required")

    try:
        tg_id = int(tg_id_raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Telegram ID")

    username = payload.get("username", "") or ""
    first_name = payload.get("first_name", "") or ""
    last_name = payload.get("last_name", "") or ""
    photo_url = payload.get("photo_url", "") or ""

    user = await save_or_update_telegram_user(
        tg_id=tg_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        photo_url=photo_url
    )
    return {"status": "ok", "user": user}


@router.post("/auth/verify-code")
async def verify_code(payload: dict = Body(...)):
    """Verifies 6-digit one-time code sent by the Telegram bot via /code command."""
    code = str(payload.get("code") or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="Kod kiritilmadi")

    user = await verify_login_code(code)
    if not user:
        return {
            "status": "error",
            "message": "❌ Kod noto'g'ri yoki 10 daqiqalik muddati tugagan. Botga qayta /code yuboring."
        }

    return {"status": "ok", "user": user}


@router.get("/user/profile")
async def user_profile(user_id: str = Query(...)):
    profile = await get_user_profile(user_id)
    if not profile:
        return {"user_id": user_id, "first_name": "O'quvchi", "is_telegram": False}
    return profile


@router.get("/admin/users")
async def list_admin_users(limit: int = Query(100, ge=1, le=500)):
    """Allows viewing all real registered Telegram users in SQLite."""
    users = await get_all_registered_users(limit=limit)
    return users


@router.post("/reminder")
async def save_reminder(payload: dict = Body(...)):
    """Save or update user daily reminder settings."""
    tg_id_raw = payload.get("tg_id")
    if not tg_id_raw:
        raise HTTPException(status_code=400, detail="Telegram ID is required to set a reminder")

    try:
        tg_id = int(tg_id_raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Telegram ID")

    reminder_time = payload.get("reminder_time", "20:00")
    is_active = bool(payload.get("is_active", True))
    book_slug = payload.get("book_slug", "elementary")
    unit_num = int(payload.get("unit_num", 1))

    res = await set_or_update_reminder(
        tg_id=tg_id,
        reminder_time=reminder_time,
        is_active=is_active,
        book_slug=book_slug,
        unit_num=unit_num
    )
    return {"status": "ok", "reminder": res}


@router.get("/reminder")
async def get_reminder(tg_id: int = Query(...)):
    reminder = await get_user_reminder(tg_id)
    return reminder or {
        "tg_id": tg_id,
        "reminder_time": "20:00",
        "is_active": False,
        "book_slug": "elementary",
        "unit_num": 1
    }


@router.post("/reminder/send-test")
async def send_test_reminder(payload: dict = Body(...)):
    """Sends an immediate test reminder message to user's Telegram."""
    tg_id_raw = payload.get("tg_id")
    if not tg_id_raw:
        raise HTTPException(status_code=400, detail="Telegram ID is required")

    try:
        tg_id = int(tg_id_raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Telegram ID")

    name = payload.get("first_name") or payload.get("username") or "O'quvchi"
    book_slug = payload.get("book_slug") or "elementary"
    unit_num = int(payload.get("unit_num") or 1)

    success = await send_telegram_reminder_notification(
        tg_id=tg_id,
        user_name=name,
        book_slug=book_slug,
        unit_num=unit_num,
        is_test=True
    )

    if not success:
        return {
            "status": "error",
            "message": "Xabar yuborilmadi. Avval Telegram botimizga (@eng_vocablary_in_use_bot) /start bosing."
        }

    return {"status": "ok", "message": "Eslatma Telegram botingizga yuborildi!"}


@router.post("/sync-user")
async def sync_user(payload: dict = Body(...)):
    user_id = str(payload.get("user_id") or "").strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    username = payload.get("username", "")
    full_name = payload.get("full_name", "")
    await sync_user_activity(user_id, username, full_name)
    return {"status": "ok"}


@router.post("/progress")
async def update_progress(payload: dict = Body(...)):
    user_id = str(payload.get("user_id") or "").strip()
    book_slug = str(payload.get("book_slug") or "").strip()
    unit_num = int(payload.get("unit_num") or 1)
    word = str(payload.get("word") or "").strip()
    status = str(payload.get("status") or "learning")

    if not user_id or not word:
        raise HTTPException(status_code=400, detail="user_id and word are required")

    res = await mark_word_progress(user_id, book_slug, unit_num, word, status)
    return res


@router.post("/toggle-save")
async def toggle_save(payload: dict = Body(...)):
    user_id = str(payload.get("user_id") or "").strip()
    word_data = payload.get("word_data") or {}
    if not user_id or not word_data.get("word"):
        raise HTTPException(status_code=400, detail="user_id and word are required")

    res = await toggle_save_word(user_id, word_data)
    return res


@router.get("/saved")
async def get_saved(user_id: str = Query(..., description="User ID or device UUID")):
    return await get_user_saved_words(user_id)


@router.post("/score")
async def save_score(payload: dict = Body(...)):
    user_id = str(payload.get("user_id") or "").strip()
    book_slug = str(payload.get("book_slug") or "elementary").strip()
    unit_num = int(payload.get("unit_num") or 1)
    score = int(payload.get("score") or 0)
    total = int(payload.get("total") or 0)

    if not user_id or total <= 0:
        raise HTTPException(status_code=400, detail="Valid user_id and total are required")

    res = await save_quiz_score(user_id, book_slug, unit_num, score, total)
    return res


@router.get("/stats")
async def get_stats(user_id: str = Query(..., description="User ID or device UUID")):
    return await get_user_stats(user_id)
