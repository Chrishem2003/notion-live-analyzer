"""
Data Transformation Engine  SPSS-like Compute, Recode, Rank, Count, Shift, and Binning.
Provides a UI for transforming variables with full SPSS compatibility.
"""
from typing import Dict, List, Any, Optional, Tuple, Union
import pandas as pd
import numpy as np
import re
import streamlit as st
from datetime import datetime, timedelta

# ─── Compute Variable ────────────────────────────────────────────────

def compute_variable(
    df: pd.DataFrame,
    expression: str,
    new_var_name: str,
) -> pd.DataFrame:
    """
    Compute a new variable using a Python expression.
    Supports: +, -, *, /, **, %, log(), sqrt(), abs(), round(), 
    mean(), sum(), min(), max(), ifelse(), recode()
    """
    df = df.copy()
    safe_builtins = {
        'abs': abs, 'round': round, 'int': int, 'float': float,
        'str': str, 'len': len, 'pow': pow, 'max': max, 'min': min,
        'sum': sum, 'mean': np.mean, 'sqrt': np.sqrt, 'log': np.log,
        'log10': np.log10, 'exp': np.exp, 'sin': np.sin, 'cos': np.cos,
        'tan': np.tan, 'floor': np.floor, 'ceil': np.ceil,
    }

    def ifelse(condition, true_val, false_val):
        """SPSS-like IF/THEN/ELSE function."""
        return np.where(condition, true_val, false_val)

    safe_builtins['ifelse'] = ifelse

    try:
        # Replace SPSS-like functions with Python
        expr_clean = expression.strip()
        result = df.eval(expr_clean, local_dict=safe_builtins)
        df[new_var_name] = result
        return df
    except Exception as e:
        st.error(f"Compute error: {str(e)}")
        return df


# ─── Recode Functions ────────────────────────────────────────────────

def recode_same(
    df: pd.DataFrame,
    col: str,
    mappings: Dict[Any, Any],
    else_val: Any = None,
    new_var: Optional[str] = None,
) -> pd.DataFrame:
    """
    Recode values to new values (same variable or new variable).
    Like SPSS Recode: recode old_val -> new_val.
    """
    df = df.copy()
    target = new_var or col
    if new_var:
        df[target] = df[col].copy()

    df[target] = df[target].replace(mappings)
    if else_val is not None:
        df.loc[~df[target].isin(list(mappings.values())), target] = else_val
    return df


def recode_different(
    df: pd.DataFrame,
    col: str,
    into_col: str,
    ranges: List[Tuple[float, float, Any]],
) -> pd.DataFrame:
    """
    Recode ranges into new values (like SPSS Recode into Different Variable).
    ranges: list of (lower_bound, upper_bound, new_value)
    """
    df = df.copy()
    df[into_col] = np.nan

    for lower, upper, new_val in ranges:
        if lower == float('-inf'):
            mask = df[col] <= upper
        elif upper == float('inf'):
            mask = df[col] >= lower
        else:
            mask = (df[col] >= lower) & (df[col] <= upper)
        df.loc[mask, into_col] = new_val

    return df


# ─── Rank Cases ──────────────────────────────────────────────────────

def rank_cases(
    df: pd.DataFrame,
    col: str,
    method: str = "average",
    ascending: bool = True,
    group_col: Optional[str] = None,
    new_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Rank cases (like SPSS Rank Cases).
    Methods: average, min, max, dense, ordinal, pct, percentile
    """
    df = df.copy()
    rank_col = new_col or f"{col}_rank"

    rank_methods = {
        "average": "average",
        "lowest": "min",
        "highest": "max",
        "sequential": "first",
        "dense": "dense",
    }

    pandas_method = rank_methods.get(method, "average")

    if group_col:
        df[rank_col] = df.groupby(group_col)[col].rank(
            method=pandas_method, ascending=ascending
        )
    else:
        df[rank_col] = df[col].rank(
            method=pandas_method, ascending=ascending
        )

    # Percentage rank
    if method == "pct":
        df[rank_col] = df[rank_col] / len(df) * 100
    elif method == "percentile":
        df[rank_col] = df[col].rank(pct=True) * 100

    return df


# ─── Count Occurrences ──────────────────────────────────────────────

def count_occurrences(
    df: pd.DataFrame,
    value: Any,
    columns: List[str],
    new_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Count occurrences of a value across multiple columns (Like SPSS Count).
    """
    df = df.copy()
    count_col = new_col or f"count_{value}"
    df[count_col] = df[columns].apply(
        lambda row: sum(1 for v in row if pd.notna(v) and str(v) == str(value)),
        axis=1
    )
    return df


# ─── Shift / Lag ────────────────────────────────────────────────────

def shift_variable(
    df: pd.DataFrame,
    col: str,
    periods: int = 1,
    group_col: Optional[str] = None,
    new_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Create lag/lead variables (like SPSS Shift).
    Positive periods = lag (previous values), negative = lead (next values).
    """
    df = df.copy()
    shift_col = new_col or f"{col}_lag{abs(periods)}"
    if group_col:
        df[shift_col] = df.groupby(group_col)[col].shift(periods)
    else:
        df[shift_col] = df[col].shift(periods)
    return df


# ─── Binning / Discretization ──────────────────────────────────────

def bin_variable(
    df: pd.DataFrame,
    col: str,
    bins: Union[int, List[float]],
    labels: Optional[List[str]] = None,
    new_col: Optional[str] = None,
    include_lowest: bool = True,
) -> pd.DataFrame:
    """
    Bin/discretize a numeric variable (like SPSS Visual Binning).
    """
    df = df.copy()
    bin_col = new_col or f"{col}_binned"

    if isinstance(bins, int):
        df[bin_col] = pd.cut(
            df[col], bins=bins, labels=labels,
            include_lowest=include_lowest
        )
    else:
        df[bin_col] = pd.cut(
            df[col], bins=bins, labels=labels,
            include_lowest=include_lowest, right=False
        )

    return df


# ─── Rename Variables ──────────────────────────────────────────────

def rename_variables(df: pd.DataFrame, rename_map: Dict[str, str]) -> pd.DataFrame:
    """Rename multiple variables at once (like SPSS Rename)."""
    df = df.copy()
    df.rename(columns=rename_map, inplace=True)

    # Update metadata if exists
    metadata = st.session_state.get("variable_metadata", {})
    if metadata:
        for old_name, new_name in rename_map.items():
            if old_name in metadata:
                metadata[new_name] = metadata.pop(old_name)
                metadata[new_name]["label"] = new_name
        st.session_state["variable_metadata"] = metadata

    return df


# ─── Sort Cases ────────────────────────────────────────────────────

def sort_cases(
    df: pd.DataFrame,
    sort_keys: List[Tuple[str, bool]],
) -> pd.DataFrame:
    """
    Sort cases by one or more variables (like SPSS Sort Cases).
    sort_keys: list of (column, ascending_bool)
    """
    df = df.copy()
    by_cols = [k[0] for k in sort_keys]
    ascending = [k[1] for k in sort_keys]
    df = df.sort_values(by=by_cols, ascending=ascending).reset_index(drop=True)
    return df


# ─── Select Cases ──────────────────────────────────────────────────

def select_cases(
    df: pd.DataFrame,
    condition: str,
    mode: str = "filter",
) -> pd.DataFrame:
    """
    Select cases by condition (like SPSS Select Cases).
    mode: 'filter' to remove, 'indicator' to add filter column
    """
    df = df.copy()
    try:
        mask = df.eval(condition)
        if mode == "filter":
            return df[mask].reset_index(drop=True)
        else:
            df["_filter_$"] = mask
            return df
    except Exception as e:
        st.error(f"Selection error: {str(e)}")
        return df


# ─── Weight Cases ──────────────────────────────────────────────────

def weight_cases(df: pd.DataFrame, weight_col: str) -> pd.DataFrame:
    """
    Apply case weights (like SPSS Weight Cases).
    Creates expanded dataset based on weight frequencies.
    """
    df = df.copy()
    try:
        weights = df[weight_col].fillna(1).astype(int)
        weights = weights.clip(lower=0)
        repeated = df.loc[df.index.repeat(weights)].reset_index(drop=True)
        repeated = repeated.drop(columns=[weight_col], errors="ignore")
        return repeated
    except Exception as e:
        st.error(f"Weighting error: {str(e)}")
        return df


# ─── UI Renderers ───────────────────────────────────────────────────

def render_compute_ui(df: pd.DataFrame) -> pd.DataFrame:
    """Render the Compute Variable UI."""
    st.subheader("🧮 Compute Variable")
    st.caption("Create a new variable based on an expression (like SPSS Compute)")

    cols = df.columns.tolist()
    col1, col2 = st.columns([2, 1])
    with col1:
        new_var = st.text_input("New variable name", value="new_var", key="compute_new")
    with col2:
        st.caption("")

    st.markdown("**Available functions:** `log(x)`, `sqrt(x)`, `abs(x)`, `round(x)`, `ifelse(condition, true, false)`, `mean(x)`, `sum(x)`")

    # Expression builder helpers
    st.markdown("**Insert column:**")
    expr_cols = st.multiselect("Select columns to include", options=cols, key="compute_cols", label_visibility="collapsed")
    expr_preview = " + ".join(expr_cols) if expr_cols else ""

    expression = st.text_area(
        "Expression (Python syntax, use column names directly)",
        value=expr_preview,
        height=100,
        key="compute_expr",
        help="Examples: 'salary * 1.1', 'log(income)', 'ifelse(age >= 18, adult, minor)'"
    )

    if st.button("▶️ Compute", type="primary"):
        if expression and new_var:
            result_df = compute_variable(df, expression, new_var)
            if new_var in result_df.columns:
                st.success(f"✅ Created '{new_var}'")
                return result_df

    return df


def render_recode_ui(df: pd.DataFrame) -> pd.DataFrame:
    """Render the Recode UI."""
    st.subheader("🔄 Recode Values")
    st.caption("Recode values into same or different variable (like SPSS Recode)")

    cols = df.columns.tolist()
    recode_type = st.radio("Recode type", ["Into Same Variable", "Into Different Variable", "Into Different (Ranges)"], horizontal=True)

    if recode_type == "Into Same Variable":
        col = st.selectbox("Select variable", options=cols, key="rec_same_col")
        df_result = df.copy()

        st.markdown("**Value mappings (old → new):**")
        mappings = {}
        num_mappings = st.number_input("Number of mappings", min_value=1, max_value=20, value=3, key="n_rec_same")

        for i in range(int(num_mappings)):
            c1, c2, c3 = st.columns(3)
            with c1:
                old_val = st.text_input(f"Old value {i+1}", key=f"rec_old_{i}")
            with c2:
                new_val = st.text_input(f"New value {i+1}", key=f"rec_new_{i}")
            with c3:
                st.caption("→")
            if old_val:
                try:
                    old_converted = float(old_val) if "." in old_val else int(old_val)
                except ValueError:
                    old_converted = old_val
                try:
                    new_converted = float(new_val) if "." in new_val else int(new_val)
                except ValueError:
                    new_converted = new_val
                mappings[old_converted] = new_converted

        else_val = st.text_input("Else (value for unmatched)", value="", key="rec_else")

        if st.button("▶️ Recode", type="primary"):
            else_converted = None
            if else_val:
                try:
                    else_converted = float(else_val) if "." in else_val else int(else_val)
                except ValueError:
                    else_converted = else_val
            df_result = recode_same(df, col, mappings, else_converted)
            st.success("✅ Recoded successfully")
            return df_result

    elif recode_type == "Into Different Variable":
        col = st.selectbox("Select variable", options=cols, key="rec_diff_col")
        new_col = st.text_input("New variable name", value=f"{col}_recoded", key="rec_diff_new")
        df_result = df.copy()

        mappings = {}
        num_mappings = st.number_input("Number of mappings", min_value=1, max_value=20, value=3, key="n_rec_diff")

        for i in range(int(num_mappings)):
            c1, c2 = st.columns(2)
            with c1:
                old_val = st.text_input(f"Old value {i+1}", key=f"rec_dold_{i}")
            with c2:
                new_val = st.text_input(f"New value {i+1}", key=f"rec_dnew_{i}")
            if old_val:
                try:
                    old_converted = float(old_val) if "." in old_val else int(old_val)
                except ValueError:
                    old_converted = old_val
                try:
                    new_converted = float(new_val) if "." in new_val else int(new_val)
                except ValueError:
                    new_converted = new_val
                mappings[old_converted] = new_converted

        if st.button("▶️ Recode into Different", type="primary"):
            df_result = recode_same(df, col, mappings, new_var=new_col)
            st.success(f"✅ Created '{new_col}'")
            return df_result

    else:  # Into Different Variable (Ranges)
        col = st.selectbox("Select numeric variable", options=df.select_dtypes(include=[np.number]).columns.tolist(), key="rec_range_col")
        new_col = st.text_input("New variable name", value=f"{col}_grouped", key="rec_range_new")
        df_result = df.copy()

        num_ranges = st.number_input("Number of ranges", min_value=1, max_value=10, value=3, key="n_ranges")
        ranges = []
        for i in range(int(num_ranges)):
            c1, c2, c3 = st.columns(3)
            with c1:
                lower = st.number_input(f"Lower bound {i+1}", value=float('-inf') if i == 0 else 0.0, key=f"rng_low_{i}", format="%f")
            with c2:
                upper = st.number_input(f"Upper bound {i+1}", value=float('inf') if i == int(num_ranges)-1 else 100.0, key=f"rng_high_{i}", format="%f")
            with c3:
                new_val = st.text_input(f"New value {i+1}", value=str(i+1), key=f"rng_val_{i}")
            try:
                new_val_converted = float(new_val) if "." in new_val else int(new_val)
            except ValueError:
                new_val_converted = new_val
            ranges.append((lower, upper, new_val_converted))

        if st.button("▶️ Recode Ranges", type="primary"):
            df_result = recode_different(df, col, new_col, ranges)
            st.success(f"✅ Created '{new_col}'")
            return df_result

    return df


def render_rank_ui(df: pd.DataFrame) -> pd.DataFrame:
    """Render the Rank Cases UI."""
    st.subheader("🏆 Rank Cases")
    st.caption("Rank cases by variable (like SPSS Rank Cases)")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cols = df.columns.tolist()

    col = st.selectbox("Rank by variable", options=numeric_cols if numeric_cols else cols, key="rank_col")
    method = st.selectbox(
        "Rank method",
        options=["average", "lowest", "highest", "sequential", "dense", "pct", "percentile"],
        index=0,
        key="rank_method",
        help="Average=mean of tied ranks, Lowest=min rank, Highest=max rank, Sequential=first seen first, Dense=no gaps"
    )
    ascending = st.checkbox("Ascending order (lowest gets rank 1)", value=True, key="rank_asc")
    group_col = st.selectbox("Group by (optional)", options=[""] + cols, key="rank_group")
    new_col = st.text_input("Rank variable name", value=f"{col}_rank", key="rank_new")

    if st.button("▶️ Rank Cases", type="primary"):
        result_df = rank_cases(
            df, col, method=method, ascending=ascending,
            group_col=group_col if group_col else None,
            new_col=new_col if new_col else None
        )
        st.success(f"✅ Created '{new_col}'")
        return result_df
    return df


def render_count_ui(df: pd.DataFrame) -> pd.DataFrame:
    """Render the Count Occurrences UI."""
    st.subheader("🔢 Count Occurrences")
    st.caption("Count occurrences of a value across variables (like SPSS Count)")

    cols = df.columns.tolist()
    value = st.text_input("Value to count", value="1", key="count_val")
    selected_cols = st.multiselect("Count across variables", options=cols, key="count_cols")
    new_col = st.text_input("Count variable name", value=f"count_{value}", key="count_new")

    if st.button("▶️ Count Occurrences", type="primary"):
        result_df = count_occurrences(df, value, selected_cols, new_col)
        st.success(f"✅ Created '{new_col}'")
        return result_df
    return df


def render_shift_ui(df: pd.DataFrame) -> pd.DataFrame:
    """Render the Shift/Lag UI."""
    st.subheader("⏳ Create Lag/Lead Variable")
    st.caption("Shift values forward or backward in time (like SPSS Create Lag)")

    cols = df.columns.tolist()
    col = st.selectbox("Variable to shift", options=cols, key="shift_col")
    periods = st.number_input("Periods (positive=lag, negative=lead)", value=1, key="shift_periods")
    group_col = st.selectbox("Group by (optional for panel data)", options=[""] + cols, key="shift_group")
    new_col = st.text_input("New variable name", value=f"{col}_lag{abs(periods)}", key="shift_new")

    if st.button("▶️ Create Shift", type="primary"):
        result_df = shift_variable(df, col, periods=int(periods), group_col=group_col or None, new_col=new_col)
        st.success(f"✅ Created '{new_col}'")
        return result_df
    return df


def render_binning_ui(df: pd.DataFrame) -> pd.DataFrame:
    """Render the Visual Binning UI."""
    st.subheader("📊 Visual Binning")
    st.caption("Bin/discretize numeric variables (like SPSS Visual Binning)")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        st.warning("No numeric variables available for binning.")
        return df

    col = st.selectbox("Variable to bin", options=numeric_cols, key="bin_col")
    new_col = st.text_input("Binned variable name", value=f"{col}_binned", key="bin_new")

    bin_method = st.radio("Binning method", ["Equal-width bins", "Custom cut points"], horizontal=True)

    if bin_method == "Equal-width bins":
        n_bins = st.slider("Number of bins", min_value=2, max_value=20, value=4, key="bin_n")
        label_type = st.radio("Labels", ["Integer labels", "Range labels"], horizontal=True, key="bin_labels")
        if label_type == "Integer labels":
            labels = [str(i+1) for i in range(n_bins)]
        else:
            labels = None

        if st.button("▶️ Bin Variable", type="primary"):
            result_df = bin_variable(df, col, bins=n_bins, labels=labels, new_col=new_col)
            st.success(f"✅ Created '{new_col}'")
            # Show distribution
            st.dataframe(result_df[new_col].value_counts().reset_index(), use_container_width=True, hide_index=True)
            return result_df
    else:
        series = df[col].dropna()
        min_val = float(series.min())
        max_val = float(series.max())
        cut_points_str = st.text_input(
            "Cut points (comma-separated, e.g.: 0, 10, 20, 30)",
            value=f"{min_val:.1f}, {(max_val-min_val)/3+min_val:.1f}, {2*(max_val-min_val)/3+min_val:.1f}, {max_val:.1f}",
            key="bin_cuts"
        )
        labels_str = st.text_input("Labels (comma-separated)", value="Low, Medium, High", key="bin_clabels")

        if st.button("▶️ Bin with Cut Points", type="primary"):
            try:
                cuts = [float(c.strip()) for c in cut_points_str.split(",")]
                if labels_str:
                    labels = [l.strip() for l in labels_str.split(",")]
                else:
                    labels = None
                result_df = bin_variable(df, col, bins=cuts, labels=labels, new_col=new_col)
                st.success(f"✅ Created '{new_col}'")
                st.dataframe(result_df[new_col].value_counts().reset_index(), use_container_width=True, hide_index=True)
                return result_df
            except Exception as e:
                st.error(f"Binning error: {str(e)}")

    return df


def render_sort_ui(df: pd.DataFrame) -> pd.DataFrame:
    """Render the Sort Cases UI."""
    st.subheader("🔀 Sort Cases")
    st.caption("Sort data by one or more variables (like SPSS Sort Cases)")

    cols = df.columns.tolist()
    sort_cols = st.multiselect("Sort by (in order)", options=cols, key="sort_cols")
    if sort_cols:
        sort_keys = []
        for col in sort_cols:
            asc = st.checkbox(f"Ascending for {col}", value=True, key=f"sort_asc_{col}")
            sort_keys.append((col, asc))

        if st.button("▶️ Sort Cases", type="primary"):
            result_df = sort_cases(df, sort_keys)
            st.success(f"✅ Sorted by {', '.join(sort_cols)}")
            return result_df
    return df


def render_select_ui(df: pd.DataFrame) -> pd.DataFrame:
    """Render the Select Cases UI."""
    st.subheader("🔍 Select Cases")
    st.caption("Select/filter cases by condition (like SPSS Select Cases)")

    cols = df.columns.tolist()
    condition = st.text_area(
        "Condition (Python syntax, using column names directly)",
        placeholder="Example: age >= 18 AND gender == 'Male'",
        height=80,
        key="select_cond"
    )
    mode = st.radio("Action", ["Filter (remove unselected)", "Create indicator variable"], horizontal=True, key="select_mode")

    if st.button("▶️ Select Cases", type="primary") and condition:
        result_df = select_cases(df, condition, mode="filter" if "filter" in mode.lower() else "indicator")
        st.success(f"✅ Applied selection  {len(result_df)} cases remaining")
        return result_df
    return df


def render_weight_ui(df: pd.DataFrame) -> pd.DataFrame:
    """Render the Weight Cases UI."""
    st.subheader("⚖️ Weight Cases")
    st.caption("Weight cases by frequency variable (like SPSS Weight Cases)")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        st.warning("No numeric variables available for weighting.")
        return df

    weight_col = st.selectbox("Weight variable", options=numeric_cols, key="weight_col")
    st.info(f"Weighting will expand the dataset based on values in '{weight_col}'. "
            f"Larger weights = more replicated cases.")

    if st.button("▶️ Weight Cases", type="primary"):
        result_df = weight_cases(df, weight_col)
        st.success(f"✅ Weighted  {len(result_df)} cases after weighting (was {len(df)})")
        return result_df
    return df


def render_rename_ui(df: pd.DataFrame) -> pd.DataFrame:
    """Render the Rename Variables UI."""
    st.subheader("✏️ Rename Variables")
    st.caption("Rename one or more variables (like SPSS Rename)")

    cols = df.columns.tolist()
    rename_map = {}
    num_renames = st.number_input("Number of variables to rename", min_value=1, max_value=20, value=1, key="n_rename")

    for i in range(int(num_renames)):
        c1, c2, c3 = st.columns(3)
        with c1:
            old_name = st.selectbox(f"Current name {i+1}", options=cols, key=f"ren_old_{i}")
        with c2:
            new_name = st.text_input(f"New name {i+1}", value=old_name, key=f"ren_new_{i}")
        with c3:
            st.caption("→")
        if old_name and new_name and old_name != new_name:
            rename_map[old_name] = new_name

    if st.button("▶️ Rename Variables", type="primary") and rename_map:
        result_df = rename_variables(df, rename_map)
        st.success(f"✅ Renamed {len(rename_map)} variables")
        return result_df
    return df


# ─── Main Transformer UI ────────────────────────────────────────────

def render_transformer_panel(df: pd.DataFrame) -> pd.DataFrame:
    """Render the full data transformer panel with tabs."""
    st.markdown("## 🔧 Data Transformation Engine")
    st.markdown("*SPSS-compatible: Compute, Recode, Rank, Count, Shift, Binning, Sort, Select, Weight, Rename*")

    if df is None or df.empty:
        st.warning("No data available. Load data first.")
        return df

    tabs = st.tabs([
        "🧮 Compute", "🔄 Recode", "🏆 Rank", "🔢 Count",
        "⏳ Shift/Lag", "📊 Binning", "🔀 Sort", "🔍 Select",
        "⚖️ Weight", "✏️ Rename"
    ])

    result_df = df.copy()

    with tabs[0]:
        result_df = render_compute_ui(result_df)
    with tabs[1]:
        result_df = render_recode_ui(result_df)
    with tabs[2]:
        result_df = render_rank_ui(result_df)
    with tabs[3]:
        result_df = render_count_ui(result_df)
    with tabs[4]:
        result_df = render_shift_ui(result_df)
    with tabs[5]:
        result_df = render_binning_ui(result_df)
    with tabs[6]:
        result_df = render_sort_ui(result_df)
    with tabs[7]:
        result_df = render_select_ui(result_df)
    with tabs[8]:
        result_df = render_weight_ui(result_df)
    with tabs[9]:
        result_df = render_rename_ui(result_df)

    st.markdown("---")
    st.subheader("📋 Transformed Data Preview")
    st.dataframe(result_df.head(20), use_container_width=True, hide_index=True)
    st.caption(f"Dataset: {len(result_df)} rows × {len(result_df.columns)} columns")

    return result_df

