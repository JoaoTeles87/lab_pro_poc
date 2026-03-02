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
    
    # Check if table needs migration (adding client_id)
    cursor.execute("PRAGMA table_info(sessions)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "client_id" not in columns:
        print("[DB] Migrating database to multitenant schema...")
        # Backup old data if needed, but since it's a POC and schema changes PK, 
        # it's safer to recreate or alter. Recreating is cleaner for POC.
        cursor.execute("DROP TABLE IF EXISTS sessions_old")
        cursor.execute("ALTER TABLE sessions RENAME TO sessions_old")
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                client_id TEXT NOT NULL,
                phone TEXT NOT NULL,
                data TEXT NOT NULL,
                updated_at REAL,
                PRIMARY KEY (client_id, phone)
            )
        ''')
        # We don't port data from sessions_old because we don't know the client_id for old sessions.
        print("[DB] Migration complete. Old table renamed to sessions_old.")
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                client_id TEXT NOT NULL,
                phone TEXT NOT NULL,
                data TEXT NOT NULL,
                updated_at REAL,
                PRIMARY KEY (client_id, phone)
            )
        ''')
    
    conn.commit()
    conn.close()

def get_session(client_id: str, phone: str) -> Optional[Dict]:
    """Retrieves a session by client_id and phone number."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT data FROM sessions WHERE client_id = ? AND phone = ?", (client_id, phone))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        try:
            return json.loads(row["data"])
        except json.JSONDecodeError:
            return None
    return None

def get_all_sessions(client_id: Optional[str] = None) -> Dict[str, Dict]:
    """Retrieves all active sessions, optionally filtered by client_id."""
    conn = get_connection()
    cursor = conn.cursor()
    
    if client_id:
        cursor.execute("SELECT client_id, phone, data FROM sessions WHERE client_id = ?", (client_id,))
    else:
        cursor.execute("SELECT client_id, phone, data FROM sessions")
        
    rows = cursor.fetchall()
    conn.close()
    
    sessions = {}
    for row in rows:
        try:
             s_data = json.loads(row["data"])
             s_data["client_id"] = row["client_id"] # Ensure it matches DB
             s_data["phone"] = row["phone"]
             sessions[row["phone"]] = s_data
        except:
             continue
    return sessions

def save_session(client_id: str, phone: str, session_data: Dict):
    """Upserts a session."""
    conn = get_connection()
    cursor = conn.cursor()
    
    json_data = json.dumps(session_data, ensure_ascii=False)
    now = time.time()
    
    cursor.execute('''
        INSERT INTO sessions (client_id, phone, data, updated_at) 
        VALUES (?, ?, ?, ?)
        ON CONFLICT(client_id, phone) DO UPDATE SET
            data = excluded.data,
            updated_at = excluded.updated_at
    ''', (client_id, phone, json_data, now))
    
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

def delete_session(client_id: str, phone: str):
    """Deletes a specific session by client_id and phone number."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE client_id = ? AND phone = ?", (client_id, phone))
    conn.commit()
    conn.close()

def clear_all_sessions(client_id: Optional[str] = None):
    """⚠️ DANGER: Deletes sessions. If client_id is None, deletes ALL."""
    conn = get_connection()
    cursor = conn.cursor()
    if client_id:
        cursor.execute("DELETE FROM sessions WHERE client_id = ?", (client_id,))
    else:
        cursor.execute("DELETE FROM sessions")
    conn.commit()
    conn.close()
