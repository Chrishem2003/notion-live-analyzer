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
    """Ensure the configured server-side bootstrap identity exists as admin.

    With both bootstrap credentials configured, the designated email is the
    authoritative administrator identity: create it even when ordinary users
    already exist, or promote/reset the password of that exact email if it
    already exists. Other accounts and their data are left untouched.

    BEGIN IMMEDIATE serializes lookup/update/insert across sessions sharing
    the SQLite file. Returns True only when a new row was inserted.
    """
    email_norm = (bootstrap_email or "").strip().lower()
    has_credentials = bool(email_norm and bootstrap_password)
    created = False

    try:
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.cursor()

        if not has_credentials:
            # Preserve safe legacy behavior when no complete bootstrap
            # credential pair is configured: never create an account from
            # an email alone and never alter existing user roles.
            conn.commit()
            return False

        password_hash, salt = hash_password(bootstrap_password)
        row = cursor.execute(
            "SELECT email FROM auth_users WHERE lower(email) = ?",
            (email_norm,),
        ).fetchone()

        if row:
            cursor.execute(
                "UPDATE auth_users SET email = ?, name = 'CHRISHEM', "
                "password_hash = ?, salt = ?, role = 'admin' "
                "WHERE lower(email) = ?",
                (email_norm, password_hash, salt, email_norm),
            )
        else:
            cursor.execute(
                "INSERT INTO auth_users (email, name, password_hash, salt, role) "
                "VALUES (?, ?, ?, ?, ?)",
                (email_norm, "CHRISHEM", password_hash, salt, "admin"),
            )
            created = True

        conn.commit()
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise

    # Keep the designated administrator's subscription override synchronized
    # whether the account was newly created or recovered/promoted.
    admin_override_plan("system:bootstrap", email_norm, "pro", "comp")
    return created
