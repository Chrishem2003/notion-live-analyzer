"""
modules/auth_store.py
Real authentication: hashed passwords + server-side roles.

Replaces the pattern in portal.py where "is_admin" was decided in the
browser by matching a typed email, and app.py where the role was a
selectbox the user picked for themselves. Neither of those is a security
boundary — this module is.

DB: sovereign_apex_engine.db (same file the rest of the app already uses)
"""

import sqlite3
import hashlib
import hmac
import os
import datetime

DB_PATH = "sovereign_apex_engine.db"
ROLES = ["user", "student_verified", "admin"]


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS auth_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            pw_hash TEXT NOT NULL,
            pw_salt TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT,
            last_login TEXT
        )
    """)
    conn.commit()
    return conn


def _hash_password(password: str, salt: bytes = None):
    if salt is None:
        salt = os.urandom(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return pw_hash.hex(), salt.hex()


def create_user(email: str, name: str, password: str, role: str = "user"):
    email = email.strip().lower()
    if role not in ROLES:
        role = "user"
    conn = get_conn()
    pw_hash, pw_salt = _hash_password(password)
    try:
        conn.execute(
            "INSERT INTO auth_users (email, name, pw_hash, pw_salt, role, created_at) VALUES (?,?,?,?,?,?)",
            (email, name, pw_hash, pw_salt, role, datetime.datetime.utcnow().isoformat()),
        )
        conn.commit()
        return {"ok": True}
    except sqlite3.IntegrityError:
        return {"ok": False, "error": "An account with that email already exists."}
    finally:
        conn.close()


def verify_login(email: str, password: str):
    """Returns the user record dict on success, or None. Never trusts client input for role."""
    email = email.strip().lower()
    conn = get_conn()
    row = conn.execute(
        "SELECT id, email, name, pw_hash, pw_salt, role FROM auth_users WHERE email=?", (email,)
    ).fetchone()
    if not row:
        conn.close()
        return None
    uid, email, name, pw_hash, pw_salt, role = row
    check_hash, _ = _hash_password(password, bytes.fromhex(pw_salt))
    if not hmac.compare_digest(check_hash, pw_hash):
        conn.close()
        return None
    conn.execute("UPDATE auth_users SET last_login=? WHERE id=?", (datetime.datetime.utcnow().isoformat(), uid))
    conn.commit()
    conn.close()
    return {"id": uid, "email": email, "name": name, "role": role}


def get_role(email: str) -> str:
    """Retrieve the server-validated role for a user by email."""
    email = email.strip().lower()
    conn = get_conn()
    row = conn.execute("SELECT role FROM auth_users WHERE email=?", (email,)).fetchone()
    conn.close()
    if not row:
        return "user"
    return row[0]


def set_role(email: str, role: str):
    """Admin-only operation — call this only from behind require_admin()."""
    if role not in ROLES:
        raise ValueError(f"Invalid role: {role}")
    conn = get_conn()
    conn.execute("UPDATE auth_users SET role=? WHERE email=?", (role, email.strip().lower()))
    conn.commit()
    conn.close()


def bootstrap_first_admin(email: str, name: str, password: str):
    """
    Run once. Creates the very first admin account, only if the auth_users
    table is completely empty (so this can't be used to silently mint a
    second admin later).
    """
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0]
    conn.close()
    if count > 0:
        return {"ok": False, "error": "Users already exist — bootstrap only runs on an empty database."}
    return create_user(email, name, password, role="admin")