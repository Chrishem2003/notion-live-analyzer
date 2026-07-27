"""
👤 Account — sign in, plan status, usage, student verification and the Notion template.
"""
import streamlit as st

st.set_page_config(page_title="Account", layout="wide", page_icon="👤")

import pandas as pd

from dataclasses import replace

from modules.accounts import AccountError, Tier
from modules.billing import PLANS, redeem_discount_code, usage_summary
from modules.config import init_session_state
from modules.eligibility import country_choices, evaluate
from modules.notion_template import claim, template_configured
from modules.session_auth import (
    current_user,
    render_account_badge,
    render_sign_in_form,
    render_sign_up_form,
    render_storage_warning,
    sign_in,
    sign_out,
    store,
)
from modules.ui_components import hero_card, load_css, section_header, watermark

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")
hero_card("👤 Your Account", "Plan, usage, verification and workspace access.", "Account")
watermark("CHRISHEM")

with st.sidebar:
    render_account_badge()

user = current_user(refresh=True)

# ─── Signed out ───────────────────────────────────────────────────────
if user is None:
    render_storage_warning()
    st.info("You're browsing on the Free plan. Create an account to start your 15-day Standard trial.")
    sign_in_tab, sign_up_tab = st.tabs(["Sign in", "Create account"])
    with sign_in_tab:
        if render_sign_in_form():
            st.rerun()
    with sign_up_tab:
        if render_sign_up_form():
            st.rerun()
    st.stop()

# ─── Plan summary ─────────────────────────────────────────────────────
plan = PLANS[user.effective_tier()]
section_header(f"🎟️ {plan.name} plan")

col1, col2, col3 = st.columns(3)
col1.metric("Plan", plan.name)
if user.trial_active():
    col2.metric("Trial days left", user.trial_days_left())
elif user.subscription_active():
    col2.metric("Renews", user.subscription_ends_at.strftime("%d %b %Y"))
else:
    col2.metric("Billing", "—")
col3.metric("Student verified", "Yes" if user.student_verified else "No")

st.caption(plan.tagline)
st.dataframe(pd.DataFrame(usage_summary(store(), user)), use_container_width=True, hide_index=True)
st.page_link("pages/48_💳_Pricing.py", label="Compare plans", icon="💳")

# ─── Student verification ─────────────────────────────────────────────
section_header("🎓 Sponsored student access")
if user.student_verified:
    st.success(f"Verified via {user.institution or 'your institution'} — Standard tier is free on this account.")
else:
    st.caption(
        "Students at universities in African Union member states and qualifying "
        "developing countries get the Standard plan free. Verification uses your "
        "university email domain and country — no identity documents are collected or stored."
    )
    choices = dict(country_choices())
    with st.form("verify_student"):
        institutional_email = st.text_input(
            "University email", value=user.email, placeholder="name@student.mak.ac.ug"
        )
        country = st.selectbox(
            "Country",
            options=list(choices),
            index=list(choices).index(user.country) if user.country in choices else 0,
            format_func=lambda code: choices[code],
        )
        if st.form_submit_button("Verify eligibility", type="primary"):
            decision = evaluate(institutional_email, country)
            if decision.eligible:
                updated = store().save_user(
                    replace(
                        user,
                        student_verified=True,
                        institution=decision.institution_domain,
                        country=decision.country_code,
                        tier=Tier.STANDARD if user.tier is Tier.FREE else user.tier,
                    )
                )
                sign_in(updated)
                st.success(decision.reason)
                st.rerun()
            else:
                st.warning(decision.reason)

# ─── Notion template ──────────────────────────────────────────────────
section_header("🗂️ Premium Notion workspace")
if user.notion_template_claimed:
    st.info("You've already claimed your workspace template. It's a one-time duplication per account.")
elif not template_configured():
    st.caption("The premium template isn't published yet — set `NOTION_TEMPLATE_URL` to enable it.")
else:
    st.caption("Premium members get a one-time duplication link into their own Notion workspace.")
    if st.button("Claim Notion template workspace", type="primary"):
        try:
            granted = claim(store(), user)
            st.success(f"Your single-use link is ready and expires in {granted.expires_hours} hours.")
            st.link_button("Open in Notion", granted.url, type="primary")
        except AccountError as exc:
            st.warning(str(exc))

# ─── Discount code ────────────────────────────────────────────────────
section_header("🏷️ Redeem a code")
with st.form("redeem_code"):
    code = st.text_input("Discount or access code")
    if st.form_submit_button("Redeem"):
        try:
            updated, message = redeem_discount_code(store(), user, code)
            sign_in(updated)
            st.success(message)
            st.rerun()
        except AccountError as exc:
            st.error(str(exc))

st.divider()
if st.button("Sign out"):
    sign_out()
    st.rerun()
