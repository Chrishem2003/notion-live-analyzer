"""
Page 64 — Global Surveillance & Impact Monitoring
Exposes the WHO surveillance, Mastercard economic impact, policy generator,
and inventory engine modules for global health, financial, and policy analysis.
"""
import sys
from pathlib import Path

import streamlit as st

current_file = Path(__file__).resolve()
root_dir = current_file.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

st.set_page_config(
    page_title="Global Surveillance & Impact Monitoring",
    page_icon="🌍",
    layout="wide",
)


def _hero(title, subtitle, badge):
    st.markdown(
        f"""
        <div style="padding:1.6rem;background:linear-gradient(135deg,rgba(244,63,94,.14),rgba(11,19,33,.96));border-radius:14px;border:1px solid rgba(244,63,94,.4);margin-bottom:1.2rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem;">
                <h1 style="color:#fb7185 !important;font-size:1.9rem;margin:0;font-weight:800;">{title}</h1>
                <span style="background:rgba(244,63,94,.16);color:#fb7185;padding:.3rem .8rem;border-radius:999px;font-size:.75rem;font-weight:700;border:1px solid #fb7185;">{badge}</span>
            </div>
            <p style="color:#cbd5e1 !important;margin:.4rem 0 0;font-size:.95rem;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


_hero(
    "🌍 Global Surveillance & Impact Monitoring",
    "WHO disease-surveillance tracking, Mastercard economic-impact analytics, automated policy generation, and resource inventory management for cross-sector monitoring.",
    "Global Health, Economic & Policy Core",
)

tab1, tab2, tab3, tab4 = st.tabs(
    ["🦠 WHO Surveillance", "💳 Mastercard Impact", "📜 Policy Generator", "📦 Inventory Engine"]
)

with tab1:
    try:
        from modules.who_surveillance import render_who_surveillance_tab

        render_who_surveillance_tab()
    except Exception as e:
        st.error(f"WHO surveillance panel failed to load: {e}")

with tab2:
    try:
        from modules.mastercard_impact import render_mastercard_impact_tab

        render_mastercard_impact_tab()
    except Exception as e:
        st.error(f"Mastercard impact panel failed to load: {e}")

with tab3:
    try:
        from modules.policy_generator import render_policy_generator_tab

        render_policy_generator_tab()
    except Exception as e:
        st.error(f"Policy generator panel failed to load: {e}")

with tab4:
    try:
        from modules.inventory_engine import render_inventory_tab

        render_inventory_tab()
    except Exception as e:
        st.error(f"Inventory engine panel failed to load: {e}")

st.markdown("---")
st.caption("CHRISHEM Multi-Problem Solver • Global Surveillance & Impact Module")
