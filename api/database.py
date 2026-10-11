import os
from pathlib import Path
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional
import aiosqlite

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "scheduler.sqlite3"


@asynccontextmanager
async def get_db():
    os.makedirs(DB_PATH.parent, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA foreign_keys=ON;")
        yield db


async def init_sqlite_db():
    """Initialize the SQLite database schema for Channel Scheduler."""
    async with get_db() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channel_scheduler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL UNIQUE,
                book_slug TEXT NOT NULL DEFAULT 'essential1',
                start_unit INTEGER NOT NULL DEFAULT 1,
                current_unit INTEGER NOT NULL DEFAULT 1,
                send_time TEXT NOT NULL DEFAULT '09:00',
                is_active INTEGER DEFAULT 1,
                finish_message TEXT,
                last_sent_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_channel_scheduler_id ON channel_scheduler(channel_id);")
        await db.commit()


# ─── Channel Scheduler CRUD ───────────────────────────────────────────────────

async def get_channel_scheduler(channel_id: str) -> Optional[dict]:
    """Get the scheduler config for a given channel."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM channel_scheduler WHERE channel_id = ?", (channel_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_all_channel_schedulers() -> list[dict]:
    """Get all channel scheduler configs."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM channel_scheduler ORDER BY id DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def save_channel_scheduler(
    channel_id: str,
    book_slug: str = "essential1",
    start_unit: int = 1,
    send_time: str = "09:00",
    is_active: bool = True,
    finish_message: Optional[str] = None,
) -> dict:
    """Create or update a channel scheduler config."""
    now = datetime.now(timezone.utc).isoformat()
    active_int = 1 if is_active else 0
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM channel_scheduler WHERE channel_id = ?", (channel_id,)
        )
        existing = await cursor.fetchone()

        if existing:
            await db.execute("""
                UPDATE channel_scheduler SET
                    book_slug = ?,
                    start_unit = ?,
                    current_unit = ?,
                    send_time = ?,
                    is_active = ?,
                    finish_message = ?,
                    updated_at = ?
                WHERE channel_id = ?
            """, (book_slug, start_unit, start_unit, send_time, active_int, finish_message, now, channel_id))
        else:
            await db.execute("""
                INSERT INTO channel_scheduler (
                    channel_id, book_slug, start_unit, current_unit,
                    send_time, is_active, finish_message, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (channel_id, book_slug, start_unit, start_unit, send_time, active_int, finish_message, now, now))
        await db.commit()

        cursor = await db.execute(
            "SELECT * FROM channel_scheduler WHERE channel_id = ?", (channel_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else {}


async def update_channel_scheduler_status(channel_id: str, is_active: bool) -> bool:
    """Toggle the scheduler on/off."""
    now = datetime.now(timezone.utc).isoformat()
    active_int = 1 if is_active else 0
    async with get_db() as db:
        await db.execute(
            "UPDATE channel_scheduler SET is_active = ?, updated_at = ? WHERE channel_id = ?",
            (active_int, now, channel_id)
        )
        await db.commit()
    return True


async def update_channel_scheduler_unit(channel_id: str, new_unit: int) -> dict:
    """Manually update the current unit number of a scheduler."""
    now = datetime.now(timezone.utc).isoformat()
    async with get_db() as db:
        await db.execute("""
            UPDATE channel_scheduler SET
                current_unit = ?,
                updated_at = ?
            WHERE channel_id = ?
        """, (new_unit, now, channel_id))
        await db.commit()

        cursor = await db.execute(
            "SELECT * FROM channel_scheduler WHERE channel_id = ?", (channel_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else {}


async def get_due_channel_schedulers(current_hhmm: str, today_date_str: str) -> list[dict]:
    """Get all active schedulers whose send_time matches current time and haven't sent today."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM channel_scheduler
            WHERE is_active = 1
              AND send_time = ?
              AND (last_sent_date IS NULL OR last_sent_date != ?)
        """, (current_hhmm, today_date_str))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def advance_channel_scheduler(channel_id: str, next_unit: int, today_date_str: str) -> dict:
    """Advance the scheduler to the next unit after sending."""
    now = datetime.now(timezone.utc).isoformat()
    async with get_db() as db:
        await db.execute("""
            UPDATE channel_scheduler SET
                current_unit = ?,
                last_sent_date = ?,
                updated_at = ?
            WHERE channel_id = ?
        """, (next_unit, today_date_str, now, channel_id))
        await db.commit()

        cursor = await db.execute(
            "SELECT * FROM channel_scheduler WHERE channel_id = ?", (channel_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else {}


async def finish_channel_scheduler(channel_id: str, today_date_str: str) -> dict:
    """Mark the scheduler as finished (deactivated) after all units are sent."""
    now = datetime.now(timezone.utc).isoformat()
    async with get_db() as db:
        await db.execute("""
            UPDATE channel_scheduler SET
                is_active = 0,
                last_sent_date = ?,
                updated_at = ?
            WHERE channel_id = ?
        """, (today_date_str, now, channel_id))
        await db.commit()

        cursor = await db.execute(
            "SELECT * FROM channel_scheduler WHERE channel_id = ?", (channel_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else {}


async def delete_channel_scheduler(channel_id: str) -> bool:
    """Delete a channel scheduler config."""
    async with get_db() as db:
        await db.execute(
            "DELETE FROM channel_scheduler WHERE channel_id = ?", (channel_id,)
        )
        await db.commit()
    return True
