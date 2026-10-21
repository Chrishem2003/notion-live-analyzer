from __future__ import annotations

import sqlite3
import threading

from modules.bootstrap_admin import ensure_bootstrap_admin_record


def _connect(path):
    conn = sqlite3.connect(path, timeout=10)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS auth_users ("
        "email TEXT PRIMARY KEY, name TEXT, password_hash TEXT, salt TEXT, role TEXT)"
    )
    conn.commit()
    return conn


def _hash_password(password):
    return f"hash:{password}", "test-salt"


def test_concurrent_bootstrap_creates_one_admin(tmp_path):
    db_path = tmp_path / "auth.sqlite3"
    _connect(db_path).close()
    barrier = threading.Barrier(2)
    overrides = []
    errors = []

    def worker():
        conn = sqlite3.connect(db_path, timeout=10)
        try:
            barrier.wait(timeout=5)
            ensure_bootstrap_admin_record(
                conn,
                " ADMIN@EXAMPLE.COM ",
                "strong-test-password",
                _hash_password,
                lambda *args: overrides.append(args),
            )
        except Exception as exc:
            errors.append(exc)
        finally:
            conn.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)

    assert not errors
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT email, role FROM auth_users").fetchall()
    conn.close()
    assert rows == [("admin@example.com", "admin")]
    assert len(overrides) == 2


def test_missing_bootstrap_credentials_do_not_create_user(tmp_path):
    conn = _connect(tmp_path / "auth.sqlite3")
    created = ensure_bootstrap_admin_record(
        conn, "admin@example.com", None, _hash_password, lambda *args: None
    )
    assert created is False
    assert conn.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0] == 0
    conn.close()


def test_bootstrap_admin_is_created_even_when_regular_users_exist(tmp_path):
    conn = _connect(tmp_path / "auth.sqlite3")
    conn.execute(
        "INSERT INTO auth_users (email, name, password_hash, salt, role) "
        "VALUES (?, ?, ?, ?, ?)",
        ("researcher@example.com", "Researcher", "hash", "salt", "user"),
    )
    conn.commit()

    created = ensure_bootstrap_admin_record(
        conn, "admin@example.com", "strong-test-password", _hash_password, lambda *args: None
    )
    rows = conn.execute("SELECT email, role FROM auth_users ORDER BY email").fetchall()
    assert created is True
    assert rows == [("admin@example.com", "admin"), ("researcher@example.com", "user")]
    conn.close()


def test_existing_designated_user_is_promoted_and_password_reset(tmp_path):
    conn = _connect(tmp_path / "auth.sqlite3")
    conn.execute(
        "INSERT INTO auth_users (email, name, password_hash, salt, role) "
        "VALUES (?, ?, ?, ?, ?)",
        ("chrishem242@gmail.com", "Chris", "old-hash", "old-salt", "user"),
    )
    conn.commit()
    overrides = []

    created = ensure_bootstrap_admin_record(
        conn,
        "CHRISHEM242@GMAIL.COM",
        "new-admin-password",
        _hash_password,
        lambda *args: overrides.append(args),
    )
    row = conn.execute(
        "SELECT email, name, password_hash, salt, role FROM auth_users"
    ).fetchone()

    assert created is False
    assert row == (
        "chrishem242@gmail.com", "CHRISHEM", "hash:new-admin-password", "test-salt", "admin"
    )
    assert len(overrides) == 1
    conn.close()


def test_existing_admin_password_is_synchronized_to_configured_secret(tmp_path):
    conn = _connect(tmp_path / "auth.sqlite3")
    conn.execute(
        "INSERT INTO auth_users (email, name, password_hash, salt, role) "
        "VALUES (?, ?, ?, ?, ?)",
        ("admin@example.com", "Admin", "old-hash", "old-salt", "admin"),
    )
    conn.commit()

    ensure_bootstrap_admin_record(
        conn, "admin@example.com", "configured-password", _hash_password, lambda *args: None
    )
    row = conn.execute(
        "SELECT password_hash, salt, role FROM auth_users WHERE email = ?",
        ("admin@example.com",),
    ).fetchone()
    assert row == ("hash:configured-password", "test-salt", "admin")
    conn.close()
