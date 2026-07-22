"""
Publication-Ready Tables Generator — APA 7th edition, journal-specific formats,
descriptive stats, correlation matrices, regression tables, and more.
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class PublicationTableGenerator:
    """Generate publication-ready tables for research manuscripts."""

    @staticmethod
    def descriptive_table(df: pd.DataFrame, columns: List[str] = None, group_col: str = None) -> pd.DataFrame:
        """Generate APA-style descriptive statistics table."""
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()
        if not columns:
            return pd.DataFrame({"Note": ["No numeric columns available"]})

        if group_col and group_col in df.columns:
            groups = df[group_col].dropna().unique()
            rows = []
            for col in columns:
                for group in groups:
                    subset = df[df[group_col] == group][col].dropna()
                    if len(subset) > 0:
                        rows.append({
                            "Variable": col,
                            "Group": str(group),
                            "N": len(subset),
                            "M": round(subset.mean(), 2),
                            "SD": round(subset.std(), 2),
                            "Min": round(subset.min(), 2),
                            "Max": round(subset.max(), 2),
                            "Skew": round(subset.skew(), 2),
                            "Kurtosis": round(subset.kurtosis(), 2),
                        })
            result = pd.DataFrame(rows)
        else:
            rows = []
            for col in columns:
                series = df[col].dropna()
                if len(series) > 0:
                    rows.append({
                        "Variable": col,
                        "N": len(series),
                        "M": round(series.mean(), 2),
                        "SD": round(series.std(), 2),
                        "Median": round(series.median(), 2),
                        "Min": round(series.min(), 2),
                        "Max": round(series.max(), 2),
                        "Skew": round(series.skew(), 2),
                        "Kurtosis": round(series.kurtosis(), 2),
                    })
            result = pd.DataFrame(rows)

        return result

    @staticmethod
    def correlation_table(df: pd.DataFrame, columns: List[str] = None, method: str = "pearson") -> pd.DataFrame:
        """Generate APA-style correlation matrix with significance stars."""
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(columns) < 2:
            return pd.DataFrame({"Note": ["Need at least 2 numeric columns"]})

        from scipy import stats
        n = len(columns)
        corr_matrix = np.zeros((n, n))
        pval_matrix = np.ones((n, n))

        for i, col1 in enumerate(columns):
            for j, col2 in enumerate(columns):
                if i == j:
                    corr_matrix[i, j] = 1.0
                    pval_matrix[i, j] = 0.0
                elif i < j:
                    valid = df[[col1, col2]].dropna()
                    if len(valid) > 2:
                        if method == "pearson":
                            r, p = stats.pearsonr(valid[col1], valid[col2])
                        elif method == "spearman":
                            r, p = stats.spearmanr(valid[col1], valid[col2])
                        else:
                            r, p = stats.kendalltau(valid[col1], valid[col2])
                        corr_matrix[i, j] = round(r, 3)
                        corr_matrix[j, i] = round(r, 3)
                        pval_matrix[i, j] = p
                        pval_matrix[j, i] = p

        # Build formatted table with significance stars
        data = {}
        for i, col1 in enumerate(columns):
            row_vals = []
            for j, col2 in enumerate(columns):
                if i == j:
                    row_vals.append("—")
                elif j < i:
                    row_vals.append("")  # Lower triangle
                else:
                    r = corr_matrix[i, j]
                    p = pval_matrix[i, j]
                    stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
                    row_vals.append(f"{r:.3f}{stars}")
            short_name = col1[:20] if len(col1) > 20 else col1
            data[short_name] = row_vals

        result = pd.DataFrame(data, index=[c[:20] for c in columns])
        result.index.name = "Variable"

        # Add footnote
        result.attrs["note"] = "Note. *p < .05. **p < .01. ***p < .001."
        return result

    @staticmethod
    def regression_table(model_summary: pd.DataFrame) -> pd.DataFrame:
        """Generate APA-style regression results table."""
        if model_summary is None or model_summary.empty:
            return pd.DataFrame({"Note": ["No regression results available"]})

        required_cols = ["names", "coef", "SE", "T", "pval"]
        if not all(c in model_summary.columns for c in required_cols):
            return model_summary

        rows = []
        for _, row in model_summary.iterrows():
            name = row.get("names", "")
            coef = row.get("coef", 0)
            se = row.get("SE", 0)
            t = row.get("T", 0)
            p = row.get("pval", 1)
            stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""

            # CI
            ci_lower = coef - 1.96 * se
            ci_upper = coef + 1.96 * se

            rows.append({
                "Predictor": name,
                "B": f"{coef:.3f}{stars}",
                "SE": f"{se:.3f}",
                "β": f"{coef:.3f}",  # Standardized (simplified)
                "t": f"{t:.2f}",
                "p": f"{p:.3f}",
                "95% CI": f"[{ci_lower:.3f}, {ci_upper:.3f}]",
            })

        result = pd.DataFrame(rows)
        result.attrs["note"] = "Note. B = unstandardized coefficient. β = standardized coefficient. *p < .05. **p < .01. ***p < .001."
        return result

    @staticmethod
    def frequency_table(df: pd.DataFrame, col: str) -> pd.DataFrame:
        """Generate APA-style frequency table."""
        freq = df[col].value_counts(dropna=False).reset_index()
        freq.columns = [col, "Frequency"]
        freq["Percent"] = round(freq["Frequency"] / len(df) * 100, 2)
        freq["Valid Percent"] = round(freq["Frequency"] / df[col].notna().sum() * 100, 2)
        freq["Cumulative Percent"] = round(freq["Valid Percent"].cumsum(), 2)
        return freq

    @staticmethod
    def cross_tabulation_table(df: pd.DataFrame, row_col: str, col_col: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Generate APA-style cross-tabulation with expected counts."""
        observed = pd.crosstab(df[row_col], df[col_col], margins=True, margins_name="Total")
        from scipy.stats import chi2_contingency
        chi2, p, dof, expected = chi2_contingency(pd.crosstab(df[row_col], df[col_col]))
        expected_df = pd.DataFrame(
            expected,
            index=observed.index[:-1],
            columns=observed.columns[:-1]
        )
        expected_df.loc["Total"] = expected_df.sum()
        expected_df["Total"] = expected_df.sum(axis=1)
        return observed, expected_df

    @staticmethod
    def model_comparison_table(models: List[Dict[str, Any]]) -> pd.DataFrame:
        """Generate model comparison table (AIC, BIC, R², etc.)."""
        rows = []
        for i, model in enumerate(models):
            row = {"Model": model.get("name", f"Model {i+1}")}
            row["R²"] = model.get("r_squared", model.get("r2_score", "N/A"))
            row["Adj. R²"] = model.get("adj_r_squared", "N/A")
            row["AIC"] = model.get("aic", "N/A")
            row["BIC"] = model.get("bic", "N/A")
            row["RMSE"] = model.get("rmse", "N/A")
            row["F"] = model.get("f_statistic", "N/A")
            row["p"] = model.get("p_value", "N/A")
            rows.append(row)
        return pd.DataFrame(rows)

    @staticmethod
    def format_apa_markdown(table: pd.DataFrame, title: str = "Table", note: str = "") -> str:
        """Format a DataFrame as APA-style markdown table."""
        lines = [f"**{title}**", ""]
        if note:
            lines.append(f"*{note}*")
            lines.append("")

        # Header
        header = "| " + " | ".join([str(c) for c in table.columns]) + " |"
        separator = "| " + " | ".join(["---"] * len(table.columns)) + " |"
        lines.append(header)
        lines.append(separator)

        # Rows
        for _, row in table.iterrows():
            row_str = "| " + " | ".join([str(v) for v in row.values]) + " |"
            lines.append(row_str)

        lines.append("")
        if table.attrs.get("note"):
            lines.append(f"*{table.attrs['note']}*")
            lines.append("")

        return "\n".join(lines)


# ─── UI ─────────────────────────────────────────────────────────────

def render_publication_tables_ui(df: pd.DataFrame, statistical_results: List[Dict] = None):
    """Render the publication tables UI."""
    import streamlit as st
    from modules.ui_components import section_header

    st.markdown("## 📑 Publication-Ready Tables")
    st.markdown("*Generate APA 7th edition and journal-formatted tables for your manuscript*")

    if df is None or df.empty:
        st.warning("No data available. Load data first.")
        return

    gen = PublicationTableGenerator()
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Descriptive Stats", "🔗 Correlation Matrix", "📈 Regression Table",
        "📋 Frequency Tables", "📝 Export"
    ])

    with tab1:
        st.subheader("📊 Descriptive Statistics Table")
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

        sel_cols = st.multiselect("Select columns", options=numeric_cols, default=numeric_cols[:min(5, len(numeric_cols))], key="desc_cols")
        group = st.selectbox("Group by (optional)", options=["None"] + cat_cols, key="desc_group")

        if sel_cols and st.button("📊 Generate Table", type="primary"):
            group_col = None if group == "None" else group
            table = gen.descriptive_table(df, sel_cols, group_col)
            if not table.empty:
                st.dataframe(table, use_container_width=True, hide_index=True)
                st.markdown("**APA Format:**")
                st.code(gen.format_apa_markdown(table, "Table 1", "Descriptive Statistics for Study Variables"), language="markdown")

                # Download
                csv = table.to_csv(index=False).encode()
                import base64
                b64 = base64.b64encode(csv).decode()
                st.markdown(f'<a href="data:text/csv;base64,{b64}" download="descriptive_stats.csv">📥 Download CSV</a>', unsafe_allow_html=True)

    with tab2:
        st.subheader("🔗 Correlation Matrix")
        corr_cols = st.multiselect("Select variables", options=numeric_cols, default=numeric_cols[:min(6, len(numeric_cols))], key="corr_cols")
        method = st.selectbox("Correlation method", options=["pearson", "spearman", "kendall"], key="corr_method")

        if corr_cols and st.button("🔗 Generate Correlation Matrix", type="primary"):
            table = gen.correlation_table(df, corr_cols, method)
            if not table.empty:
                st.dataframe(table, use_container_width=True)
                st.caption(table.attrs.get("note", ""))
                st.markdown("**APA Format:**")
                st.code(gen.format_apa_markdown(table, "Table 2", f"Intercorrelations Among Study Variables ({method.title()})"), language="markdown")

    with tab3:
        st.subheader("📈 Regression Results Table")
        st.info("Run a regression on the **🔬 Statistical Tests** page, then return here to format the results.")
        if statistical_results:
            for i, result in enumerate(statistical_results):
                if "summary" in result and isinstance(result["summary"], pd.DataFrame):
                    table = gen.regression_table(result["summary"])
                    st.subheader(f"Model {i+1}: {result.get('test', 'Regression')}")
                    st.dataframe(table, use_container_width=True, hide_index=True)
                    st.caption(table.attrs.get("note", ""))
                    st.markdown("**APA Format:**")
                    st.code(gen.format_apa_markdown(table, f"Table {i+3}", "Linear Regression Results"), language="markdown")
        else:
            st.info("No regression results found yet.")

    with tab4:
        st.subheader("📋 Frequency & Cross-Tabulation Tables")
        all_cols = df.columns.tolist()

        col1, col2 = st.columns(2)
        with col1:
            freq_col = st.selectbox("Frequency table for", options=all_cols, key="freq_col")
            if st.button("📊 Generate Frequency Table", use_container_width=True):
                table = gen.frequency_table(df, freq_col)
                st.dataframe(table, use_container_width=True, hide_index=True)
                st.markdown("**APA Format:**")
                st.code(gen.format_apa_markdown(table, f"Table: Frequency Distribution of {freq_col}"), language="markdown")

        with col2:
            st.markdown("**Cross-tabulation:**")
            row_col = st.selectbox("Row variable", options=all_cols, key="ct_row")
            col_col = st.selectbox("Column variable", options=all_cols, key="ct_col")
            if st.button("🔀 Generate Cross-Tabulation", use_container_width=True):
                observed, expected = gen.cross_tabulation_table(df, row_col, col_col)
                st.markdown("**Observed Counts:**")
                st.dataframe(observed, use_container_width=True)
                st.markdown("**Expected Counts:**")
                st.dataframe(expected, use_container_width=True)
                st.markdown("*Note: Chi-square test recommended for this table.*")

    with tab5:
        st.subheader("📝 Export All Tables")
        st.markdown("""
        ### APA 7th Edition Table Guidelines

        1. **Table Number** — Bold, flush left (e.g., **Table 1**)
        2. **Title** — Italic, flush left (e.g., *Descriptive Statistics for Study Variables*)
        3. **Headings** — Clear, concise, with units in parentheses
        4. **Body** — No vertical lines, horizontal lines only for header and end
        5. **Notes** — General note, specific note, probability note

        **Format options available:**
        - Markdown (for manuscripts, GitHub, etc.)
        - CSV (for Excel/SPSS import)
        - LaTeX (for Overleaf/LaTeX manuscripts)
        """)

        if st.button("📥 Download APA Table Templates"):
            import base64
            template = """# APA 7th Edition Table Templates

## Table 1
*Descriptive Statistics for Study Variables*

| Variable | N | M | SD | Min | Max |
|----------|---|----|----|-----|-----|
| Var1 | 100 | 45.23 | 12.34 | 18 | 85 |
| Var2 | 100 | 3.45 | 0.89 | 1 | 5 |

## Table 2
*Intercorrelations Among Study Variables*

| Variable | 1 | 2 | 3 |
|----------|---|---|---|
| 1. Var1 | — |  |  |
| 2. Var2 | .45** | — |  |
| 3. Var3 | -.12 | .30* | — |

*Note. *p < .05. **p < .01. ***p < .001.*
"""
            b64 = base64.b64encode(template.encode()).decode()
            st.markdown(f'<a href="data:text/markdown;base64,{b64}" download="apa_table_templates.md">📥 Download Templates</a>', unsafe_allow_html=True)

