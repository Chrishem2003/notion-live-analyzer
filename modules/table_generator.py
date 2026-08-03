import security_guard
import security_guard

"""
Publication-Ready Table Generator  APA-style tables, journal-specific formats,
descriptive statistics tables, correlation matrices, regression tables.
"""
from __future__ import annotations

from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')


class TableGenerator:
    """Generate publication-ready tables in APA and journal-specific formats."""

    @staticmethod
    def descriptive_stats_table(
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
        group_col: Optional[str] = None,
        include: List[str] = None,
    ) -> pd.DataFrame:
        """
        Generate descriptive statistics table in APA format.
        """
        if include is None:
            include = ["N", "Mean", "SD", "Min", "Max", "Median", "Skewness", "Kurtosis"]
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()
        if not columns:
            return pd.DataFrame({"Note": ["No numeric columns available"]})

        if group_col and group_col in df.columns:
            groups = df[group_col].dropna().unique()
            all_rows = []
            for col in columns:
                for group in groups:
                    sub = df[df[group_col] == group][col].dropna()
                    if len(sub) == 0:
                        continue
                    row = {"Variable": col, "Group": str(group), "N": len(sub)}
                    if "Mean" in include: row["Mean"] = f"{sub.mean():.2f}"
                    if "SD" in include: row["SD"] = f"{sub.std():.2f}"
                    if "Min" in include: row["Min"] = f"{sub.min():.2f}"
                    if "Max" in include: row["Max"] = f"{sub.max():.2f}"
                    if "Median" in include: row["Median"] = f"{sub.median():.2f}"
                    if "Skewness" in include: row["Skewness"] = f"{sub.skew():.2f}"
                    if "Kurtosis" in include: row["Kurtosis"] = f"{sub.kurtosis():.2f}"
                    if "SE" in include: row["SE"] = f"{sub.std() / np.sqrt(len(sub)):.2f}"
                    if "IQR" in include: row["IQR"] = f"{sub.quantile(0.75) - sub.quantile(0.25):.2f}"
                    all_rows.append(row)
            return pd.DataFrame(all_rows)
        else:
            rows = []
            for col in columns:
                series = df[col].dropna()
                if len(series) == 0:
                    continue
                row = {"Variable": col, "N": len(series)}
                if "Mean" in include: row["Mean"] = f"{series.mean():.2f}"
                if "SD" in include: row["SD"] = f"{series.std():.2f}"
                if "Min" in include: row["Min"] = f"{series.min():.2f}"
                if "Max" in include: row["Max"] = f"{series.max():.2f}"
                if "Median" in include: row["Median"] = f"{series.median():.2f}"
                if "Skewness" in include: row["Skewness"] = f"{series.skew():.2f}"
                if "Kurtosis" in include: row["Kurtosis"] = f"{series.kurtosis():.2f}"
                if "SE" in include: row["SE"] = f"{series.std() / np.sqrt(len(series)):.2f}"
                if "IQR" in include: row["IQR"] = f"{series.quantile(0.75) - series.quantile(0.25):.2f}"
                rows.append(row)
            return pd.DataFrame(rows)

    @staticmethod
    def correlation_matrix_table(
        df: pd.DataFrame,
        variables: List[str],
        method: str = "pearson",
        show_p: bool = True,
        show_stars: bool = True,
    ) -> pd.DataFrame:
        """
        Generate a formatted correlation matrix with significance stars.
        """
        from scipy import stats as scipy_stats

        corr = df[variables].corr(method=method)
        n = len(variables)
        data = []
        for i, v1 in enumerate(variables):
            row = {"Variable": v1}
            for j, v2 in enumerate(variables):
                if j <= i:
                    r = corr.loc[v1, v2]
                    if show_p:
                        valid = df[[v1, v2]].dropna()
                        if len(valid) > 2:
                            _, p = scipy_stats.pearsonr(valid[v1], valid[v2])
                            stars = ""
                            if show_stars:
                                if p < 0.001: stars = "***"
                                elif p < 0.01: stars = "**"
                                elif p < 0.05: stars = "*"
                            row[v2] = f"{r:.3f}{stars}"
                        else:
                            row[v2] = f"{r:.3f}"
                    else:
                        row[v2] = f"{r:.3f}"
                else:
                    row[v2] = ""
            data.append(row)

        result = pd.DataFrame(data)
        # Add footnote
        if show_stars:
            result.attrs["footnote"] = "*** p < .001, ** p < .01, * p < .05"
        return result

    @staticmethod
    def regression_results_table(
        models: List[Dict[str, Any]],
        model_names: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Format regression results as a publication-ready table.
        """
        if model_names is None:
            model_names = [f"Model {i1}" for i in range(len(models))]

        rows = []
        for i, model in enumerate(models):
            coefs = model.get("coefficients", {})
            r2 = model.get("r_squared", model.get("rsquared", None))
            adj_r2 = model.get("adj_r_squared", model.get("rsquared_adj", None))
            n = model.get("n", model.get("nobs", None))
            f_stat = model.get("f_statistic", model.get("fvalue", None))
            f_p = model.get("f_p_value", model.get("f_pvalue", None))

            for var_name, coef_info in coefs.items():
                if isinstance(coef_info, dict):
                    coef = coef_info.get("coef", coef_info.get("coefficient", ""))
                    se = coef_info.get("se", coef_info.get("std_err", ""))
                    p = coef_info.get("p", coef_info.get("p_value", ""))
                    stars = ""
                    if p != "" and isinstance(p, (int, float)):
                        if p < 0.001: stars = "***"
                        elif p < 0.01: stars = "**"
                        elif p < 0.05: stars = "*"
                    rows.append({
                        "Model": model_names[i],
                        "Variable": var_name,
                        "B": f"{coef:.3f}" if isinstance(coef, (int, float)) else str(coef),
                        "SE": f"{se:.3f}" if isinstance(se, (int, float)) else str(se),
                        "p": f"{p:.3f}{stars}" if isinstance(p, (int, float)) else str(p),
                    })

            # Model fit statistics
            if r2 is not None:
                rows.append({"Model": model_names[i], "Variable": "RÂ²", "B": f"{r2:.3f}", "SE": "", "p": ""})
            if adj_r2 is not None:
                rows.append({"Model": model_names[i], "Variable": "Adj. RÂ²", "B": f"{adj_r2:.3f}", "SE": "", "p": ""})
            if n is not None:
                rows.append({"Model": model_names[i], "Variable": "N", "B": str(n), "SE": "", "p": ""})
            if f_stat is not None:
                rows.append({"Model": model_names[i], "Variable": "F", "B": f"{f_stat:.3f}", "SE": "", "p": f"{f_p:.3f}" if f_p else ""})

        result = pd.DataFrame(rows)
        result.attrs["footnote"] = "*** p < .001, ** p < .01, * p < .05"
        return result

    @staticmethod
    def frequency_table(
        df: pd.DataFrame,
        column: str,
        include_cumulative: bool = True,
    ) -> pd.DataFrame:
        """
        Generate a formatted frequency table.
        """
        freq = df[column].value_counts(dropna=False).reset_index()
        freq.columns = [column, "Frequency"]
        freq["Percent"] = (freq["Frequency"] / len(df) * 100).round(2)
        if include_cumulative:
            freq["Cumulative %"] = freq["Percent"].cumsum().round(2)
        # Add total row
        total = {column: "Total", "Frequency": len(df), "Percent": 100.0}
        if include_cumulative:
            total["Cumulative %"] = 100.0
        freq = pd.concat([freq, pd.DataFrame([total])], ignore_index=True)
        return freq

    @staticmethod
    def to_apa_latex(df: pd.DataFrame, caption: str = "Table 1", label: str = "tab:results") -> str:
        """Convert a DataFrame to an APA-style LaTeX table."""
        lines = [
            r"\begin{table}[htbp]",
            r"\centering",
            rf"\caption{{{caption}}}",
            rf"\label{{{label}}}",
            r"\begin{tabular}{"  "l"  "r" * (len(df.columns) - 1)  "}",
            r"\toprule",
            " & ".join(df.columns)  r" \\",
            r"\midrule",
        ]
        for _, row in df.iterrows():
            lines.append(" & ".join(str(v) for v in row.values)  r" \\")
        lines.append(r"\bottomrule")
        footnote = df.attrs.get("footnote", "")
        if footnote:
            lines.append(r"\multicolumn{"  str(len(df.columns))  r"}{l}{\footnotesize "  footnote  "}")
        lines.append(r"\end{tabular}")
        lines.append(r"\end{table}")
        return "\n".join(lines)

    @staticmethod
    def to_apa_markdown(df: pd.DataFrame, title: str = "Table 1") -> str:
        """Convert a DataFrame to APA-style markdown table."""
        lines = [f"**{title}**", ""]
        footnote = df.attrs.get("footnote", "")
        # Header
        lines.append("| "  " | ".join(str(c) for c in df.columns)  " |")
        lines.append("| "  " | ".join("---" for _ in df.columns)  " |")
        for _, row in df.iterrows():
            lines.append("| "  " | ".join(str(v) for v in row.values)  " |")
        if footnote:
            lines.append("")
            lines.append(f"*Note.* {footnote}")
        return "\n".join(lines)


# â”€â”€â”€ UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def render_table_generator_ui():
    """Render the Publication Tables page."""
    import streamlit as st

    st.markdown("## ðŸ“‘ Publication-Ready Table Generator")
    st.markdown("*APA-style tables, correlation matrices, regression tables, and more*")

    df = st.session_state.get("active_df")
    if df is None or df.empty:
        st.warning("No data loaded.")
        return

    st.info("Generate publication-ready tables from your data. Copy to clipboard or download as Markdown/LaTeX.")

    tab1, tab2, tab3, tab4 = st.tabs([
        " Descriptive Stats", "ðŸ”— Correlation Matrix",
        "ðŸ“ Regression Table", "ðŸ“‹ Frequency Table"
    ])

    with tab1:
        st.subheader(" Descriptive Statistics Table")
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cols = st.multiselect("Variables", options=numeric_cols, default=numeric_cols[:min(5, len(numeric_cols))], key="tb_desc_cols")
        group_col = st.selectbox("Group by (optional)", options=["None"]  df.columns.tolist(), key="tb_desc_group")
        include = st.multiselect("Include", options=["N", "Mean", "SD", "Min", "Max", "Median", "Skewness", "Kurtosis", "SE", "IQR"],
                                 default=["N", "Mean", "SD", "Min", "Max"], key="tb_desc_include")

        if st.button(" Generate Table", type="primary") and cols:
            gcol = None if group_col == "None" else group_col
            result = TableGenerator.descriptive_stats_table(df, cols, gcol, include)
            if not result.empty:
                st.dataframe(result, use_container_width=True, hide_index=True)
                st.markdown("---")
                st.markdown("**ðŸ“‹ APA Markdown:**")
                st.code(TableGenerator.to_apa_markdown(result, "Table 1: Descriptive Statistics"), language="markdown")

    with tab2:
        st.subheader("ðŸ”— Correlation Matrix")
        corr_vars = st.multiselect("Variables", options=numeric_cols, default=numeric_cols[:min(6, len(numeric_cols))], key="tb_corr_vars")
        corr_method = st.selectbox("Method", options=["pearson", "spearman", "kendall"], key="tb_corr_method")
        if st.button("ðŸ”— Generate Matrix", type="primary") and len(corr_vars) >= 2:
            result = TableGenerator.correlation_matrix_table(df, corr_vars, corr_method)
            st.dataframe(result, use_container_width=True, hide_index=True)
            st.caption(result.attrs.get("footnote", ""))
            st.markdown("**ðŸ“‹ APA Markdown:**")
            st.code(TableGenerator.to_apa_markdown(result, "Table 2: Correlation Matrix"), language="markdown")

    with tab3:
        st.subheader("ðŸ“ Regression Results Table")
        st.info("Enter regression results manually or load from analysis. Provide coefficients, SEs, and p-values.")
        n_vars = st.number_input("Number of predictors", min_value=1, max_value=20, value=3, key="tb_reg_n")
        var_names = st.text_input("Variable names (comma-separated)", value="Predictor1, Predictor2, Predictor3", key="tb_reg_vars")
        coefs = st.text_input("Coefficients (comma-separated)", value="0.45, 0.32, 0.12", key="tb_reg_coefs")
        ses = st.text_input("Standard Errors (comma-separated)", value="0.12, 0.10, 0.08", key="tb_reg_ses")
        r2 = st.number_input("RÂ²", value=0.45, step=0.01, key="tb_reg_r2")
        n = st.number_input("N", value=100, step=1, key="tb_reg_n_val")

        if st.button("ðŸ“ Generate Table", type="primary"):
            vars_list = [v.strip() for v in var_names.split(",") if v.strip()]
            coefs_list = [float(c.strip()) for c in coefs.split(",") if c.strip()]
            ses_list = [float(s.strip()) for s in ses.split(",") if s.strip()]
            coefs_dict = {}
            for i, v in enumerate(vars_list):
                if i < len(coefs_list) and i < len(ses_list):
                    from scipy import stats as scipy_stats
                    t_val = coefs_list[i] / ses_list[i] if ses_list[i] > 0 else 0
                    p_val = 2 * (1 - scipy_stats.norm.cdf(abs(t_val)))
                    coefs_dict[v] = {"coef": coefs_list[i], "se": ses_list[i], "p": round(float(p_val), 4)}

            model = {"coefficients": coefs_dict, "r_squared": r2, "n": n}
            result = TableGenerator.regression_results_table([model], ["Model 1"])
            st.dataframe(result, use_container_width=True, hide_index=True)
            st.caption(result.attrs.get("footnote", ""))
            st.markdown("**ðŸ“‹ APA Markdown:**")
            st.code(TableGenerator.to_apa_markdown(result, "Table 3: Regression Results"), language="markdown")

    with tab4:
        st.subheader("ðŸ“‹ Frequency Table")
        freq_col = st.selectbox("Column", options=df.columns.tolist(), key="tb_freq_col")
        if st.button("ðŸ“‹ Generate", type="primary"):
            result = TableGenerator.frequency_table(df, freq_col)
            st.dataframe(result, use_container_width=True, hide_index=True)
            st.markdown("**ðŸ“‹ APA Markdown:**")
            st.code(TableGenerator.to_apa_markdown(result, f"Table 4: Frequency Distribution of {freq_col}"), language="markdown")
