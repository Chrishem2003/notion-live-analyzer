"""
🔧 Data Transformer Page — SPSS-like Compute, Recode, Rank, and Binning.
"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Data Transformer", layout="wide", page_icon="🔧")

from modules.page_setup import bootstrap_page, get_active_dataframe
from modules.ui_components import section_header
from modules.data_transformer import render_transformer_panel

bootstrap_page("🔧 Data Transformation Engine", "SPSS-compatible: Compute, Recode, Rank, Count, Shift, Binning, Sort, Select, Weight, Rename.", "SPSS Transform")

active_df = get_active_dataframe()

result_df = render_transformer_panel(active_df)

# Allow saving transformed data back
st.markdown("---")
section_header("💾 Save Transformed Data")
if st.button("Save Transformed Data as Active Dataset", type="primary"):
    st.session_state["active_df"] = result_df
    st.success("✅ Transformed data saved as active dataset!")

