# --- CHRISHEM AUTHOR PROFILE BLOCK ---
import os
import streamlit as st

st.markdown("# **Notion Live Analyzer**")
st.markdown("### **Creator: CHRISHEM**")
st.markdown("---")
# -------------------------------------

"""
APA Formatter  formats statistical results in APA 7th edition style.
Provides publication-ready output for all statistical tests.
"""
from typing import Dict, List, Any, Optional, Union, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
import streamlit as st
import re


class APAFormatter:
    """Format statistical results in APA 7th edition style."""

    @staticmethod
    def format_p_value(p: float, stars: bool = True) -> str:
        """Format p-value in APA style."""
        if p < 0.001:
            return "p < .001"  ("***" if stars else "")
        elif p < 0.01:
            return f"p = {p:.3f}"  ("**" if stars else "")
        elif p < 0.05:
            return f"p = {p:.3f}"  ("*" if stars else "")
        elif p < 0.10:
            return f"p = {p:.3f}"  ("†" if stars else "")
        else:
            return f"p = {p:.3f}"

    @staticmethod
    def format_effect_size(d: float, name: str = "Cohen's d") -> str:
        """Format effect size in APA style."""
        return f"{name} = {d:.2f}, {APAFormatter._interpret_effect_size(d, name)}"

    @staticmethod
    def _interpret_effect_size(val: float, name: str = "Cohen's d") -> str:
        """Interpret effect size magnitude."""
        abs_val = abs(val)
        if name == "Cohen's d" or name == "Cohen's dz":
            if abs_val >= 0.8:
                return "large effect"
            elif abs_val >= 0.5:
                return "medium effect"
            elif abs_val >= 0.2:
                return "small effect"
            else:
                return "negligible effect"
        elif name == "Eta-squared" or name == "η²":
            if abs_val >= 0.14:
                return "large effect"
            elif abs_val >= 0.06:
                return "medium effect"
            else:
                return "small effect"
        elif name == "r" or name == "R":
            if abs_val >= 0.5:
                return "strong relationship"
            elif abs_val >= 0.3:
                return "moderate relationship"
            else:
                return "weak relationship"
        elif name == "Cramer's V":
            if abs_val >= 0.5:
                return "strong association"
            elif abs_val >= 0.3:
                return "moderate association"
            else:
                return "weak association"
        elif name == "R²":
            if abs_val >= 0.26:
                return "large effect"
            elif abs_val >= 0.13:
                return "medium effect"
            else:
                return "small effect"
        return ""

    @staticmethod
    def format_mean_sd(mean: float, sd: float, decimals: int = 2) -> str:
        """Format M and SD in APA style."""
        return f"M = {mean:.{decimals}f}, SD = {sd:.{decimals}f}"

    @staticmethod
    def format_confidence_interval(ci_lower: float, ci_upper: float, confidence: float = 0.95) -> str:
        """Format confidence interval in APA style."""
        return f"{confidence*100:.0f}% CI [{ci_lower:.2f}, {ci_upper:.2f}]"

    # ─── Test-Specific Formatters ───────────────────────────────────

    @staticmethod
    def format_ttest(result: Dict[str, Any]) -> str:
        """Format t-test results in APA style."""
        if "error" in result:
            return f"Error: {result['error']}"

        test_type = result.get("test", "T-Test")
        parts = [f"A **{test_type}** was conducted."]

        if test_type == "Independent Samples T-Test":
            eff_name = "Cohen's d"
            parts.append(
                f"There was a {'significant' if result.get('significant') else 'non-significant'} "
                f"difference in scores between {result.get('group_1', 'Group 1')} "
                f"({APAFormatter.format_mean_sd(result.get('mean_1', 0), 0)}) "
                f"and {result.get('group_2', 'Group 2')} "
                f"({APAFormatter.format_mean_sd(result.get('mean_2', 0), 0)}), "
                f"t({result.get('n_1', 0)  result.get('n_2', 0) - 2}) = {result.get('t_statistic', 0):.2f}, "
                f"{APAFormatter.format_p_value(result.get('p_value', 1))}, "
                f"{APAFormatter.format_effect_size(result.get('cohens_d', 0), eff_name)}."
            )

        elif test_type == "Paired Samples T-Test":
            eff_name = "Cohen's dz"
            parts.append(
                f"There was a {'significant' if result.get('significant') else 'non-significant'} "
                f"difference between pre-test ({APAFormatter.format_mean_sd(result.get('mean_before', 0), 0)}) "
                f"and post-test ({APAFormatter.format_mean_sd(result.get('mean_after', 0), 0)}) scores, "
                f"with a mean change of {result.get('mean_change', 0):.2f}, "
                f"t({result.get('n_pairs', 0) - 1}) = {result.get('t_statistic', 0):.2f}, "
                f"{APAFormatter.format_p_value(result.get('p_value', 1))}, "
                f"{APAFormatter.format_effect_size(result.get('cohens_d', 0), eff_name)}."
            )

        elif test_type == "One-Sample T-Test":
            eff_name = "Cohen's d"
            parts.append(
                f"The mean {result.get('mean', 0):.2f} was {'significantly' if result.get('significant') else 'not significantly'} "
                f"different from the test value of {result.get('test_value', 0)}, "
                f"t({result.get('n', 0) - 1}) = {result.get('t_statistic', 0):.2f}, "
                f"{APAFormatter.format_p_value(result.get('p_value', 1))}, "
                f"{APAFormatter.format_effect_size(result.get('cohens_d', 0), eff_name)}."
            )

        return " ".join(parts)

    @staticmethod
    def format_anova(result: Dict[str, Any]) -> str:
        """Format ANOVA results in APA style."""
        if "error" in result:
            return f"Error: {result['error']}"

        test_name = result.get("test", "ANOVA")
        parts = [f"A **{test_name}** was conducted."]

        if test_name == "One-Way ANOVA":
            parts.append(
                f"There was a {'significant' if result.get('significant') else 'non-significant'} "
                f"effect of group on the dependent variable, "
                f"F({result.get('num_groups', 1) - 1}, {result.get('total_n', 0) - result.get('num_groups', 1)}) "
                f"= {result.get('f_statistic', 0):.2f}, "
                f"{APAFormatter.format_p_value(result.get('p_value', 1))}, "
                f"{APAFormatter.format_effect_size(result.get('eta_squared', 0), 'Eta-squared')}."
            )

        return " ".join(parts)

    @staticmethod
    def format_correlation(result: Dict[str, Any]) -> str:
        """Format correlation results in APA style."""
        if "error" in result:
            return f"Error: {result['error']}"

        test_name = result.get("test", "Correlation")
        parts = [f"A **{test_name}** was conducted to assess the relationship between variables."]

        if test_name == "Pearson Correlation":
            parts.append(
                f"There was a {'significant' if result.get('significant') else 'non-significant'} "
                f"{result.get('strength', '')} correlation between the variables, "
                f"r({result.get('n', 0) - 2}) = {result.get('r', 0):.2f}, "
                f"{APAFormatter.format_p_value(result.get('p_value', 1))}, "
                f"{APAFormatter.format_effect_size(result.get('r', 0), 'r')}."
            )

        elif test_name == "Spearman Rank Correlation":
            parts.append(
                f"There was a {'significant' if result.get('significant') else 'non-significant'} "
                f"correlation between the variables, "
                f"ρ({result.get('n', 0) - 2}) = {result.get('rho', 0):.2f}, "
                f"{APAFormatter.format_p_value(result.get('p_value', 1))}."
            )

        return " ".join(parts)

    @staticmethod
    def format_chi_square(result: Dict[str, Any]) -> str:
        """Format chi-square results in APA style."""
        if "error" in result:
            return f"Error: {result['error']}"

        parts = ["A **Chi-Square Test of Independence** was conducted."]
        eff_name = "Cramer's V"
        parts.append(
            f"There was a {'significant' if result.get('significant') else 'non-significant'} "
            f"association between the variables, "
            f"Chi2({result.get('degrees_of_freedom', 1)}, N = {result.get('sample_size', 0)}) "
            f"= {result.get('chi_square', 0):.2f}, "
            f"{APAFormatter.format_p_value(result.get('p_value', 1))}, "
            f"{APAFormatter.format_effect_size(result.get('cramers_v', 0), eff_name)}."
        )
        return " ".join(parts)

    @staticmethod
    def format_regression(result: Dict[str, Any]) -> str:
        """Format linear regression results in APA style."""
        if "error" in result:
            return f"Error: {result['error']}"
        if "summary" not in result:
            return "Regression results unavailable"

        summary = result["summary"]
        if isinstance(summary, pd.DataFrame):
            # Extract key values
            try:
                r2 = summary[summary['names'] == 'R-squared']['coef'].values[0] if 'R-squared' in summary['names'].values else None
                f_stat = summary[summary['names'] == 'F']['coef'].values[0] if 'F' in summary['names'].values else None
                f_pval = summary[summary['names'] == 'p-value']['coef'].values[0] if 'p-value' in summary['names'].values else None

                parts = ["A **linear regression** was conducted."]
                if r2 is not None:
                    parts.append(
                        f"The model was {'significant' if f_pval and f_pval < 0.05 else 'non-significant'}, "
                        f"F(_, _) = {float(f_stat):.2f}, {APAFormatter.format_p_value(float(f_pval))}, "
                        f"{APAFormatter.format_effect_size(float(r2), 'R²')}."
                    )
                return " ".join(parts)
            except Exception:
                return "Regression results available in table below."
        return "Regression results available in table below."

    @staticmethod
    def format_reliability(result: Dict[str, Any]) -> str:
        """Format Cronbach's alpha results in APA style."""
        if "error" in result:
            return f"Error: {result['error']}"

        alpha = result.get('alpha', 0)
        interp = result.get('interpretation', '')
        items = result.get('items', 0)
        n = result.get('n', 0)

        return (
            f"Cronbach's alpha was calculated to assess the internal consistency "
            f"of the {items}-item scale (N = {n}). "
            f"The analysis yielded α = {alpha:.3f}, indicating {interp.lower()} reliability."
        )

    @staticmethod
    def format_mann_whitney(result: Dict[str, Any]) -> str:
        """Format Mann-Whitney U results in APA style."""
        if "error" in result:
            return f"Error: {result['error']}"

        return (
            f"A Mann-Whitney U test indicated that there was "
            f"{'a significant' if result.get('significant') else 'no significant'} "
            f"difference between the groups "
            f"(U = {result.get('u_statistic', 0):.2f}, "
            f"{APAFormatter.format_p_value(result.get('p_value', 1))})."
        )

    @staticmethod
    def format_kruskal_wallis(result: Dict[str, Any]) -> str:
        """Format Kruskal-Wallis results in APA style."""
        if "error" in result:
            return f"Error: {result['error']}"

        return (
            f"A Kruskal-Wallis H test showed that there was "
            f"{'a significant' if result.get('significant') else 'no significant'} "
            f"difference between groups "
            f"(H({result.get('degrees_of_freedom', 1)}) = {result.get('h_statistic', 0):.2f}, "
            f"{APAFormatter.format_p_value(result.get('p_value', 1))})."
        )

    @staticmethod
    def format_wilcoxon(result: Dict[str, Any]) -> str:
        """Format Wilcoxon signed-rank results in APA style."""
        if "error" in result:
            return f"Error: {result['error']}"

        return (
            f"A Wilcoxon signed-rank test indicated that the median post-test scores were "
            f"{'significantly' if result.get('significant') else 'not significantly'} "
            f"different from pre-test scores "
            f"(W = {result.get('w_statistic', 0):.2f}, "
            f"{APAFormatter.format_p_value(result.get('p_value', 1))}, "
            f"n = {result.get('n_pairs', 0)})."
        )

    @staticmethod
    def format_normality(result: Dict[str, Any]) -> str:
        """Format normality test results in APA style."""
        if "error" in result:
            return f"Error: {result['error']}"

        return (
            f"A {result.get('test', 'normality test')} was conducted to assess normality. "
            f"Results indicated that the data "
            f"{'followed' if result.get('is_normal') else 'did not follow'} "
            f"a normal distribution "
            f"({result.get('statistic', 0):.2f}, "
            f"{APAFormatter.format_p_value(result.get('p_value', 1))})."
        )

    @staticmethod
    def format_descriptive(desc_df: pd.DataFrame) -> str:
        """Format descriptive statistics table as text."""
        if desc_df.empty:
            return "No descriptive statistics available."

        lines = ["Descriptive statistics are presented in Table 1.", ""]
        lines.append("**Table 1**")
        lines.append("*Descriptive Statistics for Study Variables*")
        lines.append("")
        lines.append("| Variable | N | M | SD | Min | Max |")
        lines.append("|----------|---|----|----|-----|-----|")
        for _, row in desc_df.iterrows():
            lines.append(
                f"| {row.get('Variable', '')} | {row.get('N', '')} | "
                f"{row.get('Mean', ''):.2f} | {row.get('Std Dev', ''):.2f} | "
                f"{row.get('Min', ''):.2f} | {row.get('Max', ''):.2f} |"
            )
        return "\n".join(lines)

    @staticmethod
    def auto_format(result: Dict[str, Any]) -> str:
        """Auto-detect test type and format in APA style."""
        if not result:
            return ""

        test_name = result.get("test", "")

        if "T-Test" in test_name:
            return APAFormatter.format_ttest(result)
        elif "ANOVA" in test_name:
            return APAFormatter.format_anova(result)
        elif "Chi-Square" in test_name:
            return APAFormatter.format_chi_square(result)
        elif "Pearson" in test_name or "Spearman" in test_name:
            return APAFormatter.format_correlation(result)
        elif "Mann-Whitney" in test_name:
            return APAFormatter.format_mann_whitney(result)
        elif "Kruskal-Wallis" in test_name:
            return APAFormatter.format_kruskal_wallis(result)
        elif "Wilcoxon" in test_name:
            return APAFormatter.format_wilcoxon(result)
        elif "Normality" in test_name or "Shapiro" in test_name or "Kolmogorov" in test_name:
            return APAFormatter.format_normality(result)
        elif "Cronbach" in test_name or "Alpha" in test_name:
            return APAFormatter.format_reliability(result)
        elif "Linear Regression" in test_name:
            return APAFormatter.format_regression(result)
        else:
            # Generic format
            parts = [f"A **{test_name}** was conducted."]
            if "significant" in result:
                parts.append(f"Results were {'significant' if result['significant'] else 'non-significant'}.")
            if "p_value" in result:
                parts.append(f"{APAFormatter.format_p_value(result['p_value'])}.")
            return " ".join(parts)


# ─── UI ─────────────────────────────────────────────────────────────

def render_apa_outputs_page(statistical_results: List[Dict[str, Any]] = None):
    """Render the APA outputs page."""
    st.markdown("## 📑 APA 7th Edition Results")
    st.markdown("*Publication-ready statistical reporting*")

    if not statistical_results:
        st.info("No statistical results to format. Run analyses on the **🔬 Statistical Tests** page first.")
        st.markdown("""
        ### APA Formatting Guide

        **Key APA 7th Edition reporting standards:**

        1. **T-Tests**: *t*(df) = value, *p* = value, Cohen's *d* = value
        2. **ANOVA**: *F*(df1, df2) = value, *p* = value, η² = value
        3. **Correlation**: *r*(df) = value, *p* = value
        4. **Chi-Square**: χ²(df, N = n) = value, *p* = value, V = value
        5. **Regression**: *R²* = value, *F*(df1, df2) = value, *p* = value

        **Effect size guidelines (Cohen, 1988):**
        - **Cohen's d**: 0.2 (small), 0.5 (medium), 0.8 (large)
        - **η²**: 0.01 (small), 0.06 (medium), 0.14 (large)
        - **r**: 0.1 (small), 0.3 (medium), 0.5 (large)
        """)
        return

    st.success(f"Formatting {len(statistical_results)} statistical results")

    for i, result in enumerate(statistical_results):
        with st.container():
            test_name = result.get("test", f"Analysis {i1}")
            st.subheader(f"{i1}. {test_name}")

            apa_text = APAFormatter.auto_format(result)
            st.info(apa_text)

            # Raw values
            with st.expander("View detailed values"):
                for k, v in result.items():
                    if not isinstance(v, pd.DataFrame):
                        st.markdown(f"**{k}**: {v}")

            st.markdown("---")

    # Generate full results section
    st.subheader("📄 Complete Results Section")
    if st.button("Generate APA Results Section"):
        lines = ["## Results", ""]
        for i, result in enumerate(statistical_results):
            apa_text = APAFormatter.auto_format(result)
            lines.append(apa_text)
            lines.append("")

        full_text = "\n".join(lines)
        st.markdown(full_text)
        st.code(full_text, language="markdown")


def render_apa_quick_format_ui():
    """Render quick APA formatting tool."""
    st.subheader("🔧 Quick APA Formatter")
    st.caption("Enter statistical values to get APA-formatted text")

    test_type = st.selectbox("Select test type", [
        "T-Test", "ANOVA", "Correlation", "Chi-Square", "Regression", "Descriptive"
    ], key="apa_quick_type")

    if test_type == "T-Test":
        col1, col2, col3 = st.columns(3)
        with col1:
            t_val = st.number_input("t-value", value=2.5, step=0.1, format="%.2f", key="apa_t")
            df_val = st.number_input("df", value=58, step=1, key="apa_t_df")
        with col2:
            p_val = st.number_input("p-value", value=0.015, step=0.001, format="%.4f", key="apa_t_p")
            d_val = st.number_input("Cohen's d", value=0.65, step=0.01, format="%.2f", key="apa_t_d")
        with col3:
            mean1 = st.number_input("M₁", value=45.2, step=0.1, key="apa_t_m1")
            mean2 = st.number_input("M₂", value=38.5, step=0.1, key="apa_t_m2")

        if st.button("Format T-Test"):
            result = {
                "test": "Independent Samples T-Test",
                "t_statistic": t_val,
                "p_value": p_val,
                "cohens_d": d_val,
                "mean_1": mean1, "mean_2": mean2,
                "n_1": df_val // 2  1, "n_2": df_val // 2  1,
                "significant": p_val < 0.05,
                "group_1": "Group 1", "group_2": "Group 2",
            }
            st.success(APAFormatter.format_ttest(result))

    elif test_type == "ANOVA":
        col1, col2 = st.columns(2)
        with col1:
            f_val = st.number_input("F-value", value=5.82, step=0.1, format="%.2f", key="apa_f")
            df1 = st.number_input("df₁ (between)", value=2, step=1, key="apa_f_df1")
        with col2:
            p_val = st.number_input("p-value", value=0.005, step=0.001, format="%.4f", key="apa_f_p")
            eta2 = st.number_input("η²", value=0.14, step=0.01, format="%.2f", key="apa_f_eta")

        if st.button("Format ANOVA"):
            result = {
                "test": "One-Way ANOVA",
                "f_statistic": f_val,
                "p_value": p_val,
                "eta_squared": eta2,
                "num_groups": df1  1,
                "total_n": 100,
                "significant": p_val < 0.05,
            }
            st.success(APAFormatter.format_anova(result))

    elif test_type == "Correlation":
        col1, col2 = st.columns(2)
        with col1:
            r_val = st.number_input("r-value", value=0.45, step=0.01, format="%.2f", min_value=-1.0, max_value=1.0, key="apa_r")
            n_val = st.number_input("N", value=60, step=1, key="apa_r_n")
        with col2:
            p_val = st.number_input("p-value", value=0.001, step=0.001, format="%.4f", key="apa_r_p")

        if st.button("Format Correlation"):
            result = {
                "test": "Pearson Correlation",
                "r": r_val,
                "p_value": p_val,
                "n": n_val,
                "significant": p_val < 0.05,
                "strength": "strong" if abs(r_val) > 0.5 else "moderate" if abs(r_val) > 0.3 else "weak",
            }
            st.success(APAFormatter.format_correlation(result))

    elif test_type == "Chi-Square":
        col1, col2 = st.columns(2)
        with col1:
            chi2 = st.number_input("χ² value", value=12.5, step=0.1, format="%.2f", key="apa_chi")
            df_chi = st.number_input("df", value=2, step=1, key="apa_chi_df")
        with col2:
            p_val = st.number_input("p-value", value=0.002, step=0.001, format="%.4f", key="apa_chi_p")
            cv = st.number_input("Cramer's V", value=0.35, step=0.01, format="%.2f", key="apa_chi_cv")

        if st.button("Format Chi-Square"):
            result = {
                "test": "Chi-Square Test of Independence",
                "chi_square": chi2,
                "degrees_of_freedom": df_chi,
                "p_value": p_val,
                "cramers_v": cv,
                "sample_size": 100,
                "significant": p_val < 0.05,
            }
            st.success(APAFormatter.format_chi_square(result))

