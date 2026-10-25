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

def test_supabase_identity_never_uses_legacy_email_admin_mapping():
    assert adapter.may_use_legacy_admin_email_lookup(
        {"auth_provider": "supabase", "role": "user"}, enabled=True
    ) is False


def test_legacy_admin_lookup_remains_available_when_supabase_mode_is_off():
    assert adapter.may_use_legacy_admin_email_lookup(
        {"auth_provider": "supabase", "role": "user"}, enabled=False
    ) is True


def test_legacy_identity_keeps_existing_admin_lookup_path():
    assert adapter.may_use_legacy_admin_email_lookup(
        {"email": "admin@example.com", "role": "admin"}, enabled=True
    ) is True


def test_admin_allowlist_is_empty_by_default(monkeypatch):
    monkeypatch.delenv("SUPABASE_ADMIN_USER_IDS", raising=False)
    assert adapter.configured_supabase_admin_ids() == set()
    assert adapter.supabase_role_for_user("11111111-1111-4111-8111-111111111111", True) == "user"


def test_only_exact_verified_uuid_in_server_allowlist_gets_admin():
    admin_id = "11111111-1111-4111-8111-111111111111"
    other_id = "22222222-2222-4222-8222-222222222222"
    assert adapter.supabase_role_for_user(admin_id, True, {admin_id}) == "admin"
    assert adapter.supabase_role_for_user(other_id, True, {admin_id}) == "user"


def test_uuid_allowlist_matching_is_case_and_whitespace_normalized():
    admin_id = "11111111-1111-4111-8111-111111111111"
    assert adapter.supabase_role_for_user(f" {admin_id.upper()} ", True, {admin_id}) == "admin"


def test_disabled_supabase_mode_never_assigns_admin_from_allowlist():
    admin_id = "11111111-1111-4111-8111-111111111111"
    assert adapter.supabase_role_for_user(admin_id, False, {admin_id}) == "user"


def test_current_user_clears_session_on_unexpected_client_error(monkeypatch):
    state = FakeState({
        adapter.SESSION_TOKEN_KEY: "token",
        adapter.SESSION_USER_KEY: {"id": "stale-user", "email": "stale@example.com"},
    })
    monkeypatch.setattr(adapter.st, "session_state", state)

    def broken(_token):
        raise RuntimeError("unexpected network/client error")

    monkeypatch.setattr(adapter, "verify_access_token", broken)
    assert adapter.current_supabase_user() is None
    assert adapter.SESSION_TOKEN_KEY not in state
    assert adapter.SESSION_USER_KEY not in state
