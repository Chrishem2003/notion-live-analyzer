"""
🏷️ Variable View Page — SPSS-style variable metadata editor.
"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Variable View", layout="wide", page_icon="🏷️")

from modules.page_setup import bootstrap_page, get_active_dataframe
from modules.ui_components import section_header
from modules.variable_view import render_variable_view_editor, apply_variable_metadata

bootstrap_page("🏷️ Variable View Editor", "SPSS-style variable metadata — labels, value labels, measurement levels, and missing values.", "SPSS Variable View")

active_df = get_active_dataframe()

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

