"""
Natural Language Data Query Engine — allows users to ask questions in plain English
and get automatic analysis, visualizations, and insights.
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
import re
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from modules.data_processor import infer_column_types, profile_dataset
from modules.statistical_engine import StatisticalEngine
from modules.viz_engine import auto_recommend_chart
from modules.chart_builder import build_chart


class NaturalLanguageQueryEngine:
    """Convert natural language queries into data analysis, visualizations, and insights."""

    def __init__(self):
        self.stats = StatisticalEngine()
        self.conversation_history = []

    def process_query(self, query: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Process a natural language query and return analysis results."""
        query_lower = query.lower().strip()
        col_types = infer_column_types(df)
        numeric_cols = [c for c, t in col_types.items() if t in ("numeric", "integer")]
        cat_cols = [c for c, t in col_types.items() if t in ("categorical", "string")]
        temporal_cols = [c for c, t in col_types.items() if t == "temporal"]

        # Route to appropriate handler
        if any(kw in query_lower for kw in ["mean", "average", "median", "describe", "summary", "descriptive"]):
            return self._handle_descriptive(query, df, numeric_cols)
        elif any(kw in query_lower for kw in ["compare", "difference", "vs", "versus", "t-test", "ttest"]):
            return self._handle_comparison(query, df, cat_cols, numeric_cols)
        elif any(kw in query_lower for kw in ["correlation", "relationship", "associated", "related"]):
            return self._handle_correlation(query, df, numeric_cols)
        elif any(kw in query_lower for kw in ["predict", "regression", "forecast"]):
            return self._handle_regression(query, df, numeric_cols, cat_cols)
        elif any(kw in query_lower for kw in ["chart", "plot", "graph", "visualize", "show me"]):
            return self._handle_visualization(query, df, col_types)
        elif any(kw in query_lower for kw in ["trend", "over time", "change", "increase", "decrease"]):
            return self._handle_trend(query, df, temporal_cols, numeric_cols)
        elif any(kw in query_lower for kw in ["outlier", "anomaly", "extreme"]):
            return self._handle_outliers(df, numeric_cols)
        elif any(kw in query_lower for kw in ["distribution", "histogram", "frequency"]):
            return self._handle_distribution(query, df, numeric_cols, cat_cols)
        elif any(kw in query_lower for kw in ["count", "how many", "percentage", "proportion"]):
            return self._handle_frequency(query, df, cat_cols)
        else:
            return self._handle_general(query, df, col_types)

    def _handle_descriptive(self, query: str, df: pd.DataFrame, numeric_cols: List[str]) -> Dict[str, Any]:
        """Handle descriptive statistics queries."""
        # Try to identify specific column
        target_col = self._extract_column(query, numeric_cols)

        if target_col:
            result = self.stats.descriptive_stats(df, [target_col])
            return {
                "type": "descriptive",
                "target": target_col,
                "result": result,
                "chart_type": "histogram",
                "chart_params": {"x": target_col},
                "narrative": f"**{target_col}**: Mean = {result.iloc[0]['Mean']:.2f}, SD = {result.iloc[0]['Std Dev']:.2f}, N = {result.iloc[0]['N']}",
                "confidence": 90,
            }

        if numeric_cols:
            result = self.stats.descriptive_stats(df, numeric_cols[:5])
            narrative_parts = [f"Dataset has {len(df):,} rows and {len(df.columns)} columns."]
            for _, row in result.iterrows():
                narrative_parts.append(f"- **{row['Variable']}**: M = {row['Mean']:.2f}, SD = {row['Std Dev']:.2f}")
            return {
                "type": "descriptive",
                "result": result,
                "narrative": "\n".join(narrative_parts),
                "confidence": 85,
            }

        return {"type": "error", "narrative": "No numeric columns found for descriptive analysis.", "confidence": 0}

    def _handle_comparison(self, query: str, df: pd.DataFrame, cat_cols: List[str], numeric_cols: List[str]) -> Dict[str, Any]:
        """Handle group comparison queries."""
        if not cat_cols or not numeric_cols:
            return {"type": "error", "narrative": "Need both categorical and numeric variables for comparison.", "confidence": 0}

        target_num = self._extract_column(query, numeric_cols) or numeric_cols[0]
        target_cat = self._extract_column(query, cat_cols) or cat_cols[0]

        groups = df[target_cat].dropna().unique()
        if len(groups) == 2:
            result = self.stats.independent_ttest(df, target_cat, target_num)
            if "error" not in result:
                return {
                    "type": "comparison",
                    "test": "Independent T-Test",
                    "group_var": target_cat,
                    "value_var": target_num,
                    "result": result,
                    "chart_type": "box",
                    "chart_params": {"x": target_cat, "y": target_num},
                    "narrative": f"Comparing **{target_num}** by **{target_cat}**: t({result.get('n_1', 0) + result.get('n_2', 0) - 2}) = {result.get('t_statistic', 0):.2f}, p = {result.get('p_value', 1):.3f}, d = {result.get('cohens_d', 0):.2f}",
                    "confidence": 95,
                }
        elif len(groups) >= 3:
            result = self.stats.anova_one_way(df, target_cat, target_num)
            if "error" not in result:
                return {
                    "type": "comparison",
                    "test": "One-Way ANOVA",
                    "group_var": target_cat,
                    "value_var": target_num,
                    "result": result,
                    "chart_type": "violin",
                    "chart_params": {"x": target_cat, "y": target_num},
                    "narrative": f"Comparing **{target_num}** across {len(groups)} groups of **{target_cat}**: F({result.get('num_groups', 1) - 1}, ...) = {result.get('f_statistic', 0):.2f}, p = {result.get('p_value', 1):.3f}",
                    "confidence": 90,
                }

        return {"type": "error", "narrative": f"Could not perform comparison. Try selecting different variables.", "confidence": 0}

    def _handle_correlation(self, query: str, df: pd.DataFrame, numeric_cols: List[str]) -> Dict[str, Any]:
        """Handle correlation queries."""
        if len(numeric_cols) < 2:
            return {"type": "error", "narrative": "Need at least 2 numeric columns for correlation.", "confidence": 0}

        # Try to extract two columns
        col1 = self._extract_column(query, numeric_cols, exclude=None)
        remaining = [c for c in numeric_cols if c != col1] if col1 else numeric_cols
        col2 = self._extract_column(query, remaining)

        if col1 and col2 and col1 != col2:
                    "visualization": {"type": "heatmap"},
                }
            else:
                response = {"error": "Need at least 2 numeric columns for correlation", "type": "error"}

        # 6. Compare groups
        elif re.search(r'\b(compare|difference|group|by)\b', query_lower):
            found_cat = None
            found_num = None
            for _, col_name in cat_cols_lower.items():
                if col_name.lower() in query_lower:
                    found_cat = col_name
                    break
            for _, col_name in num_cols_lower.items():
                if col_name.lower() in query_lower:
                    found_num = col_name
                    break

            if found_cat and found_num:
                groups = df.groupby(found_cat)[found_num].agg(["mean", "std", "count", "min", "max"]).round(2)
                self.last_result = groups
                response = {
                    "type": "comparison",
                    "data": groups,
                    "message": f"Comparison of {found_num} across {found_cat}:",
                    "visualization": {"type": "bar", "x": found_cat, "y": found_num},
                }
            elif found_cat:
                freq = df[found_cat].value_counts().reset_index()
                freq.columns = [found_cat, "Count"]
                self.last_result = freq
                response = {
                    "type": "comparison",
                    "data": freq,
                    "message": f"Distribution of {found_cat}:",
                    "visualization": {"type": "pie", "names": found_cat, "values": "Count"},
                }
            else:
                if cat_cols and numeric_cols:
                    groups = df.groupby(cat_cols[0])[numeric_cols[0]].agg(["mean", "std", "count"]).round(2)
                    self.last_result = groups
                    response = {
                        "type": "comparison",
                        "data": groups,
                        "message": f"Comparison of {numeric_cols[0]} across {cat_cols[0]}:",
                        "visualization": {"type": "bar", "x": cat_cols[0], "y": numeric_cols[0]},
                    }
                else:
                    response = {"error": "Cannot determine comparison variables", "type": "error"}

        # 7. Filter rows
        elif re.search(r'\b(where|filter|only|contain|greater|less|equal|>|<|=)\b', query_lower):
            response = self._process_filter_query(query_lower, df, col_names, num_cols_lower, cat_cols_lower)

        # 8. Sort / order
        elif re.search(r'\b(sort|order|arrange|rank)\b', query_lower):
            for _, col_name in (num_cols_lower | cat_cols_lower).items():
                if col_name.lower() in query_lower:
                    ascending = any(w in query_lower for w in ["ascending", "low", "small", "least"])
                    result_df = df.sort_values(col_name, ascending=ascending).head(20)
                    self.last_result = result_df
                    response = {
                        "type": "data",
                        "data": result_df,
                        "message": f"Sorted by {col_name} ({'ascending' if ascending else 'descending'}):",
                        "visualization": None,
                    }
                    break
            else:
                response = {"error": "Specify a column to sort by", "type": "error"}

        # 9. Missing values
        elif re.search(r'\b(missing|na|null|empty|incomplete)\b', query_lower):
            missing_info = []
            for col in df.columns:
                n_missing = df[col].isna().sum()
                if n_missing > 0:
                    missing_info.append({"Column": col, "Missing": n_missing, "Percentage": round(n_missing / len(df) * 100, 2)})
            result_df = pd.DataFrame(missing_info).sort_values("Missing", ascending=False)
            self.last_result = result_df
            response = {
                "type": "missing",
                "data": result_df,
                "message": "Missing value analysis:",
                "visualization": {"type": "bar", "x": "Column", "y": "Missing"},
            }

        # 10. Trend over time
        elif re.search(r'\b(trend|over time|change|increase|decrease|time series)\b', query_lower):
            date_cols = []
            for col in df.columns:
                try:
                    if pd.api.types.is_datetime64_any_dtype(df[col]):
                        date_cols.append(col)
                except Exception:
                    pass
            if date_cols and numeric_cols:
                date_col = date_cols[0]
                num_col = numeric_cols[0]
                trend_df = df[[date_col, num_col]].dropna().sort_values(date_col)
                self.last_result = trend_df
                response = {
                    "type": "trend",
                    "data": trend_df,
                    "message": f"Trend of {num_col} over time:",
                    "visualization": {"type": "line", "x": date_col, "y": num_col},
                }
            else:
                response = {"error": "Need a date column and numeric column for trend analysis", "type": "error"}

        # 11. Outliers
        elif re.search(r'\b(outlier|anomaly|abnormal|extreme)\b', query_lower):
            outlier_info = {}
            for col in numeric_cols:
                series = df[col].dropna()
                if len(series) > 3:
                    mean = series.mean()
                    std = series.std()
                    outliers = series[(series - mean).abs() > 3 * std]
                    if len(outliers) > 0:
                        outlier_info[col] = {"outliers": len(outliers), "percentage": round(len(outliers) / len(series) * 100, 2)}
            if outlier_info:
                result_df = pd.DataFrame.from_dict(outlier_info, orient="index").reset_index()
                result_df.columns = ["Column", "Outliers", "Percentage"]
                self.last_result = result_df
                response = {
                    "type": "outliers",
                    "data": result_df,
                    "message": "Outlier detection results:",
                    "visualization": {"type": "bar", "x": "Column", "y": "Outliers"},
                }
            else:
                response = {"type": "info", "data": pd.DataFrame(), "message": "No significant outliers detected (Z-score > 3)"}

        # 12. Help
        elif re.search(r'\b(help|what can|command|guide|tutorial)\b', query_lower):
            response = {
                "type": "help",
                "data": None,
                "message": "",
                "commands": [
                    "show data — Display the first rows of data",
                    "describe data — Show summary statistics",
                    "count [column] — Show frequency distribution",
                    "average [column] — Calculate mean of a column",
                    "compare [group] by [variable] — Group comparison",
                    "correlation between [col1] and [col2] — Correlation analysis",
                    "trend of [variable] over time — Time series trend",
                    "missing values — Show missing data info",
                    "outliers — Detect extreme values",
                    "sort [column] — Sort data by column",
                    "where [column] > [value] — Filter data",
                ],
            }

        # 13. Default: help
        else:
            response = {
                "type": "help",
                "data": None,
                "message": f"I didn't understand '{query}'. Try these commands:",
                "commands": [
                    "show data", "describe data", "count [column]",
                    "average [column]", "compare [group] by [variable]",
                    "correlation between [col1] and [col2]",
                    "trend over time", "missing values", "outliers", "help",
                ],
            }

        # Store response
        result = {
            "query": query,
            "response": response,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "type": response.get("type", "info"),
        }
        self.conversation_history.append({"role": "assistant", "response": result})
        return result

    def _process_filter_query(self, query: str, df: pd.DataFrame, col_names: Dict, num_cols: Dict, cat_cols: Dict) -> Dict:
        """Process filter/where queries."""
        # Pattern: column > value, column < value, column = value
        patterns = [
            (r'(\w+)\s*(>|>=|greater than|more than)\s*(\d+\.?\d*)', 'gt'),
            (r'(\w+)\s*(<|<=|less than|fewer than)\s*(\d+\.?\d*)', 'lt'),
            (r'(\w+)\s*(=|==|equals|is|equal to)\s*["\']?(.+?)["\']?\s*$', 'eq'),
            (r'(\w+)\s*(!=|<>|not equal|is not|not)\s*["\']?(.+?)["\']?\s*$', 'ne'),
        ]

        for pattern, op in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                col_match = match.group(1).strip().lower()
                if col_match in col_names:
                    actual_col = col_names[col_match]
                    if op in ('gt', 'lt'):
                        val = float(match.group(3))
                        if op == 'gt':
                            result_df = df[df[actual_col] > val]
                            desc = f"where {actual_col} > {val}"
                        else:
                            result_df = df[df[actual_col] < val]
                            desc = f"where {actual_col} < {val}"
                    elif op == 'eq':
                        val = match.group(3).strip().strip("'\"")
                        result_df = df[df[actual_col].astype(str).str.lower() == val.lower()]
                        desc = f"where {actual_col} = {val}"
                    else:  # ne
                        val = match.group(3).strip().strip("'\"")
                        result_df = df[df[actual_col].astype(str).str.lower() != val.lower()]
                        desc = f"where {actual_col} != {val}"

                    self.last_result = result_df
                    return {
                        "type": "filtered",
                        "data": result_df,
                        "message": f"Filtered {desc}: {len(result_df)} rows ({len(result_df)/len(df)*100:.1f}% of data)",
                        "visualization": None,
                    }

        return {"error": "Could not parse filter condition. Try: [column] > [value]", "type": "error"}


# ─── UI ─────────────────────────────────────────────────────────────

def render_nl_query_ui(df: pd.DataFrame):
    """Render the natural language query UI."""
    import streamlit as st

    st.markdown("## 💬 Natural Language Data Query")
    st.markdown("*Ask questions about your data in plain English*")

    if df is None or df.empty:
        st.warning("No data available. Load data first.")
        return

    # Initialize engine
    if "nl_engine" not in st.session_state:
        st.session_state["nl_engine"] = NLQueryEngine()
    engine = st.session_state["nl_engine"]

    # Example queries
    with st.expander("💡 Example queries"):
        examples = [
            "Show data",
            "Describe data",
            "Average of [numeric_column]",
            "Count of [categorical_column]",
            "Compare [group] by [variable]",
            "Correlation between [col1] and [col2]",
            "Missing values",
            "Outliers",
            "Trend over time",
            "Sort [column]",
            "Where [column] > 50",
            "Help",
        ]
        for ex in examples:
            st.markdown(f"- `{ex}`")

    # Query input
    col1, col2 = st.columns([4, 1])
    with col1:
        query = st.text_input("💬 Ask a question about your data:", placeholder="e.g., Describe the data", key="nl_query_input")
    with col2:
        st.caption("")
        submit = st.button("🔍 Ask", type="primary", use_container_width
