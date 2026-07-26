"""
File Uploader — handles file uploads in multiple formats (CSV, Excel, SPSS, SAS, STATA, JSON).
"""
from typing import Optional, Dict, Any, List
import pandas as pd
import streamlit as st
from pathlib import Path

from modules.runtime_perf import (
    check_upload_size,
    dataframe_memory_mb,
    read_csv_chunked,
    release,
    shrink_dataframe,
)

# ─── Supported Formats ────────────────────────────────────────────────
SUPPORTED_FORMATS = {
    "CSV (.csv)": "csv",
    "Excel (.xlsx)": "xlsx",
    "Excel (.xls)": "xls",
    "JSON (.json)": "json",
    "SPSS (.sav)": "sav",
    "SAS (.sas7bdat)": "sas7bdat",
    "STATA (.dta)": "dta",
    "Parquet (.parquet)": "parquet",
    "Feather (.feather)": "feather",
    "Pickle (.pkl)": "pkl",
}

def get_file_extension(filename: str) -> str:
    """Extract file extension from filename."""
    return Path(filename).suffix.lower().lstrip(".") if "." in filename else ""

def detect_encoding(file_path: str) -> str:
    """Detect file encoding (fallback to utf-8)."""
    try:
        import chardet
        with open(file_path, "rb") as f:
            raw = f.read(10000)
            result = chardet.detect(raw)
            return result.get("encoding", "utf-8")
    except ImportError:
        return "utf-8"

def parse_uploaded_file(uploaded_file) -> Optional[pd.DataFrame]:
    """
    Parse an uploaded file into a pandas DataFrame.
    Handles CSV, Excel, JSON, SPSS, SAS, STATA, Parquet, Feather, Pickle.
    """
    if uploaded_file is None:
        return None

    size_ok, size_msg = check_upload_size(uploaded_file)
    if not size_ok:
        st.error(f"⚠️ {size_msg}")
        return None

    file_ext = get_file_extension(uploaded_file.name)
    df = None
    error_msg = None
    truncated = False

    try:
        if file_ext == "csv":
            # Streamed in chunks so a large CSV never lands in RAM whole.
            for encoding in ("utf-8", "latin-1", "iso-8859-1"):
                try:
                    uploaded_file.seek(0)
                    df, truncated = read_csv_chunked(uploaded_file, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    df = None
                    continue

        elif file_ext in ("xlsx", "xls"):
            # Read all sheets
            excel_file = pd.ExcelFile(uploaded_file)
            sheet_names = excel_file.sheet_names
            if len(sheet_names) == 1:
                df = pd.read_excel(uploaded_file, sheet_name=sheet_names[0])
            else:
                # Multiple sheets — read first and store note
                df = pd.read_excel(uploaded_file, sheet_name=sheet_names[0])
                st.info(f"📋 Multiple sheets found. Loaded sheet '{sheet_names[0]}'. All sheets: {', '.join(sheet_names)}")

        elif file_ext == "json":
            df = pd.read_json(uploaded_file)

        elif file_ext == "sav":
            # SPSS .sav files
            try:
                import pyreadstat
                df, meta = pyreadstat.read_sav(uploaded_file)
                if hasattr(meta, 'variable_names'):
                    st.caption(f"SPSS file loaded — {meta.number_rows} rows, {meta.number_columns} columns")
                    if hasattr(meta, 'variable_labels'):
                        for i, label in enumerate(meta.variable_labels):
                            if label and i < len(df.columns):
                                st.caption(f"  • {df.columns[i]}: {label}")
            except ImportError:
                # Fallback: try with pandas_read_spss (supports older .sav)
                df = pd.read_spss(uploaded_file)

        elif file_ext == "sas7bdat":
            try:
                from sas7bdat import SAS7BDAT
                with SAS7BDAT(uploaded_file) as reader:
                    df = reader.to_data_frame()
            except ImportError:
                error_msg = "SAS reader not installed. Install with: pip install sas7bdat"

        elif file_ext == "dta":
            df = pd.read_stata(uploaded_file)

        elif file_ext == "parquet":
            df = pd.read_parquet(uploaded_file)

        elif file_ext == "feather":
            df = pd.read_feather(uploaded_file)

        elif file_ext in ("pkl", "pickle"):
            df = pd.read_pickle(uploaded_file)

        else:
            error_msg = f"Unsupported file format: .{file_ext}. Supported formats: {', '.join(SUPPORTED_FORMATS.keys())}"

    except Exception as e:
        error_msg = f"Error parsing {uploaded_file.name}: {str(e)}"

    if error_msg:
        st.error(error_msg)
        return None

    if df is not None and not df.empty:
        # Clean column names
        df.columns = [str(col).strip() for col in df.columns]
        if file_ext != "csv":  # CSV chunks are shrunk during the streamed read
            df = shrink_dataframe(df)
        release()
        st.success(
            f"✅ Loaded '{uploaded_file.name}' — {len(df)} rows × {len(df.columns)} columns "
            f"({dataframe_memory_mb(df):.1f} MB in memory)"
        )
        if truncated:
            st.warning(
                f"⚠️ Only the first {len(df):,} rows were loaded to stay within the memory budget. "
                "Pre-filter or sample the file to analyse the rest."
            )
        return df

    return None

def merge_datasets(
    notion_df: pd.DataFrame,
    uploaded_df: pd.DataFrame,
    merge_key: str = None,
    merge_how: str = "inner",
) -> pd.DataFrame:
    """
    Merge Notion data with uploaded file data.
    If no merge key, concatenate columns.
    """
    if notion_df is None or notion_df.empty:
        return uploaded_df
    if uploaded_df is None or uploaded_df.empty:
        return notion_df

    if merge_key and merge_key in notion_df.columns and merge_key in uploaded_df.columns:
        merged = pd.merge(notion_df, uploaded_df, on=merge_key, how=merge_how)
        st.success(f"✅ Merged on '{merge_key}' — {len(merged)} rows")
        return merged

    # No merge key — concatenate (row-wise if same columns, column-wise otherwise)
    common_cols = set(notion_df.columns) & set(uploaded_df.columns)
    if len(common_cols) > 0:
        merged = pd.concat([notion_df, uploaded_df], ignore_index=True)
        st.info(f"📊 Appended datasets — {len(merged)} rows total")
    else:
        merged = pd.concat([notion_df, uploaded_df], axis=1)
        st.info(f"📊 Combined datasets side-by-side — {len(merged)} rows, {len(merged.columns)} columns")
    return merged

def manual_data_entry() -> pd.DataFrame:
    """Create a simple UI for manual data entry."""
    st.subheader("📝 Manual Data Entry")
    st.caption("Enter small datasets quickly for analysis")
    col1, col2 = st.columns(2)
    with col1:
        n_rows = st.number_input("Number of rows", min_value=1, max_value=50, value=5)
    with col2:
        n_cols = st.number_input("Number of columns", min_value=1, max_value=20, value=3)

    col_names = []
    for i in range(n_cols):
        col_names.append(st.text_input(f"Column {i+1} name", value=f"Variable_{i+1}", key=f"man_col_{i}"))

    data = {col: [] for col in col_names}
    for row_idx in range(n_rows):
        cols = st.columns(n_cols)
        for col_idx, col_name in enumerate(col_names):
            with cols[col_idx]:
                val = st.text_input("", key=f"man_val_{row_idx}_{col_idx}", label_visibility="collapsed")
                data[col_name].append(val)

    if st.button("✅ Create Dataset", type="primary"):
        df = pd.DataFrame(data)
        st.success(f"Created dataset: {len(df)} rows × {len(df.columns)} columns")
        return df
    return pd.DataFrame()

