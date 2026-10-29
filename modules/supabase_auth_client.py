"""Supabase Auth client for staged migration away from ephemeral SQLite accounts.

The opt-in Shared AI workspace uses this adapter behind a feature flag. It uses only
the public/publishable Supabase key, never a service-role key. Access tokens
must be kept in the user's server-side Streamlit session and must not be logged.
"""
from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

import requests


class SupabaseAuthError(RuntimeError):
    """Safe, user-displayable authentication failure."""


def _configuration() -> tuple[str, str]:
    base_url = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    public_key = (
        os.getenv("SUPABASE_PUBLISHABLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
        or ""
    ).strip()

    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise SupabaseAuthError("Supabase Auth is not configured with a valid HTTPS URL.")
    if not public_key:
        raise SupabaseAuthError("Supabase Auth is not configured with a public client key.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise SupabaseAuthError("Supabase URL configuration is invalid.")
    return base_url, public_key


def _request(
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    access_token: str | None = None,
    timeout: float = 8.0,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    base_url, public_key = _configuration()
    headers = {
        "apikey": public_key,
        "Content-Type": "application/json",
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    client = session or requests
    try:
        response = client.request(
            method,
            f"{base_url}/auth/v1/{path.lstrip('/')}",
            json=payload,
            headers=headers,
            timeout=timeout,
        )
    except requests.RequestException:
        raise SupabaseAuthError("Supabase Auth could not be reached. Please try again.") from None

    if response.status_code >= 400:
        # Do not expose provider payloads: they can contain internal details.
        if response.status_code in (400, 401, 403):
            raise SupabaseAuthError("Sign-in details were not accepted or the account is not available.")
        if response.status_code == 429:
            raise SupabaseAuthError("Too many authentication attempts. Please wait and try again.")
        raise SupabaseAuthError("Authentication service is temporarily unavailable.")

    try:
        data = response.json()
    except ValueError:
        raise SupabaseAuthError("Authentication service returned an invalid response.") from None
    if not isinstance(data, dict):
        raise SupabaseAuthError("Authentication service returned an invalid response.")
    return data


def sign_in_with_password(
    email: str,
    password: str,
    *,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Authenticate an account and return minimal identity plus its access token."""
    email = (email or "").strip().lower()
    if not email or len(email) > 254 or "@" not in email:
        raise SupabaseAuthError("Enter a valid email address.")
    if not password:
        raise SupabaseAuthError("Enter your password.")

    data = _request(
        "POST",
        "token?grant_type=password",
        payload={"email": email, "password": password},
        session=session,
    )
    access_token = data.get("access_token")
    user = data.get("user")
    if not isinstance(access_token, str) or not access_token or not isinstance(user, dict):
        raise SupabaseAuthError("Authentication succeeded without a usable session.")
    user_id = user.get("id")
    verified_email = user.get("email")
    if not isinstance(user_id, str) or not user_id or not isinstance(verified_email, str):
        raise SupabaseAuthError("Authentication service returned an incomplete identity.")
    return {
        "access_token": access_token,
        "user": {"id": user_id, "email": verified_email.lower()},
        "expires_in": data.get("expires_in"),
        "token_type": data.get("token_type", "bearer"),
    }


def sign_up_with_password(
    email: str,
    password: str,
    *,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Create an ordinary Supabase Auth account; never assigns platform roles."""
    email = (email or "").strip().lower()
    if not email or len(email) > 254 or "@" not in email:
        raise SupabaseAuthError("Enter a valid email address.")
    if len(password or "") < 8:
        raise SupabaseAuthError("Use a password with at least 8 characters.")

    data = _request(
        "POST",
        "signup",
        payload={"email": email, "password": password},
        session=session,
    )
    user = data.get("user")
    if not isinstance(user, dict):
        raise SupabaseAuthError("Account creation did not return a user record.")
    # Supabase may require email confirmation; in that case no access token is
    # present and the caller must show a confirmation-needed state, not log in.
    token = data.get("access_token")
    return {
        "user": {
            "id": user.get("id"),
            "email": (user.get("email") or email).lower(),
        },
        "access_token": token if isinstance(token, str) and token else None,
        "confirmation_required": not (isinstance(token, str) and bool(token)),
    }


def verify_access_token(
    access_token: str,
    *,
    session: requests.Session | None = None,
) -> dict[str, str]:
    """Validate a bearer token with Supabase Auth; never trust decoded JWT claims alone."""
    if not isinstance(access_token, str) or not access_token.strip():
        raise SupabaseAuthError("Your session has expired. Please sign in again.")
    data = _request("GET", "user", access_token=access_token.strip(), session=session)
    user_id = data.get("id")
    email = data.get("email")
    if not isinstance(user_id, str) or not user_id or not isinstance(email, str) or not email:
        raise SupabaseAuthError("Supabase did not confirm a complete user identity.")
    return {"id": user_id, "email": email.lower()}
