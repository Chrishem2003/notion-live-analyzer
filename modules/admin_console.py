"""Super-admin console: subscribers, discount codes and system telemetry.

Access needs both an admin account **and** the `ADMIN_PANEL_PASSWORD` secret, so
a stolen session alone is not enough. When the password is unset the console
refuses to open rather than defaulting to something guessable.
"""
from __future__ import annotations

import hmac
import os
from datetime import timedelta

import pandas as pd
import streamlit as st

from modules.accounts import (
    AccountError,
    SQLiteAccountStore,
    Tier,
    extend_trial,
    set_tier,
    suspend,
    utcnow,
)
from modules.billing import PLANS, create_discount_code, usage_summary
from modules.notion_template import reset_claim
from modules.runtime_perf import memory_usage_mb
from modules.session_auth import current_user, store

UNLOCK_KEY = "_admin_unlocked"


def admin_password() -> str:
    return os.environ.get("ADMIN_PANEL_PASSWORD", "")


def unlock_gate() -> bool:
    """Render the password gate. True once the console may be shown."""
    user = current_user()
    if user is None or not user.is_admin:
        st.error("🔒 This console is restricted to the developer account.")
        st.caption(
            "Admin accounts are listed in the `ADMIN_EMAILS` environment variable."
        )
        return False

    if not admin_password():
        st.error(
            "🔒 `ADMIN_PANEL_PASSWORD` is not set, so the console stays locked. "
            "Set it in your deployment secrets to enable admin access."
        )
        return False

    if st.session_state.get(UNLOCK_KEY):
        return True

    with st.form("admin_unlock"):
        candidate = st.text_input("Admin password", type="password")
        submitted = st.form_submit_button("Unlock", type="primary")
    if submitted:
        if hmac.compare_digest(candidate or "", admin_password()):
            st.session_state[UNLOCK_KEY] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


# ═══════════════════════════════════════════════════════════════════════
# Panels
# ═══════════════════════════════════════════════════════════════════════
def render_subscribers(account_store: SQLiteAccountStore) -> None:
    users = account_store.list_users()
    if not users:
        st.info("No accounts yet.")
        return

    now = utcnow()
    frame = pd.DataFrame(
        [
            {
                "Email": user.email,
                "Plan": PLANS[user.effective_tier(now)].name,
                "Billed tier": user.tier.value,
                "Trial days left": user.trial_days_left(now),
                "Country": user.country or "—",
                "Student": "✅" if user.student_verified else "",
                "Template claimed": "✅" if user.notion_template_claimed else "",
                "Suspended": "🚫" if user.is_suspended else "",
                "Joined": user.created_at.strftime("%Y-%m-%d"),
            }
            for user in users
        ]
    )
    st.dataframe(frame, use_container_width=True, hide_index=True)

    st.markdown("#### Manage an account")
    emails = [user.email for user in users]
    selected = st.selectbox("Account", options=emails, key="admin_pick_user")
    user = next(user for user in users if user.email == selected)

    col1, col2 = st.columns(2)
    with col1:
        tier = st.selectbox(
            "Set plan",
            options=list(Tier),
            index=list(Tier).index(user.tier),
            format_func=lambda value: PLANS[value].name,
            key="admin_set_tier",
        )
        days = st.number_input(
            "Days (0 = no expiry)", min_value=0, max_value=3650, value=30, key="admin_days"
        )
        if st.button("Apply plan", type="primary"):
            set_tier(account_store, user, tier, days=int(days) or None)
            st.success(f"{user.email} → {PLANS[tier].name}")
            st.rerun()

        trial_days = st.number_input(
            "Extend trial by days", min_value=1, max_value=365, value=15, key="admin_trial"
        )
        if st.button("Extend trial"):
            extend_trial(account_store, user, int(trial_days))
            st.success(f"Trial extended by {int(trial_days)} days.")
            st.rerun()

    with col2:
        st.write("**Usage this month**")
        st.dataframe(
            pd.DataFrame(usage_summary(account_store, user)),
            use_container_width=True,
            hide_index=True,
        )
        if user.notion_template_claimed and st.button("Reset Notion template claim"):
            reset_claim(account_store, user)
            st.success("The user can claim the template again.")
            st.rerun()
        label = "Reinstate account" if user.is_suspended else "Suspend account"
        if st.button(label):
            suspend(account_store, user, not user.is_suspended)
            st.success(f"{user.email} {'reinstated' if user.is_suspended else 'suspended'}.")
            st.rerun()


def render_discount_codes(account_store: SQLiteAccountStore) -> None:
    with st.form("new_code"):
        col1, col2, col3 = st.columns(3)
        with col1:
            code = st.text_input("Code", placeholder="LAUNCH50")
            percent = st.number_input("Percent off", min_value=0, max_value=100, value=50)
        with col2:
            grants = st.selectbox(
                "Grants plan (optional)",
                options=[None, Tier.STANDARD, Tier.PREMIUM],
                format_func=lambda value: "None — discount only" if value is None else PLANS[value].name,
            )
            grant_days = st.number_input("Grant days", min_value=1, max_value=730, value=30)
        with col3:
            max_redemptions = st.number_input("Max redemptions", min_value=1, max_value=100_000, value=1)
            valid_days = st.number_input("Valid for (days)", min_value=1, max_value=730, value=30)
        if st.form_submit_button("Create code", type="primary"):
            try:
                create_discount_code(
                    account_store,
                    code,
                    percent_off=int(percent),
                    grants_tier=grants,
                    grants_days=int(grant_days) if grants else None,
                    max_redemptions=int(max_redemptions),
                    expires_at=utcnow() + timedelta(days=int(valid_days)),
                )
                st.success(f"Created {code.strip().upper()}")
            except AccountError as exc:
                st.error(str(exc))

    codes = account_store.list_discount_codes()
    if not codes:
        st.caption("No codes yet.")
        return
    st.dataframe(
        pd.DataFrame(codes)[
            ["code", "percent_off", "grants_tier", "grants_days",
             "redemptions", "max_redemptions", "expires_at"]
        ],
        use_container_width=True,
        hide_index=True,
    )
    to_delete = st.selectbox("Revoke a code", options=[c["code"] for c in codes])
    if st.button("Revoke"):
        account_store.delete_discount_code(to_delete)
        st.success(f"{to_delete} revoked.")
        st.rerun()


def render_telemetry(account_store: SQLiteAccountStore) -> None:
    users = account_store.list_users()
    now = utcnow()
    active = [user for user in users if not user.is_suspended]
    paying = [user for user in active if user.effective_tier(now) is not Tier.FREE]
    trialing = [user for user in active if user.trial_active(now)]
    mrr = sum(PLANS[user.effective_tier(now)].price_usd for user in paying if not user.trial_active(now))

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Accounts", len(users))
    col2.metric("Paid plans", len(paying) - len(trialing))
    col3.metric("On trial", len(trialing))
    col4.metric("MRR (list price)", f"${mrr:,.0f}")

    col5, col6, col7 = st.columns(3)
    col5.metric("Process memory", f"{memory_usage_mb():.0f} MB")
    col6.metric("Account backend", account_store.backend)
    col7.metric(
        "Signups (30d)",
        sum(1 for user in users if user.created_at > now - timedelta(days=30)),
    )

    if users:
        joins = pd.DataFrame({"joined": [user.created_at.date() for user in users]})
        st.bar_chart(joins.value_counts("joined").sort_index(), height=200)


def render() -> None:
    """Entry point for the admin page."""
    st.title("🛠️ Developer Console")
    if not unlock_gate():
        return

    account_store = store()
    telemetry, subscribers, codes = st.tabs(
        ["📈 Telemetry", "👥 Subscribers", "🏷️ Discount codes"]
    )
    with telemetry:
        render_telemetry(account_store)
    with subscribers:
        render_subscribers(account_store)
    with codes:
        render_discount_codes(account_store)

    if st.button("🔒 Lock console"):
        st.session_state.pop(UNLOCK_KEY, None)
        st.rerun()
