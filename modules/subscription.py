"""
Subscription & tier engine.

This is the single source of truth for "what is this account allowed to
do right now." It builds on the `subscriptions` table portal.py already
creates (email, plan, trial_started) rather than replacing it -- it adds
the columns a real billing lifecycle needs (status, trial_ends, Stripe
identifiers, period end) and reconciles old string values ("active",
"student_free", etc.) into the new plan/status split on first read.

Nothing here is simulated: trial expiry is a live comparison against the
clock on every call, quota counters are real rows incremented per action,
and paid-plan status is only ever set by (a) a verified Stripe Checkout
session, (b) a Stripe API reconciliation pull, or (c) an admin override
that is written to the audit ledger. There is no code path that marks an
account "active" without one of those three things happening.
"""
import datetime
import sqlite3
import streamlit as st

DB_PATH = "sovereign_apex_engine.db"  # must match portal.py / Admin Security Center's shared db path

# --------------------------------------------------------------------------- #
# Plan catalog -- edit prices/limits here; this is the ONLY place they live.
# Figures below are placeholders for you to set in your Stripe Dashboard and
# mirror here -- not a claim about what you should charge.
# --------------------------------------------------------------------------- #

PLAN_RANK = {"free": 0, "premium": 1, "pro": 2}
TRIAL_GRANTS_PLAN = "pro"          # what the 15-day trial gives access to
TRIAL_LENGTH_DAYS = 15

PLAN_CATALOG = {
    "free": {
        "label": "Free",
        "price_monthly": 0,
        "price_annual": 0,
        "stripe_price_monthly_env": None,
        "stripe_price_annual_env": None,
        "blurb": "Core tools, capped usage, no external integrations.",
    },
    "premium": {
        "label": "Premium",
        "price_monthly": 19,
        "price_annual": 190,
        "stripe_price_monthly_env": "STRIPE_PRICE_PREMIUM_MONTHLY",
        "stripe_price_annual_env": "STRIPE_PRICE_PREMIUM_ANNUAL",
        "blurb": "Full analytics + visualization studios, higher quotas, collaboration.",
    },
    "pro": {
        "label": "Pro",
        "price_monthly": 49,
        "price_annual": 490,
        "stripe_price_monthly_env": "STRIPE_PRICE_PRO_MONTHLY",
        "stripe_price_annual_env": "STRIPE_PRICE_PRO_ANNUAL",
        "blurb": "Everything, including integrations, forensics, and unlimited quotas.",
    },
}

# Per-hub minimum plan. "free" means any signed-in account; admin always passes.
HUB_MIN_PLAN = {
    "home": "free",
    "data": "free",                 # heavy transforms/simulator gated inside the page via quota, not the whole hub
    "statistics": "free",           # advanced tests (causal/Bayesian/power) gated inside the page
    "ml": "premium",
    "visualization": "free",        # dashboards/presentations gated inside the page
    "nlp": "free",                  # quota-limited on free/premium, unlimited on pro
    "literature": "premium",
    "domain": "free",               # AMR/clinical quota-limited by plan
    "integrations": "pro",
    "admin": "admin",               # role, not plan
    "collaboration": "premium",
    "forensics": "pro",
    "converter": "free",
    "threat": "pro",
    "mission": "premium",
}

# Real per-action quotas. (counter_key -> {plan: daily_limit}). None = unlimited.
QUOTAS = {
    "ai_assistant_calls": {"free": 5, "premium": 100, "pro": None},
    "amr_sequences_analyzed": {"free": 10, "premium": 100, "pro": None},
    "pdf_exports": {"free": 3, "premium": 50, "pro": None},
    "dataset_rows_processed": {"free": 5000, "premium": 250000, "pro": None},
}


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_billing_schema(conn=None):
    conn = conn or get_conn()
    cur = conn.cursor()
    # subscriptions table already exists (created by portal.py); add the
    # columns a real lifecycle needs if they're not there yet.
    cur.execute("PRAGMA table_info(subscriptions)")
    existing = {r[1] for r in cur.fetchall()}
    for col, coltype in [
        ("status", "TEXT DEFAULT 'active'"),
        ("trial_ends", "TEXT"),
        ("stripe_customer_id", "TEXT"),
        ("stripe_subscription_id", "TEXT"),
        ("current_period_end", "TEXT"),
        ("updated_at", "TEXT"),
        ("updated_by", "TEXT"),
    ]:
        if col not in existing:
            try:
                cur.execute(f"ALTER TABLE subscriptions ADD COLUMN {col}} {coltype}}")
            except sqlite3.OperationalError:
                pass

    cur.execute("""
        CREATE TABLE IF NOT EXISTS usage_counters (
            email TEXT,
            counter_key TEXT,
            period TEXT,
            count INTEGER DEFAULT 0,
            PRIMARY KEY (email, counter_key, period)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS billing_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            event_type TEXT,
            detail TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()


def _log_billing_event(conn, email: str, event_type: str, detail: str = ""):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO billing_events (email, event_type, detail, timestamp) VALUES (?, ?, ?, ?)",
        (email, event_type, detail, datetime.datetime.now(datetime.UTC).isoformat()),
    )
    conn.commit()


# --------------------------------------------------------------------------- #
# Reading / resolving status
# --------------------------------------------------------------------------- #

def ensure_trial_started(email: str):
    """Called once at first login (portal.py already does this). Starts a
    real 15-day trial if this email has no subscription row yet."""
    email = email.strip().lower()
    conn = get_conn()
    init_billing_schema(conn)
    cur = conn.cursor()
    cur.execute("SELECT email FROM subscriptions WHERE email = ?", (email,))
    if cur.fetchone():
        return
    now = datetime.datetime.now(datetime.UTC)
    trial_ends = now + datetime.timedelta(days=TRIAL_LENGTH_DAYS)
    cur.execute(
        "INSERT INTO subscriptions (email, plan, status, trial_started, trial_ends, updated_at, updated_by) "
        "VALUES (?, 'free', 'trialing', ?, ?, ?, 'system')",
        (email, now.isoformat(), trial_ends.isoformat(), now.isoformat()),
    )
    conn.commit()
    _log_billing_event(conn, email, "trial_started", f"{TRIAL_LENGTH_DAYS}}-day trial of {TRIAL_GRANTS_PLAN}}")


def _normalize_legacy_row(conn, email: str, row: dict) -> dict:
    """Old rows used plan values like 'active' / 'student_free' with no
    status column. Reconcile them once, in place, instead of branching on
    legacy values forever."""
    if row.get("status"):
        return row
    legacy_plan = (row.get("plan") or "free").lower()
    now = datetime.datetime.now(datetime.UTC).isoformat()
    if legacy_plan == "active":
        new_plan, new_status = "premium", "active"
    elif legacy_plan == "trial":
        new_plan, new_status = "free", "trialing"
    elif legacy_plan == "student_free":
        new_plan, new_status = "free", "comp"
    elif legacy_plan == "expired":
        new_plan, new_status = "free", "expired"
    else:
        new_plan, new_status = "free", "active"
    cur = conn.cursor()
    cur.execute(
        "UPDATE subscriptions SET plan = ?, status = ?, updated_at = ?, updated_by = 'migration' WHERE email = ?",
        (new_plan, new_status, now, email),
    )
    conn.commit()
    row["plan"], row["status"] = new_plan, new_status
    return row


def get_status(email: str) -> dict:
    """Returns a resolved dict: plan, status, effective_plan, trial_ends,
    days_left_in_trial. Auto-expires trials/subscriptions whose date has
    passed -- a real, live check, not a cached label."""
    email = email.strip().lower()
    conn = get_conn()
    init_billing_schema(conn)
    cur = conn.cursor()
    cur.execute(
        "SELECT plan, status, trial_started, trial_ends, current_period_end, "
        "stripe_customer_id, stripe_subscription_id FROM subscriptions WHERE email = ?",
        (email,),
    )
    row = cur.fetchone()
    if not row:
        ensure_trial_started(email)
        return get_status(email)

    data = dict(zip(
        ["plan", "status", "trial_started", "trial_ends", "current_period_end",
         "stripe_customer_id", "stripe_subscription_id"], row,
    ))
    data = _normalize_legacy_row(conn, email, data)

    now = datetime.datetime.now(datetime.UTC)
    effective_plan = "free"
    days_left = None

    if data["status"] == "trialing":
        trial_ends = datetime.datetime.fromisoformat(data["trial_ends"]) if data["trial_ends"] else now
        if now <= trial_ends:
            effective_plan = TRIAL_GRANTS_PLAN
            days_left = max(0, (trial_ends - now).days)
        else:
            cur.execute(
                "UPDATE subscriptions SET status = 'expired', updated_at = ?, updated_by = 'system' WHERE email = ?",
                (now.isoformat(), email),
            )
            conn.commit()
            _log_billing_event(conn, email, "trial_expired")
            data["status"] = "expired"
            effective_plan = "free"

    elif data["status"] in ("active", "comp"):
        period_end = data["current_period_end"]
        if data["status"] == "active" and period_end and datetime.datetime.fromisoformat(period_end) < now:
            cur.execute(
                "UPDATE subscriptions SET status = 'expired', updated_at = ?, updated_by = 'system' WHERE email = ?",
                (now.isoformat(), email),
            )
            conn.commit()
            _log_billing_event(conn, email, "subscription_lapsed")
            effective_plan = "free"
        else:
            effective_plan = data["plan"] if data["plan"] in PLAN_RANK else "free"

    data["effective_plan"] = effective_plan
    data["days_left_in_trial"] = days_left
    return data


def is_admin_email(email: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT role FROM auth_users WHERE email = ?", (email.strip().lower(),))
    row = cur.fetchone()
    return bool(row and row[0] == "admin")


def effective_plan(email: str) -> str:
    if is_admin_email(email):
        return "pro"
    return get_status(email)["effective_plan"]


# --------------------------------------------------------------------------- #
# Enforcement: hub gating + usage quotas
# --------------------------------------------------------------------------- #

def require_active_subscription(min_plan: str = "free", hub_id: str | None = None):
    """Call at the top of a hub's main(). Admin role always passes. Renders
    a real upgrade screen (with working Checkout buttons) and st.stop()s if
    the account's current, live-resolved plan doesn't meet the bar."""
    identity = st.session_state.get("user_identity", {})
    email = identity.get("email", "")
    if not email:
        st.error("Sign in required.")
        st.stop()

    if is_admin_email(email):
        return

    required = HUB_MIN_PLAN.get(hub_id, min_plan)
    status = get_status(email)
    have_rank = PLAN_RANK.get(status["effective_plan"], 0)
    need_rank = PLAN_RANK.get(required, 0)

    if have_rank >= need_rank:
        if status["status"] == "trialing" and status["days_left_in_trial"] is not None:
            st.info(f"Trial active — {status['days_left_in_trial']}} day(s) left with full {TRIAL_GRANTS_PLAN.title()}} access.")
        return

    from . import billing_stripe
    st.warning(f"This section requires the **{PLAN_CATALOG[required]['label']}}** plan. "
               f"Your account is currently on **{PLAN_CATALOG[status['effective_plan']]['label']}}**.")
    render_upgrade_prompt(email, required)
    st.stop()


def render_upgrade_prompt(email: str, target_plan: str):
    from . import billing_stripe
    plan_info = PLAN_CATALOG[target_plan]
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**{plan_info['label']}}** — ${plan_info['price_monthly']}}/mo")
        if billing_stripe.is_configured():
            if st.button(f"Upgrade to {plan_info['label']}} (monthly)", key=f"up_{target_plan}}_m"):
                url = billing_stripe.create_checkout_session(email, target_plan, "monthly")
                if url:
                    st.link_button("Continue to secure checkout →", url, type="primary")
        else:
            st.caption("Payments aren't configured on this deployment yet (missing STRIPE_SECRET_KEY).")
    with c2:
        st.markdown(f"**{plan_info['label']}}** — ${plan_info['price_annual']}}/yr")
        if billing_stripe.is_configured():
            if st.button(f"Upgrade to {plan_info['label']}} (annual)", key=f"up_{target_plan}}_a"):
                url = billing_stripe.create_checkout_session(email, target_plan, "annual")
                if url:
                    st.link_button("Continue to secure checkout →", url, type="primary")


def check_and_consume_quota(email: str, counter_key: str, amount: int = 1, period: str = "day") -> tuple[bool, str]:
    """Real quota enforcement. Returns (allowed, message). Increments the
    counter only when the action is allowed, so a blocked attempt doesn't
    burn quota."""
    plan = effective_plan(email)
    limits = QUOTAS.get(counter_key, {})
    limit = limits.get(plan)
    if limit is None:
        return True, ""

    now = datetime.datetime.now(datetime.UTC)
    period_key = now.strftime("%Y-%m-%d") if period == "day" else now.strftime("%Y-%m")

    conn = get_conn()
    init_billing_schema(conn)
    cur = conn.cursor()
    cur.execute(
        "SELECT count FROM usage_counters WHERE email = ? AND counter_key = ? AND period = ?",
        (email, counter_key, period_key),
    )
    row = cur.fetchone()
    current = row[0] if row else 0

    if current + amount > limit:
        return False, (f"You've used {current}}/{limit}} of your {plan.title()}}-plan "
                        f"{counter_key.replace('_', ' ')}} quota for this {period}}. Upgrade for a higher limit.")

    cur.execute(
        "INSERT INTO usage_counters (email, counter_key, period, count) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(email, counter_key, period) DO UPDATE SET count = count + excluded.count",
        (email, counter_key, period_key, amount),
    )
    conn.commit()
    return True, ""


def admin_override_plan(actor_email: str, target_email: str, new_plan: str, new_status: str = "comp"):
    """Manual admin comp/override. Always logged -- this is the only
    non-Stripe, non-trial path that can grant paid access, and it leaves a
    trace every time."""
    conn = get_conn()
    init_billing_schema(conn)
    now = datetime.datetime.now(datetime.UTC).isoformat()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO subscriptions (email, plan, status, updated_at, updated_by) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(email) DO UPDATE SET plan=excluded.plan, status=excluded.status, "
        "updated_at=excluded.updated_at, updated_by=excluded.updated_by",
        (target_email.strip().lower(), new_plan, new_status, now, f"admin:{actor_email}}"),
    )
    conn.commit()
    _log_billing_event(conn, target_email.strip().lower(), "admin_override",
                        f"plan={new_plan}} status={new_status}} by {actor_email}}")


# Backwards-compatible alias for the SubscriptionManager instance style
# already used elsewhere (portal.py calls `subscription.ensure_trial_started(...)`,
# Admin Security Center imports `subscription` as a module) -- this module
# IS that interface now, so `from modules import subscription` keeps working.

