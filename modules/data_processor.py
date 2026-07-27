"""
Data Processor — handles data type inference, cleaning, aggregation, and merging.
Includes provenance tracking integration for full lineage logging.
"""
import warnings
from typing import Dict, List, Any, Optional, Tuple, Callable
import pandas as pd
import numpy as np
from datetime import datetime

from modules.pandas_compat import is_text_dtype, text_columns

# ─── Provenance Integration ──────────────────────────────────────────
try:
    from modules.data_provenance import ProvenanceTracker, with_provenance
    _HAS_PROVENANCE = True
except ImportError:
    _HAS_PROVENANCE = False
    ProvenanceTracker = None
    with_provenance = None

# ─── Column Type Inference ────────────────────────────────────────────
def infer_column_type(series: pd.Series) -> str:
    """Infer the semantic type of a pandas Series."""
    # Drop NaN for type inference
    clean = series.dropna()
    if len(clean) == 0:
        return "unknown"

    dtype = clean.dtype

    if pd.api.types.is_integer_dtype(dtype):
        return "integer"
    if pd.api.types.is_float_dtype(dtype):
        return "numeric"
    if pd.api.types.is_bool_dtype(dtype):
        return "boolean"
    try:
        with warnings.catch_warnings():
            # Heterogeneous text columns are expected here; the format probe is deliberate.
            warnings.simplefilter("ignore", UserWarning)
            parsed = pd.to_datetime(clean, errors="coerce")
        if parsed.notna().sum() > len(clean) * 0.5:
            return "temporal"
    except (ValueError, TypeError):
        pass

    # Check for categorical
    if len(clean.unique()) <= min(20, len(clean) * 0.1):
        return "categorical"

    # Check for text / rich text
    if is_text_dtype(clean):
        sample = clean.iloc[0] if len(clean) > 0 else ""
        if isinstance(sample, str) and len(sample) > 50:
            return "text"
        return "string"

    return "unknown"

def infer_column_types(df: pd.DataFrame) -> Dict[str, str]:
    """Infer types for all columns in a DataFrame."""
    return {col: infer_column_type(df[col]) for col in df.columns}

def get_column_summary(df: pd.DataFrame, col: str) -> Dict[str, Any]:
    """Get comprehensive summary statistics for a single column."""
    col_type = infer_column_type(df[col])
    summary = {
        "name": col,
        "type": col_type,
        "dtype": str(df[col].dtype),
        "non_null_count": int(df[col].notna().sum()),
        "null_count": int(df[col].isna().sum()),
        "null_pct": round(float(df[col].isna().mean() * 100), 2),
        "unique_count": int(df[col].nunique()),
        "unique_pct": round(float(df[col].nunique() / max(len(df), 1) * 100), 2),
    }

    if col_type in ("numeric", "integer"):
        summary.update({
            "mean": round(float(df[col].mean()), 4) if not df[col].isna().all() else None,
            "median": round(float(df[col].median()), 4) if not df[col].isna().all() else None,
            "std": round(float(df[col].std()), 4) if not df[col].isna().all() else None,
            "var": round(float(df[col].var()), 4) if not df[col].isna().all() else None,
            "min": round(float(df[col].min()), 4) if not df[col].isna().all() else None,
            "max": round(float(df[col].max()), 4) if not df[col].isna().all() else None,
            "q1": round(float(df[col].quantile(0.25)), 4) if not df[col].isna().all() else None,
            "q3": round(float(df[col].quantile(0.75)), 4) if not df[col].isna().all() else None,
            "iqr": round(float(df[col].quantile(0.75) - df[col].quantile(0.25)), 4) if not df[col].isna().all() else None,
            "skewness": round(float(df[col].skew()), 4) if not df[col].isna().all() else None,
            "kurtosis": round(float(df[col].kurtosis()), 4) if not df[col].isna().all() else None,
        })
    elif col_type == "temporal":
        summary.update({
            "min_date": str(df[col].min()) if not df[col].isna().all() else None,
            "max_date": str(df[col].max()) if not df[col].isna().all() else None,
            "range_days": (df[col].max() - df[col].min()).days if not df[col].isna().all() else None,
        })
    elif col_type in ("categorical", "string"):
        top_values = df[col].value_counts().head(10)
        summary.update({
            "top_values": top_values.to_dict(),
            "top_value": str(top_values.index[0]) if len(top_values) > 0 else None,
            "top_freq": int(top_values.iloc[0]) if len(top_values) > 0 else None,
        })

    return summary

# ─── Data Profiling ───────────────────────────────────────────────────
def profile_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate a full profile of the dataset."""
    col_types = infer_column_types(df)
    return {
        "rows": len(df),
        "columns": len(df.columns),
        "memory_usage": df.memory_usage(deep=True).sum(),
        "column_types": col_types,
        "type_distribution": pd.Series(list(col_types.values())).value_counts().to_dict(),
        "missing_cells": int(df.isna().sum().sum()),
        "missing_pct": round(float(df.isna().mean().mean() * 100), 2),
        "duplicate_rows": int(df.duplicated().sum()),
        "numeric_columns": [c for c, t in col_types.items() if t in ("numeric", "integer")],
        "categorical_columns": [c for c, t in col_types.items() if t in ("categorical", "string")],
        "temporal_columns": [c for c, t in col_types.items() if t == "temporal"],
        "boolean_columns": [c for c, t in col_types.items() if t == "boolean"],
    }

# ─── Data Cleaning ────────────────────────────────────────────────────
def clean_dataframe(df: pd.DataFrame, options: Dict[str, bool] = None) -> pd.DataFrame:
    """Clean a DataFrame based on options."""
    if options is None:
        options = {
            "remove_duplicates": True,
            "fill_numeric_na": "mean",
            "fill_categorical_na": "mode",
            "strip_whitespace": True,
        }
    df = df.copy()

    if options.get("remove_duplicates"):
        df = df.drop_duplicates()

    if options.get("strip_whitespace"):
        for col in text_columns(df):
            df[col] = df[col].astype(str).str.strip()

    if options.get("fill_numeric_na") == "mean":
        for col in df.select_dtypes(include=[np.number]).columns:
            df[col] = df[col].fillna(df[col].mean())
    elif options.get("fill_numeric_na") == "median":
        for col in df.select_dtypes(include=[np.number]).columns:
            df[col] = df[col].fillna(df[col].median())
    elif options.get("fill_numeric_na") == "zero":
        df[df.select_dtypes(include=[np.number]).columns] = df.select_dtypes(include=[np.number]).fillna(0)

    if options.get("fill_categorical_na") == "mode":
        for col in text_columns(df):
            if df[col].isna().any():
                mode_val = df[col].mode()
                if len(mode_val) > 0:
                    df[col] = df[col].fillna(mode_val[0])
    return df

# ─── Aggregation Engine ───────────────────────────────────────────────
def groupby_aggregate(
    df: pd.DataFrame,
    group_cols: List[str],
    agg_col: str,
    agg_func: str = "mean",
) -> pd.DataFrame:
    """Perform groupby aggregation."""
    valid_funcs = ["mean", "sum", "count", "min", "max", "std", "var", "median"]
    if agg_func not in valid_funcs:
        agg_func = "mean"
    return df.groupby(group_cols)[agg_col].agg(agg_func).reset_index()

def pivot_table(
    df: pd.DataFrame,
    index_cols: List[str],
    columns_col: str,
    values_col: str,
    agg_func: str = "mean",
) -> pd.DataFrame:
    """Create a pivot table."""
    return df.pivot_table(
        index=index_cols,
        columns=columns_col,
        values=values_col,
        aggfunc=agg_func,
    ).reset_index()

def rolling_aggregate(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    window: int = 7,
    agg_func: str = "mean",
) -> pd.DataFrame:
    """Compute rolling window aggregation over a date-ordered series."""
    df_sorted = df.sort_values(date_col).reset_index(drop=True)
    rolling = df_sorted[value_col].rolling(window=window, min_periods=1)
    if agg_func == "mean":
        df_sorted[f"rolling_{agg_func}_{window}"] = rolling.mean()
    elif agg_func == "sum":
        df_sorted[f"rolling_{agg_func}_{window}"] = rolling.sum()
    elif agg_func == "std":
        df_sorted[f"rolling_{agg_func}_{window}"] = rolling.std()
    return df_sorted

# ─── Outlier Detection ────────────────────────────────────────────────
def detect_outliers_iqr(df: pd.DataFrame, col: str, multiplier: float = 1.5) -> pd.Series:
    """Detect outliers using the IQR method."""
    q1 = df[col].quantile(0.25)
    q3 = df[col].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr
    return (df[col] < lower) | (df[col] > upper)

def detect_outliers_zscore(df: pd.DataFrame, col: str, threshold: float = 3.0) -> pd.Series:
    """Detect outliers using the Z-score method."""
    mean = df[col].mean()
    std = df[col].std()
    if std == 0:
        return pd.Series([False] * len(df))
    z_scores = (df[col] - mean) / std
    return z_scores.abs() > threshold

# ─── Binning / Discretization ─────────────────────────────────────────
def bin_column(
    df: pd.DataFrame,
    col: str,
    bins: int = 5,
    labels: List[str] = None,
) -> pd.Series:
    """Discretize a numeric column into bins."""
    return pd.cut(df[col], bins=bins, labels=labels)

def bin_column_quantile(
    df: pd.DataFrame,
    col: str,
    q: int = 4,
    labels: List[str] = None,
) -> pd.Series:
    """Discretize based on quantiles."""
    return pd.qcut(df[col], q=q, labels=labels)


# ═══════════════════════════════════════════════════════════════════════
# PROVENANCE-TRACKED WRAPPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def tracked_clean_dataframe(
    df: pd.DataFrame,
    tracker: "ProvenanceTracker",
    options: Dict[str, bool] = None,
) -> pd.DataFrame:
    """Clean a DataFrame with provenance tracking."""
    if tracker is None:
        return clean_dataframe(df, options)

    with tracker.track(
        "clean_dataframe",
        operation_desc="Remove duplicates, fill NAs, strip whitespace",
        parameters={"options": options},
    ) as ctx:
        result = clean_dataframe(df, options)
        ctx.capture(df, result)
        return result


def tracked_groupby_aggregate(
    df: pd.DataFrame,
    tracker: "ProvenanceTracker",
    group_cols: List[str],
    agg_col: str,
    agg_func: str = "mean",
) -> pd.DataFrame:
    """Groupby aggregation with provenance tracking."""
    if tracker is None:
        return groupby_aggregate(df, group_cols, agg_col, agg_func)

    with tracker.track(
        "groupby_aggregate",
        operation_desc=f"Group by {group_cols}, aggregate {agg_col} with {agg_func}",
        parameters={"group_cols": group_cols, "agg_col": agg_col, "agg_func": agg_func},
    ) as ctx:
        result = groupby_aggregate(df, group_cols, agg_col, agg_func)
        ctx.capture(df, result)
        return result


def tracked_pivot_table(
    df: pd.DataFrame,
    tracker: "ProvenanceTracker",
    index_cols: List[str],
    columns_col: str,
    values_col: str,
    agg_func: str = "mean",
) -> pd.DataFrame:
    """Pivot table with provenance tracking."""
    if tracker is None:
        return pivot_table(df, index_cols, columns_col, values_col, agg_func)

    with tracker.track(
        "pivot_table",
        operation_desc=f"Pivot: index={index_cols}, columns={columns_col}, values={values_col}",
        parameters={
            "index_cols": index_cols,
            "columns_col": columns_col,
            "values_col": values_col,
            "agg_func": agg_func,
        },
    ) as ctx:
        result = pivot_table(df, index_cols, columns_col, values_col, agg_func)
        ctx.capture(df, result)
        return result


def tracked_rolling_aggregate(
    df: pd.DataFrame,
    tracker: "ProvenanceTracker",
    date_col: str,
    value_col: str,
    window: int = 7,
    agg_func: str = "mean",
) -> pd.DataFrame:
    """Rolling aggregate with provenance tracking."""
    if tracker is None:
        return rolling_aggregate(df, date_col, value_col, window, agg_func)

    with tracker.track(
        "rolling_aggregate",
        operation_desc=f"Rolling {agg_func} of {value_col} over {window} periods",
        parameters={"date_col": date_col, "value_col": value_col, "window": window, "agg_func": agg_func},
    ) as ctx:
        result = rolling_aggregate(df, date_col, value_col, window, agg_func)
        ctx.capture(df, result)
        return result


def tracked_bin_column(
    df: pd.DataFrame,
    tracker: "ProvenanceTracker",
    col: str,
    bins: int = 5,
    labels: List[str] = None,
) -> pd.Series:
    """Bin a column with provenance tracking."""
    if tracker is None:
        return bin_column(df, col, bins, labels)

    with tracker.track(
        "bin_column",
        operation_desc=f"Discretize {col} into {bins} bins",
        parameters={"col": col, "bins": bins, "labels": labels},
    ) as ctx:
        result = bin_column(df, col, bins, labels)
        ctx.capture(df, df.copy())  # Capture even though result is a Series
        return result


def get_tracker_from_session() -> "ProvenanceTracker":
    """Get or create a provenance tracker from Streamlit session state."""
    import streamlit as st

    tracker = st.session_state.get("_provenance_tracker")
    if tracker is None:
        from modules.data_provenance import ProvenanceTracker
        tracker = ProvenanceTracker()
        st.session_state["_provenance_tracker"] = tracker
    return tracker

