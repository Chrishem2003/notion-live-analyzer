"""
Page 62 — Admin Billing & Management Portal
Exposes the autonomous admin privileges, enterprise billing reconciliation,
and the developer management console (user management, promo codes, analytics).
"""
import sys
from pathlib import Path

import streamlit as st

current_file = Path(__file__).resolve()
root_dir = current_file.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

st.set_page_config(
    page_title="Admin Billing & Management Portal",
    page_icon="🛡️",
    layout="wide",
)


def _hero(title, subtitle, badge):
    st.markdown(
        f"""
        <div style="padding:1.6rem;background:linear-gradient(135deg,rgba(56,189,248,.14),rgba(11,19,33,.96));border-radius:14px;border:1px solid rgba(56,189,248,.4);margin-bottom:1.2rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem;">
                <h1 style="color:#38bdf8 !important;font-size:1.9rem;margin:0;font-weight:800;">{title}</h1>
                <span style="background:rgba(56,189,248,.16);color:#38bdf8;padding:.3rem .8rem;border-radius:999px;font-size:.75rem;font-weight:700;border:1px solid #38bdf8;">{badge}</span>
            </div>
            <p style="color:#cbd5e1 !important;margin:.4rem 0 0;font-size:.95rem;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


_hero(
    "🛡️ Admin Billing & Management Portal",
    "Autonomous admin privilege matrix, intelligent enterprise billing reconciliation, financial ledger exports, plus the developer management console for user tiers, promo codes, and platform analytics.",
    "Enterprise Administration & Billing Core",
)

tab1, tab2 = st.tabs(["📊 Billing & Privileges", "👥 Management Console"])

with tab1:
    try:
        from modules.admin_billing_core import render_admin_billing_panel

        render_admin_billing_panel()
    except Exception as e:
        st.error(f"Admin billing panel failed to load: {e}")

with tab2:
    try:
        from modules.admin_portal import render_admin_router

        render_admin_router()
    except Exception as e:
        st.error(f"Admin management console failed to load: {e}")

st.markdown("---")
st.caption("CHRISHEM Multi-Problem Solver • Admin Billing & Management Module")
