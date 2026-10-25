"""Streamlit-facing adapter for the staged Supabase Auth migration.

This module is opt-in and is used only when SUPABASE_AUTH_ENABLED is true.
It deliberately has no fallback to local SQLite authentication: a Supabase
outage must never silently downgrade authentication.
"""
from __future__ import annotations

import os
import uuid
from typing import Any

import streamlit as st

from modules.supabase_auth_client import (
    SupabaseAuthError,
    sign_in_with_password,
    sign_up_with_password,
    verify_access_token,
)

SESSION_TOKEN_KEY = "_supabase_access_token"
SESSION_USER_KEY = "supabase_user"


def _enabled() -> bool:
    return os.getenv("SUPABASE_AUTH_ENABLED", "false").strip().lower() in {
        "1", "true", "yes", "on"
    }


def _normalize_uuid(value: str) -> str | None:
    """Return a canonical UUID string, rejecting arbitrary strings."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return str(uuid.UUID(value.strip()))
    except (ValueError, AttributeError, TypeError):
        return None


def configured_supabase_admin_ids(value: str | None = None) -> set[str]:
    """Parse a server-controlled allowlist, retaining valid UUIDs only.

    Never put emails or user-editable metadata in this allowlist. Empty or
    malformed configuration grants no administrator privileges.
    """
    raw = os.getenv("SUPABASE_ADMIN_USER_IDS", "") if value is None else value
    normalized = (_normalize_uuid(item) for item in raw.split(","))
    return {item for item in normalized if item is not None}


def supabase_role_for_user(user_id: str, enabled: bool, admin_ids: set[str] | None = None) -> str:
    """Resolve a role from a verified Supabase UUID and server allowlist."""
    normalized_user_id = _normalize_uuid(user_id)
    if not enabled or normalized_user_id is None:
        return "user"
    allowed_source = configured_supabase_admin_ids() if admin_ids is None else admin_ids
    allowed = {
        normalized for item in allowed_source
        if (normalized := _normalize_uuid(item)) is not None
    }
    return "admin" if normalized_user_id in allowed else "user"


def may_use_legacy_admin_email_lookup(identity: dict[str, Any], enabled: bool) -> bool:
    """Never use legacy email-based roles for a Supabase-authenticated session."""
    return not (enabled and identity.get("auth_provider") == "supabase")


def current_supabase_user() -> dict[str, str] | None:
    """Revalidate the current session token; clear invalid/expired sessions."""
    token = st.session_state.get(SESSION_TOKEN_KEY)
    if not token:
        st.session_state.pop(SESSION_USER_KEY, None)
        return None
    try:
        user = verify_access_token(token)
    except Exception:
        # Fail closed on network/client surprises too; never retain stale identity.
        st.session_state.pop(SESSION_TOKEN_KEY, None)
        st.session_state.pop(SESSION_USER_KEY, None)
        return None
    st.session_state[SESSION_USER_KEY] = user
    return user


def logout_supabase_user() -> None:
    """Clear access token and identity from the server-side Streamlit session."""
    st.session_state.pop(SESSION_TOKEN_KEY, None)
    st.session_state.pop(SESSION_USER_KEY, None)


def render_supabase_auth() -> dict[str, Any] | None:
    """Render opt-in sign-in/register UI and return verified identity on login.

    Returns None while signed out. This function does not assign roles or
    touch the legacy account database. Email-confirmation signup is displayed
    as a pending state rather than an authenticated session.
    """
    if not _enabled():
        st.error(
            "Supabase Auth adapter is not enabled. The legacy login has not "
            "been replaced; set SUPABASE_AUTH_ENABLED only after staging tests."
        )
        st.stop()

    existing_user = current_supabase_user()
    if existing_user:
        st.success(f"Shared AI identity verified: {existing_user['email']}")
        if st.button("Sign out of Shared AI", key="supabase_shared_ai_logout"):
            logout_supabase_user()
            st.rerun()
        return current_supabase_user()

    st.subheader("Secure account access")
    sign_in_tab, sign_up_tab = st.tabs(["Sign in", "Create account"])
    with sign_in_tab:
        email = st.text_input("Email address", key="supabase_signin_email")
        password = st.text_input(
            "Password", type="password", key="supabase_signin_password"
        )
        if st.button("Sign in securely", key="supabase_signin_submit"):
            try:
                session = sign_in_with_password(email, password)
                # Token stays in Streamlit's server-side session state only.
                st.session_state[SESSION_TOKEN_KEY] = session["access_token"]
                user = verify_access_token(session["access_token"])
                st.session_state[SESSION_USER_KEY] = user
                st.rerun()
            except SupabaseAuthError as exc:
                st.error(str(exc))

    with sign_up_tab:
        new_email = st.text_input("Email address", key="supabase_signup_email")
        new_password = st.text_input(
            "Password (at least 8 characters)",
            type="password",
            key="supabase_signup_password",
        )
        confirm = st.text_input(
            "Confirm password", type="password", key="supabase_signup_confirm"
        )
        if st.button("Create account", key="supabase_signup_submit"):
            if new_password != confirm:
                st.error("The passwords do not match.")
            else:
                try:
                    result = sign_up_with_password(new_email, new_password)
                    if result["confirmation_required"]:
                        st.success(
                            "Account request received. Check your email to confirm "
                            "the account, then return here to sign in."
                        )
                    else:
                        st.success("Account created. Please sign in to continue.")
                except SupabaseAuthError as exc:
                    st.error(str(exc))

    return current_supabase_user()
