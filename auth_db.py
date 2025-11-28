import os
import sqlite3
from typing import Optional, Dict

DB_PATH = os.environ.get("AUTH_DB_PATH", os.path.join(os.path.dirname(__file__), "auth.db"))

# Ensure the directory for the DB exists (useful when AUTH_DB_PATH contains a directory)
db_dir = os.path.dirname(DB_PATH)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)


def _get_conn():
    # Use a slightly larger timeout and allow multi-threaded access if the app uses threads.
    # The DB file is local by default; set `AUTH_DB_PATH` env var to change location.
    return sqlite3.connect(DB_PATH, timeout=30)


def init_db() -> None:
    '''User table schema: telegram_id (Primary Key), google_sub, email, name

    Notes:
    - By default the DB file is `auth.db` next to this module.
    - You can override the file path with the `AUTH_DB_PATH` environment variable.
    - The module ensures the parent directory exists when possible.
    '''
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
    """Returns a dictionary with keys 'tg_id', 'google_sub', 'email', 'name'''' or None if not found. """
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

def delete_user(tg_id: int) -> None:
    """Delete a user record by Telegram id."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE tg_id = ?", (tg_id,))
        conn.commit()
    finally:
        conn.close()