import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def connect_db():
    """Stabilisce la connessione al database usando le variabili d'ambiente."""
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
        print(f"Errore di connessione al DB: {e}")
        # Gestione dell'errore (potresti voler terminare il programma qui)
        return None

def setup_database():
    """Esegue lo script SQL per creare le tabelle."""
    conn = connect_db()
    if conn is None:
        return

    try:
        cur = conn.cursor()
        
        sql_commands = [
            """
            -- Crea la tabella users (1)
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username VARCHAR(255) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL CHECK (role IN ('follower', 'leader', 'admin')),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                last_access TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            -- Crea la tabella events (2)
            CREATE TABLE IF NOT EXISTS events (
                event_id SERIAL PRIMARY KEY,
                event_type VARCHAR(50) NOT NULL CHECK (event_type IN ('serata', 'porta_party', 'workshop')),
                title VARCHAR(255) NOT NULL,
                start_date_time TIMESTAMP WITH TIME ZONE NOT NULL,
                end_date_time TIMESTAMP WITH TIME ZONE NOT NULL CHECK (end_date_time > start_date_time),
                location VARCHAR(255),
                capacity INTEGER NOT NULL CHECK (capacity >= 0),
                cost DECIMAL(10,2) DEFAULT 0.00 CHECK (cost >= 0.00),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            -- Crea la tabella reservations (3)
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
            -- Indice di unicità per prevenire doppie prenotazioni
            CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_reservation ON reservations (user_id, event_id);
            """
        ]
        
        for command in sql_commands:
            cur.execute(command)
        
        conn.commit()
        print("Tabelle del database create o verificate con successo.")
        
    except psycopg2.ProgrammingError as e:
        # Questo può accadere se le tabelle esistono già e stai provando a ricrearle senza IF NOT EXISTS
        print(f"Errore SQL durante la creazione delle tabelle: {e}")
        conn.rollback() # Annulla qualsiasi operazione pendente in caso di errore
        
    except Exception as e:
        print(f"Errore generico durante il setup del DB: {e}")
        
    finally:
        if conn:
            conn.close()

# Esegui la funzione di setup
if __name__ == "__main__":
    setup_database()    