from flask import Flask, request, jsonify, make_response
import os
import bcrypt # Library for secure password hashing
import logging
from dotenv import load_dotenv

# Import the Data Layer module (assumed to handle database interaction)
import db_adapter 

load_dotenv()
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# ---------------------------------------
# PASSWORD MANAGEMENT (Business Logic Layer)
# ---------------------------------------
def hash_password(password: str) -> str:
    """Hashes the password using bcrypt."""
    # Encode password, generate a salt, hash, and decode back to string for storage
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verifies if the provided password matches the stored hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception as e:
        logging.error(f"Error during password verification: {e}")
        return False


# ---------------------------------------
# HTTP ENDPOINT — REGISTRATION
# ---------------------------------------
@app.post("/register")
def register_user_api():
    """Registers a new user via API."""
    data = request.get_json()

    # Check for all required fields
    required = ["telegram_id", "name", "surname", "birthdate", "username", "password", "role"]
    if not all(k in data for k in required):
        return jsonify({"error": "Missing fields in JSON"}), 400

    try:
        # Hash the plain text password before storage
        hashed_password = hash_password(data["password"])
        
        # Call the Data Layer to insert the user
        result = db_adapter.insert_new_user(data, hashed_password)

        if result is True:
            return jsonify({"status": "ok", "message": "Registration successful"}), 201
        
        # Handle conflict errors (user or username already exists)
        if result == "User already exists" or result == "Username already in use":
            return jsonify({"error": result}), 409
        
        return jsonify({"error": "Internal database error"}), 500

    except Exception as e:
        logging.error(f"General error in /register: {e}")
        return jsonify({"error": f"Internal server error: {e}"}), 500


# ---------------------------------------
# HTTP ENDPOINT — LOGIN (NOW WITH TOKEN)
# ---------------------------------------
@app.post("/login")
def login_user_api():
    """Authenticates the user, updates last_access, and creates a session token."""
    data = request.get_json()

    if "username" not in data or "password" not in data:
        return jsonify({"error": "Missing fields"}), 400

    # 1. Retrieve user data (including the stored hash)
    result = db_adapter.fetch_user_by_username(data["username"])
    
    if not result:
        return jsonify({"error": "Invalid credentials"}), 401 # User not found

    user_id, stored_hash, role, name, surname = result

    # 2. Verify the password against the stored hash
    if not verify_password(data["password"], stored_hash):
        return jsonify({"error": "Invalid credentials"}), 401 # Password mismatch

    # 3. Update last_access (for statistics/tracking)
    db_adapter.update_user_last_access(user_id)
    
    # 4. Create Session Token in the database
    token = db_adapter.create_session_token(user_id)
    
    if not token:
        logging.error(f"Error creating token for user_id: {user_id}")
        return jsonify({"error": "Failed to create session token"}), 500

    # 5. Return user info and the new session token
    return jsonify({
        "status": "ok",
        "token": token,  # <-- TOKEN RETURNED to the client
        "user_id": user_id,
        "role": role,
        "name": name,
        "surname": surname
    }), 200

# ---------------------------------------
# HTTP ENDPOINT — VALIDATE TOKEN (/start)
# ---------------------------------------
@app.post("/validate") # Specific endpoint for Bot session status check
def validate_token_api():
    """
    Checks if the token provided by the bot is valid and not expired.
    Used by the Bot when starting up (/start).
    """
    data = request.get_json()
    token = data.get("token")
    
    if not token:
        # If the bot doesn't send a token, it means no local session exists
        return jsonify({"status": "unauthenticated"}), 401 

    # Check the token's validity and retrieve user data if valid
    user_info = db_adapter.validate_session_token(token)
    
    if user_info:
        # Session is valid (token exists and is not expired)
        return jsonify(user_info), 200
    else:
        # Token not found or expired in the sessions table
        return jsonify({"status": "session_expired", "message": "Session token invalid or expired"}), 401
    
# ---------------------------------------
# HTTP ENDPOINT — LOGOUT (Using Token in body)
# ---------------------------------------
@app.post("/logout") 
def logout_user_api():
    """Performs logout by deleting the session token from the database."""
    data = request.get_json()
    token = data.get("token")
    
    if not token:
        return jsonify({"error": "Missing token"}), 400
    
    # Call the Data Layer to delete the token record
    success = db_adapter.delete_session_token(token)
    
    if success:
        return jsonify({"status": "ok", "message": "Logout successful"}), 200
    else:
        # Use 404 to indicate the token wasn't found (maybe already deleted)
        return jsonify({"error": "Token not found or internal server error"}), 404 

# ---------------------------------------
# START SERVER
# ---------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("AUTH_SERVICE_PORT", 5001))
    logging.info(f"Auth Service started on port {port}...")
    app.run(host="0.0.0.0", port=port)