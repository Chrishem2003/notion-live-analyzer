from __future__ import annotations

import requests
import pytest

from modules import supabase_auth_client as auth


class FakeResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data or {}

    def json(self):
        return self._data


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.response


@pytest.fixture(autouse=True)
def auth_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "public-test-key")
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)


def test_sign_in_returns_verified_identity_and_token():
    session = FakeSession(FakeResponse(data={
        "access_token": "opaque-test-token",
        "expires_in": 3600,
        "token_type": "bearer",
        "user": {"id": "user-123", "email": "TEST@example.com"},
    }))

    result = auth.sign_in_with_password(" TEST@example.com ", "long-password", session=session)

    assert result["access_token"] == "opaque-test-token"
    assert result["user"] == {"id": "user-123", "email": "test@example.com"}
    method, url, kwargs = session.calls[0]
    assert method == "POST"
    assert url == "https://example.supabase.co/auth/v1/token?grant_type=password"
    assert kwargs["headers"]["apikey"] == "public-test-key"
    assert kwargs["json"]["email"] == "test@example.com"
    assert kwargs["timeout"] <= 10


def test_token_verification_calls_supabase_user_endpoint():
    session = FakeSession(FakeResponse(data={
        "id": "user-456",
        "email": "Second@Example.com",
    }))

    result = auth.verify_access_token("access-token", session=session)

    assert result == {"id": "user-456", "email": "second@example.com"}
    method, url, kwargs = session.calls[0]
    assert method == "GET"
    assert url == "https://example.supabase.co/auth/v1/user"
    assert kwargs["headers"]["Authorization"] == "Bearer access-token"


def test_signup_does_not_grant_roles_and_handles_email_confirmation():
    session = FakeSession(FakeResponse(data={
        "user": {"id": "user-789", "email": "new@example.com"},
        "access_token": None,
    }))

    result = auth.sign_up_with_password("new@example.com", "long-password", session=session)

    assert result["user"] == {"id": "user-789", "email": "new@example.com"}
    assert result["access_token"] is None
    assert result["confirmation_required"] is True
    assert "role" not in result["user"]


@pytest.mark.parametrize("email,password", [
    ("", "long-password"),
    ("not-an-email", "long-password"),
    ("valid@example.com", ""),
])
def test_signin_rejects_invalid_inputs_without_network(email, password):
    session = FakeSession(FakeResponse(data={}))
    with pytest.raises(auth.SupabaseAuthError):
        auth.sign_in_with_password(email, password, session=session)
    assert session.calls == []


def test_signup_requires_minimum_password_length():
    session = FakeSession(FakeResponse(data={}))
    with pytest.raises(auth.SupabaseAuthError):
        auth.sign_up_with_password("valid@example.com", "short", session=session)
    assert session.calls == []


def test_auth_errors_do_not_leak_provider_response():
    session = FakeSession(FakeResponse(
        status_code=401,
        data={"message": "secret internal diagnostic"},
    ))
    with pytest.raises(auth.SupabaseAuthError) as exc:
        auth.sign_in_with_password("valid@example.com", "long-password", session=session)
    assert "secret internal diagnostic" not in str(exc.value)


def test_rejects_non_https_supabase_url(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "http://example.supabase.co")
    session = FakeSession(FakeResponse(data={}))
    with pytest.raises(auth.SupabaseAuthError):
        auth.verify_access_token("access-token", session=session)
    assert session.calls == []


def test_missing_public_key_fails_closed(monkeypatch):
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    session = FakeSession(FakeResponse(data={}))
    with pytest.raises(auth.SupabaseAuthError):
        auth.verify_access_token("access-token", session=session)
    assert session.calls == []
