"""
modules/billing_stripe.py
Real Stripe Checkout integration. Reads keys from environment variables —
never hardcode a secret key in source. The setup script writes a
D:\\ChrishemHub\\.env.example you copy to .env and fill in.

This does NOT try to guess your pricing — set STRIPE_PRICE_ID to a Price
you create in the Stripe Dashboard first.
"""

import os
import streamlit as st

try:
    import stripe
    STRIPE_SDK_AVAILABLE = True
except ImportError:
    STRIPE_SDK_AVAILABLE = False

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:8501")

if STRIPE_SDK_AVAILABLE and STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


def is_configured() -> bool:
    return STRIPE_SDK_AVAILABLE and bool(STRIPE_SECRET_KEY) and bool(STRIPE_PRICE_ID)


def create_checkout_session(customer_email: str):
    """Returns a Stripe Checkout URL, or None if not configured."""
    if not is_configured():
        return None
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer_email=customer_email,
        line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
        success_url=f"{APP_BASE_URL}/?checkout=success",
        cancel_url=f"{APP_BASE_URL}/?checkout=cancelled",
    )
    return session.url


def render_upgrade_button(customer_email: str):
    """Drop-in replacement for the placeholder button in subscription.py."""
    if not is_configured():
        st.info(
            "Payments aren't wired up yet. Set STRIPE_SECRET_KEY and STRIPE_PRICE_ID "
            "(see D:\\ChrishemHub\\.env.example) to enable real checkout."
        )
        return
    url = create_checkout_session(customer_email)
    if url:
        st.link_button("💳 Continue to Payment", url, type="primary")
    else:
        st.error("Could not create a checkout session. Check your Stripe configuration.")


def handle_webhook_event(payload: bytes, sig_header: str):
    """
    Call this from a small separate webhook receiver (Stripe posts here, not
    through Streamlit — Streamlit isn't a real HTTP API server). A minimal
    FastAPI/Flask receiver is the right shape; see webhook_server_example.py.
    On 'checkout.session.completed' or 'invoice.paid', call:
        from modules.subscription import get_conn
        conn = get_conn()
        conn.execute("UPDATE subscriptions SET plan='active' WHERE email=?", (email,))
    """
    if not STRIPE_WEBHOOK_SECRET:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET not configured.")
    event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    return event
