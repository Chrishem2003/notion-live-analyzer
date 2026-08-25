﻿"""
Stripe billing integration.

This is the only honest way to do "real payments": a real processor. All
functions here either call the actual Stripe API or return None/False when
Stripe isn't configured -- there is no simulated "payment successful"
branch. `verify_checkout_session` re-fetches the session from Stripe's own
API (never trusts client-supplied query params) before granting access.

Required environment variables (set only what you need):
    STRIPE_SECRET_KEY
    STRIPE_PRICE_PREMIUM_MONTHLY, STRIPE_PRICE_PREMIUM_ANNUAL
    STRIPE_PRICE_PRO_MONTHLY, STRIPE_PRICE_PRO_ANNUAL
    APP_BASE_URL                 (e.g. https://your-deployed-app-url)
    STRIPE_WEBHOOK_SECRET        (optional but recommended -- see verify_webhook)

Architecture note: Streamlit has no native route to receive Stripe webhooks
(no `POST /webhook` endpoint). Two supported paths, both real:
  1. Checkout-return verification (implemented below, no extra service
     needed): after payment, Stripe redirects the browser back to
     APP_BASE_URL with ?session_id=...; the app verifies that session
     server-side via the Stripe API on load and updates the subscription.
     This covers new purchases and upgrades.
  2. For renewals, cancellations, and failed payments happening while the
     user isn't in the app, run `reconcile_subscription(email)` -- exposed
     to admins as a manual "Resync from Stripe" action, and safe to call on
     every login for premium/pro accounts. For fully automatic sync, add a
     small webhook receiver (FastAPI/Flask, a few routes) as a sidecar
     process that calls reconcile_subscription() on `customer.subscription.*`
     events -- `verify_webhook()` below implements the signature check for
     that sidecar; it just isn't reachable from inside Streamlit itself.
"""
import os
import datetime

try:
    import stripe
    STRIPE_SDK_AVAILABLE = True
except ImportError:
    STRIPE_SDK_AVAILABLE = False

from modules import subscription as sub_module


def is_configured() -> bool:
    return STRIPE_SDK_AVAILABLE and bool(os.environ.get("STRIPE_SECRET_KEY"))


def _client():
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    return stripe


def _price_id(plan: str, cycle: str) -> str | None:
    info = sub_module.PLAN_CATALOG.get(plan, {})
    env_key = info.get(f"stripe_price_{cycle}_env")
    return os.environ.get(env_key) if env_key else None


def get_or_create_customer(email: str) -> str | None:
    if not is_configured():
        return None
    email = email.strip().lower()
    conn = sub_module.get_conn()
    sub_module.init_billing_schema(conn)
    cur = conn.cursor()
    cur.execute("SELECT stripe_customer_id FROM subscriptions WHERE email = ?", (email,))
    row = cur.fetchone()
    if row and row[0]:
        return row[0]

    client = _client()
    customer = client.Customer.create(email=email)
    cur.execute(
        "UPDATE subscriptions SET stripe_customer_id = ? WHERE email = ?",
        (customer.id, email),
    )
    conn.commit()
    return customer.id


def create_checkout_session(email: str, plan: str, cycle: str = "monthly") -> str | None:
    if not is_configured():
        return None
    price_id = _price_id(plan, cycle)
    if not price_id:
        return None
    base_url = os.environ.get("APP_BASE_URL", "")
    if not base_url:
        return None

    client = _client()
    customer_id = get_or_create_customer(email)
    session = client.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{base_url}?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{base_url}?checkout=cancelled",
        client_reference_id=email,
        metadata={"plan": plan, "cycle": cycle, "email": email},
        allow_promotion_codes=True,
    )
    return session.url


def create_billing_portal_session(email: str) -> str | None:
    if not is_configured():
        return None
    conn = sub_module.get_conn()
    cur = conn.cursor()
    cur.execute("SELECT stripe_customer_id FROM subscriptions WHERE email = ?", (email.strip().lower(),))
    row = cur.fetchone()
    if not row or not row[0]:
        return None
    base_url = os.environ.get("APP_BASE_URL", "")
    client = _client()
    portal = client.billing_portal.Session.create(customer=row[0], return_url=base_url or None)
    return portal.url


def _plan_from_price_id(price_id: str) -> str | None:
    for plan in ("premium", "pro"):
        for cycle in ("monthly", "annual"):
            if _price_id(plan, cycle) == price_id:
                return plan
    return None


def _apply_subscription_state(email: str, plan: str, stripe_subscription_id: str,
                               current_period_end, status_raw: str):
    conn = sub_module.get_conn()
    sub_module.init_billing_schema(conn)
    cur = conn.cursor()
    status = "active" if status_raw in ("active", "trialing") else (
        "past_due" if status_raw == "past_due" else "expired"
    )
    
    period_end_iso = datetime.datetime.fromtimestamp(current_period_end, datetime.UTC).isoformat() if current_period_end else None
    now = datetime.datetime.now(datetime.UTC).isoformat()
    
    cur.execute(
        "UPDATE subscriptions SET plan = ?, status = ?, stripe_subscription_id = ?, "
        "current_period_end = ?, updated_at = ?, updated_by = 'stripe' WHERE email = ?",
        (plan, status, stripe_subscription_id, period_end_iso, now, email),
    )
    if cur.rowcount == 0:
        cur.execute(
            "INSERT INTO subscriptions (email, plan, status, stripe_subscription_id, current_period_end, "
            "updated_at, updated_by) VALUES (?, ?, ?, ?, ?, ?, 'stripe')",
            (email, plan, status, stripe_subscription_id, period_end_iso, now),
        )
    conn.commit()
    sub_module._log_billing_event(conn, email, "stripe_state_applied", f"plan={plan} status={status}")


def verify_checkout_session(session_id: str) -> dict | None:
    if not is_configured():
        return None
    client = _client()
    try:
        session = client.checkout.Session.retrieve(session_id, expand=["subscription"])
    except Exception:
        return None
    if session.payment_status != "paid" and session.status != "complete":
        return None

    email = (session.metadata or {}).get("email") or session.client_reference_id
    plan = (session.metadata or {}).get("plan")
    subscription_obj = session.subscription
    if not email or not plan or not subscription_obj:
        return None

    _apply_subscription_state(
        email=email.strip().lower(),
        plan=plan,
        stripe_subscription_id=subscription_obj.id,
        current_period_end=subscription_obj.current_period_end,
        status_raw=subscription_obj.status,
    )
    return {"email": email, "plan": plan, "status": subscription_obj.status}


def reconcile_subscription(email: str) -> dict | None:
    if not is_configured():
        return None
    email = email.strip().lower()
    conn = sub_module.get_conn()
    cur = conn.cursor()
    cur.execute("SELECT stripe_customer_id FROM subscriptions WHERE email = ?", (email,))
    row = cur.fetchone()
    if not row or not row[0]:
        return None

    client = _client()
    subs = client.Subscription.list(customer=row[0], status="all", limit=1)
    if not subs.data:
        return None
    s = subs.data[0]
    price_id = s["items"]["data"][0]["price"]["id"]
    plan = _plan_from_price_id(price_id) or "premium"
    _apply_subscription_state(email, plan, s.id, s.current_period_end, s.status)
    return {"email": email, "plan": plan, "status": s.status}


def verify_webhook(payload: bytes, sig_header: str):
    if not is_configured():
        raise RuntimeError("Stripe not configured")
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not secret:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET not set")
    client = _client()
    return client.Webhook.construct_event(payload, sig_header, secret)
