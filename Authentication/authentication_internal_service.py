import psycopg2 # PostgreSQL adapter for Python
import os # For accessing environment variables
import bcrypt # For secure password hashing
from dotenv import load_dotenv # To load environment variables from .env file
from datetime import datetime, timezone, timedelta # For handling dates and session timeout

# Load variables from .env file
load_dotenv() 

# Function to establish the DB connection (reused from setup_database)
def connect_db():
    """Establishes a connection to the PostgreSQL database."""
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
        print(f"DB connection error: {e}")
        return None

def hash_password(password):
    """Generates a secure hash for the given password using bcrypt."""
    # bcrypt requires input to be bytes
    password_bytes = password.encode('utf-8')
    # Generate salt and hash the password in one step (standard practice)
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    # Return the hash as a string (decoded from bytes)
    return hashed.decode('utf-8')

# authentication_internal_service.py (register_user)

# Assume hash_password is here or imported
# from .auth_utils import hash_password 

def register_user(user_id, name, surname, birthdate, username, raw_password, role='follower'):
    """
    Registers a new user with full details (name, surname, birthdate, username, password)
    into the database. Default role is 'follower'.
    Returns True on success, or an error message (string) on failure.
    """
    conn = connect_db()
    if conn is None:
        return "Database connection failed."
    
    # 1. Hashes the password
    password_hash = hash_password(raw_password)
    
    # SQL to insert the new user (MUST INCLUDE ALL NEW FIELDS)
    insert_query = """
        INSERT INTO users (
            user_id, name, surname, birthdate, username, password_hash, role, last_access
        ) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (user_id) DO NOTHING 
        RETURNING user_id;
    """
    
    try:
        cur = conn.cursor()
        # Values must be passed in the exact order of the query
        cur.execute(insert_query, (
            user_id, name, surname, birthdate, username, password_hash, role
        ))
        
        if cur.rowcount == 0:
            return f"User with ID {user_id} already exists."
            
        conn.commit()
        return True
        
    except psycopg2.IntegrityError:
        conn.rollback()
        # Handles errors like duplicate usernames (UNIQUE constraint on username)
        return "Username already taken."
        
    except psycopg2.DataError as e:
        conn.rollback()
        # Handles errors like invalid birthdate format or check constraint violation
        return f"Invalid data format (e.g., Birthdate must be YYYY-MM-DD or in the past): {e}"
        
    except psycopg2.Error as e:
        conn.rollback()
        return f"Database error: {e}"
        
    finally:
        if conn:
            conn.close() # Close connection

def authenticate_user(username, raw_password):
    """
    Authenticates a user based on username and password.
    Returns (user_id, role) on success, or None on failure.
    """
    conn = connect_db()
    if conn is None:
        return None
        
    # SQL to retrieve user hash and role
    select_query = "SELECT user_id, password_hash, role FROM users WHERE username = %s;"
    
    try:
        cur = conn.cursor()
        cur.execute(select_query, (username,))
        result = cur.fetchone()
        
        if result is None:
            return None # User not found
            
        user_id, stored_hash, role = result
        
        # 2. Verify the password hash
        # bcrypt.checkpw requires bytes input for both password and hash
        if bcrypt.checkpw(raw_password.encode('utf-8'), stored_hash.encode('utf-8')):
            
            # 3. Update last_access on successful login (Internal Service 1 - Added Feature)
            update_query = "UPDATE users SET last_access = CURRENT_TIMESTAMP WHERE user_id = %s;"
            cur.execute(update_query, (user_id,))
            conn.commit()
            
            return user_id, role # Authentication successful!
        else:
            return None # Password mismatch
            
    except psycopg2.Error as e:
        print(f"Authentication DB error: {e}")
        return None
        
    finally:
        if conn:
            conn.close()

# auth_utils.py (get_user_role)
def get_user_role(user_id):
    """
    Retrieves user data (username, role, name, surname) from the database by user ID.
    Returns a dictionary with details, or None if the user is not found.
    """
    conn = connect_db() 
    if conn is None:
        return None

    # Select all relevant fields for welcome message or logic
    select_query = "SELECT username, role, name, surname FROM users WHERE user_id = %s;"
    
    try:
        cur = conn.cursor()
        cur.execute(select_query, (user_id,))
        result = cur.fetchone()
        
        if result:
            # Returns a dict with the retrieved user details
            return {"username": result[0], "role": result[1], "name": result[2], "surname": result[3]}
        return None
        
    except psycopg2.Error as e:
        print(f"DB retrieval error: {e}")
        return None
        
    finally:
        if conn:
            conn.close()

def logout_user(user_id):
    """
    Sets the last_access field to NULL to invalidate the user's session immediately.
    Returns True on success, False otherwise.
    """
    conn = connect_db()
    if conn is None:
        return False

    # SQL statement to clear the session
    logout_query = "UPDATE users SET last_access = NULL WHERE user_id = %s;"
    
    try:
        cur = conn.cursor()
        cur.execute(logout_query, (user_id,))
        conn.commit()
        return True
        
    except psycopg2.Error as e:
        print(f"Logout DB error: {e}")
        conn.rollback()
        return False
        
    finally:
        if conn:
            conn.close()

def check_session_timeout(user_id):
    """
    Checks if the user's session has expired (inactive for more than 5 minutes).
    If expired, forces logout (sets last_access to NULL).
    Returns True if session is OK (and extends it), False if session has expired or DB error.
    """
    TIMEOUT_SECONDS = 300 # 5 minutes timeout
    conn = connect_db()
    if conn is None:
        return False

    # Get the last access timestamp
    select_query = "SELECT last_access FROM users WHERE user_id = %s;"
    
    try:
        cur = conn.cursor()
        cur.execute(select_query, (user_id,))
        result = cur.fetchone()
        
        if result is None or result[0] is None:
            # User not found or already logged out
            return False 

        last_access = result[0] # last_access is a timezone-aware datetime object
        current_time = datetime.now(timezone.utc) # Use UTC for comparison

        # Calculate the difference (timedelta)
        time_difference = current_time - last_access
        
        if time_difference > timedelta(seconds=TIMEOUT_SECONDS):
            # Session expired! Force logout (set to NULL)
            print(f"User {user_id} session timed out after {time_difference.total_seconds()}s.")
            logout_user(user_id) # Use the newly created function
            return False # Session expired
        
        # Session valid. UPDATE last_access (Extend session)
        update_query = "UPDATE users SET last_access = CURRENT_TIMESTAMP WHERE user_id = %s;"
        cur.execute(update_query, (user_id,))
        conn.commit()
        return True # Session OK
        
    except Exception as e:
        print(f"Session check error: {e}")
        return False
        
    finally:
        if conn:
            conn.close()