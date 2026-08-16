"""
Page 63 — Academic Portfolio & Grants Studio
Exposes the academic portfolio studio, grant engine, grant matcher, and
grant formatter modules for research funding and scholarly portfolio work.
"""
import sys
from pathlib import Path

import streamlit as st

current_file = Path(__file__).resolve()
root_dir = current_file.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

st.set_page_config(
    page_title="Academic Portfolio & Grants Studio",
    page_icon="🎓",
    layout="wide",
)


def _hero(title, subtitle, badge):
    st.markdown(
        f"""
        <div style="padding:1.6rem;background:linear-gradient(135deg,rgba(16,185,129,.14),rgba(11,19,33,.96));border-radius:14px;border:1px solid rgba(16,185,129,.4);margin-bottom:1.2rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem;">
                <h1 style="color:#34d399 !important;font-size:1.9rem;margin:0;font-weight:800;">{title}</h1>
                <span style="background:rgba(16,185,129,.16);color:#34d399;padding:.3rem .8rem;border-radius:999px;font-size:.75rem;font-weight:700;border:1px solid #34d399;">{badge}</span>
            </div>
            <p style="color:#cbd5e1 !important;margin:.4rem 0 0;font-size:.95rem;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


_hero(
    "🎓 Academic Portfolio & Grants Studio",
    "Build your scholarly academic portfolio, discover and match funding opportunities, and generate publication-ready grant proposals with proper formatting.",
    "Academic & Grant Research Core",
)

tab1, tab2, tab3, tab4 = st.tabs(
    ["📁 Academic Portfolio", "💰 Grant Engine", "🔀 Grant Matcher", "📝 Grant Formatter"]
)

with tab1:
    try:
        from modules.academic_portfolio_studio import render_academic_portfolio_studio_panel

        render_academic_portfolio_studio_panel()
    except Exception as e:
        st.error(f"Academic portfolio studio failed to load: {e}")

with tab2:
    try:
        from modules.grant_engine import render_grant_engine_tab

        render_grant_engine_tab()
    except Exception as e:
        st.error(f"Grant engine failed to load: {e}")

with tab3:
    try:
        from modules.grant_matcher import render_grant_matcher_tab

        render_grant_matcher_tab()
    except Exception as e:
        st.error(f"Grant matcher failed to load: {e}")

with tab4:
    try:
        from modules.grant_formatter import render_grant_formatter_ui

        render_grant_formatter_ui()
    except Exception as e:
        st.error(f"Grant formatter failed to load: {e}")

st.markdown("---")
st.caption("CHRISHEM Multi-Problem Solver • Academic Portfolio & Grants Module")
