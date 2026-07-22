"""
🔬 Statistical Tests Page — SPSS-level statistical analysis suite.
T-tests, ANOVA, Correlation, Regression, Non-parametric tests, and more.
"""
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Statistical Tests", layout="wide", page_icon="🔬")

from modules.config import init_session_state
from modules.ui_components import hero_card, section_header, load_css, watermark, insight_card, stat_result_card
from modules.statistical_engine import StatisticalEngine
from modules.data_processor import profile_dataset, infer_column_types

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")
hero_card("🔬 Statistical Tests", "Professional research-grade statistical analysis — replaces SPSS, STATA, and SAS.", "SPSS Replacement Suite")
watermark("CHRISHEM")

# ─── Data Selection ──────────────────────────────────────────────────
active_df = st.session_state.get("active_df")
if active_df is None or active_df.empty:
    # Try notion data
    active_df = st.session_state.get("notion_df")

if active_df is None or active_df.empty:
    st.warning("⚠️ No data available. Load data from the **File Analyzer** page or connect to Notion first.")
    st.stop()

# Get column types
col_types = infer_column_types(active_df)
numeric_cols = [c for c, t in col_types.items() if t in ("numeric", "integer")]
cat_cols = [c for c, t in col_types.items() if t in ("categorical", "string")]
bool_cols = [c for c, t in col_types.items() if t == "boolean"]
temporal_cols = [c for c, t in col_types.items() if t == "temporal"]

# Initialize engine
engine = StatisticalEngine()

# ─── Test Type Selection ─────────────────────────────────────────────
test_categories = {
    "Descriptive Statistics": ["Descriptive Stats", "Frequency Table", "Cross-Tabulation", "Descriptive by Group"],
    "T-Tests": ["Independent T-Test", "Paired T-Test", "One-Sample T-Test"],
    "ANOVA": ["One-Way ANOVA", "Two-Way ANOVA"],
    "Categorical Tests": ["Chi-Square Test"],
    "Correlation": ["Pearson Correlation", "Spearman Correlation", "Correlation Matrix"],
    "Regression": ["Linear Regression", "Logistic Regression"],
    "Non-Parametric Tests": ["Mann-Whitney U", "Kruskal-Wallis H", "Wilcoxon Signed-Rank"],
    "Normality & Diagnostics": ["Normality Test"],
    "Power Analysis": ["Power Analysis (T-Test)"],
    "Reliability": ["Cronbach's Alpha"],
    "Factor Analysis": ["KMO Test", "Bartlett's Test"],
}

all_tests = []
for category, tests in test_categories.items():
    for test in tests:
        all_tests.append(f"{category} → {test}")

selected_test = st.selectbox("📋 Select Statistical Test", options=all_tests)

# Parse selection
test_name = selected_test.split(" → ", 1)[1] if " → " in selected_test else selected_test

st.markdown("---")

# ─── Run Selected Test ───────────────────────────────────────────────
if test_name == "Descriptive Stats":
    cols = st.multiselect("Select variables", options=numeric_cols, default=numeric_cols[:min(3, len(numeric_cols))] if numeric_cols else None)
    if st.button("📊 Run Descriptive Statistics", type="primary"):
        if cols:
            result = engine.descriptive_stats(active_df, cols)
            st.dataframe(result, use_container_width=True, hide_index=True)
            # Pretty summary
            for col in cols:
                series = active_df[col].dropna()
                st.markdown(f"**{col}** — Mean={series.mean():.2f}, Std={series.std():.2f}, Min={series.min():.2f}, Max={series.max():.2f}")
        else:
            st.warning("Please select at least one variable.")

elif test_name == "Frequency Table":
    if cat_cols:
        col = st.selectbox("Select categorical variable", options=cat_cols)
        if st.button("📊 Generate Frequency Table", type="primary"):
            result = engine.frequency_table(active_df, col)
            st.dataframe(result, use_container_width=True, hide_index=True)
            # Bar chart
            from modules.chart_builder import build_bar
            fig = build_bar(result, x=col, y="Frequency", title=f"Frequency Distribution of {col}")
            if fig:
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No categorical variables available.")

elif test_name == "Cross-Tabulation":
    if len(cat_cols) >= 2:
        row_col = st.selectbox("Row variable", options=cat_cols)
        col_col = st.selectbox("Column variable", options=cat_cols, index=min(1, len(cat_cols)-1))
        if st.button("📊 Generate Cross-Tabulation", type="primary"):
            result = engine.cross_tabulation(active_df, row_col, col_col)
            st.dataframe(result, use_container_width=True)
    else:
        st.warning("Need at least 2 categorical variables.")

elif test_name == "Descriptive by Group":
    if cat_cols and numeric_cols:
        group_col = st.selectbox("Group by", options=cat_cols)
        value_col = st.selectbox("Variable", options=numeric_cols)
        if st.button("📊 Compute", type="primary"):
            result = engine.descriptive_by_group(active_df, group_col, value_col)
            st.dataframe(result, use_container_width=True)
    else:
        st.warning("Need at least 1 categorical and 1 numeric variable.")

elif test_name == "Independent T-Test":
    if len(cat_cols) >= 1 and len(numeric_cols) >= 1:
        # Find a categorical with exactly 2 groups
        binary_cats = [c for c in cat_cols if active_df[c].nunique() == 2]
        if binary_cats:
            group_col = st.selectbox("Group variable (2 groups)", options=binary_cats)
            value_col = st.selectbox("Test variable", options=numeric_cols)
            if st.button("▶️ Run T-Test", type="primary"):
                result = engine.independent_ttest(active_df, group_col, value_col)
                if "error" in result:
                    st.error(result["error"])
                else:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("T-Statistic", result["t_statistic"])
                    with col2:
                        st.metric("P-Value", result["p_value"])
                    with col3:
                        st.metric("Cohen's d", result["cohens_d"])
                    st.markdown(f"**Significant**: {'✅ Yes' if result.get('significant') else '❌ No'} (α=0.05)")
                    st.markdown(f"**Effect Size**: {result.get('effect_size', 'N/A')}")
                    st.markdown(f"**Groups**: {result['group_1']} (n={result['n_1']}, μ={result['mean_1']}) vs {result['group_2']} (n={result['n_2']}, μ={result['mean_2']})")
        else:
            st.warning("No categorical variable with exactly 2 groups found.")
    else:
        st.warning("Need at least 1 categorical and 1 numeric variable.")

elif test_name == "Paired T-Test":
    if len(numeric_cols) >= 2:
        before = st.selectbox("Before / First measure", options=numeric_cols)
        after = st.selectbox("After / Second measure", options=numeric_cols, index=min(1, len(numeric_cols)-1))
        if before != after:
            if st.button("▶️ Run Paired T-Test", type="primary"):
                result = engine.paired_ttest(active_df, before, after)
                if "error" in result:
                    st.error(result["error"])
                else:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("T-Statistic", result["t_statistic"])
                    with col2:
                        st.metric("P-Value", result["p_value"])
                    with col3:
                        st.metric("Cohen's d", result["cohens_d"])
                    st.markdown(f"**Mean Change**: {result['mean_change']} | **Significant**: {'✅' if result.get('significant') else '❌'}")
        else:
            st.warning("Please select two different variables.")
    else:
        st.warning("Need at least 2 numeric variables.")

elif test_name == "One-Sample T-Test":
    if numeric_cols:
        col = st.selectbox("Variable", options=numeric_cols)
        test_val = st.number_input("Test value (population mean)", value=0.0, step=0.1)
        if st.button("▶️ Run One-Sample T-Test", type="primary"):
            result = engine.one_sample_ttest(active_df, col, test_val)
            if "error" in result:
                st.error(result["error"])
            else:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("T-Statistic", result["t_statistic"])
                with col2:
                    st.metric("P-Value", result["p_value"])
                with col3:
                    st.metric("Cohen's d", result["cohens_d"])
                st.markdown(f"**Sample Mean**: {result['mean']} vs **Test Value**: {test_val} | **Significant**: {'✅' if result.get('significant') else '❌'}")
    else:
        st.warning("Need at least 1 numeric variable.")

elif test_name == "One-Way ANOVA":
    if cat_cols and numeric_cols:
        group_col = st.selectbox("Factor (groups)", options=cat_cols)
        value_col = st.selectbox("Dependent variable", options=numeric_cols)
        if st.button("▶️ Run One-Way ANOVA", type="primary"):
            result = engine.anova_one_way(active_df, group_col, value_col)
            if "error" in result:
                st.error(result["error"])
            else:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("F-Statistic", result["f_statistic"])
                with col2:
                    st.metric("P-Value", result["p_value"])
                st.markdown(f"**Eta-Squared**: {result['eta_squared']} | **Significant**: {'✅' if result.get('significant') else '❌'}")
                if "post_hoc" in result and not result["post_hoc"].empty and "Note" not in result["post_hoc"].columns:
                    st.subheader("Post-Hoc Tukey HSD")
                    st.dataframe(result["post_hoc"], use_container_width=True, hide_index=True)
    else:
        st.warning("Need at least 1 categorical and 1 numeric variable.")

elif test_name == "Two-Way ANOVA":
    if len(cat_cols) >= 2 and numeric_cols:
        f1 = st.selectbox("Factor 1", options=cat_cols)
        f2 = st.selectbox("Factor 2", options=[c for c in cat_cols if c != f1])
        dep = st.selectbox("Dependent variable", options=numeric_cols)
        if st.button("▶️ Run Two-Way ANOVA", type="primary"):
            result = engine.anova_two_way(active_df, f1, f2, dep)
            if not result.empty and "error" not in result.columns:
                st.dataframe(result, use_container_width=True, hide_index=True)
            else:
                st.error("Two-Way ANOVA failed. Check data requirements.")
    else:
        st.warning("Need at least 2 categorical and 1 numeric variable.")

elif test_name == "Chi-Square Test":
    if len(cat_cols) >= 2:
        col1_c = st.selectbox("Variable 1", options=cat_cols)
        col2_c = st.selectbox("Variable 2", options=[c for c in cat_cols if c != col1_c])
        if st.button("▶️ Run Chi-Square Test", type="primary"):
            result = engine.chi_square_test(active_df, col1_c, col2_c)
            if "error" in result:
                st.error(result["error"])
            else:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Chi-Square", result["chi_square"])
                with col2:
                    st.metric("DF", result["degrees_of_freedom"])
                with col3:
                    st.metric("P-Value", result["p_value"])
                st.markdown(f"**Cramer's V**: {result['cramers_v']} | **Significant**: {'✅' if result.get('significant') else '❌'}")
                st.subheader("Contingency Table")
                st.dataframe(result.get("contingency_table", pd.DataFrame()), use_container_width=True)
    else:
        st.warning("Need at least 2 categorical variables.")

elif test_name == "Pearson Correlation":
    if len(numeric_cols) >= 2:
        col1_c = st.selectbox("Variable 1", options=numeric_cols)
        col2_c = st.selectbox("Variable 2", options=[c for c in numeric_cols if c != col1_c])
        if st.button("▶️ Run Pearson Correlation", type="primary"):
            result = engine.pearson_correlation(active_df, col1_c, col2_c)
            if "error" in result:
                st.error(result["error"])
            else:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("R", result["r"])
                with col2:
                    st.metric("R²", result["r_squared"])
                with col3:
                    st.metric("P-Value", result["p_value"])
                st.markdown(f"**Strength**: {result.get('strength', 'N/A')} | **Significant**: {'✅' if result.get('significant') else '❌'}")
    else:
        st.warning("Need at least 2 numeric variables.")

elif test_name == "Spearman Correlation":
    if len(numeric_cols) >= 2:
        col1_c = st.selectbox("Variable 1", options=numeric_cols)
        col2_c = st.selectbox("Variable 2", options=[c for c in numeric_cols if c != col1_c])
        if st.button("▶️ Run Spearman Correlation", type="primary"):
            result = engine.spearman_correlation(active_df, col1_c, col2_c)
            if "error" in result:
                st.error(result["error"])
            else:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Rho", result["rho"])
                with col2:
                    st.metric("P-Value", result["p_value"])
                st.markdown(f"**Significant**: {'✅' if result.get('significant') else '❌'}")
    else:
        st.warning("Need at least 2 numeric variables.")

elif test_name == "Correlation Matrix":
    if len(numeric_cols) >= 2:
        selected_cols = st.multiselect("Select variables", options=numeric_cols, default=numeric_cols[:min(5, len(numeric_cols))])
        if selected_cols and st.button("📊 Show Correlation Matrix", type="primary"):
            result = engine.correlation_matrix(active_df[selected_cols])
            st.dataframe(result.round(4), use_container_width=True)
            # Heatmap
            from modules.chart_builder import build_heatmap
            fig = build_heatmap(pd.DataFrame(), title="Correlation Matrix")
            if fig is None:
                # Build manually
                import plotly.figure_factory as ff
                fig = ff.create_annotated_heatmap(
                    result.values, x=list(result.columns), y=list(result.index),
                    colorscale="RdBu_r", zmin=-1, zmax=1
                )
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Need at least 2 numeric variables.")

elif test_name == "Linear Regression":
    if len(numeric_cols) >= 2:
        target = st.selectbox("Target (dependent)", options=numeric_cols)
        features = st.multiselect("Features (predictors)", options=[c for c in numeric_cols if c != target])
        if features and st.button("▶️ Run Linear Regression", type="primary"):
            result = engine.linear_regression(active_df, target, features)
            if "error" in result:
                st.error(result["error"])
            elif "summary" in result:
                st.dataframe(result["summary"], use_container_width=True, hide_index=True)
    else:
        st.warning("Need at least 2 numeric variables.")

elif test_name == "Logistic Regression":
    bool_or_binary = [c for c in cat_cols if active_df[c].nunique() == 2]
    if bool_cols:
        bool_or_binary.extend(bool_cols)
    if bool_or_binary and numeric_cols:
        target = st.selectbox("Binary target", options=bool_or_binary)
        features = st.multiselect("Features (predictors)", options=numeric_cols)
        if features and st.button("▶️ Run Logistic Regression", type="primary"):
            result = engine.logistic_regression(active_df, target, features)
            if "error" in result:
                st.error(result["error"])
            elif "summary" in result:
                st.dataframe(result["summary"], use_container_width=True, hide_index=True)
    else:
        st.warning("Need a binary target variable and at least 1 numeric predictor.")

elif test_name == "Mann-Whitney U":
    binary_cats = [c for c in cat_cols if active_df[c].nunique() == 2]
    if binary_cats and numeric_cols:
        group_col = st.selectbox("Group variable (2 groups)", options=binary_cats)
        value_col = st.selectbox("Test variable", options=numeric_cols)
        if st.button("▶️ Run Mann-Whitney U", type="primary"):
            result = engine.mann_whitney(active_df, group_col, value_col)
            if "error" in result:
                st.error(result["error"])
            else:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("U Statistic", result["u_statistic"])
                with col2:
                    st.metric("P-Value", result["p_value"])
                st.markdown(f"**Significant**: {'✅' if result.get('significant') else '❌'}")
    else:
        st.warning("Need a binary categorical and a numeric variable.")

elif test_name == "Kruskal-Wallis H":
    if cat_cols and numeric_cols:
        group_col = st.selectbox("Group variable", options=cat_cols)
        value_col = st.selectbox("Test variable", options=numeric_cols)
        if st.button("▶️ Run Kruskal-Wallis", type="primary"):
            result = engine.kruskal_wallis(active_df, group_col, value_col)
            if "error" in result:
                st.error(result["error"])
            else:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("H Statistic", result["h_statistic"])
                with col2:
                    st.metric("P-Value", result["p_value"])
                st.markdown(f"**Significant**: {'✅' if result.get('significant') else '❌'}")
    else:
        st.warning("Need at least 1 categorical and 1 numeric variable.")

elif test_name == "Wilcoxon Signed-Rank":
    if len(numeric_cols) >= 2:
        before = st.selectbox("Before / First measure", options=numeric_cols)
        after = st.selectbox("After / Second measure", options=numeric_cols, index=min(1, len(numeric_cols)-1))
        if before != after:
            if st.button("▶️ Run Wilcoxon Test", type="primary"):
                result = engine.wilcoxon_signed_rank(active_df, before, after)
                if "error" in result:
                    st.error(result["error"])
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("W Statistic", result["w_statistic"])
                    with col2:
                        st.metric("P-Value", result["p_value"])
                    st.markdown(f"**Significant**: {'✅' if result.get('significant') else '❌'}")
    else:
        st.warning("Need at least 2 numeric variables.")

elif test_name == "Normality Test":
    if numeric_cols:
        col = st.selectbox("Select variable", options=numeric_cols)
        if st.button("▶️ Test Normality", type="primary"):
            result = engine.test_normality(active_df, col)
            if "error" in result:
                st.error(result["error"])
            else:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Statistic", result["statistic"])
                with col2:
                    st.metric("P-Value", result["p_value"])
                st.markdown(f"**Normal Distribution**: {'✅ Yes' if result.get('is_normal') else '❌ No'} ({result['test']})")
    else:
        st.warning("No numeric variables available.")

elif test_name == "Power Analysis (T-Test)":
    st.markdown("**Power Analysis — Estimate Required Sample Size**")
    effect = st.slider("Expected effect size (Cohen's d)", 0.1, 2.0, 0.5, 0.05)
    alpha = st.slider("Alpha (α)", 0.01, 0.10, 0.05, 0.01)
    power = st.slider("Desired power (1-β)", 0.5, 0.99, 0.80, 0.05)
    if st.button("📊 Calculate Sample Size", type="primary"):
        result = engine.power_ttest(effect_size=effect, alpha=alpha, power=power)
        st.metric("Required N per Group", result["required_n_per_group"])
        st.metric("Total N Needed", result["total_n"])
        st.markdown(f"**Settings**: d={effect}, α={alpha}, power={power}")

elif test_name == "Cronbach's Alpha":
    if len(numeric_cols) >= 2:
        items = st.multiselect("Select scale items", options=numeric_cols, default=numeric_cols[:min(3, len(numeric_cols))])
        if len(items) >= 2 and st.button("▶️ Calculate Alpha", type="primary"):
            result = engine.cronbach_alpha(active_df, items)
            if "error" in result:
                st.error(result["error"])
            else:
                st.metric("Cronbach's α", result["alpha"])
                st.markdown(f"**Interpretation**: {result.get('interpretation', 'N/A')}")
                st.markdown(f"**Items**: {result['items']} | **Sample**: n={result['n']}")
    else:
        st.warning("Need at least 2 numeric variables (scale items).")

elif test_name == "KMO Test":
    if len(numeric_cols) >= 2:
        variables = st.multiselect("Select variables for KMO", options=numeric_cols, default=numeric_cols[:min(4, len(numeric_cols))])
        if len(variables) >= 2 and st.button("▶️ Calculate KMO", type="primary"):
            result = engine.kmo_test(active_df, variables)
            if "error" in result:
                st.error(result["error"])
            else:
                st.metric("KMO Overall", result["kmo_overall"])
                st.markdown(f"**Interpretation**: {result.get('interpretation', 'N/A')}")
                if "kmo_per_variable" in result:
                    st.subheader("KMO per Variable")
                    for var, val in result["kmo_per_variable"].items():
                        st.markdown(f"  • **{var}**: {val}")
    else:
        st.warning("Need at least 2 numeric variables.")

elif test_name == "Bartlett's Test":
    if len(numeric_cols) >= 2:
        variables = st.multiselect("Select variables", options=numeric_cols, default=numeric_cols[:min(4, len(numeric_cols))])
        if len(variables) >= 2 and st.button("▶️ Run Bartlett's Test", type="primary"):
            result = engine.bartlett_test(active_df, variables)
            if "error" in result:
                st.error(result["error"])
            else:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Chi-Square", result["chi_square"])
                with col2:
                    st.metric("P-Value", result["p_value"])
                st.markdown(f"**Sphericity Assumption Met**: {'✅ Yes' if result.get('significant') else '❌ No'} (data suitable {'✅' if result.get('significant') else '❌'} for factor analysis)")
    else:
        st.warning("Need at least 2 numeric variables.")

