from flask import Flask, request, jsonify
import psycopg2
import os
import bcrypt
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

app = Flask(__name__)

# ---------------------------------------
# DATABASE CONNECTION
# ---------------------------------------
def connect_db():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
        return conn
    except psycopg2.Error as e:
        print("Database connection error:", e)
        return None


# ---------------------------------------
# PASSWORD MANAGEMENT
# ---------------------------------------
def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# ---------------------------------------
# HTTP ENDPOINT — REGISTRATION
# ---------------------------------------
@app.post("/register")
def register_user():
    data = request.get_json()

    required = ["telegram_id", "name", "surname", "birthdate", "username", "password", "role"]
    if not all(k in data for k in required):
        return "Missing fields in JSON", 400

    conn = connect_db()
    if conn is None:
        return "DB connection error", 500

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
                data["telegram_id"],
                data["name"],
                data["surname"],
                data["birthdate"],
                data["username"],
                hash_password(data["password"]),
                data["role"]
            ),
        )

        if cur.rowcount == 0:
            return "User already exists", 409

        conn.commit()
        return jsonify({"status": "ok"}), 200

    except psycopg2.IntegrityError:
        conn.rollback()
        return "Username already in use", 409

    except Exception as e:
        conn.rollback()
        return f"Database error: {e}", 500

    finally:
        conn.close()


# ---------------------------------------
# HTTP ENDPOINT — LOGIN
# ---------------------------------------
@app.post("/login")
def login_user():
    data = request.get_json()

    if "username" not in data or "password" not in data or "telegram_id" not in data:
        return "Missing fields", 400

    conn = connect_db()
    if conn is None:
        return "DB connection error", 500

    try:
        cur = conn.cursor()

        cur.execute("SELECT user_id, password_hash, role, name, surname FROM users WHERE username = %s",
                    (data["username"],))
        result = cur.fetchone()

        if not result:
            return "Invalid credentials", 401

        user_id, stored_hash, role, name, surname = result

        if not verify_password(data["password"], stored_hash):
            return "Invalid credentials", 401

        # Update last access
        cur.execute(
            "UPDATE users SET last_access = CURRENT_TIMESTAMP WHERE user_id = %s",
            (user_id,)
        )
        conn.commit()

        return jsonify({
            "status": "ok",
            "role": role,
            "name": name,
            "surname": surname
        }), 200

    except Exception as e:
        return f"Database error: {e}", 500

    finally:
        conn.close()


# ---------------------------------------
# START SERVER
# ---------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=os.getenv("AUTH_SERVICE_PORT", 5001))
