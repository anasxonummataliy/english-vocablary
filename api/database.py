import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from typing import Optional
import aiosqlite

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "webapp.sqlite3"


@asynccontextmanager
async def get_db():
    os.makedirs(DB_PATH.parent, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA foreign_keys=ON;")
        yield db


async def init_sqlite_db():
    async with get_db() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS web_users (
                user_id TEXT PRIMARY KEY,
                tg_id INTEGER,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                photo_url TEXT,
                streak INTEGER DEFAULT 1,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Auto-migration for web_users columns
        cols = [r[1] for r in await (await db.execute("PRAGMA table_info(web_users);")).fetchall()]
        for col, col_type in [("tg_id", "INTEGER"), ("first_name", "TEXT"), ("last_name", "TEXT"), ("photo_url", "TEXT")]:
            if col not in cols:
                try:
                    await db.execute(f"ALTER TABLE web_users ADD COLUMN {col} {col_type};")
                except Exception:
                    pass

        await db.execute("""
            CREATE TABLE IF NOT EXISTS word_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                book_slug TEXT NOT NULL,
                unit_num INTEGER NOT NULL,
                word TEXT NOT NULL,
                status TEXT DEFAULT 'learning', -- 'learning', 'mastered'
                leitner_box INTEGER DEFAULT 1,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, book_slug, unit_num, word)
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS saved_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                book_slug TEXT NOT NULL,
                unit_num INTEGER NOT NULL,
                word TEXT NOT NULL,
                transcription TEXT,
                part_of_speech TEXT,
                uzbek TEXT NOT NULL,
                description TEXT,
                example TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, word)
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS quiz_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                book_slug TEXT NOT NULL,
                unit_num INTEGER NOT NULL,
                score INTEGER NOT NULL,
                total INTEGER NOT NULL,
                percentage REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                tg_id INTEGER NOT NULL,
                reminder_time TEXT DEFAULT '20:00',
                is_active INTEGER DEFAULT 1,
                book_slug TEXT DEFAULT 'elementary',
                unit_num INTEGER DEFAULT 1,
                last_sent_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tg_id)
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS login_codes (
                code TEXT PRIMARY KEY,
                tg_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                photo_url TEXT,
                expires_at TIMESTAMP NOT NULL,
                used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        await db.execute("CREATE INDEX IF NOT EXISTS idx_word_progress_user ON word_progress(user_id, book_slug, unit_num);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_saved_words_user ON saved_words(user_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_quiz_scores_user ON quiz_scores(user_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_reminders_tg ON reminders(tg_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_login_codes_tg ON login_codes(tg_id);")

        await db.commit()


async def save_login_code(
    code: str,
    tg_id: int,
    username: str = "",
    first_name: str = "",
    last_name: str = "",
    photo_url: str = "",
    duration_minutes: int = 10
) -> dict:
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)).isoformat()
    now = datetime.now(timezone.utc).isoformat()
    async with get_db() as db:
        await db.execute("UPDATE login_codes SET used = 1 WHERE tg_id = ?", (tg_id,))
        await db.execute("""
            INSERT INTO login_codes (code, tg_id, username, first_name, last_name, photo_url, expires_at, used, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
        """, (code, tg_id, username, first_name, last_name, photo_url, expires_at, now))
        await db.commit()
    return {
        "code": code,
        "tg_id": tg_id,
        "expires_at": expires_at
    }


async def verify_login_code(code: str) -> Optional[dict]:
    code = code.strip()
    now = datetime.now(timezone.utc).isoformat()
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM login_codes 
            WHERE code = ? AND used = 0 AND expires_at > ?
        """, (code, now))
        row = await cursor.fetchone()
        if not row:
            return None
        
        row_dict = dict(row)
        await db.execute("UPDATE login_codes SET used = 1 WHERE code = ?", (code,))
        await db.commit()
        
        user = await save_or_update_telegram_user(
            tg_id=row_dict["tg_id"],
            username=row_dict.get("username", "") or "",
            first_name=row_dict.get("first_name", "") or "",
            last_name=row_dict.get("last_name", "") or "",
            photo_url=row_dict.get("photo_url", "") or ""
        )
        return user


async def save_or_update_telegram_user(
    tg_id: int,
    username: str = "",
    first_name: str = "",
    last_name: str = "",
    photo_url: str = ""
) -> dict:
    user_id = f"tg_{tg_id}"
    now = datetime.now(timezone.utc).isoformat()
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM web_users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row:
            await db.execute("""
                UPDATE web_users SET 
                    tg_id = ?,
                    username = COALESCE(NULLIF(?, ''), username),
                    first_name = COALESCE(NULLIF(?, ''), first_name),
                    last_name = COALESCE(NULLIF(?, ''), last_name),
                    photo_url = COALESCE(NULLIF(?, ''), photo_url),
                    last_active = ?
                WHERE user_id = ?
            """, (tg_id, username, first_name, last_name, photo_url, now, user_id))
        else:
            await db.execute("""
                INSERT INTO web_users (user_id, tg_id, username, first_name, last_name, photo_url, streak, last_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (user_id, tg_id, username, first_name, last_name, photo_url, now, now))
        await db.commit()

        cursor = await db.execute("SELECT * FROM web_users WHERE user_id = ?", (user_id,))
        updated = await cursor.fetchone()
        return dict(updated) if updated else {}


async def sync_user_activity(user_id: str, username: str = "", full_name: str = ""):
    now = datetime.now(timezone.utc).isoformat()
    async with get_db() as db:
        cursor = await db.execute("SELECT user_id, last_active, streak FROM web_users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row:
            await db.execute(
                "UPDATE web_users SET last_active = ?, username = COALESCE(NULLIF(?, ''), username), first_name = COALESCE(NULLIF(?, ''), first_name) WHERE user_id = ?",
                (now, username, full_name, user_id)
            )
        else:
            await db.execute(
                "INSERT INTO web_users (user_id, username, first_name, streak, last_active, created_at) VALUES (?, ?, ?, 1, ?, ?)",
                (user_id, username, full_name, now, now)
            )
        await db.commit()


async def get_user_profile(user_id: str) -> Optional[dict]:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM web_users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_all_registered_users(limit: int = 100) -> list[dict]:
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT 
                u.*,
                (SELECT COUNT(*) FROM word_progress WHERE user_id = u.user_id AND status = 'mastered') as mastered_count,
                (SELECT COUNT(*) FROM quiz_scores WHERE user_id = u.user_id) as quiz_count,
                (SELECT r.reminder_time FROM reminders r WHERE r.tg_id = u.tg_id) as reminder_time
            FROM web_users u
            ORDER BY u.last_active DESC
            LIMIT ?
        """, (limit,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def set_or_update_reminder(
    tg_id: int,
    reminder_time: str,
    is_active: bool,
    book_slug: str = "elementary",
    unit_num: int = 1
) -> dict:
    user_id = f"tg_{tg_id}"
    now = datetime.now(timezone.utc).isoformat()
    active_int = 1 if is_active else 0
    async with get_db() as db:
        await db.execute("""
            INSERT INTO reminders (user_id, tg_id, reminder_time, is_active, book_slug, unit_num, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tg_id) DO UPDATE SET
                reminder_time = excluded.reminder_time,
                is_active = excluded.is_active,
                book_slug = excluded.book_slug,
                unit_num = excluded.unit_num
        """, (user_id, tg_id, reminder_time, active_int, book_slug, unit_num, now))
        await db.commit()

        cursor = await db.execute("SELECT * FROM reminders WHERE tg_id = ?", (tg_id,))
        row = await cursor.fetchone()
        return dict(row) if row else {}


async def get_user_reminder(tg_id: int) -> Optional[dict]:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM reminders WHERE tg_id = ?", (tg_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_due_reminders(current_hhmm: str, today_date_str: str) -> list[dict]:
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT r.*, u.first_name, u.username
            FROM reminders r
            LEFT JOIN web_users u ON u.tg_id = r.tg_id
            WHERE r.is_active = 1 
              AND r.reminder_time = ?
              AND (r.last_sent_date IS NULL OR r.last_sent_date != ?)
        """, (current_hhmm, today_date_str))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def mark_reminder_sent(reminder_id: int, today_date_str: str):
    async with get_db() as db:
        await db.execute("UPDATE reminders SET last_sent_date = ? WHERE id = ?", (today_date_str, reminder_id))
        await db.commit()


async def mark_word_progress(user_id: str, book_slug: str, unit_num: int, word: str, status: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    async with get_db() as db:
        await db.execute("""
            INSERT INTO word_progress (user_id, book_slug, unit_num, word, status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, book_slug, unit_num, word) DO UPDATE SET
                status = excluded.status,
                updated_at = excluded.updated_at
        """, (user_id, book_slug, unit_num, word, status, now))
        await db.commit()
    return {"status": "ok", "word": word, "new_status": status}


async def toggle_save_word(user_id: str, word_data: dict) -> dict:
    word = word_data.get("word")
    if not word:
        return {"saved": False}
    
    async with get_db() as db:
        cursor = await db.execute("SELECT id FROM saved_words WHERE user_id = ? AND word = ?", (user_id, word))
        row = await cursor.fetchone()
        if row:
            await db.execute("DELETE FROM saved_words WHERE id = ?", (row["id"],))
            await db.commit()
            return {"saved": False, "word": word}
        else:
            now = datetime.now(timezone.utc).isoformat()
            await db.execute("""
                INSERT INTO saved_words (user_id, book_slug, unit_num, word, transcription, part_of_speech, uzbek, description, example, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                word_data.get("book_slug", "elementary"),
                word_data.get("unit_num", 1),
                word,
                word_data.get("transcription", ""),
                word_data.get("part_of_speech", ""),
                word_data.get("uzbek", ""),
                word_data.get("description", ""),
                word_data.get("example", ""),
                now
            ))
            await db.commit()
            return {"saved": True, "word": word}


async def get_user_saved_words(user_id: str) -> list[dict]:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM saved_words WHERE user_id = ? ORDER BY id DESC", (user_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def save_quiz_score(user_id: str, book_slug: str, unit_num: int, score: int, total: int) -> dict:
    percentage = round((score / total) * 100, 1) if total > 0 else 0
    now = datetime.now(timezone.utc).isoformat()
    async with get_db() as db:
        await db.execute("""
            INSERT INTO quiz_scores (user_id, book_slug, unit_num, score, total, percentage, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, book_slug, unit_num, score, total, percentage, now))
        await db.commit()
    return {"status": "ok", "score": score, "total": total, "percentage": percentage}


async def get_user_stats(user_id: str) -> dict:
    async with get_db() as db:
        mastered_cursor = await db.execute("SELECT COUNT(*) as count FROM word_progress WHERE user_id = ? AND status = 'mastered'", (user_id,))
        mastered_count = (await mastered_cursor.fetchone())["count"]

        learning_cursor = await db.execute("SELECT COUNT(*) as count FROM word_progress WHERE user_id = ? AND status = 'learning'", (user_id,))
        learning_count = (await learning_cursor.fetchone())["count"]

        saved_cursor = await db.execute("SELECT COUNT(*) as count FROM saved_words WHERE user_id = ?", (user_id,))
        saved_count = (await saved_cursor.fetchone())["count"]

        quiz_cursor = await db.execute("SELECT COUNT(*) as count, AVG(percentage) as avg_score, MAX(percentage) as max_score FROM quiz_scores WHERE user_id = ?", (user_id,))
        quiz_row = await quiz_cursor.fetchone()
        quiz_count = quiz_row["count"] or 0
        avg_score = round(quiz_row["avg_score"] or 0, 1)
        max_score = round(quiz_row["max_score"] or 0, 1)

        recent_quizzes = await db.execute("SELECT book_slug, unit_num, score, total, percentage, created_at FROM quiz_scores WHERE user_id = ? ORDER BY id DESC LIMIT 5", (user_id,))
        recent_rows = [dict(r) for r in await recent_quizzes.fetchall()]

    return {
        "mastered_words": mastered_count,
        "learning_words": learning_count,
        "saved_words": saved_count,
        "quizzes_completed": quiz_count,
        "avg_quiz_score": avg_score,
        "max_quiz_score": max_score,
        "recent_quizzes": recent_rows
    }
