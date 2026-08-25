
import sqlite3
import os
import datetime

DB_PATH = "sovereign_apex_engine.db"  # matches app.py and modules/subscription.py — was
# previously "chrishem_engine.db", a separate file the rest of the app never read from,
# so every log_backend_event()/save_user_session() call was silently writing to a
# SQLite file no admin panel or query ever looked at.

def init_db():
    """
    Automatically initializes SQLite backend tables on system startup.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # User Sessions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            username TEXT PRIMARY KEY,
            auth_gateway TEXT,
            last_login TEXT,
            preferred_language TEXT
        )
    """)
    
    # System Audit & Vault Logs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            log_level TEXT,
            message TEXT
        )
    """)
    
    conn.commit()
    conn.close()

def log_backend_event(level: str, message: str):
    """
    Persists audit events and operational logs directly to the database.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO system_logs (timestamp, log_level, message) VALUES (?, ?, ?)", 
                   (timestamp, level, message))
    conn.commit()
    conn.close()

def save_user_session(username: str, gateway: str, lang: str):
    """
    Saves or updates user session state in the persistent backend.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO user_sessions (username, auth_gateway, last_login, preferred_language)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET
            auth_gateway = excluded.auth_gateway,
            last_login = excluded.last_login,
            preferred_language = excluded.preferred_language
    """, (username, gateway, timestamp, lang))
    conn.commit()
    conn.close()
