from __future__ import annotations

from modules import supabase_auth_streamlit as adapter


class FakeState(dict):
    def pop(self, key, default=None):
        return super().pop(key, default)


def test_adapter_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("SUPABASE_AUTH_ENABLED", raising=False)
    assert adapter._enabled() is False


def test_adapter_flag_accepts_explicit_true(monkeypatch):
    monkeypatch.setenv("SUPABASE_AUTH_ENABLED", "true")
    assert adapter._enabled() is True


def test_logout_clears_token_and_identity(monkeypatch):
    state = FakeState({
        adapter.SESSION_TOKEN_KEY: "secret-token",
        adapter.SESSION_USER_KEY: {"id": "user-1", "email": "one@example.com"},
    })
    monkeypatch.setattr(adapter.st, "session_state", state)
    adapter.logout_supabase_user()
    assert adapter.SESSION_TOKEN_KEY not in state
    assert adapter.SESSION_USER_KEY not in state


def test_current_user_clears_expired_or_invalid_session(monkeypatch):
    state = FakeState({
        adapter.SESSION_TOKEN_KEY: "expired-token",
        adapter.SESSION_USER_KEY: {"id": "stale-user", "email": "stale@example.com"},
    })
    monkeypatch.setattr(adapter.st, "session_state", state)

    def invalid(_token):
        raise adapter.SupabaseAuthError("session expired")

    monkeypatch.setattr(adapter, "verify_access_token", invalid)
    assert adapter.current_supabase_user() is None
    assert adapter.SESSION_TOKEN_KEY not in state
    assert adapter.SESSION_USER_KEY not in state


def test_current_user_returns_remote_verified_identity(monkeypatch):
    state = FakeState({adapter.SESSION_TOKEN_KEY: "valid-token"})
    monkeypatch.setattr(adapter.st, "session_state", state)
    monkeypatch.setattr(
        adapter,
        "verify_access_token",
        lambda token: {"id": "user-2", "email": "two@example.com"},
    )
    result = adapter.current_supabase_user()
    assert result == {"id": "user-2", "email": "two@example.com"}
    assert state[adapter.SESSION_USER_KEY] == result
