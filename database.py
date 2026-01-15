import sqlite3
import pandas as pd

DB_PATH = "appointments.db"

def init_database():
    """Initialize SQLite database for persistent storage"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create appointments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_slot TEXT NOT NULL,
            specialization TEXT NOT NULL,
            doctor_name TEXT NOT NULL,
            is_available BOOLEAN NOT NULL,
            patient_to_attend TEXT,
            patient_age INTEGER,
            patient_phone TEXT,
            confirmation_number TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create chat history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def load_appointments_from_db():
    """Load appointments data from SQLite database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM appointments", conn)
        conn.close()
        
        if df.empty:
            return None
        
        df['is_available'] = df['is_available'].astype(bool)
        return df
    except Exception as e:
        print(f"Error loading from database: {e}")
        return None

def save_appointments_to_db(df):
    """Save appointments data to SQLite database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        
        # Clear existing data
        cursor = conn.cursor()
        cursor.execute("DELETE FROM appointments")
        
        # Insert updated data
        df.to_sql('appointments', conn, if_exists='append', index=False)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving to database: {e}")
        return False

def save_chat_message(session_id, role, content):
    """Save a chat message to database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chat_history (session_id, role, content)
            VALUES (?, ?, ?)
        """, (session_id, role, content))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving chat message: {e}")

def load_chat_history(session_id):
    """Load chat history for a session from database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT role, content FROM chat_history
            WHERE session_id = ?
            ORDER BY created_at ASC
        """, (session_id,))
        messages = cursor.fetchall()
        conn.close()
        return [{"role": role, "content": content} for role, content in messages]
    except Exception as e:
        print(f"Error loading chat history: {e}")
        return []