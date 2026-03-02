import sqlite3
import os
import json

DB_PATH = os.path.join("data", "sessions.db")

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"[MIGRATION] Database {DB_PATH} does not exist. Skipping.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check current schema
    cursor.execute("PRAGMA table_info(sessions)")
    columns = [row[1] for row in cursor.fetchall()]

    if "client_id" in columns:
        print("[MIGRATION] database already has client_id column. No migration needed.")
        conn.close()
        return

    print("[MIGRATION] Starting migration to v2 (Multitenant)...")

    # 1. Rename old table
    cursor.execute("DROP TABLE IF EXISTS sessions_old")
    cursor.execute("ALTER TABLE sessions RENAME TO sessions_old")

    # 2. Create new table with composite PK
    cursor.execute('''
        CREATE TABLE sessions (
            client_id TEXT NOT NULL,
            phone TEXT NOT NULL,
            data TEXT NOT NULL,
            updated_at REAL,
            PRIMARY KEY (client_id, phone)
        )
    ''')

    # 3. Migrate data with default client_id
    default_client = "clinica_teste"
    cursor.execute("SELECT phone, data, updated_at FROM sessions_old")
    rows = cursor.fetchall()
    
    migrated_count = 0
    for phone, data, updated_at in rows:
        try:
            # Inject client_id and phone into internal JSON data if not present
            s_data = json.loads(data)
            s_data["client_id"] = default_client
            s_data["phone"] = phone
            json_data = json.dumps(s_data, ensure_ascii=False)
            
            cursor.execute('''
                INSERT INTO sessions (client_id, phone, data, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (default_client, phone, json_data, updated_at))
            migrated_count += 1
        except Exception as e:
            print(f" [ERR] Failed to migrate session {phone}: {e}")

    print(f"[MIGRATION] Successfully migrated {migrated_count} sessions to '{default_client}'.")

    # 4. Cleanup
    # cursor.execute("DROP TABLE sessions_old") # Optional: Keep for safety for now
    
    conn.commit()
    conn.close()
    print("[MIGRATION] Done.")

if __name__ == "__main__":
    migrate()
