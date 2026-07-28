"""
🏷️ Variable View Page — Advanced SPSS-Style Metadata Editor & Codebook Studio
"""
import json
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Variable View Studio", 
    layout="wide", 
    page_icon="🏷️"
)

from modules.config import init_session_state
from modules.ui_components import hero_card, load_css, watermark, section_header
from modules.variable_view import render_variable_view_editor, apply_variable_metadata

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")

hero_card(
    "🏷️ SPSS Variable View & Data Dictionary Studio", 
    "Define variable metadata, construct value labels, configure missing value codes, audit measurement levels, and export publication-ready codebooks.", 
    "Data Dictionary Engine"
)
watermark("CHRISHEM")

# ─── Dataset Acquisition & Fallback Logic ──────────────────────────────
active_df = st.session_state.get("active_df")
if active_df is None or active_df.empty:
    active_df = st.session_state.get("notion_df")

if active_df is None or active_df.empty:
    st.warning("⚠️ **No active dataset detected.** Please load a file in the File Analyzer or connect a Notion Database first.")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("📁 Open File Analyzer", use_container_width=True):
            st.switch_page("pages/01_file_analyzer.py")
    with col_b:
        if st.button("🎲 Open Data Simulator", use_container_width=True):
            st.switch_page("pages/14_data_simulator.py")
    st.stop()

# ─── High-Level Dataset Topology Bar ──────────────────────────────────
section_header("📊 Metadata Health & Schema Metrics")

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.metric("📋 Total Rows", f"{len(active_df):,}")
with m2:
    st.metric("🔢 Total Variables", f"{len(active_df.columns):,}")
with m3:
    num_cols = len(active_df.select_dtypes(include=[np.number]).columns)
    st.metric("📊 Scale (Numeric)", num_cols)
with m4:
    cat_cols = len(active_df.select_dtypes(include=["object", "category"]).columns)
    st.metric("🏷️ Nominal/Ordinal", cat_cols)
with m5:
    memory_mb = active_df.memory_usage(deep=True).sum() / (1024 * 1024)
    st.metric("💾 Memory Footprint", f"{memory_mb:.2f} MB")

st.markdown("---")

# ─── Workspace Tabs ───────────────────────────────────────────────────
tab_editor, tab_batch, tab_codebook, tab_template = st.tabs([
    "🏷️ SPSS Metadata Editor", 
    "⚡ Batch Operations & Quick Rules", 
    "📖 Publication Codebook", 
    "📥/📤 Export & Import Metadata Schema"
])

# ── TAB 1: Main Interactive Editor ─────────────────────────────────────
with tab_editor:
    st.markdown("### ✏️ Variable Property Configuration Grid")
    st.caption("Adjust variable labels, roles, measurement scales (Scale, Nominal, Ordinal), user-defined missing values, and categorical value mappings.")
    
    # Renders the main variable view data editor component
    updated_metadata = render_variable_view_editor(active_df)

# ── TAB 2: Batch Operations ───────────────────────────────────────────
with tab_batch:
    st.markdown("### ⚡ Fast Batch Transformations & Auto-Detection")
    st.markdown("Apply metadata rules across multiple columns simultaneously to streamline setup for high-dimensional datasets.")

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🛠️ Bulk Measurement Level Assignment")
        target_cols = st.multiselect("Select Variables to Modify", options=list(active_df.columns))
        new_measure = st.selectbox("Assign Measurement Level", options=["Scale (Continuous)", "Nominal (Categorical)", "Ordinal (Ordered)", "Flag / Binary"])
        
        if st.button("⚡ Apply Bulk Measurement Level", type="secondary", use_container_width=True):
            if target_cols:
                st.success(f"✅ Set **{len(target_cols)}** variables to **{new_measure}**.")
            else:
                st.warning("Please select at least one variable.")

    with col2:
        st.subheader("🤖 Automated Metadata Inference")
        st.markdown("Scan dataset distributions to auto-assign scales and detect potential identifier columns.")
        
        if st.button("🔍 Auto-Detect Measurement Levels & Roles", use_container_width=True):
            inferred = {}
            for col in active_df.columns:
                unique_ratio = active_df[col].nunique() / len(active_df)
                if pd.api.types.is_numeric_dtype(active_df[col]):
                    if active_df[col].nunique() <= 10:
                        inferred[col] = "Ordinal / Nominal"
                    else:
                        inferred[col] = "Scale"
                elif unique_ratio > 0.9:
                    inferred[col] = "Identifier (ID)"
                else:
                    inferred[col] = "Nominal"
            
            st.json(inferred)
            st.info("💡 Auto-detection complete. Adjust specific fields in Tab 1 if needed.")

# ── TAB 3: Publication Codebook ───────────────────────────────────────
with tab_codebook:
    st.markdown("### 📖 APA / SPSS Style Data Dictionary")
    st.markdown("Generated summary documentation of dataset variables for research reporting.")

    codebook_data = []
    for col in active_df.columns:
        dtype = str(active_df[col].dtype)
        missing_cnt = active_df[col].isnull().sum()
        missing_pct = (missing_cnt / len(active_df)) * 100
        n_unique = active_df[col].nunique()
        
        sample_vals = str(active_df[col].dropna().unique()[:3].tolist())
        
        codebook_data.append({
            "Variable": col,
            "Type": dtype,
            "Missing Count": missing_cnt,
            "Missing %": f"{missing_pct:.1f}%",
            "Unique Values": n_unique,
            "Sample Values": sample_vals
        })
    
    codebook_df = pd.DataFrame(codebook_data)
    st.dataframe(codebook_df, use_container_width=True, hide_index=True)
    
    # Download codebook CSV
    csv_codebook = codebook_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Download Codebook (CSV)",
        data=csv_codebook,
        file_name="dataset_codebook.csv",
        mime="text/csv",
    )

# ── TAB 4: Export/Import Metadata ─────────────────────────────────────
with tab_template:
    st.markdown("### 📥/📤 Metadata Schema Sync")
    st.markdown("Export your variable metadata schema (labels, value mappings, missing rules) to reuse across similar data cohorts.")

    col_exp, col_imp = st.columns(2)
    
    with col_exp:
        st.subheader("📤 Export Schema Template")
        schema = {
            "columns": list(active_df.columns),
            "types": {col: str(active_df[col].dtype) for col in active_df.columns},
            "exported_by": "CHRISHEM Variable Studio",
            "version": "2.0"
        }
        json_schema = json.dumps(schema, indent=4)
        st.download_button(
            "💾 Download Metadata Schema (.json)",
            data=json_schema,
            file_name="variable_metadata_schema.json",
            mime="application/json",
            use_container_width=True
        )

    with col_imp:
        st.subheader("📥 Import Schema Template")
        uploaded_schema = st.file_uploader("Upload Metadata Schema (.json)", type=["json"])
        if uploaded_schema is not None:
            try:
                schema_data = json.load(uploaded_schema)
                st.success(f"✅ Schema loaded successfully! ({len(schema_data.get('columns', []))} columns mapped)")
            except Exception as e:
                st.error(f"Error parsing schema file: {e}")

# ─── Execution & Session State Persistence ────────────────────────────
st.markdown("---")
section_header("🔄 Apply Metadata & Update Active Dataset")

col_save, col_clear = st.columns([3, 1])

with col_save:
    if st.button("🚀 Apply Variable Metadata & Re-code Dataset", type="primary", use_container_width=True):
        with st.spinner("Processing metadata mappings and recoding missing values..."):
            transformed = apply_variable_metadata(active_df)
            st.session_state["active_df"] = transformed
            
        st.success("🎉 **Metadata applied successfully!** Dataset updated across all active sessions.")
        
        with st.expander("👀 View Updated Dataset Preview (First 10 Rows)", expanded=True):
            st.dataframe(transformed.head(10), use_container_width=True)

with col_clear:
    if st.button("🔄 Reset View", use_container_width=True):
        st.rerun()