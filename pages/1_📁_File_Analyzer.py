"""
📁 Advanced File Analyzer & Multi-Format Ingestion Engine
Parsing support for CSV, Excel (XLSX/XLS), SPSS (.sav), SAS (.sas7bdat),
STATA (.dta), Parquet, Feather, Pickle, JSON — plus profiling, data-quality
scoring, filtering, transformation, visualization, aggregation, PII masking,
and multi-format export.
"""
import streamlit as st
import pandas as pd
import numpy as np
import os
import re
import sys
import csv
import io
import json
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="Advanced File Analyzer", layout="wide", page_icon="📁")

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

from modules.config import init_session_state
from modules.ui_components import hero_card, section_header, load_css, watermark
from modules.file_uploader import parse_uploaded_file, merge_datasets, manual_data_entry, SUPPORTED_FORMATS
from modules.data_processor import profile_dataset, infer_column_types
from modules.export import render_export_buttons

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")

hero_card(
    "📁 Advanced File Analyzer & Explorer Engine",
    "Universal data parsing for CSV, Excel, SPSS (.sav), SAS, STATA, JSON, and binary formats "
    "with automated profiling, data-quality scoring, transformation, and visualization.",
    badge_text="v5.0 — Profiling, Transform & Visual Analytics"
)
watermark("CHRISHEM")

# ─── SECURITY: sandbox root for local directory browsing ───────────────
SAFE_ROOT = root_dir.resolve()


def path_is_safe(candidate: Path) -> bool:
    """Only allow browsing inside the app's own workspace, never outside it."""
    try:
        candidate.resolve().relative_to(SAFE_ROOT)
        return True
    except ValueError:
        return False


# ─── Encoding / delimiter detection ─────────────────────────────────────
def detect_delimiter(sample_text: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample_text, delimiters=",;\t|")
        return dialect.delimiter
    except Exception:
        return ","


def robust_parse_file(file_obj_or_path):
    """
    Parser supporting all research formats (CSV, Excel, SPSS, SAS, Stata, JSON, Parquet, Feather, Pickle).
    Handles both Streamlit UploadedFile objects and local filesystem paths.
    Auto-detects CSV encoding and delimiter.
    """
    try:
        filename = file_obj_or_path.name if hasattr(file_obj_or_path, "name") else str(file_obj_or_path)
        ext = filename.lower().split(".")[-1]

        if ext == "csv" or ext == "txt":
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
                    return pd.read_csv(source, encoding=enc, sep=delim, engine="python", low_memory=False)
                except Exception:
                    continue
            st.error(f"❌ Could not parse '{filename}' — unrecognized encoding or delimiter.")
            return None

        elif ext in ["xls", "xlsx"]:
            if hasattr(file_obj_or_path, "seek"):
                file_obj_or_path.seek(0)
            return pd.read_excel(file_obj_or_path, sheet_name=0)

        elif ext == "json":
            if hasattr(file_obj_or_path, "seek"):
                file_obj_or_path.seek(0)
            return pd.read_json(file_obj_or_path)

        elif ext == "sav":  # SPSS
            try:
                import pyreadstat
                if isinstance(file_obj_or_path, (str, Path)):
                    df, _meta = pyreadstat.read_sav(str(file_obj_or_path))
                else:
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".sav") as tmp:
                        tmp.write(file_obj_or_path.read())
                        tmp_path = tmp.name
                    df, _meta = pyreadstat.read_sav(tmp_path)
                    os.unlink(tmp_path)
                return df
            except ImportError:
                st.error("⚠️ `pyreadstat` library required for SPSS (.sav) files. Install via `pip install pyreadstat`.")
                return None

        elif ext == "sas7bdat":  # SAS
            try:
                import pyreadstat
                if isinstance(file_obj_or_path, (str, Path)):
                    df, _meta = pyreadstat.read_sas7bdat(str(file_obj_or_path))
                else:
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".sas7bdat") as tmp:
                        tmp.write(file_obj_or_path.read())
                        tmp_path = tmp.name
                    df, _meta = pyreadstat.read_sas7bdat(tmp_path)
                    os.unlink(tmp_path)
                return df
            except ImportError:
                st.error("⚠️ `pyreadstat` library required for SAS files.")
                return None

        elif ext == "dta":  # STATA
            try:
                import pyreadstat
                if isinstance(file_obj_or_path, (str, Path)):
                    df, _meta = pyreadstat.read_dta(str(file_obj_or_path))
                else:
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".dta") as tmp:
                        tmp.write(file_obj_or_path.read())
                        tmp_path = tmp.name
                    df, _meta = pyreadstat.read_dta(tmp_path)
                    os.unlink(tmp_path)
                return df
            except ImportError:
                st.error("⚠️ `pyreadstat` library required for STATA files.")
                return None

        elif ext == "parquet":
            return pd.read_parquet(file_obj_or_path)

        elif ext == "feather":
            return pd.read_feather(file_obj_or_path)

        elif ext in ["pkl", "pickle"]:
            return pd.read_pickle(file_obj_or_path)

        else:
            return parse_uploaded_file(file_obj_or_path)

    except Exception as e:
        st.error(f"❌ Error parsing file '{getattr(file_obj_or_path, 'name', file_obj_or_path)}': {e}")
        return None


# ─── Data quality, outliers, PII ────────────────────────────────────────
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
            .apply(lambda v: PHONE_RE.sub("[PHONE MASKED]", EMAIL_RE.sub("[EMAIL MASKED]", v)))
        )
    return masked


def generate_pandas_snippet(source_name: str, ops: list) -> str:
    lines = [f'df = pd.read_csv("{source_name}")  # adjust loader to match your source format']
    lines.extend(ops)
    return "\n".join(lines)


# ─── Ingestion Mode Selector ───────────────────────────────────────────
st.markdown("---")
ingestion_mode = st.radio(
    "Select Data Ingestion Channel",
    options=["📤 Direct File Uploader (Standard)", "📂 Local Server / Directory Explorer"],
    horizontal=True,
)

active_df = None
active_source_name = None

if ingestion_mode == "📤 Direct File Uploader (Standard)":
    section_header("📤 Upload Data File")
    st.caption(
        f"Supported formats: {', '.join(SUPPORTED_FORMATS.keys())}, SPSS (.sav), SAS (.sas7bdat), "
        "STATA (.dta), Parquet, Feather. Encoding and delimiter are auto-detected for CSV/TXT."
    )

    uploaded_file = st.file_uploader(
        "Choose a data file",
        type=["csv", "xlsx", "xls", "json", "sav", "sas7bdat", "dta", "parquet", "feather", "pkl", "txt"],
        help="Upload your dataset for instant profiling and automated analysis.",
    )

    if uploaded_file is not None:
        with st.spinner(f"Parsing '{uploaded_file.name}'..."):
            active_df = robust_parse_file(uploaded_file)
            active_source_name = uploaded_file.name

else:
    section_header("📂 Local Server & Directory Explorer")
    st.info(
        "🔒 For security, this browser is sandboxed to the application's own workspace folder — "
        "it cannot read files outside of it."
    )

    default_path = str(SAFE_ROOT)
    target_dir_raw = st.text_input("Directory Path to Scan", value=default_path, placeholder="/path/to/data/folder")
    target_dir = Path(target_dir_raw) if target_dir_raw else SAFE_ROOT

    if not path_is_safe(target_dir):
        st.error("⚠️ That path is outside the allowed workspace. Directory browsing is restricted for security reasons.")
    elif not target_dir.exists() or not target_dir.is_dir():
        st.error("⚠️ Invalid directory path specified. Please verify the folder location.")
    else:
        valid_extensions = (".csv", ".xlsx", ".xls", ".json", ".sav", ".sas7bdat", ".dta", ".parquet", ".feather", ".pkl")
        found_files = []
        for r, dirs, files in os.walk(target_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("venv", "__pycache__", "node_modules")]
            for f in files:
                if f.lower().endswith(valid_extensions):
                    found_files.append(os.path.join(r, f))

        if found_files:
            st.success(f"🔍 Discovered {len(found_files)} readable data file(s) in directory.")
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
            st.info("📭 No supported data files found in this directory path.")

# Persist a freshly-loaded file into session state as the "working" dataset
if active_df is not None and not active_df.empty:
    st.session_state["uploaded_df"] = active_df
    st.session_state["active_df"] = active_df
    st.session_state["working_df"] = active_df.copy()
    st.session_state["data_source"] = "advanced_analyzer"
    st.session_state["source_name"] = active_source_name or "dataset"
    st.session_state.setdefault("transform_log", [])
    st.session_state["transform_log"] = []
elif active_df is not None and active_df.empty:
    st.warning("⚠️ The selected file parsed successfully, but the dataset is completely empty.")

working_df = st.session_state.get("working_df")

# ─── Analysis Hub ────────────────────────────────────────────────────
if working_df is not None and not working_df.empty:
    st.markdown("---")
    tabs = st.tabs(
        ["📊 Overview", "🩺 Data Quality", "👁️ Preview & Filter", "🛠️ Transform",
         "📈 Visualize", "🧮 Aggregate", "📥 Export", "🔗 Merge"]
    )

    # ── Overview ──
    with tabs[0]:
        section_header("📊 Dataset Overview & Statistical Summary")
        profile = profile_dataset(working_df)
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Rows", f"{working_df.shape[0]:,}")
        with col2:
            st.metric("Total Columns", f"{working_df.shape[1]:,}")
        with col3:
            st.metric("Numeric Columns", len(profile.get("numeric_columns", [])))
        with col4:
            st.metric("Categorical Columns", len(profile.get("categorical_columns", [])))
        with col5:
            mem_mb = working_df.memory_usage(deep=True).sum() / (1024 ** 2)
            st.metric("Memory Usage", f"{mem_mb:.2f} MB")

        section_header("📋 Column Metadata & Data Types")
        col_types = infer_column_types(working_df)
        type_df = pd.DataFrame(
            [
                {
                    "Column Name": col,
                    "Data Type": str(working_df[col].dtype),
                    "Inferred Type": ctype,
                    "Null Count": int(working_df[col].isnull().sum()),
                    "Null %": round(working_df[col].isnull().mean() * 100, 2),
                    "Unique Values": int(working_df[col].nunique()),
                }
                for col, ctype in col_types.items()
            ]
        )
        st.dataframe(type_df, use_container_width=True, hide_index=True)

    # ── Data Quality ──
    with tabs[1]:
        section_header("🩺 Data Quality & Health Check")
        dq = compute_data_quality(working_df)

        score_color = "🟢" if dq["score"] >= 80 else "🟡" if dq["score"] >= 50 else "🔴"
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"{score_color} Health Score", f"{dq['score']}/100")
        c2.metric("Missing Cells", f"{dq['missing_cells']:,}", f"{dq['missing_pct']}%")
        c3.metric("Duplicate Rows", f"{dq['duplicate_rows']:,}", f"{dq['duplicate_pct']}%")
        c4.metric("Whitespace Issues", f"{dq['whitespace_issues']:,}")

        st.markdown("##### Missing Values by Column")
        na_counts = working_df.isnull().sum()
        na_df = na_counts[na_counts > 0].sort_values(ascending=False).reset_index()
        na_df.columns = ["Column", "Missing Count"]
        if not na_df.empty:
            na_df["Missing %"] = round(na_df["Missing Count"] / len(working_df) * 100, 2)
            st.dataframe(na_df, use_container_width=True, hide_index=True)
            if PLOTLY_AVAILABLE:
                fig = px.bar(na_df, x="Column", y="Missing Count", title="Missing Values per Column")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("✅ No missing values detected.")

        st.markdown("##### Outlier Detection (Numeric Columns)")
        numeric_cols = working_df.select_dtypes(include=np.number).columns.tolist()
        if numeric_cols:
            outlier_col = st.selectbox("Column to inspect", numeric_cols, key="outlier_col")
            method = st.radio("Detection method", ["IQR (1.5×)", "Z-score (>3)"], horizontal=True, key="outlier_method")
            series = working_df[outlier_col]
            outliers = detect_outliers_iqr(series) if method.startswith("IQR") else detect_outliers_zscore(series)
            st.write(f"Found **{len(outliers)}** outlier value(s) in `{outlier_col}` ({len(outliers)/len(series)*100:.2f}% of non-null rows).")
            if len(outliers) > 0:
                st.dataframe(outliers.to_frame(name=outlier_col), use_container_width=True)
        else:
            st.info("No numeric columns available for outlier detection.")

    # ── Preview & Filter ──
    with tabs[2]:
        section_header("👁️ Interactive Data Preview & Filtering")
        filtered_df = working_df

        with st.expander("🔎 Filter rows", expanded=False):
            filter_col = st.selectbox("Column", ["(none)"] + list(working_df.columns), key="filter_col")
            if filter_col != "(none)":
                col_series = working_df[filter_col]
                if pd.api.types.is_numeric_dtype(col_series):
                    lo, hi = float(col_series.min()), float(col_series.max())
                    if lo < hi:
                        rng = st.slider("Range", lo, hi, (lo, hi), key="filter_range")
                        filtered_df = filtered_df[(filtered_df[filter_col] >= rng[0]) & (filtered_df[filter_col] <= rng[1])]
                else:
                    options = col_series.dropna().unique().tolist()
                    chosen = st.multiselect("Values", options, default=options[:min(10, len(options))], key="filter_values")
                    if chosen:
                        filtered_df = filtered_df[filtered_df[filter_col].isin(chosen)]

        search_term = st.text_input("🔍 Search across all columns", key="global_search")
        if search_term:
            mask = filtered_df.astype(str).apply(lambda row: row.str.contains(search_term, case=False, na=False)).any(axis=1)
            filtered_df = filtered_df[mask]

        sort_col1, sort_col2 = st.columns([2, 1])
        with sort_col1:
            sort_by = st.selectbox("Sort by column", ["(none)"] + list(working_df.columns), key="sort_col")
        with sort_col2:
            sort_dir = st.radio("Direction", ["Ascending", "Descending"], horizontal=True, key="sort_dir")
        if sort_by != "(none)":
            filtered_df = filtered_df.sort_values(by=sort_by, ascending=(sort_dir == "Ascending"))

        row_limit = st.slider("Display Row Count", min_value=10, max_value=max(10, min(1000, len(filtered_df))), value=min(50, max(10, len(filtered_df))), step=10)
        st.caption(f"Showing {min(row_limit, len(filtered_df))} of {len(filtered_df)} filtered rows (dataset total: {len(working_df)}).")
        st.dataframe(filtered_df.head(row_limit), use_container_width=True, hide_index=True)

        if st.checkbox("Show Descriptive Statistics (.describe())", value=True, key="show_describe"):
            with st.expander("📈 Advanced Statistical Breakdown"):
                st.dataframe(filtered_df.describe(include="all"), use_container_width=True)

    # ── Transform ──
    with tabs[3]:
        section_header("🛠️ Schema Transformation")
        st.caption("Changes here update the working dataset used across all tabs and the export section.")

        t1, t2, t3 = st.columns(3)

        with t1:
            st.markdown("**Rename column**")
            rn_col = st.selectbox("Column", working_df.columns, key="rn_col")
            rn_new = st.text_input("New name", key="rn_new")
            if st.button("Apply rename", key="btn_rename") and rn_new:
                st.session_state["working_df"] = working_df.rename(columns={rn_col: rn_new})
                st.session_state["transform_log"].append(f'df = df.rename(columns={{"{rn_col}": "{rn_new}"}})')
                st.rerun()

        with t2:
            st.markdown("**Drop columns**")
            drop_cols = st.multiselect("Columns to drop", working_df.columns, key="drop_cols")
            if st.button("Apply drop", key="btn_drop") and drop_cols:
                st.session_state["working_df"] = working_df.drop(columns=drop_cols)
                st.session_state["transform_log"].append(f"df = df.drop(columns={drop_cols})")
                st.rerun()

        with t3:
            st.markdown("**Convert data type**")
            cv_col = st.selectbox("Column", working_df.columns, key="cv_col")
            cv_type = st.selectbox("Convert to", ["string", "float", "int", "datetime", "category"], key="cv_type")
            if st.button("Apply conversion", key="btn_convert"):
                try:
                    new_df = working_df.copy()
                    if cv_type == "datetime":
                        new_df[cv_col] = pd.to_datetime(new_df[cv_col], errors="coerce")
                    elif cv_type == "int":
                        new_df[cv_col] = pd.to_numeric(new_df[cv_col], errors="coerce").astype("Int64")
                    elif cv_type == "float":
                        new_df[cv_col] = pd.to_numeric(new_df[cv_col], errors="coerce")
                    else:
                        new_df[cv_col] = new_df[cv_col].astype(cv_type)
                    st.session_state["working_df"] = new_df
                    st.session_state["transform_log"].append(f'df["{cv_col}"] = df["{cv_col}"].astype("{cv_type}")  # or pd.to_datetime/pd.to_numeric as appropriate')
                    st.success(f"Converted `{cv_col}` to {cv_type}.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Conversion failed: {e}")

        st.markdown("---")
        m1, m2 = st.columns(2)
        with m1:
            st.markdown("**Handle missing values**")
            mv_col = st.selectbox("Column", ["(all columns)"] + list(working_df.columns), key="mv_col")
            mv_action = st.radio("Action", ["Drop rows with nulls", "Fill with mean", "Fill with median", "Fill with mode", "Fill with 0 / empty string"], key="mv_action")
            if st.button("Apply missing-value handling", key="btn_mv"):
                new_df = working_df.copy()
                cols_target = list(new_df.columns) if mv_col == "(all columns)" else [mv_col]
                if mv_action == "Drop rows with nulls":
                    new_df = new_df.dropna(subset=cols_target)
                else:
                    for c in cols_target:
                        if mv_action == "Fill with mean" and pd.api.types.is_numeric_dtype(new_df[c]):
                            new_df[c] = new_df[c].fillna(new_df[c].mean())
                        elif mv_action == "Fill with median" and pd.api.types.is_numeric_dtype(new_df[c]):
                            new_df[c] = new_df[c].fillna(new_df[c].median())
                        elif mv_action == "Fill with mode":
                            mode_val = new_df[c].mode()
                            if not mode_val.empty:
                                new_df[c] = new_df[c].fillna(mode_val[0])
                        elif mv_action == "Fill with 0 / empty string":
                            fill_val = 0 if pd.api.types.is_numeric_dtype(new_df[c]) else ""
                            new_df[c] = new_df[c].fillna(fill_val)
                st.session_state["working_df"] = new_df
                st.session_state["transform_log"].append(f"# missing-value handling: {mv_action} on {cols_target}")
                st.rerun()

        with m2:
            st.markdown("**Mask PII before analysis**")
            pii_cols = st.multiselect("Columns to mask (emails / phone numbers)", working_df.select_dtypes(include="object").columns.tolist(), key="pii_cols")
            if st.button("Apply PII masking", key="btn_pii") and pii_cols:
                st.session_state["working_df"] = mask_pii(working_df, pii_cols)
                st.session_state["transform_log"].append(f"# PII masking applied to columns: {pii_cols}")
                st.success(f"Masked PII patterns in: {', '.join(pii_cols)}")
                st.rerun()

        st.markdown("---")
        if st.button("↩️ Reset to originally loaded dataset", key="btn_reset_working"):
            st.session_state["working_df"] = st.session_state["active_df"].copy()
            st.session_state["transform_log"] = []
            st.rerun()

    # ── Visualize ──
    with tabs[4]:
        section_header("📈 Automated Visualizations")
        if not PLOTLY_AVAILABLE:
            st.warning("⚠️ `plotly` is not installed. Run `pip install plotly` to enable charts.")
        else:
            numeric_cols = working_df.select_dtypes(include=np.number).columns.tolist()
            categorical_cols = working_df.select_dtypes(include=["object", "category"]).columns.tolist()
            datetime_cols = working_df.select_dtypes(include="datetime").columns.tolist()

            chart_type = st.selectbox(
                "Chart type",
                ["Histogram", "Scatter Plot", "Bar Chart (categorical counts)", "Time Series", "Correlation Heatmap"],
            )

            if chart_type == "Histogram" and numeric_cols:
                col = st.selectbox("Column", numeric_cols, key="hist_col")
                fig = px.histogram(working_df, x=col, title=f"Distribution of {col}")
                st.plotly_chart(fig, use_container_width=True)

            elif chart_type == "Scatter Plot" and len(numeric_cols) >= 2:
                cx, cy = st.columns(2)
                x_col = cx.selectbox("X axis", numeric_cols, key="sx")
                y_col = cy.selectbox("Y axis", numeric_cols, index=min(1, len(numeric_cols) - 1), key="sy")
                color_col = st.selectbox("Color by (optional)", ["(none)"] + categorical_cols, key="scolor")
                fig = px.scatter(working_df, x=x_col, y=y_col, color=None if color_col == "(none)" else color_col, title=f"{y_col} vs {x_col}")
                st.plotly_chart(fig, use_container_width=True)

            elif chart_type == "Bar Chart (categorical counts)" and categorical_cols:
                col = st.selectbox("Column", categorical_cols, key="bar_col")
                counts = working_df[col].value_counts().head(30).reset_index()
                counts.columns = [col, "Count"]
                fig = px.bar(counts, x=col, y="Count", title=f"Top values in {col}")
                st.plotly_chart(fig, use_container_width=True)

            elif chart_type == "Time Series" and datetime_cols and numeric_cols:
                dt_col = st.selectbox("Date column", datetime_cols, key="ts_dt")
                val_col = st.selectbox("Value column", numeric_cols, key="ts_val")
                ts_df = working_df[[dt_col, val_col]].dropna().sort_values(dt_col)
                fig = px.line(ts_df, x=dt_col, y=val_col, title=f"{val_col} over time")
                st.plotly_chart(fig, use_container_width=True)

            elif chart_type == "Correlation Heatmap" and len(numeric_cols) >= 2:
                corr = working_df[numeric_cols].corr(numeric_only=True)
                fig = px.imshow(corr, text_auto=".2f", aspect="auto", title="Correlation Matrix", color_continuous_scale="RdBu_r", zmin=-1, zmax=1)
                st.plotly_chart(fig, use_container_width=True)

            else:
                st.info("Not enough compatible columns for this chart type. Try a different chart or check your column types.")

    # ── Aggregate ──
    with tabs[5]:
        section_header("🧮 Group & Aggregate")
        categorical_cols = working_df.select_dtypes(include=["object", "category"]).columns.tolist()
        numeric_cols = working_df.select_dtypes(include=np.number).columns.tolist()

        if categorical_cols and numeric_cols:
            group_cols = st.multiselect("Group by", categorical_cols, key="agg_group")
            agg_col = st.selectbox("Aggregate column", numeric_cols, key="agg_col")
            agg_funcs = st.multiselect("Functions", ["sum", "mean", "median", "count", "std", "min", "max"], default=["sum", "mean", "count"], key="agg_funcs")
            if group_cols and agg_funcs:
                result = working_df.groupby(group_cols)[agg_col].agg(agg_funcs).reset_index()
                st.dataframe(result, use_container_width=True, hide_index=True)
                if PLOTLY_AVAILABLE and len(group_cols) == 1 and agg_funcs:
                    fig = px.bar(result, x=group_cols[0], y=agg_funcs[0], title=f"{agg_funcs[0]}({agg_col}) by {group_cols[0]}")
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Choose at least one group-by column and one aggregate function.")
        else:
            st.info("Aggregation requires at least one categorical column and one numeric column.")

    # ── Export ──
    with tabs[6]:
        section_header("📥 Export Processed Dataset")
        render_export_buttons(working_df)

        st.markdown("##### Additional export formats")
        e1, e2, e3 = st.columns(3)
        with e1:
            st.download_button("⬇️ Download as CSV", working_df.to_csv(index=False).encode("utf-8"), file_name="dataset.csv", mime="text/csv")
        with e2:
            st.download_button("⬇️ Download as JSON", working_df.to_json(orient="records").encode("utf-8"), file_name="dataset.json", mime="application/json")
        with e3:
            xlsx_buffer = io.BytesIO()
            with pd.ExcelWriter(xlsx_buffer, engine="openpyxl") as writer:
                working_df.to_excel(writer, index=False, sheet_name="Data")
            st.download_button("⬇️ Download as Excel", xlsx_buffer.getvalue(), file_name="dataset.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        st.markdown("##### 🧾 Reproduce these steps in Python")
        log = st.session_state.get("transform_log", [])
        snippet = generate_pandas_snippet(st.session_state.get("source_name", "your_file"), log if log else ["# no transformations applied yet"])
        st.code(snippet, language="python")

    # ── Merge ──
    with tabs[7]:
        if st.session_state.get("notion_df") is not None and not st.session_state["notion_df"].empty:
            section_header("🔗 Merge with Notion Data")
            notion_df = st.session_state["notion_df"]
            common_cols = list(set(working_df.columns) & set(notion_df.columns))
            merge_key = st.selectbox(
                "Merge key column (optional)",
                options=[""] + common_cols,
                help="Select a common column to merge on. If none selected, datasets will be concatenated.",
            )
            merge_how = st.selectbox("Merge method", options=["inner", "outer", "left", "right"], index=0)

            if st.button("🔄 Execute Dataset Merge", type="primary"):
                merged = merge_datasets(notion_df, working_df, merge_key=merge_key or None, merge_how=merge_how)
                if merged is not None and not merged.empty:
                    st.session_state["merged_df"] = merged
                    st.session_state["working_df"] = merged
                    st.session_state["active_df"] = merged
                    st.session_state["data_source"] = "merged"
                    st.success(f"✅ Successfully merged datasets: {len(merged)} rows × {len(merged.columns)} columns")
                    st.dataframe(merged.head(20), use_container_width=True, hide_index=True)
        else:
            st.info("No secondary Notion dataset is currently loaded, so there's nothing to merge yet.")

# ─── Manual Data Entry Fallback ──────────────────────────────────────
st.markdown("---")
section_header("✏️ Or Enter Data Manually")
manual_df = manual_data_entry()
if manual_df is not None and not manual_df.empty:
    st.session_state["active_df"] = manual_df
    st.session_state["working_df"] = manual_df.copy()
    st.session_state["data_source"] = "manual"
    st.dataframe(manual_df, use_container_width=True, hide_index=True)