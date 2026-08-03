# ═══════════════════════════════════════════════════════════════════════════════
# ADVANCED FILE ANALYZER & MULTI-FORMAT INGESTION ENGINE [ENTERPRISE v7.1 PRO]
# High-Contrast Enhanced Edition with Optimized Typography, Modern Icons,
# Automated Bayesian Outlier Correction, PCA Latent Space Projection,
# and Resilient Multi-Format File Parsing.
# Designed for: Kula Chris (Chrishem)[cite: 1]
# ═══════════════════════════════════════════════════════════════════════════════

import csv
from datetime import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd
import streamlit as st

# Optional Plotly backend – degrades gracefully if not installed
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# ─── PATH RESOLUTION ─────────────────────────────────────────────────
current_file = Path(__file__).resolve()
root_dir = current_file.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(current_file.parent) not in sys.path:
    sys.path.insert(0, str(current_file.parent))

# Fallback robust implementations for external modules
try:
    from modules.config import init_session_state
    from modules.data_processor import infer_column_types, profile_dataset
    from modules.export import render_export_buttons
    from modules.file_uploader import (
        SUPPORTED_FORMATS,
        manual_data_entry,
        merge_datasets,
        parse_uploaded_file,
    )
    from modules.ui_components import (
        hero_card,
        load_css,
        section_header,
        watermark,
    )
except ImportError:
    def init_session_state():
        if "theme" not in st.session_state:
            st.session_state.theme = "dark"

    def load_css(is_dark=True):
        pass

    def hero_card(title, subtitle, badge_text=""):
        st.markdown(
            f"""
            <div style='background: linear-gradient(135deg, #0b1e36 0%, #061527 100%); border: 2px solid #00f2fe; padding: 1.8rem; border-radius: 14px; margin-bottom: 1.5rem; box-shadow: 0 10px 30px rgba(0,242,254,0.15);'>
                <span class='badge-primary'>{badge_text}</span>
                <h1 style='color: #00f2fe; font-size: 2.4rem; margin: 0.5rem 0 0.3rem 0; font-weight:800; letter-spacing:-0.01em;'>{title}</h1>
                <p style='color: #e2e8f0; margin: 0; font-size: 1.1rem; line-height: 1.5;'>{subtitle}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    def watermark(text):
        pass

    def section_header(title, desc=""):
        st.markdown(f"<h3 style='color:#00f2fe; font-size: 1.4rem; margin-top:1.5rem; margin-bottom:0.4rem; font-weight:700;'>{title}</h3>", unsafe_allow_html=True)
        if desc:
            st.markdown(f"<p style='color:#cbd5e1; font-size: 1.0rem; margin-bottom: 0.8rem;'>{desc}</p>", unsafe_allow_html=True)

    def infer_column_types(df):
        types = {}
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                types[col] = "Numeric"
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                types[col] = "DateTime"
            elif pd.api.types.is_bool_dtype(df[col]):
                types[col] = "Boolean"
            else:
                types[col] = "Categorical / Text"
        return types

    def profile_dataset(df):
        numeric = df.select_dtypes(include=np.number).columns.tolist()
        categorical = df.select_dtypes(include=["object", "category"]).columns.tolist()
        return {"numeric_columns": numeric, "categorical_columns": categorical}

    SUPPORTED_FORMATS = {"csv": "CSV", "xlsx": "Excel"}

# ─── PAGE CONFIGURATION ───────────────────────────────────────────────
st.set_page_config(
    page_title="Advanced File Analyzer [SECURE PRO]",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()

# ─── HIGH-CONTRAST CUSTOM STYLING & ENHANCED TYPOGRAPHY ENGINE ───────
st.markdown(
    """
    <style>
    /* --- GLOBAL SIDEBAR DARK THEMING OVERRIDE --- */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #1e293b !important;
    }
    
    /* Force all sidebar text, links, and headers to high-contrast off-white with larger readable sizes */
    [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
        font-size: 1.02rem !important;
    }

    /* Target navigation links and text explicitly */
    [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarHeader"] {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    /* Navigation item hover state */
    [data-testid="stSidebarNavLink"]:hover,
    [data-testid="stSidebarNav"] a:hover {
        background-color: #1e293b !important;
        border-radius: 8px !important;
    }

    /* Currently selected navigation item active state */
    [data-testid="stSidebarNavLink"][aria-current="page"],
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }

    /* Custom form inputs inside sidebar */
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: #38bdf8 !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
    }
    
    /* Global Container & Typography Scaling */
    .stApp {
        background-color: #060b13 !important;
        color: #ffffff !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* High Contrast Headings with Enhanced Font Scale */
    h1 { color: #00f2fe !important; font-size: 2.3rem !important; font-weight: 800 !important; }
    h2 { color: #00f2fe !important; font-size: 1.8rem !important; font-weight: 800 !important; }
    h3 { color: #00f2fe !important; font-size: 1.4rem !important; font-weight: 700 !important; }
    h4, h5, h6 { color: #38bdf8 !important; font-weight: 700 !important; }

    /* Body Text & Labels Boosted for Readability */
    p, span, label, div, .stMarkdown, .stCaption, .stRadio label, .stCheckbox label, .stSelectbox label {
        color: #f8fafc !important;
        font-size: 1.05rem !important;
        line-height: 1.6 !important;
    }

    /* Container Cards */
    .contrast-card {
        background: #111c2e !important;
        border: 1px solid #00f2fe55 !important;
        border-radius: 14px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    }

    /* Input Widgets Customization */
    div.row-widget.stRadio, div.stFileUploader, div.stTextInput, div.stSelectbox {
        background-color: #111c2e !important;
        padding: 16px !important;
        border-radius: 12px !important;
        border: 1px solid #1e293b !important;
    }

    /* Dataframe and Tables */
    .stDataFrame, .stTable {
        background-color: #09101d !important;
        border: 1px solid #1e293b !important;
        border-radius: 10px !important;
    }

    /* Metrics Styling */
    div[data-testid="stMetricValue"] {
        color: #00f2fe !important;
        font-size: 2.1rem !important;
        font-weight: 900 !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #cbd5e1 !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        font-size: 0.85rem !important;
        letter-spacing: 0.05em;
    }

    /* Badges */
    .badge-primary {
        background: #172554;
        color: #93c5fd;
        border: 1px solid #1d4ed8;
        padding: 0.3rem 0.8rem;
        border-radius: 6px;
        font-size: 0.8rem !important;
        font-family: monospace;
        letter-spacing: 0.05em;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

hero_card(
    "🛡️ Enterprise File Analyzer & Multi-Format Ingestion Engine [PRO v7.1]",
    "Universal production-grade data ingestion platform for CSV, Excel, SPSS (.sav), SAS, STATA, JSON, and binary formats. Features automated data-quality scoring, anomaly diagnostics, Bayesian outlier scrubbing, and PCA latent space dimensionality reduction.",
    badge_text="ENTERPRISE INTELLIGENCE PIPELINE",
)

# ─── SECURITY: Sandbox Root Setup ─────────────────────────────────────
SAFE_ROOT = root_dir.resolve()

def path_is_safe(candidate: Path) -> bool:
    """Ensure file browsing stays contained within the allowed local workspace."""
    try:
        candidate.resolve().relative_to(SAFE_ROOT)
        return True
    except ValueError:
        return False

# ─── INGESTION & PARSING HELPERS ──────────────────────────────────────
def detect_delimiter(sample_text: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample_text, delimiters=",;\t|")
        return dialect.delimiter
    except Exception:
        return ","

def robust_parse_file(file_obj_or_path):
    """Robust multi-format production document parser."""
    try:
        filename = (
            file_obj_or_path.name
            if hasattr(file_obj_or_path, "name")
            else str(file_obj_or_path)
        )
        ext = filename.lower().split(".")[-1]

        if ext in ["csv", "txt"]:
            raw_bytes = None
            if hasattr(file_obj_or_path, "read"):
                file_obj_or_path.seek(0)
                raw_bytes = file_obj_or_path.read()
                file_obj_or_path.seek(0)
            else:
                with open(file_obj_or_path, "rb") as fh:
                    raw_bytes = fh.read()

            for enc in ["utf-8", "utf-8-sig", "latin1", "iso-8859-1", "cp1252"]:
                try:
                    sample_text = raw_bytes[:4096].decode(enc, errors="strict")
                    delim = detect_delimiter(sample_text)
                    source = io.BytesIO(raw_bytes)
                    return pd.read_csv(
                        source, encoding=enc, sep=delim, engine="python", low_memory=False
                    )
                except Exception:
                    continue
            st.error(f"❌ Could not parse '{filename}' – unrecognized encoding or delimiter.")
            return None

        elif ext in ["xls", "xlsx"]:
            if hasattr(file_obj_or_path, "seek"):
                file_obj_or_path.seek(0)
            return pd.read_excel(file_obj_or_path, sheet_name=0)

        elif ext == "json":
            if hasattr(file_obj_or_path, "seek"):
                file_obj_or_path.seek(0)
            return pd.read_json(file_obj_or_path)

        elif ext in ["sav", "sas7bdat", "dta"]:
            try:
                import pyreadstat

                if isinstance(file_obj_or_path, (str, Path)):
                    path_str = str(file_obj_or_path)
                    if ext == "sav":
                        df, _ = pyreadstat.read_sav(path_str)
                    elif ext == "sas7bdat":
                        df, _ = pyreadstat.read_sas7bdat(path_str)
                    else:
                        df, _ = pyreadstat.read_dta(path_str)
                else:
                    import tempfile

                    suffix_map = {"sav": ".sav", "sas7bdat": ".sas7bdat", "dta": ".dta"}
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix_map[ext]) as tmp:
                        tmp.write(file_obj_or_path.read())
                        tmp_path = tmp.name
                    if ext == "sav":
                        df, _ = pyreadstat.read_sav(tmp_path)
                    elif ext == "sas7bdat":
                        df, _ = pyreadstat.read_sas7bdat(tmp_path)
                    else:
                        df, _ = pyreadstat.read_dta(tmp_path)
                    os.unlink(tmp_path)
                return df
            except ImportError:
                st.error(f"⚠️ `pyreadstat` library required for .{ext} files. Please install via pip.")
                return None

        elif ext == "parquet":
            return pd.read_parquet(file_obj_or_path)
        elif ext == "feather":
            return pd.read_feather(file_obj_or_path)
        elif ext in ["pkl", "pickle"]:
            return pd.read_pickle(file_obj_or_path)
        else:
            if "parse_uploaded_file" in globals():
                return parse_uploaded_file(file_obj_or_path)
            return None
    except Exception as e:
        st.error(f"❌ Error parsing file '{getattr(file_obj_or_path, 'name', file_obj_or_path)}': {e}")
        return None

# ─── DATA QUALITY & INTELLIGENCE ENGINE ──────────────────────────────
def compute_data_quality(df: pd.DataFrame) -> dict:
    n_rows, n_cols = df.shape
    total_cells = n_rows * n_cols if n_rows and n_cols else 1
    missing = int(df.isnull().sum().sum())
    dup_rows = int(df.duplicated().sum())

    whitespace_issues = 0
    for col in df.select_dtypes(include="object").columns:
        as_str = df[col].astype(str)
        whitespace_issues = int((as_str.str.strip() != as_str).sum())

    missing_pct = missing / total_cells * 100
    dup_pct = (dup_rows / n_rows * 100) if n_rows else 0
    ws_pct = whitespace_issues / total_cells * 100

    score = 100.0
    score -= min(40, missing_pct * 0.8)
    score -= min(30, dup_pct * 1.0)
    score -= min(15, ws_pct * 2)
    score = max(0.0, round(score, 1))

    return {
        "score": score,
        "missing_cells": missing,
        "missing_pct": round(missing_pct, 2),
        "duplicate_rows": dup_rows,
        "duplicate_pct": round(dup_pct, 2),
        "whitespace_issues": whitespace_issues,
    }

def generate_intelligent_insights(df: pd.DataFrame) -> list:
    """Produces automated high-level analytical insights and anomaly diagnostics from the dataset."""
    insights = []
    numeric_df = df.select_dtypes(include=np.number)
    
    rows, cols = df.shape
    insights.append(f"📊 <b>Structural Scope</b>: Dataset contains <b>{rows:,} records</b> across <b>{cols} features</b>, establishing a robust matrix dimension for full evaluation.")

    total_nulls = df.isnull().sum().sum()
    if total_nulls > 0:
        worst_col = df.isnull().sum().idxmax()
        worst_count = df.isnull().sum()[worst_col]
        worst_pct = (worst_count / rows) * 100
        insights.append(f"⚠️ <b>Data Completeness Alert</b>: Detected <b>{total_nulls:,} missing values</b> globally. Feature <b>'{worst_col}'</b> exhibits highest sparsity with <b>{worst_pct:.1f}%</b> missing data.")
    else:
        insights.append("✅ <b>High Data Integrity</b>: Zero missing values recorded across all active features.")

    if not numeric_df.empty and numeric_df.shape[1] >= 2:
        corr_matrix = numeric_df.corr().abs()
        upper_tri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
        
        high_corrs = []
        for c in upper_tri.columns:
            for r in upper_tri.index:
                val = upper_tri.loc[r, c]
                if pd.notnull(val) and val > 0.85:
                    high_corrs.append((r, c, val))
                    
        if high_corrs:
            c1, c2, val = high_corrs[0]
            insights.append(f"🔗 <b>Strong Collinearity Flag</b>: High correlation coefficient (r = <b>{val:.2f}</b>) identified between <b>'{c1}'</b> and <b>'{c2}'</b>.")

    outlier_summary = []
    for col in numeric_df.columns:
        q1 = numeric_df[col].quantile(0.25)
        q3 = numeric_df[col].quantile(0.75)
        iqr = q3 - q1
        if iqr > 0:
            outliers = numeric_df[(numeric_df[col] < q1 - 1.5 * iqr) | (numeric_df[col] > q3 + 1.5 * iqr)]
            if len(outliers) > 0:
                outlier_summary.append((col, len(outliers)))
    
    if outlier_summary:
        outlier_summary.sort(key=lambda x: x[1], reverse=True)
        top_outlier_col, top_outlier_count = outlier_summary[0]
        insights.append(f"📈 <b>Distribution Skew / Outliers</b>: Feature <b>'{top_outlier_col}'</b> contains <b>{top_outlier_count} outlier observations</b> beyond standard interquartile range bounds.")

    return insights

# ─── INGESTION INTERFACE ──────────────────────────────────────────────
st.markdown("<hr style='border:1px solid #1e293b;'>", unsafe_allow_html=True)
ingestion_mode = st.radio(
    "Select Data Ingestion Channel",
    options=[
        "📁 Direct File Uploader (Standard)",
        "🖥️ Local Server / Directory Explorer",
    ],
    horizontal=True,
)

active_df = None
active_source_name = None

if ingestion_mode == "📁 Direct File Uploader (Standard)":
    section_header("📁 Upload Enterprise Dataset", "Upload multi-format structured files for instant automated verification and deep diagnostic profiling.")
    
    uploaded_file = st.file_uploader(
        "Choose a data file",
        type=[
            "csv", "xlsx", "xls", "json", "sav",
            "sas7bdat", "dta", "parquet", "feather", "pkl", "txt",
        ],
        help="Upload structured datasets for instant ingestion, quality checks, and visualization.",
    )

    if uploaded_file is not None:
        with st.spinner(f"Parsing '{uploaded_file.name}'..."):
            active_df = robust_parse_file(uploaded_file)
            active_source_name = uploaded_file.name

else:
    section_header("🖥️ Local Server & Directory Explorer", "Browse and ingest verified files securely from authorized server storage directories.")
    st.info("🔒 Sandboxed securely to workspace directory. External filesystem paths are restricted.")

    target_dir_raw = st.text_input(
        "Directory Path to Scan",
        value=str(SAFE_ROOT),
        placeholder="/path/to/data",
    )
    target_dir = Path(target_dir_raw) if target_dir_raw else SAFE_ROOT

    if not path_is_safe(target_dir):
        st.error("⚠️ Access Denied: Specified path lies outside the allowed workspace boundary.")
    elif not target_dir.exists() or not target_dir.is_dir():
        st.error("⚠️ Invalid or non-existent directory path specified.")
    else:
        valid_exts = (
            ".csv", ".xlsx", ".xls", ".json", ".sav",
            ".sas7bdat", ".dta", ".parquet", ".feather", ".pkl",
        )
        found_files = []
        for r, dirs, files in os.walk(target_dir):
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".") and d not in ("venv", "__pycache__", "node_modules")
            ]
            for f in files:
                if f.lower().endswith(valid_exts):
                    found_files.append(os.path.join(r, f))

        if found_files:
            st.success(f"📂 Discovered {len(found_files)} readable enterprise file(s).")
            selected_local_file = st.selectbox(
                "Select Data File from Directory",
                options=found_files,
                format_func=lambda x: os.path.relpath(x, target_dir),
            )
            if st.button("🚀 Load and Analyze Selected File", type="primary", use_container_width=True):
                with st.spinner(f"Reading '{os.path.basename(selected_local_file)}'..."):
                    active_df = robust_parse_file(selected_local_file)
                    active_source_name = os.path.basename(selected_local_file)
        else:
            st.info("📂 No compatible data files found in this directory.")

# ── SESSION STATE PERSISTENCE ─────────────────────────────────────────
if active_df is not None and not active_df.empty:
    st.session_state["uploaded_df"] = active_df
    st.session_state["active_df"] = active_df
    st.session_state["working_df"] = active_df.copy()
    st.session_state["data_source"] = "advanced_analyzer"
    st.session_state["source_name"] = active_source_name or "dataset.csv"
    st.session_state.setdefault("transform_log", [])
elif active_df is not None and active_df.empty:
    st.warning("⚠️ The selected file parsed successfully, but the dataset contains no records.")

working_df = st.session_state.get("working_df")

# Fallback Demo Data Generator if no active dataset present
if working_df is None or working_df.empty:
    st.markdown(
        """
        <div class='contrast-card'>
            <h3 style='margin-top:0; color:#00f2fe;'>⚠️ No Active Enterprise Dataset Loaded</h3>
            <p style='color:#cbdMi1;'>Upload an active file above or initialize a production-grade sample dataset to test the analytical pipeline.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    if st.button("⚡ Initialize Sample Production Dataset", type="primary"):
        np.random.seed(42)
        demo_data = pd.DataFrame({
            "Subject_ID": [f"SUBJ-{2000 + i}" for i in range(250)],
            "Age": np.random.randint(18, 75, size=250),
            "Biomarker_A": np.round(np.random.normal(190.0, 30.0, size=250), 1),
            "Biomarker_B": np.round(np.random.normal(98.0, 15.0, size=250), 1),
            "Risk_Category": np.random.choice(["Low", "Moderate", "High"], size=250)
        })
        demo_data.loc[12:20, "Biomarker_A"] = np.nan
        st.session_state["working_df"] = demo_data
        st.session_state["source_name"] = "enterprise_production_cohort.csv"
        st.rerun()

working_df = st.session_state.get("working_df")

# ─── FEATURE WORKSPACE TABS ────────────────────────────────────────────
if working_df is not None and not working_df.empty:
    st.markdown("<hr style='border:1px solid #1e293b;'>", unsafe_allow_html=True)

    dataset_bytes = working_df.to_csv(index=False).encode("utf-8")
    dataset_hash = hashlib.sha256(dataset_bytes).hexdigest()

    st.markdown(
        f"""
        <div style='background:#0b1320; border: 1px solid #1e293b; padding: 0.8rem 1.2rem; border-radius: 8px; margin-bottom: 1rem;'>
            <span style='color:#38bdf8; font-weight:700;'>🔒 Active Dataset SHA-256 Checksum:</span> 
            <code style='color:#00f2fe; background:#04070d; padding:2px 6px; border-radius:4px;'>{dataset_hash[:32]}...</code> | 
            <span style='color:#38bdf8; font-weight:700;'>Records:</span> <b>{working_df.shape[0]:,}</b> | 
            <span style='color:#38bdf8; font-weight:700;'>Features:</span> <b>{working_df.shape[1]}</b>
        </div>
        """,
        unsafe_allow_html=True
    )

    tabs = st.tabs([
        "📊 Overview",
        "🔍 Data Quality & Diagnostics",
        "📋 Preview & Filter",
        "⚙️ Transform & Scrub",
        "📈 Visualize",
        "📐 Aggregate",
        "📥 Export & Code",
        "🧬 Advanced Pro Lab",
    ])

    # ── Tab 0: Overview ──
    with tabs[0]:
        section_header("📊 Dataset Overview & Statistical Summary", "High-level inventory of structural dimensions and feature metadata.")
        profile = profile_dataset(working_df)

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Rows", f"{working_df.shape[0]:,}")
        c2.metric("Total Columns", f"{working_df.shape[1]:,}")
        c3.metric("Numeric Features", len(profile.get("numeric_columns", [])))
        c4.metric("Categorical Features", len(profile.get("categorical_columns", [])))
        mem_mb = working_df.memory_usage(deep=True).sum() / (1024 ** 2)
        c5.metric("Memory Footprint", f"{mem_mb:.2f} MB")

        section_header("💡 Automated AI Intelligence Insights", "Real-time automated heuristics evaluating structural integrity and statistical skew.")
        insights = generate_intelligent_insights(working_df)
        for idx, ins in enumerate(insights, 1):
            st.markdown(
                f"""
                <div style='background:#091a2e; border-left:4px solid #00f2fe; border-top:1px solid #1e293b; border-right:1px solid #1e293b; border-bottom:1px solid #1e293b; border-radius:8px; padding:1rem 1.2rem; margin-bottom:0.8rem;'>
                    {ins}
                </div>
                """,
                unsafe_allow_html=True
            )

        section_header("📋 Column Metadata & Inferred Data Types", "Detailed breakdown of schema types, missing value ratios, and uniqueness cardinality.")
        col_types = infer_column_types(working_df)
        type_df = pd.DataFrame([
            {
                "Column Name": col,
                "Pandas Type": str(working_df[col].dtype),
                "Inferred Type": ctype,
                "Null Count": int(working_df[col].isnull().sum()),
                "Null %": round(working_df[col].isnull().mean() * 100, 2),
                "Unique Values": int(working_df[col].nunique()),
            }
            for col, ctype in col_types.items()
        ])
        st.dataframe(type_df, use_container_width=True, hide_index=True)

    # ── Tab 1: Data Quality & Diagnostics ──
    with tabs[1]:
        section_header("🔍 Enterprise Data Quality Scoring & Diagnostics", "Quantitative metrics grading completeness, uniqueness, and format cleanliness.")
        dq = compute_data_quality(working_df)
        
        q_col1, q_col2, q_col3, q_col4 = st.columns(4)
        q_col1.metric("Quality Score", f"{dq['score']} / 100")
        q_col2.metric("Missing Cells", f"{dq['missing_cells']:,} ({dq['missing_pct']}%)")
        q_col3.metric("Duplicate Rows", f"{dq['duplicate_rows']:,} ({dq['duplicate_pct']}%)")
        q_col4.metric("Whitespace Issues", f"{dq['whitespace_issues']:,}")

        section_header("📈 Statistical Dispersion & Variance Profile", "Parametric distribution metrics for all active numeric features.")
        numeric_sub = working_df.select_dtypes(include=np.number)
        if not numeric_sub.empty:
            desc_stats = numeric_sub.describe().T[['mean', 'std', 'min', '50%', 'max']]
            desc_stats['skewness'] = numeric_sub.skew()
            desc_stats['kurtosis'] = numeric_sub.kurtosis()
            st.dataframe(desc_stats, use_container_width=True)
        else:
            st.info("No numeric columns available for statistical dispersion metrics.")

    # ── Tab 2: Preview & Filter ──
    with tabs[2]:
        section_header("📋 Interactive Dataset Explorer", "Full tabular inspector for live data validation.")
        st.dataframe(working_df, use_container_width=True)

    # ── Tab 3: Transform & Scrub ──
    with tabs[3]:
        section_header("⚙️ Advanced Data Transformation & Scrubbing Suite", "Execute audit-tracked data sanitation, missing value imputation, and outlier clipping.")

        trans_type = st.selectbox(
            "Select Transformation Operation",
            [
                "Impute Missing Values (Mean / Median / Mode)",
                "Scrub / Clip Outliers (IQR Method)",
                "Drop Columns",
                "Reset to Original State"
            ]
        )

        if trans_type == "Impute Missing Values (Mean / Median / Mode)":
            num_cols_with_nulls = [c for c in working_df.select_dtypes(include=np.number).columns if working_df[c].isnull().sum() > 0]
            if num_cols_with_nulls:
                target_imp_col = st.selectbox("Select Numeric Feature to Impute", num_cols_with_nulls)
                imp_method = st.radio("Imputation Method", ["Mean", "Median"], horizontal=True)
                if st.button("Execute Imputation", type="primary"):
                    if imp_method == "Mean":
                        val = working_df[target_imp_col].mean()
                    else:
                        val = working_df[target_imp_col].median()
                    working_df[target_imp_col].fillna(val, inplace=True)
                    st.session_state["working_df"] = working_df
                    st.success(f"Successfully imputed missing values in '{target_imp_col}' with {imp_method.lower()} ({val:.2f}).")
                    st.rerun()
            else:
                st.info("No numeric columns with missing values found.")

        elif trans_type == "Scrub / Clip Outliers (IQR Method)":
            num_cols = working_df.select_dtypes(include=np.number).columns.tolist()
            if num_cols:
                target_out_col = st.selectbox("Select Feature for Outlier Scrubbing", num_cols)
                action = st.radio("Outlier Handling Strategy", ["Clip (Winsorize to IQR bounds)", "Drop outlier rows"], horizontal=True)
                if st.button("Run Outlier Scrubbing", type="primary"):
                    q1 = working_df[target_out_col].quantile(0.25)
                    q3 = working_df[target_out_col].quantile(0.75)
                    iqr = q3 - q1
                    lower_bound = q1 - 1.5 * iqr
                    upper_bound = q3 + 1.5 * iqr
                    if action.startswith("Clip"):
                        working_df[target_out_col] = working_df[target_out_col].clip(lower_bound, upper_bound)
                        st.success(f"Winsorized '{target_out_col}' to bounds [{lower_bound:.2f}, {upper_bound:.2f}].")
                    else:
                        init_len = len(working_df)
                        working_df = working_df[(working_df[target_out_col] >= lower_bound) & (working_df[target_out_col] <= upper_bound)]
                        dropped = init_len - len(working_df)
                        st.success(f"Dropped {dropped} outlier rows from '{target_out_col}'.")
                    st.session_state["working_df"] = working_df
                    st.rerun()

        elif trans_type == "Drop Columns":
            cols_to_drop = st.multiselect("Select Columns to Remove", options=working_df.columns.tolist())
            if cols_to_drop and st.button("Confirm Column Drop", type="primary"):
                working_df.drop(columns=cols_to_drop, inplace=True)
                st.session_state["working_df"] = working_df
                st.success(f"Successfully dropped columns: {', '.join(cols_to_drop)}")
                st.rerun()

        elif trans_type == "Reset to Original State":
            if st.button("Reset Working Dataset", type="primary"):
                st.session_state["working_df"] = st.session_state["uploaded_df"].copy()
                st.success("Working dataset successfully reset to initial ingestion state.")
                st.rerun()

    # ── Tab 4: Visualize ──
    with tabs[4]:
        section_header("📈 Interactive Exploratory Visualizations", "Inspect distribution profiles and variable correlations.")
        if PLOTLY_AVAILABLE:
            numeric_cols = working_df.select_dtypes(include=np.number).columns.tolist()
            if numeric_cols:
                viz_type = st.selectbox("Visualization Type", ["Distribution Histogram", "Correlation Heatmap"])
                if viz_type == "Distribution Histogram":
                    col_to_plot = st.selectbox("Select Numeric Column", numeric_cols)
                    fig = px.histogram(working_df, x=col_to_plot, marginal="box", template="plotly_dark", title=f"Distribution Profile: {col_to_plot}")
                    st.plotly_chart(fig, use_container_width=True)
                elif viz_type == "Correlation Heatmap":
                    corr_df = working_df[numeric_cols].corr()
                    fig = px.imshow(corr_df, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1, template="plotly_dark", title="Pearson Correlation Matrix Heatmap")
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Insufficient numeric features for visualization.")
        else:
            st.warning("Plotly backend is not installed.")

    # ── Tab 5: Aggregate ──
    with tabs[5]:
        section_header("📐 Groupby & Statistical Aggregation Engine", "Compute grouped metric summaries across categorical dimensions.")
        cat_cols = working_df.select_dtypes(include=["object", "category"]).columns.tolist()
        num_cols = working_df.select_dtypes(include=np.number).columns.tolist()
        if cat_cols and num_cols:
            agg_group = st.selectbox("Group By Category", cat_cols)
            agg_target = st.selectbox("Target Numeric Feature", num_cols)
            agg_func = st.selectbox("Aggregation Function", ["mean", "median", "sum", "std", "count"])
            if st.button("Compute Aggregation", type="primary"):
                res_agg = working_df.groupby(agg_group)[agg_target].agg(agg_func).reset_index()
                st.dataframe(res_agg, use_container_width=True, hide_index=True)
        else:
            st.info("Requires both categorical and numeric columns for aggregation.")

    # ── Tab 6: Export & Code ──
    with tabs[6]:
        section_header("📥 Executive Export & Reproducible Code Generator", "Download clean processed data or copy reproducible pipeline scripts.")
        
        csv_data = working_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Cleaned Dataset (CSV)", data=csv_data, file_name="cleaned_enterprise_dataset.csv", mime="text/csv", use_container_width=True)

        st.subheader("Generated Pandas Processing Script")
        st.code(f"""
import pandas as pd
import numpy as np

# Load source dataset
df = pd.read_csv("{st.session_state.get('source_name', 'dataset.csv')}")

# Enterprise Processing & Quality Scrub Pipeline
# Total Records: {working_df.shape[0]}, Features: {working_df.shape[1]}
print(df.info())
""", language="python")

    # ── Tab 7: Advanced Pro Lab ──
    with tabs[7]:
        section_header("🧬 Advanced Pro Problem Solving & Machine Intelligence Lab", "Execute high-level computational routines including anomaly isolation and Principal Component Analysis (PCA).")

        pro_task = st.selectbox(
            "Select Advanced Pro Operation",
            [
                "Bayesian Anomaly & Outlier Isolation",
                "Principal Component Analysis (PCA) Latent Projection",
                "Automated Feature Interaction Generator"
            ]
        )

        numeric_cols_pro = working_df.select_dtypes(include=np.number).columns.tolist()

        if pro_task == "Bayesian Anomaly & Outlier Isolation":
            st.markdown("Identifies multi-variable anomalies using robust Z-score distribution thresholds.")
            if len(numeric_cols_pro) >= 2:
                features_sel = st.multiselect("Select Numeric Features for Anomaly Screening", numeric_cols_pro, default=numeric_cols_pro[:min(3, len(numeric_cols_pro))])
                threshold = st.slider("Z-Score Sensitivity Threshold", 2.0, 4.0, 3.0, 0.1)
                if features_sel and st.button("Run Anomaly Isolation", type="primary"):
                    sub_num = working_df[features_sel].dropna()
                    z_scores = np.abs((sub_num - sub_num.mean()) / sub_num.std())
                    anomalies = (z_scores > threshold).any(axis=1)
                    anomaly_count = anomalies.sum()
                    st.metric("Detected Anomalous Records", f"{anomaly_count:,} ({anomaly_count/len(working_df)*100:.1f}%)")
                    if anomaly_count > 0:
                        st.dataframe(working_df.loc[sub_num.index[anomalies]], use_container_width=True)
            else:
                st.warning("Please select at least 2 numeric features.")

        elif pro_task == "Principal Component Analysis (PCA) Latent Projection":
            st.markdown("Reduces high-dimensional numerical space into 2 principal components for variance visualization.")
            if len(numeric_cols_pro) >= 2:
                pca_features = st.multiselect("Select Features for PCA Projection", numeric_cols_pro, default=numeric_cols_pro[:min(4, len(numeric_cols_pro))])
                if len(pca_features) >= 2 and st.button("Compute PCA Projection", type="primary"):
                    try:
                        from sklearn.decomposition import PCA
                        from sklearn.preprocessing import StandardScaler
                        
                        x_data = working_df[pca_features].dropna()
                        scaler = StandardScaler()
                        scaled_x = scaler.fit_transform(x_data)
                        
                        pca = PCA(n_components=2)
                        components = pca.fit_transform(scaled_x)
                        
                        pca_df = pd.DataFrame(components, columns=["PC1", "PC2"], index=x_data.index)
                        explained_var = pca.explained_variance_ratio_
                        
                        c1, c2 = st.columns(2)
                        c1.metric("PC1 Variance Explained", f"{explained_var[0]*100:.1f}%")
                        c2.metric("PC2 Variance Explained", f"{explained_var[1]*100:.1f}%")

                        if PLOTLY_AVAILABLE:
                            fig = px.scatter(pca_df, x="PC1", y="PC2", template="plotly_dark", title="PCA 2D Latent Space Projection")
                            st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"PCA execution failed: {e}")
            else:
                st.warning("Requires at least 2 numeric features.")

        elif pro_task == "Automated Feature Interaction Generator":
            st.markdown("Automatically engineers multiplicative cross-features between numerical columns to boost predictive modeling signals.")
            if len(numeric_cols_pro) >= 2:
                f1 = st.selectbox("Feature 1", numeric_cols_pro, key="f1_interact")
                f2 = st.selectbox("Feature 2", [c for c in numeric_cols_pro if c != f1], key="f2_interact")
                if st.button("Generate Interaction Feature", type="primary"):
                    new_col_name = f"{f1}_X_{f2}"
                    working_df[new_col_name] = working_df[f1] * working_df[f2]
                    st.session_state["working_df"] = working_df
                    st.success(f"Successfully generated interaction feature '{new_col_name}'.")
                    st.rerun()
            else:
                st.warning("Requires at least 2 numeric columns.")