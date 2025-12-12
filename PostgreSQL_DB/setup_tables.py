import psycopg2 # PostgreSQL adapter for Python
import os # For accessing environment variables
from dotenv import load_dotenv # To load environment variables from .env file

# Load environment variables from .env file
load_dotenv()

def connect_db():
    """Establishes a connection to the database using environment variables."""
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
        # Error handling (you might want to terminate the program here)
        return None

def setup_database():
    """Executes the SQL script to create the tables."""
    conn = connect_db()
    if conn is None:
        return

    try:
        cur = conn.cursor()
        
        sql_commands = [
            """
            -- Creates the users table (1)
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                surname VARCHAR(100) NOT NULL,
                birthdate DATE NOT NULL CHECK (birthdate <= CURRENT_DATE),
                username VARCHAR(255) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL CHECK (role IN ('follower', 'leader', 'admin')),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                last_access TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            -- Creates the events table (2)
            CREATE TABLE IF NOT EXISTS events (
                event_id SERIAL PRIMARY KEY,
                event_type VARCHAR(50) NOT NULL CHECK (event_type IN ('serata', 'porta_party', 'workshop')),
                title VARCHAR(255) NOT NULL,
                start_date_time TIMESTAMP WITH TIME ZONE NOT NULL,
                end_date_time TIMESTAMP WITH TIME ZONE NOT NULL CHECK (end_date_time > start_date_time),
                location VARCHAR(255),
                capacity INTEGER NOT NULL CHECK (capacity >= 0),
                cost DECIMAL(10,2) DEFAULT 0.00 CHECK (cost >= 0.00),
                description TEXT,
                poster_image_url VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            -- Creates the reservations table (3)
            CREATE TABLE IF NOT EXISTS reservations (
                reservation_id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
                event_id INTEGER NOT NULL REFERENCES events (event_id) ON DELETE CASCADE,
                payment_status VARCHAR(50) NOT NULL CHECK (payment_status IN ('pending', 'paid', 'failed')),
                qr_code_value VARCHAR(255) UNIQUE,
                is_checked_in BOOLEAN DEFAULT FALSE,
                check_in_time TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            -- Unique index to prevent double bookings
            CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_reservation ON reservations (user_id, event_id);
            """,
            """
            -- Creates the sessions table (4) - MODIFICATA PER TIMEOUT FISSO
            CREATE TABLE IF NOT EXISTS sessions (
                token VARCHAR(255) PRIMARY KEY,       -- Il token univoco di sessione
                user_id INTEGER NOT NULL REFERENCES users (user_id) ON DELETE CASCADE, -- Correzione del tipo: deve essere INTEGER
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP WITH TIME ZONE NOT NULL -- NUOVO: Definisce il momento di scadenza del token
            );
            -- Aggiungi un indice per velocizzare la ricerca per user_id
            CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
            """           
        ]
        
        # Execute each SQL command
        for command in sql_commands:
            cur.execute(command)
        
        conn.commit() # Commit changes to the database
        print("Database tables created or verified successfully.")
        
    except psycopg2.ProgrammingError as e:
        # Handles errors like trying to recreate tables without IF NOT EXISTS
        print(f"SQL error during table creation: {e}")
        conn.rollback() # Rollback any pending operation on error
        
    except Exception as e:
        print(f"Generic error during DB setup: {e}")
        
    finally:
        if conn:
            conn.close() # Close connection

# Execute the setup function
if __name__ == "__main__":
    setup_database()