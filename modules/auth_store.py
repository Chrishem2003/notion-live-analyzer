"""
modules/auth_store.py
Real authentication: hashed passwords + server-side roles.

Public account creation always creates an ordinary user. Privileged roles are
assigned only by explicit trusted server-side workflows, such as the
single-use first-admin bootstrap below; email addresses never confer roles.

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
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
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
    """Create a normal account; never allow caller-selected privilege elevation.

    The role argument remains for call-site compatibility but is deliberately
    ignored. Admin/student verification roles must be assigned by trusted,
    separately authorized server-side workflows.
    """
    email = email.strip().lower()
    conn = get_conn()
    pw_hash, pw_salt = _hash_password(password)
    try:
        conn.execute(
            "INSERT INTO auth_users (email, name, pw_hash, pw_salt, role, created_at) VALUES (?,?,?,?,?,?)",
            (email, name, pw_hash, pw_salt, "user", datetime.datetime.now(datetime.UTC).isoformat()),
        )
        conn.commit()
        return {"ok": True}
    except sqlite3.IntegrityError:
        return {"ok": False, "error": "An account with that email already exists."}
    finally:
        conn.close()


def verify_login(email: str, password: str):
    """Return the database-stored role only after successful password verification."""
    email = email.strip().lower()
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id, email, name, pw_hash, pw_salt, role FROM auth_users WHERE email=?", (email,)
        ).fetchone()
        if not row:
            return None
        uid, email, name, pw_hash, pw_salt, role = row
        try:
            check_hash, _ = _hash_password(password, bytes.fromhex(pw_salt))
        except (TypeError, ValueError):
            return None
        if not hmac.compare_digest(check_hash, pw_hash):
            return None

        conn.execute(
            "UPDATE auth_users SET last_login=? WHERE id=?",
            (datetime.datetime.now(datetime.UTC).isoformat(), uid),
        )
        conn.commit()
        return {"id": uid, "email": email, "name": name, "role": role}
    finally:
        conn.close()


def get_role(email: str) -> str:
    """Retrieve the stored role; email identity alone never grants privileges."""
    email = email.strip().lower()
    conn = get_conn()
    try:
        row = conn.execute("SELECT role FROM auth_users WHERE email=?", (email,)).fetchone()
        return row[0] if row else "user"
    finally:
        conn.close()


def set_role(email: str, role: str):
    """Admin-only operation — call this only from behind require_admin()."""
    if role not in ROLES:
        raise ValueError(f"Invalid role: {role}")
    conn = get_conn()
    try:
        conn.execute("UPDATE auth_users SET role=? WHERE email=?", (role, email.strip().lower()))
        conn.commit()
    finally:
        conn.close()


def bootstrap_first_admin(email: str, name: str, password: str):
    """Atomically create the first admin, and only while the user table is empty.

    BEGIN IMMEDIATE serializes concurrent bootstrap attempts so two requests
    cannot both observe an empty table and create privileged accounts.
    """
    email = email.strip().lower()
    conn = get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        count = conn.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0]
        if count > 0:
            conn.commit()
            return {"ok": False, "error": "Users already exist — bootstrap only runs on an empty database."}

        pw_hash, pw_salt = _hash_password(password)
        conn.execute(
            "INSERT INTO auth_users (email, name, pw_hash, pw_salt, role, created_at) VALUES (?,?,?,?,?,?)",
            (email, name, pw_hash, pw_salt, "admin", datetime.datetime.now(datetime.UTC).isoformat()),
        )
        conn.commit()
        return {"ok": True}
    except sqlite3.IntegrityError:
        if conn.in_transaction:
            conn.rollback()
        return {"ok": False, "error": "Admin bootstrap could not create the initial account."}
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()
