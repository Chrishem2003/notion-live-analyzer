"""
Page 61 — Subscriptions, Licensing & Access Control Hub
Exposes the tiered subscription engine, Stripe checkout, African student
verification, and sovereign access-control/licensing panels that previously
had no Streamlit display page.
"""
import sys
from pathlib import Path

import streamlit as st

current_file = Path(__file__).resolve()
root_dir = current_file.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

st.set_page_config(
    page_title="Subscriptions, Licensing & Access",
    page_icon="💳",
    layout="wide",
)


def _hero(title, subtitle, badge):
    st.markdown(
        f"""
        <div style="padding:1.6rem;background:linear-gradient(135deg,rgba(139,92,246,.14),rgba(11,19,33,.96));border-radius:14px;border:1px solid rgba(139,92,246,.4);margin-bottom:1.2rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem;">
                <h1 style="color:#a78bfa !important;font-size:1.9rem;margin:0;font-weight:800;">{title}</h1>
                <span style="background:rgba(139,92,246,.16);color:#a78bfa;padding:.3rem .8rem;border-radius:999px;font-size:.75rem;font-weight:700;border:1px solid #a78bfa;">{badge}</span>
            </div>
            <p style="color:#cbd5e1 !important;margin:.4rem 0 0;font-size:.95rem;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


_hero(
    "💳 Subscriptions, Licensing & Access Control",
    "Manage your enterprise tier, verify African student eligibility for free Standard access, launch the Stripe checkout flow, and review sovereign access-control & licensing enclaves.",
    "Tiered Licensing & Access Core",
)

tab1, tab2, tab3 = st.tabs(
    ["🔐 Access Control & Licensing", "💳 Subscription & Stripe", "🎓 Student Verification"]
)

with tab1:
    try:
        from modules.access_control import render_access_control_panel

        render_access_control_panel()
    except Exception as e:
        st.error(f"Access Control panel failed to load: {e}")

with tab2:
    try:
        from modules.stripe_verification import render_subscription_panel

        render_subscription_panel()
    except Exception as e:
        st.error(f"Subscription panel failed to load: {e}")

    st.markdown("---")
    try:
        from modules.verification import render_tier_selector

        render_tier_selector()
    except Exception as e:
        st.error(f"Tier selector failed to load: {e}")

with tab3:
    try:
        from modules.verification import render_verification_ui

        render_verification_ui()
    except Exception as e:
        st.error(f"Student verification UI failed to load: {e}")

st.markdown("---")
st.caption("CHRISHEM Multi-Problem Solver • Subscriptions, Licensing & Access Module")
