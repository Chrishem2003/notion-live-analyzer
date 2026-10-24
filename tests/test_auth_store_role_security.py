from __future__ import annotations

import sqlite3
import threading

import modules.auth_store as auth_store


def test_public_registration_cannot_select_privileged_role(tmp_path, monkeypatch):
    monkeypatch.setattr(auth_store, "DB_PATH", str(tmp_path / "auth.sqlite3"))

    result = auth_store.create_user("ordinary@example.com", "Ordinary", "correct horse battery", role="admin")

    assert result["ok"] is True
    assert auth_store.get_role("ordinary@example.com") == "user"
    logged_in = auth_store.verify_login("ordinary@example.com", "correct horse battery")
    assert logged_in is not None
    assert logged_in["role"] == "user"


def test_email_address_does_not_auto_elevate_account(tmp_path, monkeypatch):
    monkeypatch.setattr(auth_store, "DB_PATH", str(tmp_path / "auth.sqlite3"))
    email = "chrishem242@gmail.com"

    assert auth_store.create_user(email, "New Account", "user-controlled-password")["ok"] is True
    assert auth_store.get_role(email) == "user"
    assert auth_store.verify_login(email, "user-controlled-password")["role"] == "user"


def test_bootstrap_admin_is_single_use_and_explicit(tmp_path, monkeypatch):
    monkeypatch.setattr(auth_store, "DB_PATH", str(tmp_path / "auth.sqlite3"))

    first = auth_store.bootstrap_first_admin("admin@example.com", "Administrator", "strong-admin-password")
    second = auth_store.bootstrap_first_admin("second@example.com", "Second", "another-strong-password")

    assert first["ok"] is True
    assert second["ok"] is False
    assert auth_store.verify_login("admin@example.com", "strong-admin-password")["role"] == "admin"
    assert auth_store.get_role("second@example.com") == "user"


def test_concurrent_bootstrap_creates_at_most_one_admin(tmp_path, monkeypatch):
    db_path = str(tmp_path / "auth.sqlite3")
    monkeypatch.setattr(auth_store, "DB_PATH", db_path)
    # Initialize the schema before threads contend for the bootstrap lock.
    auth_store.get_conn().close()
    barrier = threading.Barrier(2)
    results = []
    errors = []

    def worker(email):
        try:
            barrier.wait(timeout=5)
            results.append(auth_store.bootstrap_first_admin(email, "Administrator", "strong-admin-password"))
        except Exception as exc:
            errors.append(exc)

    threads = [
        threading.Thread(target=worker, args=("admin-one@example.com",)),
        threading.Thread(target=worker, args=("admin-two@example.com",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)

    assert not errors
    assert all(not thread.is_alive() for thread in threads)
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT email, role FROM auth_users ORDER BY email").fetchall()
    finally:
        conn.close()
    assert len(rows) == 1
    assert rows[0][1] == "admin"
    assert sum(bool(result.get("ok")) for result in results) == 1

def test_streamlit_signup_does_not_persist_caller_selected_role():
    """Guard the separate AuthStore implementation in app.py against role regressions."""
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    method_start = source.index('    def create_user(self, email, name, password, role="user"):')
    method_end = source.index("    def get_or_create_oauth_user(", method_start)
    method = source[method_start:method_end]

    assert 'pwd_hash, salt, "user"' in method
    assert "pwd_hash, salt, role" not in method
