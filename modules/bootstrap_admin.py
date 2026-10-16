"""Race-safe bootstrap-admin initialization for the Streamlit app."""
from __future__ import annotations

import sqlite3
from collections.abc import Callable


HashPassword = Callable[[str], tuple[str, str]]
AdminOverridePlan = Callable[[str, str, str, str], object]


def ensure_bootstrap_admin_record(
    conn: sqlite3.Connection,
    bootstrap_email: str | None,
    bootstrap_password: str | None,
    hash_password: HashPassword,
    admin_override_plan: AdminOverridePlan,
) -> bool:
    """Create the bootstrap admin only when the account table is empty.

    BEGIN IMMEDIATE serializes the empty-table check and insert across Streamlit
    sessions/processes sharing the same SQLite file. Returns True only when this
    call inserted the bootstrap account.
    """
    email_norm = (bootstrap_email or "").strip().lower()
    try:
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.cursor()
        user_count = cursor.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0]
        if user_count > 0:
            if email_norm:
                cursor.execute(
                    "UPDATE auth_users SET name = 'CHRISHEM' "
                    "WHERE email = ? AND role = 'admin'",
                    (email_norm,),
                )
            conn.commit()
            return False

        if not email_norm or not bootstrap_password:
            conn.commit()
            return False

        password_hash, salt = hash_password(bootstrap_password)
        cursor.execute(
            "INSERT INTO auth_users (email, name, password_hash, salt, role) "
            "VALUES (?,?,?,?,?)",
            (email_norm, "CHRISHEM", password_hash, salt, "admin"),
        )
        conn.commit()
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise

    admin_override_plan("system:bootstrap", email_norm, "pro", "comp")
    return True
