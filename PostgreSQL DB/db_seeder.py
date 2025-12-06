import psycopg2
import os
from dotenv import load_dotenv
import bcrypt # Importiamo la libreria bcrypt

# Carica le variabili dal file .env
load_dotenv() 

# Funzione per stabilire la connessione al DB (riutilizzata da setup_database)
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
        
        # 1. Popolazione della Tabella USERS
        
        # Le password in chiaro di test
        admin_password_clear = "SecureAdmin456!"
        chica_password_clear = "SecureChica789!"
        chico_password_clear = "SecureChico012!"
        
        # Genera gli hash reali
        admin_hash = hash_password(admin_password_clear)
        chica_hash = hash_password(chica_password_clear)
        chico_hash = hash_password(chico_password_clear)
        
        users_data = [
            (1000000001, 'admin_test', admin_hash, 'admin'),
            (1000000002, 'chica_test', chica_hash, 'follower'),
            (1000000003, 'chico_test', chico_hash, 'leader'),
        ]
        
        # Insert Users Query
        insert_users_query = """
            INSERT INTO users (user_id, username, password_hash, role) 
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING;
        """
        cur.executemany(insert_users_query, users_data)
        print(f"Inserted {cur.rowcount} new users with real hashes.")
        
        # (Il resto dello script per events e reservations rimane invariato, ma lo includiamo per completezza)

        # 2. Popolazione della Tabella EVENTS
        events_data = [
            ('serata', 'Bot Launch Party', '2025-12-15 20:00:00', '2025-12-15 23:00:00','Test Location', 20.00, 50),
            ('porta_party', 'Christmas Party', '2026-01-10 22:00:00', '2026-01-11 02:00:00','VIP Venue', 10.00, 30),
            ('workshop', 'Lady Style Workshop', '2026-02-05 10:00:00', '2026-02-05 16:00:00','Tech Hub', 25.00, 20),
        ]
        
        insert_events_query = """
            INSERT INTO events (event_type, title, start_date_time, end_date_time, location, cost, capacity) 
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING event_id;
        """
        cur.executemany(insert_events_query, events_data)
        print(f"Inserted {cur.rowcount} new events.")

        # 3. Popolazione della Tabella RESERVATIONS
        # Recupera l'ID dell'evento di test (ad esempio, il primo evento inserito)
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

        conn.commit()
        print("--- Seeding completed successfully. ---")

    except Exception as e:
        print(f"Error during DB seeding: {e}")
        conn.rollback()
        
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    seed_database()