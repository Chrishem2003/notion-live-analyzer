st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)

"""
🏷️ Variable View Page — SPSS-style variable metadata editor.
"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Variable View", layout="wide", page_icon="🏷️")

from modules.config import init_session_state
from modules.ui_components import hero_card, load_css, watermark, section_header
from modules.variable_view import render_variable_view_editor, apply_variable_metadata

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")
hero_card("🏷️ Variable View Editor", "SPSS-style variable metadata — labels, value labels, measurement levels, and missing values.", "SPSS Variable View")
watermark("CHRISHEM")

active_df = st.session_state.get("active_df")
if active_df is None or active_df.empty:
    active_df = st.session_state.get("notion_df")

if active_df is None or active_df.empty:
    st.warning("⚠️ No data available. Load data first.")
    st.stop()

st.info(f"**Dataset**: {len(active_df)} rows × {len(active_df.columns)} columns")

render_variable_view_editor(active_df)

# Apply metadata
st.markdown("---")
section_header("🔄 Apply Metadata to Data")
if st.button("Apply Variable Metadata to Dataset", type="primary"):
    transformed = apply_variable_metadata(active_df)
    st.session_state["active_df"] = transformed
    st.success("✅ Metadata applied! (value labels replaced, missing values set to NaN)")
    st.dataframe(transformed.head(20), use_container_width=True, hide_index=True)

