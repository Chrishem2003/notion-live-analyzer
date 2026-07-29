st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)

"""
🔧 Data Transformer Page — SPSS-like Compute, Recode, Rank, and Binning.
"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Data Transformer", layout="wide", page_icon="🔧")

from modules.config import init_session_state
from modules.ui_components import hero_card, load_css, watermark, section_header
from modules.data_transformer import render_transformer_panel

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")
hero_card("🔧 Data Transformation Engine", "SPSS-compatible: Compute, Recode, Rank, Count, Shift, Binning, Sort, Select, Weight, Rename.", "SPSS Transform")
watermark("CHRISHEM")

active_df = st.session_state.get("active_df")
if active_df is None or active_df.empty:
    active_df = st.session_state.get("notion_df")

if active_df is None or active_df.empty:
    st.warning("⚠️ No data available. Load data first.")
    st.stop()

result_df = render_transformer_panel(active_df)

# Allow saving transformed data back
st.markdown("---")
section_header("💾 Save Transformed Data")
if st.button("Save Transformed Data as Active Dataset", type="primary"):
    st.session_state["active_df"] = result_df
    st.success("✅ Transformed data saved as active dataset!")

