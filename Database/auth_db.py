import os
import sqlite3
from typing import Optional, Dict

DB_PATH = os.path.join(os.path.dirname(__file__), "auth.db")

def _get_conn():
    return sqlite3.connect(DB_PATH)

def init_db() -> None:
    '''User table schema: telegram_id (Primary Key), google_sub, email, name'''
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                tg_id INTEGER PRIMARY KEY,
                name TEXT,
                surname TEXT,
                role TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

def insert_user(tg_id: int, name: str, surname:str, role: str) -> None:
    """Insert a new user record."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (tg_id, name, surname, role) VALUES (?, ?, ?, ?)",
            (tg_id, name, surname, role),
        )
        conn.commit()
    finally:
        conn.close()

def get_user(tg_id: int) -> Optional[Dict]:
    """Retrieve a user record by Telegram ID."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT tg_id, name, surname, role FROM users WHERE tg_id = ?", (tg_id,))
        row = cur.fetchone()
        if row:
            return {
                "tg_id": row[0],
                "name": row[1],
                "surname": row[2],
                "role": row[3],
            }
        return None
    finally:
        conn.close()