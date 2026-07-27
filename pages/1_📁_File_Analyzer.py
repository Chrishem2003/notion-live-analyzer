"""
📁 Advanced File Analyzer & Multi-Format Ingestion Engine [SECURE]
Enhanced parsing support for CSV, Excel (XLSX/XLS), SPSS (.sav), SAS (.sas7bdat), 
STATA (.dta), Parquet, Feather, Pickle, and advanced local file explorers.
"""
import streamlit as st
import pandas as pd
import os
import sys
from pathlib import Path

st.set_page_config(page_title="Advanced File Analyzer [SECURE]", layout="wide", page_icon="📁")

# ─── ULTIMATE PATH RESOLUTION ────────────────────────────────────────
current_file = Path(__file__).resolve()
root_dir = current_file.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(current_file.parent) not in sys.path:
    sys.path.insert(0, str(current_file.parent))

from modules.config import init_session_state
from modules.ui_components import hero_card, section_header, load_css, watermark
from modules.file_uploader import parse_uploaded_file, merge_datasets, manual_data_entry, SUPPORTED_FORMATS
from modules.data_processor import profile_dataset, infer_column_types
from modules.export import render_export_buttons

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")

hero_card(
    "📁 Advanced File Analyzer & Explorer Engine [CLASSIFIED]",
    "Universal data parsing for CSV, Excel, SPSS (.sav), SAS, STATA, JSON, and binary formats "
    "with robust error handling, automated profiling, and local directory scanning.",
    badge_text="🔒 v4.2 — Advanced Multi-Format Ingestion & Deep Profiler"
)
watermark("CHRISHEM")

# ─── Robust Parser Wrapper for Local/Uploaded Binaries ─────────────────
def robust_parse_file(file_obj_or_path):
    """
    Advanced parser supporting all research formats (CSV, Excel, SPSS, SAS, Stata, JSON, Parquet)
    handles both Streamlit UploadedFile objects and local filesystem paths seamlessly.
    """
    try:
        # Determine filename or suffix
        if hasattr(file_obj_or_path, "name"):
            filename = file_obj_or_path.name
        else:
            filename = str(file_obj_or_path)

        ext = filename.lower().split('.')[-1]

        if ext == 'csv':
            # Try multiple encodings for robustness
            for enc in ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']:
                try:
                    if hasattr(file_obj_or_path, "seek"):
                        file_obj_or_path.seek(0)
                    return pd.read_csv(file_obj_or_path, encoding=enc, low_memory=False)
                except Exception:
                    continue
            return None

        elif ext in ['xls', 'xlsx']:
            if hasattr(file_obj_or_path, "seek"):
                file_obj_or_path.seek(0)
            return pd.read_excel(file_obj_or_path, sheet_name=0)

        elif ext == 'json':
            if hasattr(file_obj_or_path, "seek"):
                file_obj_or_path.seek(0)
            return pd.read_json(file_obj_or_path)

        elif ext == 'sav':  # SPSS
            try:
                import pyreadstat
                if isinstance(file_obj_or_path, (str, Path)):
                    df, meta = pyreadstat.read_sav(str(file_obj_or_path))
                else:
                    # Streamlit uploaded file needs temporary save for pyreadstat
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".sav") as tmp:
                        tmp.write(file_obj_or_path.read())
                        tmp_path = tmp.name
                    df, meta = pyreadstat.read_sav(tmp_path)
                    os.unlink(tmp_path)
                return df
            except ImportError:
                st.error("⚠️ `pyreadstat` library required for SPSS (.sav) files. Install via pip install pyreadstat.")
                return None

        elif ext == 'sas7bdat':  # SAS
            try:
                import pyreadstat
                if isinstance(file_obj_or_path, (str, Path)):
                    df, meta = pyreadstat.read_sas7bdat(str(file_obj_or_path))
                else:
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".sas7bdat") as tmp:
                        tmp.write(file_obj_or_path.read())
                        tmp_path = tmp.name
                    df, meta = pyreadstat.read_sas7bdat(tmp_path)
                    os.unlink(tmp_path)
                return df
            except ImportError:
                st.error("⚠️ `pyreadstat` library required for SAS files.")
                return None

        elif ext == 'dta':  # STATA
            try:
                import pyreadstat
                if isinstance(file_obj_or_path, (str, Path)):
                    df, meta = pyreadstat.read_dta(str(file_obj_or_path))
                else:
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".dta") as tmp:
                        tmp.write(file_obj_or_path.read())
                        tmp_path = tmp.name
                    df, meta = pyreadstat.read_dta(tmp_path)
                    os.unlink(tmp_path)
                return df
            except ImportError:
                st.error("⚠️ `pyreadstat` library required for STATA files.")
                return None

        elif ext == 'parquet':
            return pd.read_parquet(file_obj_or_path)

        elif ext == 'feather':
            return pd.read_feather(file_obj_or_path)

        elif ext in ['pkl', 'pickle']:
            return pd.read_pickle(file_obj_or_path)

        else:
            # Fallback to standard module parser
            return parse_uploaded_file(file_obj_or_path)

    except Exception as e:
        st.error(f"❌ Error parsing file '{getattr(file_obj_or_path, 'name', file_obj_or_path)}': {e}")
        return None

# ─── Ingestion Mode Selector ───────────────────────────────────────────
st.markdown("---")
ingestion_mode = st.radio(
    "Select Data Ingestion Channel",
    options=["📤 Direct File Uploader (Standard)", "📂 Local Server / Directory Explorer"],
    horizontal=True
)

active_df = None

if ingestion_mode == "📤 Direct File Uploader (Standard)":
    section_header("📤 Upload Data File")
    st.caption(f"Supported formats: {', '.join(SUPPORTED_FORMATS.keys())}, SPSS (.sav), SAS (.sas7bdat), STATA (.dta), Parquet, Feather")

    uploaded_file = st.file_uploader(
        "Choose a data file",
        type=["csv", "xlsx", "xls", "json", "sav", "sas7bdat", "dta", "parquet", "feather", "pkl", "txt"],
        help="Upload your dataset for instant profiling and automated analysis.",
    )

    if uploaded_file is not None:
        with st.spinner(f"Parsing '{uploaded_file.name}' with advanced format handler..."):
            active_df = robust_parse_file(uploaded_file)

else:
    section_header("📂 Local Server & Directory Explorer")
    st.markdown("Scan local workspace paths or specify a directory to load datasets directly from disk.")
    
    default_path = str(root_dir)
    target_dir = st.text_input("Directory Path to Scan", value=default_path, placeholder="/path/to/data/folder")
    
    if os.path.exists(target_dir) and os.path.isdir(target_dir):
        valid_extensions = ('.csv', '.xlsx', '.xls', '.json', '.sav', '.sas7bdat', '.dta', '.parquet', '.feather', '.pkl')
        
        found_files = []
        for root, dirs, files in os.walk(target_dir):
            # Skip hidden/venv folders
            if any(p.startswith('.') or p in ['venv', '__pycache__', 'node_modules'] for p in Path(root).parts):
                continue
            for f in files:
                if f.lower().endswith(valid_extensions):
                    found_files.append(os.path.join(root, f))
        
        if found_files:
            st.success(f"🔍 Discovered {len(found_files)} readable data file(s) in directory.")
            selected_local_file = st.selectbox(
                "Select Data File from Directory",
                options=found_files,
                format_func=lambda x: os.path.relpath(x, target_dir)
            )
            
            if st.button("🚀 Load and Analyze Selected File", type="primary", use_container_width=True):
                with st.spinner(f"Reading '{os.path.basename(selected_local_file)}'..."):
                    active_df = robust_parse_file(selected_local_file)
        else:
            st.info("📭 No supported data files found in this directory path.")
    else:
        st.error("⚠️ Invalid directory path specified. Please verify the folder location.")

# ─── Dataset Analysis & Visualization Hub ──────────────────────────────
if active_df is not None and not active_df.empty:
    st.session_state["uploaded_df"] = active_df
    st.session_state["active_df"] = active_df
    st.session_state["data_source"] = "advanced_analyzer"

    st.markdown("---")
    section_header("📊 Dataset Overview & Statistical Summary")
    
    profile = profile_dataset(active_df)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Rows", f"{profile['rows']:,}")
    with col2:
        st.metric("Total Columns", f"{profile['columns']:,}")
    with col3:
        st.metric("Numeric Columns", len(profile.get("numeric_columns", [])))
    with col4:
        st.metric("Categorical Columns", len(profile.get("categorical_columns", [])))

    # Data preview with search & column filter
    section_header("👁️ Interactive Data Preview")
    col_prev1, col_prev2 = st.columns([2, 1])
    with col_prev1:
        row_limit = st.slider("Display Row Count", min_value=10, max_value=min(1000, len(active_df)), value=50, step=10)
    with col_prev2:
        show_summary_stats = st.checkbox("Show Descriptive Statistics (.describe())", value=True)

    st.dataframe(active_df.head(row_limit), use_container_width=True, hide_index=True)

    if show_summary_stats:
        with st.expander("📈 Advanced Statistical Breakdown"):
            st.dataframe(active_df.describe(include="all"), use_container_width=True)

    # Column Types & Metadata
    section_header("📋 Column Metadata & Data Types")
    col_types = infer_column_types(active_df)
    type_df = pd.DataFrame([
        {
            "Column Name": col, 
            "Data Type": str(active_df[col].dtype),
            "Inferred Type": ctype,
            "Null Count": int(active_df[col].isnull().sum()),
            "Unique Values": int(active_df[col].nunique())
        } 
        for col, ctype in col_types.items()
    ])
    st.dataframe(type_df, use_container_width=True, hide_index=True)

    # Export Section
    section_header("📥 Export Processed Dataset")
    render_export_buttons(active_df)

    # Merge option with Notion or secondary buffers
    if st.session_state.get("notion_df") is not None and not st.session_state["notion_df"].empty:
        section_header("🔗 Merge with Notion Data")
        notion_df = st.session_state["notion_df"]

        common_cols = list(set(active_df.columns) & set(notion_df.columns))
        merge_key = st.selectbox(
            "Merge key column (optional)",
            options=[""] + common_cols,
            help="Select a common column to merge on. If none selected, datasets will be concatenated."
        )
        merge_how = st.selectbox("Merge method", options=["inner", "outer", "left", "right"], index=0)

        if st.button("🔄 Execute Dataset Merge", type="primary"):
            merged = merge_datasets(notion_df, active_df, merge_key=merge_key or None, merge_how=merge_how)
            if merged is not None and not merged.empty:
                st.session_state["merged_df"] = merged
                st.session_state["active_df"] = merged
                st.session_state["data_source"] = "merged"
                st.success(f"✅ Successfully merged datasets: {len(merged)} rows × {len(merged.columns)} columns")
                st.dataframe(merged.head(20), use_container_width=True, hide_index=True)

elif active_df is not None and active_df.empty:
    st.warning("⚠️ The selected file parsed successfully, but the dataset is completely empty.")

# ─── Manual Data Entry Fallback ──────────────────────────────────────
st.markdown("---")
section_header("✏️ Or Enter Data Manually")
manual_df = manual_data_entry()
if manual_df is not None and not manual_df.empty:
    st.session_state["active_df"] = manual_df
    st.session_state["data_source"] = "manual"
    st.dataframe(manual_df, use_container_width=True, hide_index=True)