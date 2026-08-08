"""
modules/subscription.py
15-day free trial, paid plan gate, and free-tier for verified students.

This module never trusts anything from st.session_state as the source of
truth for entitlement — it always re-checks against the DB row for the
logged-in user's email. session_state is only a display cache.
"""

import sqlite3
import datetime
import streamlit as st

DB_PATH = "sovereign_apex_engine.db"
TRIAL_DAYS = 15


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            email TEXT PRIMARY KEY,
            trial_started TEXT,
            plan TEXT DEFAULT 'trial',           -- trial | active | expired | student_free
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            renews_at TEXT
        )
    """)
    conn.commit()
    return conn


def ensure_trial_started(email: str):
    conn = get_conn()
    row = conn.execute("SELECT email FROM subscriptions WHERE email=?", (email,)).fetchone()
    if not row:
        conn.execute(
            "INSERT INTO subscriptions (email, trial_started, plan) VALUES (?,?,?)",
            (email, datetime.datetime.utcnow().isoformat(), "trial"),
        )
        conn.commit()
    conn.close()


def get_status(email: str) -> dict:
    """
    Returns {'plan': ..., 'days_left': int|None, 'active': bool}
    plan values: trial, active, expired, student_free
    """
    conn = get_conn()
    row = conn.execute(
        "SELECT trial_started, plan, renews_at FROM subscriptions WHERE email=?", (email,)
    ).fetchone()
    conn.close()

    if not row:
        return {"plan": "no_account", "days_left": None, "active": False}

    trial_started, plan, renews_at = row

    if plan == "student_free":
        return {"plan": "student_free", "days_left": None, "active": True}

    if plan == "active":
        return {"plan": "active", "days_left": None, "active": True}

    # trial or expired: compute live from trial_started
    started = datetime.datetime.fromisoformat(trial_started)
    elapsed = (datetime.datetime.utcnow() - started).days
    days_left = TRIAL_DAYS - elapsed
    if days_left > 0:
        return {"plan": "trial", "days_left": days_left, "active": True}
    else:
        # flip to expired in the DB so admin views are accurate
        conn = get_conn()
        conn.execute("UPDATE subscriptions SET plan='expired' WHERE email=?", (email,))
        conn.commit()
        conn.close()
        return {"plan": "expired", "days_left": 0, "active": False}


def grant_student_free(email: str):
    """Call ONLY after admin/verification approval — see modules/verification.py."""
    conn = get_conn()
    conn.execute(
        "INSERT INTO subscriptions (email, trial_started, plan) VALUES (?,?,?) "
        "ON CONFLICT(email) DO UPDATE SET plan='student_free'",
        (email, datetime.datetime.utcnow().isoformat(), "student_free"),
    )
    conn.commit()
    conn.close()


def require_active_subscription():
    """
    Call at the top of any hub page's main(). Blocks the page with an
    upgrade prompt if the user's trial/plan is not active. Real payment
    integration (Stripe Checkout) hooks into the 'Upgrade Now' button —
    see the TODO below.
    """
    identity = st.session_state.get("user_identity", {})
    email = identity.get("email")
    role = identity.get("role")

    if not email:
        st.error("You must be signed in to use this hub.")
        st.stop()

    if role == "admin":
        return  # admins are never paywalled

    ensure_trial_started(email)
    status = get_status(email)

    if status["active"]:
        if status["plan"] == "trial" and status["days_left"] is not None and status["days_left"] <= 3:
            st.warning(f"⏳ Your free trial ends in {status['days_left']} day(s). Upgrade to keep access.")
        return

    st.error("🔒 Your free trial has ended. Upgrade to continue using this hub.")
    st.markdown(
        "Choose a plan, or apply for the **free student tier** "
        "(requires institution ID + verification review) in your account settings."
    )
    from modules import billing_stripe
    billing_stripe.render_upgrade_button(email)
    st.stop()
