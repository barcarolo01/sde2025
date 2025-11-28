import os
import sqlite3
from typing import Optional, Dict

DB_PATH = os.path.join(os.path.dirname(__file__), "auth.db")


def _get_conn():
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    """Create the simple users table if it doesn't exist."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                tg_id INTEGER PRIMARY KEY,
                google_sub TEXT,
                email TEXT,
                name TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def link_user(tg_id: int, google_sub: str, email: str, name: str) -> None:
    """Insert or update a user record linking Telegram id to Google account."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (tg_id, google_sub, email, name) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(tg_id) DO UPDATE SET google_sub=excluded.google_sub, email=excluded.email, name=excluded.name",
            (tg_id, google_sub, email, name),
        )
        conn.commit()
    finally:
        conn.close()


def get_user(tg_id: int) -> Optional[Dict[str, str]]:
    """Return a dict with keys 'tg_id', 'google_sub', 'email', 'name' or None if not found."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT tg_id, google_sub, email, name FROM users WHERE tg_id = ?", (tg_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            "tg_id": row[0],
            "google_sub": row[1],
            "email": row[2],
            "name": row[3],
        }
    finally:
        conn.close()
