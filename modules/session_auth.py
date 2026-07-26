"""Streamlit glue for accounts: session, sign-in UI and feature gates.

Keeps every Streamlit dependency out of :mod:`modules.accounts` and
:mod:`modules.billing`, which stay importable from tests and webhook handlers.
"""
from __future__ import annotations

from typing import Callable, Optional

import streamlit as st

from modules.accounts import (
    AccountError,
    SQLiteAccountStore,
    Tier,
    User,
    authenticate,
    get_store,
    register,
    storage_is_durable,
)
from modules.billing import (
    FEATURE_LABELS,
    PLANS,
    UNLIMITED,
    Entitlement,
    check_access,
    plan_for_user,
)
from modules.eligibility import country_choices, evaluate

SESSION_USER_KEY = "_account_user_id"


@st.cache_resource(show_spinner=False)
def _store() -> SQLiteAccountStore:
    """One store per process — it holds a connection factory, not user state."""
    return get_store()


def store() -> SQLiteAccountStore:
    return _store()


def current_user(refresh: bool = False) -> Optional[User]:
    """The signed-in user, re-read from the store so tier changes take effect."""
    user_id = st.session_state.get(SESSION_USER_KEY)
    if not user_id:
        return None
    cached = st.session_state.get("_account_user_obj")
    if cached is not None and not refresh and cached.id == user_id:
        return cached
    user = store().get_user(user_id)
    st.session_state["_account_user_obj"] = user
    if user is None:
        st.session_state.pop(SESSION_USER_KEY, None)
    return user


def sign_in(user: User) -> None:
    st.session_state[SESSION_USER_KEY] = user.id
    st.session_state["_account_user_obj"] = user


def sign_out() -> None:
    st.session_state.pop(SESSION_USER_KEY, None)
    st.session_state.pop("_account_user_obj", None)


def is_admin() -> bool:
    user = current_user()
    return bool(user and user.is_admin)


# ═══════════════════════════════════════════════════════════════════════
# Gating
# ═══════════════════════════════════════════════════════════════════════
ANON_USAGE_KEY = "_anon_usage"


def entitlement(feature: str) -> Entitlement:
    """Entitlement for the current visitor, signed in or not.

    Anonymous visitors get the Free plan, metered per browser session. That is
    weaker than a server-side count — clearing the session resets it — but it
    keeps the app usable without an account while still nudging heavy users to
    sign in, and no anonymous visitor can exceed Free limits in one sitting.
    """
    user = current_user()
    if user is not None:
        return check_access(user, feature, store())

    plan = PLANS[Tier.FREE]
    limit = plan.quota(feature)
    if feature in plan.features and limit == 0:
        return Entitlement(True, limit=UNLIMITED)
    if limit == 0:
        return check_access(None, feature, store())

    used = st.session_state.get(ANON_USAGE_KEY, {}).get(feature, 0)
    if used >= limit:
        return Entitlement(
            False,
            f"You've used the {limit} free {FEATURE_LABELS.get(feature, feature).lower()} "
            "available without an account. Sign in to keep going.",
            used=used,
            limit=limit,
            required_tier=Tier.STANDARD,
        )
    return Entitlement(True, used=used, limit=limit)


def consume(feature: str) -> Entitlement:
    """Record one use for the current visitor. Raises when out of allowance."""
    result = entitlement(feature)
    if not result.allowed:
        raise AccountError(result.reason)

    user = current_user()
    if user is not None:
        if result.limit != UNLIMITED:
            store().record_usage(user.id, feature)
        return result

    if result.limit != UNLIMITED:
        usage = dict(st.session_state.get(ANON_USAGE_KEY, {}))
        usage[feature] = usage.get(feature, 0) + 1
        st.session_state[ANON_USAGE_KEY] = usage
    return result


def require(feature: str, *, stop: bool = True) -> Entitlement:
    """Gate a page or block on a feature, rendering an upgrade prompt if denied.

    ``require("audit_check")`` at the top of a page is the whole integration;
    pass ``stop=False`` to gate part of a page instead of the whole thing.
    """
    result = entitlement(feature)
    if result.allowed:
        return result

    st.warning(result.reason)
    if result.required_tier:
        plan = PLANS[result.required_tier]
        st.page_link(
            "pages/48_💳_Pricing.py",
            label=f"View the {plan.name} plan — ${plan.price_usd:.0f}/month",
            icon="💳",
        )
    if stop:
        st.stop()
    return result


def gated(feature: str) -> Callable:
    """Decorator form of :func:`require` for page render functions."""

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            require(feature)
            return func(*args, **kwargs)

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator


# ═══════════════════════════════════════════════════════════════════════
# UI
# ═══════════════════════════════════════════════════════════════════════
def render_storage_warning() -> None:
    if not storage_is_durable():
        st.info(
            "🗄️ Accounts are stored in a local SQLite file. On hosted Streamlit "
            "the container filesystem resets on redeploy — set `SUPABASE_URL` and "
            "`SUPABASE_SERVICE_KEY` to persist them.",
            icon="ℹ️",
        )


def render_sign_in_form() -> Optional[User]:
    with st.form("sign_in"):
        email = st.text_input("Email", key="signin_email")
        password = st.text_input("Password", type="password", key="signin_password")
        submitted = st.form_submit_button("Sign in", type="primary")
    if not submitted:
        return None
    try:
        user = authenticate(store(), email, password)
    except AccountError as exc:
        st.error(str(exc))
        return None
    sign_in(user)
    st.success(f"Signed in as {user.email}")
    return user


def render_sign_up_form() -> Optional[User]:
    choices = country_choices()
    with st.form("sign_up"):
        email = st.text_input("Email", key="signup_email")
        st.caption("Using a university address (….ac.ug, ….edu) unlocks sponsored access.")
        password = st.text_input("Password", type="password", key="signup_password")
        country = st.selectbox(
            "Country",
            options=[code for code, _ in choices] + ["--"],
            format_func=lambda code: dict(choices).get(code, "Other / not listed"),
            index=len(choices),
            key="signup_country",
        )
        submitted = st.form_submit_button("Create account", type="primary")
    if not submitted:
        return None

    country_code = None if country == "--" else country
    try:
        user = register(store(), email, password, country=country_code)
    except AccountError as exc:
        st.error(str(exc))
        return None

    sign_in(user)
    st.success(f"Account created — your {PLANS[Tier.STANDARD].name} trial is running.")

    decision = evaluate(email, country_code)
    if decision.eligible:
        from dataclasses import replace

        user = store().save_user(
            replace(user, student_verified=True, institution=decision.institution_domain)
        )
        sign_in(user)
        st.success(decision.reason)
    return user


def render_account_badge() -> None:
    """Compact account state for the sidebar."""
    user = current_user()
    if user is None:
        st.caption("Not signed in — running on the Free plan.")
        st.page_link("pages/47_👤_Account.py", label="Sign in", icon="👤")
        return

    plan = plan_for_user(user)
    st.caption(f"👤 {user.email}")
    badge = plan.name
    if user.trial_active():
        badge += f" · trial, {user.trial_days_left()}d left"
    elif user.subscription_active():
        badge += f" · renews {user.subscription_ends_at:%d %b}"
    st.caption(f"🎟️ {badge}")
