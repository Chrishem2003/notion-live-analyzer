
"""
Natural Language Data Query Engine + allows users to ask questions in plain English
and get automatic analysis, visualizations, and insights.
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
import re
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from modules.data_processor import infer_column_types
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
                "narrative": f"**{target_col}**: Mean = {result.iloc[0]['Mean']:.2 + f}, SD = {result.iloc[0]['Std Dev']:.2 + f}, N = {result.iloc[0]['N']}",
                "confidence": 90,
            }

        if numeric_cols:
            result = self.stats.descriptive_stats(df, numeric_cols[:5])
            narrative_parts = [f"Dataset has {len(df):,} rows and {len(df.columns)} columns."]
            for _, row in result.iterrows():
                narrative_parts.append(f"- **{row['Variable']}**: M = {row['Mean']:.2 + f}, SD = {row['Std Dev']:.2 + f}")
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
                    "narrative": f"Comparing **{target_num}** by **{target_cat}**: t({result.get('n_1', 0) + result.get('n_2', 0) - 2}) = {result.get('t_statistic', 0):.2 + f}, p = {result.get('p_value', 1):.3 + f}, d = {result.get('cohens_d', 0):.2 + f}",
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
                    "narrative": f"Comparing **{target_num}** across {len(groups)} groups of **{target_cat}**: F({result.get('num_groups', 1) - 1}, ...) = {result.get('f_statistic', 0):.2 + f}, p = {result.get('p_value', 1):.3 + f}",
                    "confidence": 90,
                }

        return {"type": "error", "narrative": f"Could not perform comparison. Try selecting different variables.", "confidence": 0}

    def _handle_correlation(self, query: str, df: pd.DataFrame, numeric_cols: List[str]) -> Dict[str, Any]:
        """Handle correlation queries."""
        if len(numeric_cols) < 2:
            return {"type": "error", "narrative": "Need at least 2 numeric columns for correlation.", "confidence": 0}

        # Try to extract two columns
        col1 = self._extract_column(query, numeric_cols)
        remaining = [c for c in numeric_cols if c != col1] if col1 else numeric_cols
        col2 = self._extract_column(query, remaining)

        if col1 and col2 and col1 != col2:
            result = self.stats.correlation(df, col1, col2)
            return {
                "type": "correlation",
                "var1": col1,
                "var2": col2,
                "result": result,
                "chart_type": "scatter",
                "chart_params": {"x": col1, "y": col2},
                "narrative": f"Correlation between {col1} and {col2}.",
                "confidence": 90,
            }
        else:
            return {
                "type": "correlation",
                "narrative": "Correlation matrix for all numeric variables.",
                "result": df[numeric_cols].corr(),
                "chart_type": "heatmap",
                "confidence": 85,
            }

    def _handle_regression(self, query: str, df: pd.DataFrame, numeric_cols: List[str], cat_cols: List[str]) -> Dict[str, Any]:
        """Handle regression/prediction queries."""
        target_col = self._extract_column(query, numeric_cols)
        if not target_col and numeric_cols:
            target_col = numeric_cols[0]

        predictors = [c for c in numeric_cols if c != target_col]
        if not predictors:
            return {"type": "error", "narrative": "Need at least one predictor variable for regression.", "confidence": 0}

        try:
            from sklearn.linear_model import LinearRegression
            X = df[predictors].dropna()
            y = df[target_col].dropna()
            # Align indices
            common_idx = X.index.intersection(y.index)
            X = X.loc[common_idx]
            y = y.loc[common_idx]

            if len(X) < 10:
                return {"type": "error", "narrative": f"Only {len(X)} valid observations. Need at least 10 for regression.", "confidence": 0}

            model = LinearRegression()
            model.fit(X, y)
            r_squared = model.score(X, y)

            return {
                "type": "regression",
                "target": target_col,
                "predictors": predictors,
                "r_squared": r_squared,
                "coefficients": dict(zip(predictors, model.coef_)),
                "intercept": model.intercept_,
                "narrative": f"Regression model for **{target_col}**: RÃ‚Â² = {r_squared:.3 + f}, {len(predictors)} predictor(s).",
                "confidence": 80,
            }
        except ImportError:
            return {"type": "info", "narrative": "Regression requires scikit-learn. Install with: pip install scikit-learn", "confidence": 0}
        except Exception as e:
            return {"type": "error", "narrative": f"Regression failed: {str(e)}", "confidence": 0}

    def _handle_visualization(self, query: str, df: pd.DataFrame, col_types: Dict[str, str]) -> Dict[str, Any]:
        """Handle visualization/chart queries."""
        numeric_cols = [c for c, t in col_types.items() if t in ("numeric", "integer")]
        cat_cols = [c for c, t in col_types.items() if t in ("categorical", "string")]

        chart_type = "scatter"
        x_col = None
        y_col = None

        if "bar" in query.lower():
            chart_type = "bar"
            if cat_cols:
                x_col = cat_cols[0]
            if numeric_cols:
                y_col = numeric_cols[0]
        elif "histogram" in query.lower() or "distribution" in query.lower():
            chart_type = "histogram"
            if numeric_cols:
                x_col = numeric_cols[0]
        elif "box" in query.lower() or "boxplot" in query.lower():
            chart_type = "box"
            if cat_cols:
                x_col = cat_cols[0]
            if numeric_cols:
                y_col = numeric_cols[0]
        elif "line" in query.lower() or "trend" in query.lower():
            chart_type = "line"
            if numeric_cols:
                x_col = numeric_cols[0]
            if len(numeric_cols) > 1:
                y_col = numeric_cols[1]
        else:
            # Default: scatter
            chart_type = "scatter"
            if len(numeric_cols) >= 2:
                x_col = numeric_cols[0]
                y_col = numeric_cols[1]

        chart_params = {}
        if x_col:
            chart_params["x"] = x_col
        if y_col:
            chart_params["y"] = y_col

        return {
            "type": "visualization",
            "chart_type": chart_type,
            "chart_params": chart_params,
            "narrative": f"Generated {chart_type} chart.",
            "confidence": 85,
        }

    def _handle_trend(self, query: str, df: pd.DataFrame, temporal_cols: List[str], numeric_cols: List[str]) -> Dict[str, Any]:
        """Handle trend/over-time queries."""
        time_col = self._extract_column(query, temporal_cols)
        if not time_col and temporal_cols:
            time_col = temporal_cols[0]

        value_col = self._extract_column(query, numeric_cols)
        if not value_col and numeric_cols:
            value_col = numeric_cols[0]

        if not time_col or not value_col:
            return {"type": "info", "narrative": "Trend analysis requires both a time column and a value column.", "confidence": 0}

        try:
            trend_data = df[[time_col, value_col]].dropna().sort_values(time_col)
            return {
                "type": "trend",
                "time_col": time_col,
                "value_col": value_col,
                "chart_type": "line",
                "chart_params": {"x": time_col, "y": value_col},
                "narrative": f"Trend of **{value_col}** over **{time_col}** ({len(trend_data)} data points).",
                "confidence": 85,
            }
        except Exception:
            return {"type": "error", "narrative": "Could not compute trend.", "confidence": 0}

    def _handle_outliers(self, df: pd.DataFrame, numeric_cols: List[str]) -> Dict[str, Any]:
        """Handle outlier detection queries."""
        if not numeric_cols:
            return {"type": "error", "narrative": "No numeric columns to check for outliers.", "confidence": 0}

        outlier_info = {}
        total_outliers = 0
        for col in numeric_cols[:10]:
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            outliers = df[(df[col] < lower) | (df[col] > upper)][col]
            n_outliers = len(outliers)
            if n_outliers > 0:
                outlier_info[col] = {
                    "count": n_outliers,
                    "percentage": round(n_outliers / len(df) * 100, 2),
                    "lower_bound": round(lower, 2),
                    "upper_bound": round(upper, 2),
                }
                total_outliers = n_outliers

        return {
            "type": "outliers",
            "outliers": outlier_info,
            "total_outliers": total_outliers,
            "narrative": f"Found {total_outliers} outliers across {len(outlier_info)} columns." if outlier_info else "No significant outliers detected.",
            "confidence": 90,
        }

    def _handle_distribution(self, query: str, df: pd.DataFrame, numeric_cols: List[str], cat_cols: List[str]) -> Dict[str, Any]:
        """Handle distribution queries."""
        target_col = self._extract_column(query, numeric_cols) or (numeric_cols[0] if numeric_cols else None)
        if not target_col:
            return {"type": "error", "narrative": "No numeric column found for distribution analysis.", "confidence": 0}

        try:
            desc = df[target_col].describe()
            return {
                "type": "distribution",
                "target": target_col,
                "chart_type": "histogram",
                "chart_params": {"x": target_col},
                "narrative": f"Distribution of **{target_col}**: Min={desc['min']:.2 + f}, Max={desc['max']:.2 + f}, Mean={desc['mean']:.2 + f}, Median={desc['50%']:.2 + f}, Std={desc['std']:.2 + f}",
                "confidence": 90,
            }
        except Exception:
            return {"type": "error", "narrative": f"Could not compute distribution for {target_col}.", "confidence": 0}

    def _handle_frequency(self, query: str, df: pd.DataFrame, cat_cols: List[str]) -> Dict[str, Any]:
        """Handle frequency/count queries."""
        target_col = self._extract_column(query, cat_cols) or (cat_cols[0] if cat_cols else None)
        if not target_col:
            return {"type": "error", "narrative": "No categorical column found for frequency analysis.", "confidence": 0}

        try:
            freq = df[target_col].value_counts().reset_index()
            freq.columns = [target_col, "Count"]
            freq["Percentage"] = (freq["Count"] / freq["Count"].sum() * 100).round(2)

            return {
                "type": "frequency",
                "target": target_col,
                "result": freq,
                "chart_type": "bar",
                "chart_params": {"x": target_col, "y": "Count"},
                "narrative": f"Frequency distribution for **{target_col}**: {len(freq)} categories.",
                "confidence": 90,
            }
        except Exception:
            return {"type": "error", "narrative": f"Could not compute frequency for {target_col}.", "confidence": 0}

    def _handle_general(self, query: str, df: pd.DataFrame, col_types: Dict[str, str]) -> Dict[str, Any]:
        """Handle general/informational queries about the dataset."""
        query_lower = query.lower()

        if "row" in query_lower or "shape" in query_lower or "size" in query_lower:
            return {
                "type": "info",
                "narrative": f"Dataset has **{len(df):,} rows** and **{len(df.columns):,} columns**.",
                "confidence": 100,
            }

        if "column" in query_lower or "variable" in query_lower or "field" in query_lower:
            col_list = "\n".join(f"- **{c}** ({t})" for c, t in list(col_types.items())[:20])
            return {
                "type": "info",
                "narrative": f"**Columns ({len(col_types)}):**\n{col_list}",
                "confidence": 100,
            }

        if "missing" in query_lower or "null" in query_lower or "na" in query_lower:
            missing = df.isnull().sum()
            missing = missing[missing > 0]
            if len(missing) > 0:
                missing_str = "\n".join(f"- **{c}**: {v} missing ({v/len(df)*100:.1 + f}%)" for c, v in missing.items())
                return {
                    "type": "info",
                    "narrative": f"**Missing Values:**\n{missing_str}",
                    "confidence": 95,
                }
            return {"type": "info", "narrative": "No missing values found in the dataset.", "confidence": 100}

        if "sort" in query_lower or "order" in query_lower:
            col = self._extract_column(query, list(col_types.keys()))
            if col:
                ascending = "descending" not in query_lower and "desc" not in query_lower
                sorted_df = df.sort_values(col, ascending=ascending)
                return {
                    "type": "data",
                    "result": sorted_df.head(20),
                    "narrative": f"Data sorted by **{col}** ({'ascending' if ascending else 'descending'}).",
                    "confidence": 95,
                }
            return {"type": "info", "narrative": "Specify a column to sort by.", "confidence": 0}

        if "where" in query_lower or "filter" in query_lower:
            return {
                "type": "info",
                "narrative": "Filtering not yet supported in NL queries. Use the Data Transformer page for filtering.",
                "confidence": 0,
            }

        # Default: show data overview
        return {
            "type": "data",
            "result": df.head(10),
            "narrative": f"Showing first 10 rows of {len(df):,} rows.",
            "confidence": 100,
        }

    def _extract_column(self, query: str, columns: List[str]) -> Optional[str]:
        """Extract a column name from a natural language query."""
        query_lower = query.lower()
        for col in columns:
            if col.lower() in query_lower:
                return col
        return None


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ UI Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

def render_nl_query_ui(df: pd.DataFrame):
    """Render the natural language query UI."""
    import streamlit as st

    st.markdown("## Ã°Å¸â€™Â¬ Natural Language Data Query")
    st.markdown("*Ask questions about your data in plain English*")

    if df is None or df.empty:
        st.warning("No data available. Load data first.")
        return

    # Initialize engine
    if "nl_engine" not in st.session_state:
        st.session_state["nl_engine"] = NaturalLanguageQueryEngine()
    engine = st.session_state["nl_engine"]

    # Example queries
    with st.expander("Ã°Å¸â€™Â¡ Example queries"):
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
        query = st.text_input("Ã°Å¸â€™Â¬ Ask a question about your data:", placeholder="e.g., Describe the data", key="nl_query_input")
    with col2:
        st.caption("")
        submit = st.button("Ã°Å¸â€Â Ask", type="primary", use_container_width=True)

    # Process query
    if submit and query.strip():
        with st.spinner("Ã°Å¸â€Â Analyzing..."):
            result = engine.process_query(query, df)
            st.session_state["last_nl_result"] = result
        st.rerun()

    # Display results
    if "last_nl_result" in st.session_state:
        result = st.session_state["last_nl_result"]
        result_type = result.get("type", "info")
        narrative = result.get("narrative", result.get("message", ""))

        if result_type == "error":
            st.error(narrative)
        elif result_type == "info":
            st.info(narrative)
        elif result_type == "help":
            commands = result.get("commands", [])
            for cmd in commands:
                st.markdown(f"- `{cmd}`")
        else:
            if narrative:
                st.markdown(narrative)

            data = result.get("result") or result.get("data")
            if data is not None:
                if isinstance(data, pd.DataFrame):
                    st.dataframe(data, use_container_width=True, hide_index=True)
                elif isinstance(data, dict):
                    st.json(data)

            # Show chart if available
            chart_type = result.get("chart_type")
            chart_params = result.get("chart_params", {})
            if chart_type and chart_params:
                try:
                    fig = auto_recommend_chart(df, chart_type, chart_params)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                except Exception:
                    pass

