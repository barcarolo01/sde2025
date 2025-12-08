import json
import os
from dotenv import load_dotenv
from flask import Flask, request
import psycopg2

app = Flask(__name__)

# This function performs the connection to the database
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

# Root endpoint to verify service is running
@app.route("/")
def root():
    return "<h1>Calendar service is working!</h1>"

# Endpoint to create a new event
@app.route("/events/create", methods = ['POST'])
def event_create():
    #Check if the user can create a new event
    if 0==0: # TODO: 
        return "Unauthorized", 401
    
    # Retrieve the json file
    event_data = request.get_json()
    if not event_data:
        return "No JSON data received", 400

    # Extract information from the json file
    Event_Type = event_data.get("event_type")
    Title = event_data.get("title")
    Start_Date = event_data.get("start_date")
    Start_Time = event_data.get("start_time")
    End_Date = event_data.get("end_date")
    End_Time = event_data.get("end_time")
    Location = event_data.get("location")
    Capacity = event_data.get("capacity")
    Cost = event_data.get("cost")
    Is_Active = event_data.get("is_active")

    # Connect to the database
    conn = connect_db()
    if conn is None:
        return "Internal Server Error: impossible to connect to the database",500
    
    # Insert the event into the database
    try:
        cur = conn.cursor()
        sql_command = """
        INSERT INTO events (event_type, title, start_date_time, end_date_time, location, capacity, cost, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """
        parameters = (Event_Type, Title, f"{Start_Date} {Start_Time}", f"{End_Date} {End_Time}", Location, Capacity, Cost, Is_Active)
        cur.execute(sql_command, parameters)
        conn.commit()
 
    except Exception as e:
        conn.rollback()
        return "Generic error during DB insertion",500
        
    finally:
        if conn:
            conn.close()

    return "Created",201 # Return 201 if the event is created successfully

# Endpoint to fetch a list of events
@app.route("/events", methods = ['GET'])
def fetch_events():
    PAGE_SIZE = 3
    offset  = request.args.get('offset', default=0, type=int)
    
    # Connect to the database
    conn = connect_db()
    if conn is None:
        return "Internal Server Error: impossible to connect to the database",500
    
    try:
        cur = conn.cursor()
        if 0==0: # TODO: check if user is authorized
            query =f"""
                SELECT event_id, event_type, title, start_date_time, end_date_time, location, capacity, cost
                FROM events WHERE start_date_time > NOW()
                ORDER BY start_date_time ASC LIMIT {PAGE_SIZE} OFFSET {offset}
                """
        else:
            query = f"""
                SELECT event_id, event_type, title, start_date_time, end_date_time, location, capacity, cost
                FROM events WHERE start_date_time > NOW() AND is_active = TRUE
                ORDER BY start_date_time ASC LIMIT {PAGE_SIZE} OFFSET {offset}
                """
        cur.execute(query)
        rows = cur.fetchall()
        
        # Get column names from cursor
        colnames = [desc[0] for desc in cur.description]

        # Convert rows to list of dicts
        data = [dict(zip(colnames, row)) for row in rows]

        cur.close()
        conn.close()

        # Return JSON string
        return json.dumps(data, default=str), 200

    except Exception as e:
        conn.rollback()
        return "Generic error during DB insertion",500

# Endpoint to fetch a single event by its ID
@app.route("/events/<int:event_id>", methods=['GET'])
def fetch_single_event(event_id):
    # Connect to the database
    conn = connect_db()
    if conn is None:
        return "Internal Server Error: impossible to connect to the database",500
    
    try:
        cur = conn.cursor()
        if 0==0: # TODO: check if user is authorized
            query =f"SELECT * FROM events WHERE event_id = {event_id}"
        else:
            query = f" SELECT * FROM events WHERE event_id = {event_id} AND is_active = TRUE "

        cur.execute(query)
        rows = cur.fetchall()
        if len(rows) == 0:
            return "Event not found", 404
        
        # Get column names from cursor
        colnames = [desc[0] for desc in cur.description]

        # Convert rows to list of dicts
        data = [dict(zip(colnames, row)) for row in rows]

        cur.close()
        conn.close()

        # Return JSON string
        return json.dumps(data, default=str), 200

    except Exception as e:
        conn.rollback()
        return "Generic error during DB insertion",500

    

if __name__ == "__main__":
    load_dotenv()  # Loads variables from .env into environment
    CALENDAR_SERVICE_PORT = os.environ.get("CALENDAR_SERVICE_PORT")
    app.run(host="0.0.0.0", port=CALENDAR_SERVICE_PORT, debug=True)