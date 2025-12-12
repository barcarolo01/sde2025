import psycopg2
import os
import logging
from typing import Optional, Tuple, Dict, Any
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
import uuid # Used to generate universally unique IDs (session tokens)

load_dotenv()
logging.basicConfig(level=logging.INFO)

# DB Configuration (Read from environment variables)
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Session Configuration
SESSION_TIMEOUT_MINUTES = 30 # Token validity period in minutes


def get_db_connection():
    """Establishes the connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except psycopg2.Error as e:
        logging.error(f"Database connection error: {e}")
        return None

# ==================== USER FUNCTIONS ====================

def fetch_user_by_username(username: str) -> Optional[Tuple]:
    """Retrieves password hash and essential data by username for login verification."""
    conn = get_db_connection()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT user_id, password_hash, role, name, surname
            FROM users 
            WHERE username = %s
            """, 
            (username,)
        )
        # Returns (user_id, password_hash, role, name, surname)
        return cur.fetchone()
    except Exception as e:
        logging.error(f"DB Error in fetch_user_by_username: {e}")
        return None
    finally:
        if conn: conn.close()

def insert_new_user(user_data: Dict[str, Any], hashed_password: str) -> bool:
    """Inserts a new user into the DB."""
    conn = get_db_connection()
    if not conn: return "DB connection error"
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (user_id, name, surname, birthdate, username, password_hash, role, last_access)
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO NOTHING
            RETURNING user_id;
            """,
            (
                user_data["telegram_id"],
                user_data["name"],
                user_data["surname"],
                user_data["birthdate"],
                user_data["username"],
                hashed_password,
                user_data["role"]
            ),
        )

        if cur.rowcount == 0:
            conn.rollback()
            return "User already exists" # Conflict on Telegram ID (user_id)

        conn.commit()
        return True

    except psycopg2.IntegrityError:
        # Handles errors like duplicate unique usernames
        conn.rollback()
        return "Username already in use" 

    except Exception as e:
        logging.error(f"DB Error in insert_new_user: {e}")
        conn.rollback()
        return f"Database error: {e}"

    finally:
        if conn: conn.close()

def update_user_last_access(user_id: int):
    """Updates the last access timestamp for tracking/statistics (not session expiry)."""
    conn = get_db_connection()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET last_access = CURRENT_TIMESTAMP WHERE user_id = %s",
            (user_id,)
        )
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"DB Error in update_user_last_access: {e}")
        return False
    finally:
        if conn: conn.close()

# ==================== SESSION (Token) FUNCTIONS ====================

def create_session_token(user_id: int) -> Optional[str]:
    """Generates, saves, and returns a new session token."""
    conn = get_db_connection()
    if not conn: return None
    
    token = str(uuid.uuid4()) # Generate a unique token string
    # Calculate token expiration time in UTC
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=SESSION_TIMEOUT_MINUTES) 
    
    try:
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO sessions (token, user_id, expires_at)
            VALUES (%s, %s, %s)
            """,
            (token, user_id, expires_at)
        )
        conn.commit()
        return token
    except Exception as e:
        logging.error(f"DB Error in create_session_token: {e}")
        conn.rollback()
        return None
    finally:
        if conn: conn.close()


def validate_session_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Checks if a token is valid (exists and is not expired).
    Returns essential user data (role, name) if valid.
    """
    conn = get_db_connection()
    if not conn: return None
    try:
        cur = conn.cursor()
        
        # Joins sessions and users tables. Checks if token exists AND has not expired.
        cur.execute(
            """
            SELECT 
                u.user_id, u.name, u.surname, u.role
            FROM sessions s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.token = %s AND s.expires_at > CURRENT_TIMESTAMP
            """,
            (token,)
        )
        result = cur.fetchone()
        
        if result:
            user_id, name, surname, role = result
            # Return user details for the bot's use
            return {
                "user_id": user_id,
                "name": name,
                "surname": surname,
                "role": role,
                "status": "ok"
            }
        return None # Token not found or expired
    except Exception as e:
        logging.error(f"DB Error in validate_session_token: {e}")
        return None
    finally:
        if conn: conn.close()


def delete_session_token(token: str) -> bool:
    """Deletes the session token (LOGOUT action)."""
    conn = get_db_connection()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM sessions WHERE token = %s",
            (token,)
        )
        conn.commit()
        # Check if any row was deleted (meaning the token existed)
        return cur.rowcount > 0 
    except Exception as e:
        logging.error(f"DB Error in delete_session_token: {e}")
        conn.rollback()
        return False
    finally:
        if conn: conn.close()