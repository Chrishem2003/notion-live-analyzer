"""
📁 File Analyzer Page — Upload and analyze files (CSV, Excel, SPSS, SAS, STATA, JSON)
"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="File Analyzer", layout="wide", page_icon="📁")

from modules.config import init_session_state
from modules.ui_components import hero_card, section_header, load_css, watermark
from modules.file_uploader import parse_uploaded_file, merge_datasets, manual_data_entry, SUPPORTED_FORMATS
from modules.data_processor import profile_dataset, infer_column_types
from modules.export import render_export_buttons

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")
hero_card("📁 File Analyzer", "Upload CSV, Excel, SPSS, SAS, STATA, or JSON files for automated analysis and visualization.", "Upload & Analyze")
watermark("CHRISHEM")

# ─── File Upload Section ─────────────────────────────────────────────
section_header("📤 Upload Data File")
st.caption(f"Supported formats: {', '.join(SUPPORTED_FORMATS.keys())}")

uploaded_file = st.file_uploader(
    "Choose a file",
    type=["csv", "xlsx", "xls", "json", "sav", "sas7bdat", "dta", "parquet", "feather", "pkl"],
    help="Upload your data file. For SPSS (.sav), SAS (.sas7bdat), or STATA (.dta) files.",
)

if uploaded_file is not None:
    with st.spinner("Parsing file..."):
        uploaded_df = parse_uploaded_file(uploaded_file)

    if uploaded_df is not None and not uploaded_df.empty:
        st.session_state["uploaded_df"] = uploaded_df
        st.session_state["active_df"] = uploaded_df
        st.session_state["data_source"] = "upload"

        # Profile
        profile = profile_dataset(uploaded_df)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Rows", profile["rows"])
        with col2:
            st.metric("Columns", profile["columns"])
        with col3:
            st.metric("Numeric", len(profile.get("numeric_columns", [])))
        with col4:
            st.metric("Categorical", len(profile.get("categorical_columns", [])))

        # Data preview
        section_header("👁️ Data Preview")
        st.dataframe(uploaded_df.head(50), use_container_width=True, hide_index=True)

        # Column types
        section_header("📋 Column Types")
        col_types = infer_column_types(uploaded_df)
        type_df = pd.DataFrame([
            {"Column": col, "Type": ctype} for col, ctype in col_types.items()
        ])
        st.dataframe(type_df, use_container_width=True, hide_index=True)

        # Export
        section_header("📥 Export")
        render_export_buttons(uploaded_df)

        # Merge option
        if st.session_state.get("notion_df") is not None and not st.session_state["notion_df"].empty:
            section_header("🔗 Merge with Notion Data")
            notion_df = st.session_state["notion_df"]

            common_cols = list(set(uploaded_df.columns) & set(notion_df.columns))
            merge_key = st.selectbox(
                "Merge key column (optional)",
                options=[""] + common_cols,
                help="Select a common column to merge on. If none selected, datasets will be concatenated."
            )
            merge_how = st.selectbox("Merge method", options=["inner", "outer", "left", "right"], index=0)

            if st.button("🔄 Merge Datasets", type="primary"):
                merged = merge_datasets(notion_df, uploaded_df, merge_key=merge_key or None, merge_how=merge_how)
                if merged is not None and not merged.empty:
                    st.session_state["merged_df"] = merged
                    st.session_state["active_df"] = merged
                    st.session_state["data_source"] = "merged"
                    st.success(f"Merged dataset: {len(merged)} rows × {len(merged.columns)} columns")
                    st.dataframe(merged.head(20), use_container_width=True, hide_index=True)

    else:
        st.error("Failed to parse the uploaded file. Please check the file format and try again.")

# ─── Manual Data Entry ───────────────────────────────────────────────
st.markdown("---")
section_header("✏️ Or Enter Data Manually")
manual_df = manual_data_entry()
if manual_df is not None and not manual_df.empty:
    st.session_state["active_df"] = manual_df
    st.session_state["data_source"] = "manual"
    st.dataframe(manual_df, use_container_width=True, hide_index=True)

