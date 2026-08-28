import sqlite3
import os

DB_PATH = "career_studio.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Core User Accounts & Isolation (Advancement 14)
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'individual',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        full_name TEXT,
        summary TEXT,
        industry TEXT,
        seniority TEXT,
        experience_relevance REAL DEFAULT 80.0,
        evidence_strength REAL DEFAULT 85.0,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    # Master Career Knowledge Graph (Advancement 6)
    cursor.execute('''CREATE TABLE IF NOT EXISTS graph_experiences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        company TEXT,
        industry TEXT,
        seniority TEXT,
        start_date TEXT,
        end_date TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS graph_achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        experience_id INTEGER,
        description TEXT,
        metrics TEXT,
        FOREIGN KEY(experience_id) REFERENCES graph_experiences(id)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS graph_skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        skill_name TEXT,
        category TEXT,
        evidence_strength REAL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS target_job_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_title TEXT,
        industry TEXT,
        seniority TEXT,
        required_skills TEXT,
        preferred_skills TEXT,
        responsibilities TEXT
    )''')

    # Application Analytics & Tracking (Advancement 9 & 10)
    cursor.execute('''CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        job_title TEXT,
        company TEXT,
        cv_version TEXT,
        status TEXT,
        response_received INTEGER DEFAULT 0,
        interview_stage TEXT,
        offer_extended INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    # Compensation & Negotiation Studio (Advancement 12)
    cursor.execute('''CREATE TABLE IF NOT EXISTS offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        company TEXT,
        salary REAL,
        remote_status TEXT,
        equity TEXT,
        notes TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    # Audit Logs & Security Governance (Advancement 14)
    cursor.execute('''CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
    conn.close()
