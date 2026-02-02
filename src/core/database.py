import sqlite3
import json
import os
import time
from typing import Dict, Optional

DB_PATH = os.path.join("data", "sessions.db")

def get_connection():
    """Returns a connection to the SQLite database."""
    # Ensure data dir exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Simple Key-Value store logic, but inside SQL
    # phone is the key, data is the full JSON blob
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            phone TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            updated_at REAL
        )
    ''')
    
    conn.commit()
    conn.close()

def get_session(phone: str) -> Optional[Dict]:
    """Retrieves a session by phone number."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT data FROM sessions WHERE phone = ?", (phone,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        try:
            return json.loads(row["data"])
        except json.JSONDecodeError:
            return None
    return None

def get_all_sessions() -> Dict[str, Dict]:
    """Retrieves all active sessions for the Dashboard."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT phone, data FROM sessions")
    rows = cursor.fetchall()
    conn.close()
    
    sessions = {}
    for row in rows:
        try:
             sessions[row["phone"]] = json.loads(row["data"])
        except:
             continue
    return sessions

def save_session(phone: str, session_data: Dict):
    """Upserts a session."""
    conn = get_connection()
    cursor = conn.cursor()
    
    json_data = json.dumps(session_data, ensure_ascii=False)
    now = time.time()
    
    cursor.execute('''
        INSERT INTO sessions (phone, data, updated_at) 
        VALUES (?, ?, ?)
        ON CONFLICT(phone) DO UPDATE SET
            data = excluded.data,
            updated_at = excluded.updated_at
    ''', (phone, json_data, now))
    
    conn.commit()
    conn.close()

def prune_old_sessions(days_retention: int = 30):
    """Deletes sessions inactive for more than X days."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Calculate cutoff timestamp
        limit_time = time.time() - (days_retention * 86400)
        
        cursor.execute("DELETE FROM sessions WHERE updated_at < ?", (limit_time,))
        deleted = cursor.rowcount
        
        if deleted > 0:
            print(f"[DB] Auto-pruned {deleted} old sessions (>{days_retention} days).")
            # Reclaim disk space
            cursor.execute("VACUUM")
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB] Error pruning sessions: {e}")
