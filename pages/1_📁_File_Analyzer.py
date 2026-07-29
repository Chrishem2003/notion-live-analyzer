# ═══════════════════════════════════════════════════════════════════════════════
# ADVANCED FILE ANALYZER & MULTI-FORMAT INGESTION ENGINE [ENTERPRISE EDITION v6.1]
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

# Optional charting backend — degrade gracefully if not installed
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

# Fallback robust imports for core modules
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
        st.title(title)
        st.markdown(f"*{subtitle}* — `[{badge_text}]`")

    def watermark(text):
        pass

    def section_header(title, desc=""):
        st.subheader(title)
        if desc:
            st.caption(desc)

    SUPPORTED_FORMATS = {"csv": "CSV", "xlsx": "Excel"}


# ─── Page Configuration ───────────────────────────────────────────────
st.set_page_config(
    page_title="Advanced File Analyzer [SECURE]",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")

# ─── High-Contrast Custom Styling & Readability Enhancements ──────────
st.markdown(
    """
    <style>
    /* Global App Container */
    .stApp {
        background-color: #0b0f19 !important;
        color: #f8fafc !important;
    }
    
    /* Ensure all text elements are high-contrast and readable */
    h1, h2, h3, h4, h5, h6, span, p, label, div, .stMarkdown, .stCaption, .stRadio label, .stCheckbox label {
        color: #f8fafc !important;
    }

    /* Solid Container Cards for Form Elements to prevent wash-out */
    div.row-widget.stRadio, div.stFileUploader, div.stTextInput, div.stSelectbox {
        background-color: #111827 !important;
        padding: 16px !important;
        border-radius: 10px !important;
        border: 1px solid #1f2937 !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }

    /* Dataframe and Tables styling */
    .stDataFrame, .stTable {
        background-color: #111827 !important;
        border-radius: 8px !important;
    }

    /* Metric Card Custom Styling */
    .metric-card {
        background: #111827 !important;
        border: 1px solid #374151 !important;
        padding: 18px !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

hero_card(
    "📁 Advanced File Analyzer & Explorer Engine",
    "Universal data parsing for CSV, Excel, SPSS (.sav), SAS, STATA, JSON, and binary formats "
    "with automated profiling, data-quality scoring, anomaly detection, and visualization.",
    badge_text="v6.1 Enterprise — High Contrast & Pipeline Automation",
)
watermark("CHRISHEM")

# ─── SECURITY: Sandbox Root Setup ─────────────────────────────────────
SAFE_ROOT = root_dir.resolve()


def path_is_safe(candidate: Path) -> bool:
    """Ensure file browsing stays contained within the allowed local workspace."""
    try:
        candidate.resolve().relative_to(SAFE_ROOT)
        return True
    except ValueError:
        return False


# ─── Ingestion & Parsing Helpers ──────────────────────────────────────
def detect_delimiter(sample_text: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample_text, delimiters=",;\t|")
        return dialect.delimiter
    except Exception:
        return ","


def robust_parse_file(file_obj_or_path):
    """Robust multi-format research document parser."""
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
            st.error(
                f"❌ Could not parse '{filename}' — unrecognized encoding or delimiter."
            )
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
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=suffix_map[ext]
                    ) as tmp:
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
                st.error(
                    f"⚠️ `pyreadstat` library required for .{ext} files. Please install via pip."
                )
                return None

        elif ext == "parquet":
            return pd.read_parquet(file_obj_or_path)
        elif ext == "feather":
            return pd.read_feather(file_obj_or_path)
        elif ext in ["pkl", "pickle"]:
            return pd.read_pickle(file_obj_or_path)
        else:
            return (
                parse_uploaded_file(file_obj_or_path)
                if "parse_uploaded_file" in globals()
                else None
            )
    except Exception as e:
        st.error(
            f"❌ Error parsing file '{getattr(file_obj_or_path, 'name', file_obj_or_path)}': {e}"
        )
        return None


# ─── Data Quality & Analytics Utilities ───────────────────────────────
def compute_data_quality(df: pd.DataFrame) -> dict:
    n_rows, n_cols = df.shape
    total_cells = n_rows * n_cols if n_rows and n_cols else 1
    missing = int(df.isnull().sum().sum())
    dup_rows = int(df.duplicated().sum())

    whitespace_issues = 0
    for col in df.select_dtypes(include="object").columns:
        as_str = df[col].astype(str)
        whitespace_issues += int((as_str.str.strip() != as_str).sum())

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


def detect_outliers_iqr(series: pd.Series) -> pd.Series:
    clean = series.dropna()
    if clean.empty:
        return pd.Series(dtype=series.dtype)
    q1, q3 = clean.quantile(0.25), clean.quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return clean[(clean < lower) | (clean > upper)]


def detect_outliers_zscore(series: pd.Series, threshold: float = 3.0) -> pd.Series:
    clean = series.dropna()
    if clean.empty or clean.std() == 0:
        return pd.Series(dtype=series.dtype)
    z = (clean - clean.mean()) / clean.std()
    return clean[z.abs() > threshold]


EMAIL_RE = re.compile(r"[\w.\-+]+@[\w\-]+\.[\w.\-]+")
PHONE_RE = re.compile(r"(\+?\d[\d\-\s()]{7,}\d)")


def mask_pii(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    masked = df.copy()
    for col in columns:
        masked[col] = (
            masked[col]
            .astype(str)
            .apply(
                lambda v: PHONE_RE.sub(
                    "[PHONE MASKED]", EMAIL_RE.sub("[EMAIL MASKED]", v)
                )
            )
        )
    return masked


# ─── Main Interface Setup ─────────────────────────────────────────────
st.markdown("---")
ingestion_mode = st.radio(
    "Select Data Ingestion Channel",
    options=[
        "📤 Direct File Uploader (Standard)",
        "📂 Local Server / Directory Explorer",
    ],
    horizontal=True,
)

active_df = None
active_source_name = None

if ingestion_mode == "📤 Direct File Uploader (Standard)":
    section_header("📤 Upload Data File")
    st.caption(
        "Supported formats: CSV, Excel, SPSS (.sav), SAS (.sas7bdat), STATA (.dta), JSON, Parquet, Feather, Pickle."
    )

    uploaded_file = st.file_uploader(
        "Choose a data file",
        type=[
            "csv", "xlsx", "xls", "json", "sav",
            "sas7bdat", "dta", "parquet", "feather", "pkl", "txt",
        ],
        help="Upload dataset for instant profiling, quality checks, and visualization.",
    )

    if uploaded_file is not None:
        with st.spinner(f"Parsing '{uploaded_file.name}'..."):
            active_df = robust_parse_file(uploaded_file)
            active_source_name = uploaded_file.name

else:
    section_header("📂 Local Server & Directory Explorer")
    st.info("🔒 Sandboxed securely to workspace directory. External paths restricted.")

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
            st.success(f"🔍 Discovered {len(found_files)} readable data file(s).")
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
            st.info("📭 No compatible data files found in this directory.")

# ── Session Management & State Persistence ───────────────────────────
if active_df is not None and not active_df.empty:
    st.session_state["uploaded_df"] = active_df
    st.session_state["active_df"] = active_df
    st.session_state["working_df"] = active_df.copy()
    st.session_state["data_source"] = "advanced_analyzer"
    st.session_state["source_name"] = active_source_name or "dataset.csv"
    st.session_state.setdefault("transform_log", [])
    st.session_state["transform_log"] = []
elif active_df is not None and active_df.empty:
    st.warning("⚠️ The selected file parsed successfully, but the dataset contains no records.")

working_df = st.session_state.get("working_df")

# ─── Advanced Feature Workspace Tabs ───────────────────────────────────
if working_df is not None and not working_df.empty:
    st.markdown("---")

    dataset_bytes = working_df.to_csv(index=False).encode("utf-8")
    dataset_hash = hashlib.sha256(dataset_bytes).hexdigest()

    st.caption(
        f"🔗 **Active Dataset SHA-256 Checksum:** `{dataset_hash[:24]}...` | "
        f"Records: **{working_df.shape[0]:,}** | Features: **{working_df.shape[1]}**"
    )

    tabs = st.tabs([
        "📊 Overview",
        "🩺 Data Quality",
        "👁️ Preview & Filter",
        "🛠️ Transform",
        "📈 Visualize",
        "🧮 Aggregate",
        "📥 Export & Code",
        "🔗 Merge",
    ])

    # ── Tab 0: Overview ──
    with tabs[0]:
        section_header("📊 Dataset Overview & Statistical Summary")
        profile = (
            profile_dataset(working_df)
            if "profile_dataset" in globals()
            else {"numeric_columns": [], "categorical_columns": []}
        )

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Rows", f"{working_df.shape[0]:,}")
        c2.metric("Total Columns", f"{working_df.shape[1]:,}")
        c3.metric("Numeric Features", len(profile.get("numeric_columns", working_df.select_dtypes(include=np.number).columns)))
        c4.metric("Categorical Features", len(profile.get("categorical_columns", working_df.select_dtypes(include=["object", "category"]).columns)))
        mem_mb = working_df.memory_usage(deep=True).sum() / (1024 ** 2)
        c5.metric("Memory Footprint", f"{mem_mb:.2f} MB")

        section_header("📋 Column Metadata & Data Types")
        col_types = (
            infer_column_types(working_df)
            if "infer_column_types" in globals()
            else {c: str(working_df[c].dtype) for c in working_df.columns}
        )
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