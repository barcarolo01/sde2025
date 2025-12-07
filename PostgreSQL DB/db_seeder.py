import psycopg2 # PostgreSQL adapter for Python
import os # For accessing environment variables
from dotenv import load_dotenv # To load environment variables from .env file
import bcrypt # Imports the bcrypt library for hashing

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


def seed_database():
    """
    Inserts initial test data (users, events, reservations) into the database.
    Now using real bcrypt hashing for security.
    """
    conn = connect_db()
    if conn is None:
        print("Cannot proceed with seeding. DB connection failed.")
        return

    cur = conn.cursor()

    try:
        print("--- Starting Database Seeding with REAL HASHING ---")
        
        # 1. Populating the USERS Table
        
        # Clear test passwords
        admin_password_clear = "SecureAdmin456!"
        chica_password_clear = "SecureChica789!"
        chico_password_clear = "SecureChico123!"
        
        # Generate real hashes
        admin_hash = hash_password(admin_password_clear)
        chica_hash = hash_password(chica_password_clear)
        chico_hash = hash_password(chico_password_clear)
        
        users_data = [
            (1000000001, 'admin', 'test', '2000-01-01', 'admin_test', admin_hash, 'admin'),
            (1000000002, 'chica', 'loca', '2003-01-01', 'chica_test', chica_hash, 'follower'),
            (1000000003, 'chico', 'loco', '1999-01-01', 'chico_test', chico_hash, 'leader'),
        ]
        
        # Insert Users Query
        insert_users_query = """
            INSERT INTO users (user_id, name, surname, birthdate, username, password_hash, role) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING;
        """
        # Execute the query for multiple users
        cur.executemany(insert_users_query, users_data)
        print(f"Inserted {cur.rowcount} new users with real hashes.")
        
        # (The rest of the script for events and reservations remains the same, but included for completeness)

        # 2. Populating the EVENTS Table
        events_data = [
            ('serata', 'Bot Launch Party', '2025-12-15 20:00:00', '2025-12-15 23:00:00','Test Location', 20.00, 50),
            ('porta_party', 'Christmas Party', '2025-11-29 18:00:00', '2025-11-29 23:00:00','VIP Venue', 10.00, 30),
            ('workshop', 'Lady Style Workshop', '2025-11-15 14:00:00', '2025-11-15 16:00:00','FitUp', 25.00, 20),
        ]
        
        insert_events_query = """
            INSERT INTO events (event_type, title, start_date_time, end_date_time, location, cost, capacity) 
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING event_id;
        """
        cur.executemany(insert_events_query, events_data)
        print(f"Inserted {cur.rowcount} new events.")

        # 3. Populating the RESERVATIONS Table
        # Retrieve the ID of the test event (e.g., the first inserted event)
        cur.execute("SELECT event_id FROM events WHERE title = %s;", ('Bot Launch Party',))
        event_id_test = cur.fetchone()[0]
        reservations_data = (
            1000000002,             
            event_id_test,          
            'paid',                 
            'E1_U2_TOKEN_ABC123'    
        )
        
        insert_reservations_query = """
            INSERT INTO reservations (user_id, event_id, payment_status, qr_code_value) 
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, event_id) DO NOTHING;
        """
        cur.execute(insert_reservations_query, reservations_data)
        print(f"Inserted {cur.rowcount} new reservations.")

        conn.commit() # Final commit for all inserts
        print("--- Seeding completed successfully. ---")

    except Exception as e:
        print(f"Error during DB seeding: {e}")
        conn.rollback() # Rollback on error
        
    finally:
        if cur:
            cur.close() # Close cursor
        if conn:
            conn.close() # Close connection

if __name__ == "__main__":
    seed_database()