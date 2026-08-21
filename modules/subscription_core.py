"""
subscription_core.py  pure, dependency-light trial/subscription/access logic.

This module is the SINGLE source of truth for "can this user use paid
features?". It has no Streamlit/UI importing at module import time (the
Streamlit helpers import streamlit lazily inside the function), so it can be
unit tested in isolation and imported by any page.

Adapted from the UPGRADE_BRIEF addendum reference implementation. The payment
provider layer is behind an interface so you can start with one provider
(e.g. Flutterwave) and swap/add others without rewriting business logic.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Callable, Optional


TRIAL_LENGTH_DAYS = 15  # one constant, referenced everywhere â€” never hardcoded


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"


class SubStatus(str, Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELED = "canceled"


@dataclass
class User:
    id: str
    email: str
    password_hash: str
    role: Role = Role.USER
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Subscription:
    user_id: str
    status: SubStatus
    trial_started_at: datetime
    trial_ends_at: datetime
    current_period_end: Optional[datetime] = None
    provider_customer_id: Optional[str] = None
    provider_subscription_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Password hashing (delegates to security_config's scrypt hasher)
# ---------------------------------------------------------------------------

def hash_password(plaintext: str) -> str:
    """Hash a password. Backed by modules.security_config (stdlib scrypt)."""
    from modules.security_config import hash_password as _h
    return _h(plaintext)


def verify_password(plaintext: str, password_hash: str) -> bool:
    """Verify a password. Backed by modules.security_config."""
    from modules.security_config import verify_password as _v
    return _v(plaintext, password_hash)


# ---------------------------------------------------------------------------
# Trial / access logic
# ---------------------------------------------------------------------------

def start_trial(user_id: str) -> Subscription:
    """Create a new trial subscription starting now."""
    now = datetime.now(timezone.utc)
    return Subscription(
        user_id=user_id,
        status=SubStatus.TRIAL,
        trial_started_at=now,
        trial_ends_at=now + timedelta(days=TRIAL_LENGTH_DAYS),
    )


def activate_subscription(
    user_id: str,
    trial_started_at: Optional[datetime] = None,
    current_period_end: Optional[datetime] = None,
    provider_customer_id: Optional[str] = None,
    provider_subscription_id: Optional[str] = None,
) -> Subscription:
    """Create/lift a subscription to ACTIVE (e.g. after a successful webhook)."""
    now = datetime.now(timezone.utc)
    return Subscription(
        user_id=user_id,
        status=SubStatus.ACTIVE,
        trial_started_at=trial_started_at or now,
        trial_ends_at=now + timedelta(days=TRIAL_LENGTH_DAYS),
        current_period_end=current_period_end,
        provider_customer_id=provider_customer_id,
        provider_subscription_id=provider_subscription_id,
    )


def has_access(sub: Optional[Subscription]) -> bool:
    """The single source of truth for paid-feature access.

    ``has_access = sub.status == ACTIVE OR now < sub.trial_ends_at``.
    Call this everywhere access is gated. Never duplicate this check.
    """
    if sub is None:
        return False
    now = datetime.now(timezone.utc)
    if sub.status == SubStatus.ACTIVE:
        return True
    if sub.status == SubStatus.TRIAL and now < sub.trial_ends_at:
        return True
    return False


def needs_payment(sub: Optional[Subscription]) -> bool:
    """True when the user has no active access and should be prompted to pay."""
    return not has_access(sub)


def days_left_in_trial(sub: Optional[Subscription]) -> int:
    """Remaining whole days in a trial (0 if not on trial or expired)."""
    if sub is None or sub.status != SubStatus.TRIAL:
        return 0
    delta = sub.trial_ends_at - datetime.now(timezone.utc)
    return max(0, delta.days)


# ---------------------------------------------------------------------------
# Streamlit-style gating helpers (import streamlit lazily)
# ---------------------------------------------------------------------------

def require_access(user: User, get_subscription_fn: Callable[[str], Optional[Subscription]]):
    """Call at the TOP of every gated Streamlit page, before real logic runs.

    Returns the subscription if access is granted; otherwise shows a warning
    and calls ``st.stop()`` so the rest of the page does not execute.
    """
    import streamlit as st  # lazy so this module stays importable without streamlit

    sub = get_subscription_fn(user.id)
    if not has_access(sub):
        st.warning(
            "Your 15-day trial has ended. Subscribe to keep using this feature."
        )
        if st.button("Subscribe now"):
            # Adapt: point to your actual subscribe page/route.
            st.switch_page("pages/1_ðŸ“_File_Analyzer.py")  # placeholder
        st.stop()
    return sub


def require_admin(user: User):
    """Call at the TOP of every admin-only Streamlit page."""
    import streamlit as st

    if user.role != Role.ADMIN:
        st.error("You don't have access to this page.")
        st.stop()


# ---------------------------------------------------------------------------
# Payment provider interface  swap implementations without touching logic
# ---------------------------------------------------------------------------

class PaymentProvider:
    """Abstract interface. Implement one concrete class per provider
    (e.g. FlutterwaveProvider, PesapalProvider) so business logic never
    calls a provider SDK directly."""

    def create_checkout_session(self, user: User, plan_id: str) -> str:
        """Return a URL to redirect the user to for payment."""
        raise NotImplementedError

    def cancel_subscription(self, provider_subscription_id: str) -> None:
        raise NotImplementedError


class FlutterwaveProvider(PaymentProvider):
    """Stub Flutterwave implementation to make the interface concrete.

    Wire the real API calls (checkout creation, webhook verification) here
    using requests and credentials from the environment. Never hardcode keys.
    """

    def __init__(self, public_key: Optional[str] = None):
        # In production resolve from env: os.environ["FLUTTERWAVE_PUBLIC_KEY"]
        self.public_key = public_key or os.environ.get("FLUTTERWAVE_PUBLIC_KEY", "")

    def create_checkout_session(self, user: User, plan_id: str) -> str:
        if not self.public_key:
            raise RuntimeError("Flutterwave public key not configured")
        # Replace with a real Flutterwave checkout request.
        return f"https://checkout.example.com/{plan_id}}?customer={user.email}}"

    def cancel_subscription(self, provider_subscription_id: str) -> None:
        if not self.public_key:
            raise RuntimeError("Flutterwave public key not configured")


# ---------------------------------------------------------------------------
# Webhook verification  this is what actually updates subscription status.
# Never trust a client-side "payment succeeded" redirect on its own.
# ---------------------------------------------------------------------------

def verify_and_handle_webhook(
    raw_body: bytes,
    signature_header: str,
    webhook_secret: str,
    update_subscription_fn: Callable[..., None],
) -> bool:
    """Verify an HMAC-signed webhook and, if valid, apply the update.

    This is a generic HMAC-SHA256 shape. Providers differ (header name,
    algorithm, payload envelope) â€” adapt to the chosen provider's docs and
    pass the correct secret. Returns True only when the signature matched.
    """
    if not webhook_secret:
        return False
    expected_sig = hmac.new(
        webhook_secret.encode(), raw_body, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, signature_header):
        return False  # reject: signature mismatch, do not trust this payload

    # Parse raw_body per your provider's payload shape, then e.g.:
    # update_subscription_fn(user_id=..., status=SubStatus.ACTIVE, ...)
    update_subscription_fn(raw_body=raw_body)
    return True


# ---------------------------------------------------------------------------
# Admin seed (delegates to security_config)  convenience re-export
# ---------------------------------------------------------------------------

def seed_admin_if_needed(get_user_by_email_fn, create_user_fn):
    """Convenience wrapper around security_config.seed_admin_if_needed."""
    from modules.security_config import seed_admin_if_needed as _seed
    return _seed(get_user_by_email_fn, create_user_fn)

