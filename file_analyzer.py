
"""File Analyzer  Local File Parser & Fallback Analytics."""
import pandas as pd
import streamlit as st
from typing import Optional

SUPPORTED_FORMATS = ["csv", "xlsx", "xls", "json", "parquet", "pkl"]

def parse_uploaded_file(uploaded_file) -> Optional[pd.DataFrame]:
    """Parse an uploaded file into a DataFrame."""
    if uploaded_file is None:
        return None
    
    ext = uploaded_file.name.split(".")[-1].lower()
    df = None
    error_msg = None
    
    try:
        if ext == "csv":
            try:
                df = pd.read_csv(uploaded_file, encoding="utf-8")
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                try:
                    df = pd.read_csv(uploaded_file, encoding="latin-1")
                except:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, encoding="iso-8859-1")
        
        elif ext in ("xlsx", "xls"):
            df = pd.read_excel(uploaded_file)
        
        elif ext == "json":
            df = pd.read_json(uploaded_file)
        
        elif ext == "parquet":
            df = pd.read_parquet(uploaded_file)
        
        elif ext in ("pkl", "pickle"):
            df = pd.read_pickle(uploaded_file)
        
        else:
            error_msg = f"Unsupported: .{ext}"
    
    except Exception as e:
        error_msg = str(e)
    
    if error_msg:
        st.error(f"Error: {error_msg}")
        return None
    
    if df is not None:
        df.columns = [str(c).strip() for c in df.columns]
    
    return df

def get_column_stats(df: pd.DataFrame) -> dict:
    """Generate statistical summary for DataFrame columns."""
    if df is None or df.empty:
        return {}
    
    stats = {}
    for col in df.columns:
        col_data = df[col]
        col_stats = {
            "dtype": str(col_data.dtype),
            "null_count": int(col_data.isnull().sum()),
            "unique_count": int(col_data.nunique()),
            "missing_pct": round(col_data.isnull().sum() / len(df) * 100, 1)
        }
        
        # Numeric stats
        if pd.api.types.is_numeric_dtype(col_data):
            col_stats["min"] = col_data.min()
            col_stats["max"] = col_data.max()
            col_stats["mean"] = round(col_data.mean(), 2)
            col_stats["median"] = round(col_data.median(), 2)
        
        # String stats
        elif pd.api.types.is_object_dtype(col_data):
            col_stats["min_len"] = col_data.astype(str).str.len().min()
            col_stats["max_len"] = col_data.astype(str).str.len().max()
        
        stats[col] = col_stats
    
    return stats

def render_file_analyzer_page():
    """Render the File Analyzer UI."""
    st.write("Upload CSV, Excel, JSON, Parquet, or Pickle files for analysis.")
    
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=SUPPORTED_FORMATS,
        help="Supported: CSV, Excel (.xlsx/.xls), JSON, Parquet, Pickle"
    )
    
    if uploaded_file:
        df = parse_uploaded_file(uploaded_file)
        
        if df is not None and not df.empty:
            st.success(f"Loaded: {len(df)} rows Ãƒâ€” {len(df.columns)} columns")
            
            # Store in session
            st.session_state["uploaded_df"] = df
            
            # Show data preview
            with st.expander(" Data Preview", expanded=True):
                st.dataframe(df.head(50), use_container_width=True)
            
            # Column statistics
            st.subheader("ðŸ“ˆ Column Statistics")
            stats = get_column_stats(df)
            
            for col, col_stats in stats.items():
                with st.expander(f"ðŸ“‹ {col}"):
                    cols = st.columns(4)
                    cols[0].metric("Type", col_stats["dtype"])
                    cols[1].metric("Nulls", f"{col_stats['null_count']} ({col_stats['missing_pct']}%)")
                    cols[2].metric("Unique", col_stats["unique_count"])
                    
                    if "mean" in col_stats:
                        cols[3].metric("Mean", col_stats["mean"])
                        st.caption(f"Range: {col_stats['min']} - {col_stats['max']} | Median: {col_stats['median']}")
                    elif "min_len" in col_stats:
                        st.caption(f"String length: {col_stats['min_len']} - {col_stats['max_len']}")
        else:
            st.info("No data loaded. Upload a file to begin.")
    else:
        st.info("Drag and drop a file above to analyze.")

