import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
import pandas as pd
import scipy.stats as stats
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

try:
    import statsmodels.api as sm
    from statsmodels.formula.api import ols
    from statsmodels.stats.power import TTestIndPower
    from statsmodels.stats.multicomp import pairwise_tukeyhsd
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.session_manager import get_active_dataframe
from modules.shared_ui import (
    hero_card,
    section_header,
    render_dataset_context_banner,
    metric_card,
    render_export_buttons,
)


def get_df() -> pd.DataFrame:
    df = get_active_dataframe()
    if df is None:
        np.random.seed(42)
        return pd.DataFrame({
            "CategoryGroup": np.random.choice(["Group A", "Group B", "Group C"], 150),
            "BinaryGroup": np.random.choice(["Control", "Treatment"], 150),
            "Score_Numeric": np.random.normal(75, 12, 150),
            "Metric_Value": np.random.normal(50, 8, 150),
            "Predictor_X": np.random.normal(30, 5, 150),
            "Binary_Outcome": np.random.choice([0, 1], 150),
            "Condition_Before": np.random.normal(60, 10, 150),
            "Condition_After": np.random.normal(65, 10, 150),
        })
    return df


def generate_ai_interpretation(
    test_name: str, 
    p_value: float, 
    effect: float = None, 
    effect_label: str = "Effect Size", 
    assumption_warning: str = None
) -> str:
    sig = p_value < 0.05
    narrative = (
        f"> **Executive Summary:** The **{test_name}}** result is "
        f"{'**statistically significant** ($p < 0.05$)' if sig else '**not statistically significant** ($p \\ge 0.05$)'}} "
        f"with $p = **{p_value:.5f}}**$."
    )
    narrative += "\n> **Key Takeaway:** " + (
        "Reject $H_0$ — sufficient evidence of a reliable effect." 
        if sig else 
        "Fail to reject $H_0$ — insufficient evidence to reject the null hypothesis."
    )
    if effect is not None:
        narrative += f"\n> **{effect_label}}:** `{effect:.4f}}`"
    if assumption_warning:
        narrative += f"\n> ⚠️ **Assumption Notice:** {assumption_warning}}"
    return narrative


def check_normality_shapiro(series: pd.Series):
    clean = series.dropna()
    if len(clean) < 3:
        return True, "Insufficient sample size ($N < 3$) for normality testing."
    if len(clean) > 5000:
        clean = clean.sample(5000, random_state=42)
    stat, p = stats.shapiro(clean)
    is_normal = p > 0.05
    msg = f"Shapiro-Wilk $W = {stat:.4f}}$, $p = {p:.4f}}$ ({'Normal distribution consistent' if is_normal else 'Significant non-normality detected'}})"
    return is_normal, msg


def log_test_result(test_name: str, p_value: float, effect_label: str = None, effect_value: float = None):
    if "stats_test_ledger" not in st.session_state:
        st.session_state["stats_test_ledger"] = []
    st.session_state["stats_test_ledger"].append({
        "Test": test_name,
        "P-Value (Raw)": float(p_value),
        "Effect Label": effect_label or "—",
        "Effect Value": float(effect_value) if effect_value is not None else None,
        "Timestamp": pd.Timestamp.now().strftime("%H:%M:%S"),
    })


def benjamini_hochberg(pvals: np.ndarray) -> np.ndarray:
    m = len(pvals)
    if m == 0:
        return np.array([])
    order = np.argsort(pvals)
    ranked = np.asarray(pvals)[order]
    adj = ranked * m / (np.arange(m) + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    adj = np.clip(adj, 0, 1)
    out = np.empty(m)
    out[order] = adj
    return out


def plot_qq(series: pd.Series, title: str = "Normal Q-Q Plot"):
    clean = series.dropna().values
    (osm, osr), (slope, intercept, r) = stats.probplot(clean, dist="norm")
    x_vals = np.array([osm[0], osm[-1]])
    y_vals = slope * x_vals + intercept

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=osm, y=osr, mode='markers', name='Sample Quantiles', marker=dict(color='#1f77b4')))
    fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode='lines', name='Theoretical Line', line=dict(color='red', dash='dash')))
    fig.update_layout(
        title=title,
        xaxis_title="Theoretical Quantiles",
        yaxis_title="Sample Quantiles",
        margin=dict(l=20, r=20, t=40, b=20),
        height=320
    )
    return fig


def render_ledger_tab():
    section_header("📋 Multiple-Comparisons Ledger", "Bonferroni and Benjamini-Hochberg FDR adjustments across logged session hypothesis tests.")

    ledger = st.session_state.get("stats_test_ledger", [])
    if not ledger:
        st.info("ℹ️ No statistical tests logged in this session yet.")
        return

    ledger_df = pd.DataFrame(ledger)
    m = len(ledger_df)
    raw_p = ledger_df["P-Value (Raw)"].values
    ledger_df["Bonferroni p"] = np.clip(raw_p * m, 0, 1)
    ledger_df["BH-FDR p"] = benjamini_hochberg(raw_p)
    ledger_df["Significant (raw α=.05)"] = raw_p < 0.05
    ledger_df["Significant (Bonferroni)"] = ledger_df["Bonferroni p"] < 0.05
    ledger_df["Significant (BH-FDR)"] = ledger_df["BH-FDR p"] < 0.05

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tests Executed", m)
    c2.metric("Significant (Raw α=.05)", int(ledger_df["Significant (raw α=.05)"].sum()))
    c3.metric("Survive Bonferroni", int(ledger_df["Significant (Bonferroni)"].sum()))
    c4.metric("Survive BH-FDR", int(ledger_df["Significant (BH-FDR)"].sum()))

    if int(ledger_df["Significant (raw α=.05)"].sum()) > int(ledger_df["Significant (BH-FDR)"].sum()):
        st.warning("⚠️ High False Discovery Rate Notice: Certain significant tests do not maintain significance under multiple-comparison corrections.")

    st.dataframe(ledger_df, use_container_width=True, hide_index=True)
    render_export_buttons(ledger_df, base_name="multiple_comparisons_ledger")

    if st.button("🗑️ Reset Ledger", key="clear_ledger"):
        st.session_state["stats_test_ledger"] = []
        st.rerun()


def render_param_tests(df: pd.DataFrame):
    section_header("Parametric Hypothesis Tests", "t-tests, ANOVA, correlation, and linear regression with real-time assumption verification.")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    binary_cats = [c for c in cat_cols if df[c].dropna().nunique() == 2]

    test = st.selectbox("Select Parametric Model", [
        "Independent t-Test", "Paired t-Test", "One-Way ANOVA", "Two-Way ANOVA",
        "Pearson Correlation", "Linear Regression",
    ], key="param_test_sel")

    if test == "Independent t-Test":
        if binary_cats and numeric_cols:
            c1, c2 = st.columns(2)
            g = c1.selectbox("Grouping Factor (2 groups)", binary_cats, key="t_group")
            v = c2.selectbox("Target Variable", numeric_cols, key="t_val")

            sub_df = df[[g, v]].dropna()
            g_keys = sub_df[g].unique()
            g1 = sub_df[sub_df[g] == g_keys[0]][v].values
            g2 = sub_df[sub_df[g] == g_keys[1]][v].values

            if len(g1) >= 3 and len(g2) >= 3:
                _, norm_msg1 = check_normality_shapiro(pd.Series(g1))
                _, norm_msg2 = check_normality_shapiro(pd.Series(g2))
                levene_stat, levene_p = stats.levene(g1, g2)
                homog_msg = f"Levene's Test $p = {levene_p:.4f}}$ ({'Homogeneity of variance met' if levene_p > 0.05 else 'Variance heterogeneity detected'}})"

                with st.expander("🔍 Pre-flight Statistical Assumptions Diagnostics"):
                    st.write(f"- **Group 1 ({g_keys[0]}}) Normality:** {norm_msg1}}")
                    st.write(f"- **Group 2 ({g_keys[1]}}) Normality:** {norm_msg2}}")
                    st.write(f"- **Variance Homogeneity:** {homog_msg}}")
                    fig_box = px.box(sub_df, x=g, y=v, points="all", title=f"Group Comparison: {v}} by {g}}")
                    st.plotly_chart(fig_box, use_container_width=True)

                if st.button("▶️ Compute Independent t-Test", type="primary", key="run_ttest"):
                    equal_var = levene_p > 0.05
                    stat_val, p_val = stats.ttest_ind(g1, g2, equal_var=equal_var)

                    n1, n2 = len(g1), len(g2)
                    s1, s2 = np.std(g1, ddof=1), np.std(g2, ddof=1)
                    pooled_sd = np.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2)) if (n1 + n2 - 2) > 0 else 1.0
                    cohens_d = (np.mean(g1) - np.mean(g2)) / pooled_sd if pooled_sd > 0 else 0.0

                    se_d = np.sqrt((n1 + n2) / (n1 * n2) + (cohens_d ** 2) / (2 * (n1 + n2)))
                    d_ci = (cohens_d - 1.96 * se_d, cohens_d + 1.96 * se_d)

                    col_m1, col_m2, col_m3 = st.columns(3)
                    col_m1.metric("t-Statistic", f"{stat_val:.4f}}")
                    col_m2.metric("P-Value", f"{p_val:.6f}}")
                    col_m3.metric("Cohen's d", f"{cohens_d:.4f}}", delta=f"95% CI [{d_ci[0]:.3f}}, {d_ci[1]:.3f}}]")

                    warning = None if equal_var else "Equal variance assumption violated; Welch's t-test calculated."
                    st.markdown(generate_ai_interpretation("Independent t-Test", p_val, effect=cohens_d, effect_label="Cohen's d", assumption_warning=warning))
                    log_test_result(f"Independent t-Test ({v}} by {g}})", p_val, "Cohen's d", cohens_d)
        else:
            st.info("Requires at least one binary categorical feature and one continuous numeric feature.")

    elif test == "Paired t-Test":
        if len(numeric_cols) >= 2:
            c1, c2 = st.columns(2)
            before = c1.selectbox("Baseline Measure (Time 1)", numeric_cols, key="pair_before")
            after = c2.selectbox("Post-Measure (Time 2)", [c for c in numeric_cols if c != before], key="pair_after")

            clean_df = df[[before, after]].dropna()
            diffs = clean_df[after] - clean_df[before]

            _, diff_norm_msg = check_normality_shapiro(diffs)
            with st.expander("🔍 Pre-flight Statistical Assumptions"):
                st.write(f"- **Differences Distribution Normality:** {diff_norm_msg}}")
                st.plotly_chart(plot_qq(diffs, "Q-Q Plot of Differences"), use_container_width=True)

            if st.button("▶️ Compute Paired t-Test", type="primary", key="run_paired"):
                stat_val, p_val = stats.ttest_rel(clean_df[before], clean_df[after])
                cohens_d_paired = diffs.mean() / diffs.std(ddof=1) if diffs.std(ddof=1) > 0 else 0.0

                c1_m, c2_m, c3_m = st.columns(3)
                c1_m.metric("t-Statistic", f"{stat_val:.4f}}")
                c2_m.metric("P-Value", f"{p_val:.6f}}")
                c3_m.metric("Paired Cohen's d", f"{cohens_d_paired:.4f}}")

                st.markdown(generate_ai_interpretation("Paired t-Test", p_val, effect=cohens_d_paired, effect_label="Cohen's d (paired)"))
                log_test_result(f"Paired t-Test ({before}} vs {after}})", p_val, "Cohen's d", cohens_d_paired)
        else:
            st.info("Requires at least 2 continuous numeric variables.")

    elif test == "One-Way ANOVA":
        if cat_cols and numeric_cols:
            c1, c2 = st.columns(2)
            g = c1.selectbox("Factor Variable", cat_cols, key="anova_group")
            v = c2.selectbox("Dependent Measure", numeric_cols, key="anova_val")

            if st.button("▶️ Compute One-Way ANOVA", type="primary", key="run_anova"):
                sub_df = df[[g, v]].dropna()
                groups = [x[v].values for _, x in sub_df.groupby(g)]
                if len(groups) >= 2:
                    f_val, p_val = stats.f_oneway(*groups)
                    k = len(groups)
                    n = sum(len(gr) for gr in groups)
                    eta_sq = (f_val * (k - 1)) / (f_val * (k - 1) + (n - k)) if (n - k) > 0 and (f_val * (k - 1) + (n - k)) > 0 else 0.0

                    c1_m, c2_m, c3_m = st.columns(3)
                    c1_m.metric("F-Statistic", f"{f_val:.4f}}")
                    c2_m.metric("P-Value", f"{p_val:.6f}}")
                    c3_m.metric("Eta-Squared (η²)", f"{eta_sq:.4f}}")

                    st.markdown(generate_ai_interpretation("One-Way ANOVA", p_val, effect=eta_sq, effect_label="Eta-Squared (η²)"))
                    log_test_result(f"One-Way ANOVA ({v}} by {g}})", p_val, "Eta-Squared", eta_sq)

                    if p_val < 0.05 and STATSMODELS_AVAILABLE:
                        st.markdown("#### Tukey HSD Post-Hoc Pairwise Comparisons")
                        tukey = pairwise_tukeyhsd(endog=sub_df[v], groups=sub_df[g], alpha=0.05)
                        tukey_df = pd.DataFrame(data=tukey._results_table.data[1:], columns=tukey._results_table.data[0])
                        st.dataframe(tukey_df, use_container_width=True, hide_index=True)
        else:
            st.info("Requires continuous dependent variable and categorical factor.")

    elif test == "Two-Way ANOVA":
        if len(cat_cols) >= 2 and numeric_cols and STATSMODELS_AVAILABLE:
            f1 = st.selectbox("Factor 1", cat_cols, key="twoway_f1")
            f2 = st.selectbox("Factor 2", [c for c in cat_cols if c != f1], key="twoway_f2")
            dep = st.selectbox("Dependent Measure", numeric_cols, key="twoway_dep")

            if st.button("▶️ Compute Two-Way ANOVA", type="primary", key="run_twoway"):
                try:
                    clean_df = df[[f1, f2, dep]].dropna()
                    model = ols(f"{dep}} ~ C({f1}}) * C({f2}})", data=clean_df).fit()
                    anova_table = sm.stats.anova_lm(model, typ=2)

                    ss_resid = anova_table.loc["Residual", "sum_sq"]
                    breakdown = []
                    for term in anova_table.index:
                        if term == "Residual":
                            continue
                        ss_term = anova_table.loc[term, "sum_sq"]
                        partial_eta = ss_term / (ss_term + ss_resid) if (ss_term + ss_resid) > 0 else np.nan
                        p_term = anova_table.loc[term, "PR(>F)"]
                        breakdown.append({
                            "Term": term,
                            "F-Value": anova_table.loc[term, "F"],
                            "P-Value": p_term,
                            "Partial η²": partial_eta
                        })
                        log_test_result(f"Two-Way ANOVA — {term}} ({dep}})", p_term, "Partial η²", partial_eta)

                    breakdown_df = pd.DataFrame(breakdown)
                    st.markdown("#### Factor Effect Decomposition Table")
                    st.dataframe(breakdown_df, use_container_width=True, hide_index=True)
                except Exception as e:
                    st.error(f"Computation failure in Two-Way ANOVA: {e}}")
        else:
            st.info("Requires two categorical factors and one numeric dependent feature.")

    elif test == "Pearson Correlation":
        if len(numeric_cols) >= 2:
            c1, c2 = st.columns(2)
            v1 = c1.selectbox("Variable X", numeric_cols, key="corr_v1")
            v2 = c2.selectbox("Variable Y", [c for c in numeric_cols if c != v1], key="corr_v2")

            if st.button("▶️ Compute Pearson Correlation", type="primary", key="run_corr"):
                clean = df[[v1, v2]].dropna()
                r, p = stats.pearsonr(clean[v1], clean[v2])
                n = len(clean)

                # Fisher z-transformation for CI
                if abs(r) < 1.0 and n > 3:
                    z = np.arctanh(r)
                    se = 1.0 / np.sqrt(n - 3)
                    z_lo, z_hi = z - 1.96 * se, z + 1.96 * se
                    r_lo, r_hi = np.tanh(z_lo), np.tanh(z_hi)
                else:
                    r_lo, r_hi = r, r

                c1_m, c2_m = st.columns(2)
                c1_m.metric("Pearson r", f"{r:.4f}}", delta=f"95% CI [{r_lo:.3f}}, {r_hi:.3f}}]")
                c2_m.metric("P-Value", f"{p:.6f}}")

                fig_scat = px.scatter(clean, x=v1, y=v2, trendline="ols", title=f"Scatter plot: {v1}} vs {v2}}")
                st.plotly_chart(fig_scat, use_container_width=True)

                st.markdown(generate_ai_interpretation("Pearson Correlation", p, effect=r, effect_label="Pearson r"))
                log_test_result(f"Pearson Correlation ({v1}} vs {v2}})", p, "r", r)
        else:
            st.info("Requires at least 2 numeric variables.")

    elif test == "Linear Regression":
        if len(numeric_cols) >= 2 and STATSMODELS_AVAILABLE:
            target = st.selectbox("Dependent Target Variable (Y)", numeric_cols, key="reg_target")
            features = st.multiselect("Predictor Variables (X)", [c for c in numeric_cols if c != target], key="reg_feats")

            if features and st.button("▶️ Fit Linear Model", type="primary", key="run_reg"):
                try:
                    clean = df[[target] + features].dropna()
                    X = sm.add_constant(clean[features])
                    y = clean[target]
                    model = sm.OLS(y, X).fit()

                    st.code(str(model.summary()), language="text")

                    r_sq = model.rsquared
                    adj_r_sq = model.rsquared_adj
                    f_p = model.f_pvalue

                    c1_m, c2_m = st.columns(2)
                    c1_m.metric("R-Squared (R²)", f"{r_sq:.4f}}")
                    c2_m.metric("Adjusted R²", f"{adj_r_sq:.4f}}")

                    st.markdown(generate_ai_interpretation("Multiple OLS Regression", f_p, effect=r_sq, effect_label="R²"))
                    log_test_result(f"OLS Regression ({target}} ~ {'+'.join(features)}})", f_p, "R²", r_sq)
                except Exception as e:
                    st.error(f"Regression estimation error: {e}}")
        else:
            st.info("Requires at least 2 numeric features.")


def render_nonparam_tests(df: pd.DataFrame):
    section_header("Non-Parametric Tests", "Distribution-free rank-based tests and categorical association analysis.")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    binary_cats = [c for c in cat_cols if df[c].dropna().nunique() == 2]

    test = st.selectbox("Select Non-Parametric Model", [
        "Mann-Whitney U", "Kruskal-Wallis H", "Wilcoxon Signed-Rank",
        "Spearman Correlation", "Chi-Square Test", "Fisher's Exact Test", "McNemar's Test",
    ], key="nonparam_test_sel")

    if test == "Mann-Whitney U":
        if binary_cats and numeric_cols:
            g = st.selectbox("Grouping Variable (2 groups)", binary_cats, key="mw_group")
            v = st.selectbox("Test Variable", numeric_cols, key="mw_val")

            if st.button("▶️ Compute Mann-Whitney U", type="primary", key="run_mw"):
                sub = df[[g, v]].dropna()
                groups = [x[v].values for _, x in sub.groupby(g)]
                if len(groups) == 2:
                    stat_val, p_val = stats.mannwhitneyu(groups[0], groups[1])
                    n1, n2 = len(groups[0]), len(groups[1])
                    rank_biserial = 1 - (2 * stat_val) / (n1 * n2) if (n1 * n2) > 0 else 0.0

                    c1_m, c2_m, c3_m = st.columns(3)
                    c1_m.metric("U-Statistic", f"{stat_val:.4f}}")
                    c2_m.metric("P-Value", f"{p_val:.6f}}")
                    c3_m.metric("Rank-Biserial r", f"{rank_biserial:.4f}}")

                    st.markdown(generate_ai_interpretation("Mann-Whitney U", p_val, effect=rank_biserial, effect_label="Rank-Biserial r"))
                    log_test_result(f"Mann-Whitney U ({v}} by {g}})", p_val, "Rank-Biserial r", rank_biserial)
        else:
            st.info("Requires continuous numeric feature and a binary categorical group.")

    elif test == "Kruskal-Wallis H":
        if cat_cols and numeric_cols:
            g = st.selectbox("Factor Variable", cat_cols, key="kw_group")
            v = st.selectbox("Test Measure", numeric_cols, key="kw_val")

            if st.button("▶️ Compute Kruskal-Wallis H", type="primary", key="run_kw"):
                sub = df[[g, v]].dropna()
                groups = [x[v].values for _, x in sub.groupby(g)]
                if len(groups) >= 2:
                    stat_val, p_val = stats.kruskal(*groups)
                    k = len(groups)
                    n = sum(len(gr) for gr in groups)
                    eta_sq_h = (stat_val - k + 1) / (n - k) if (n - k) > 0 else np.nan

                    c1_m, c2_m, c3_m = st.columns(3)
                    c1_m.metric("H-Statistic", f"{stat_val:.4f}}")
                    c2_m.metric("P-Value", f"{p_val:.6f}}")
                    c3_m.metric("Eta-Squared (H)", f"{eta_sq_h:.4f}}")

                    st.markdown(generate_ai_interpretation("Kruskal-Wallis H", p_val, effect=eta_sq_h, effect_label="Eta-Squared (H)"))
                    log_test_result(f"Kruskal-Wallis H ({v}} by {g}})", p_val, "Eta-Squared (H)", eta_sq_h)
        else:
            st.info("Requires categorical variable and numeric measure.")

    elif test == "Wilcoxon Signed-Rank":
        if len(numeric_cols) >= 2:
            b = st.selectbox("Measure 1", numeric_cols, key="wx_before")
            a = st.selectbox("Measure 2", [c for c in numeric_cols if c != b], key="wx_after")

            if st.button("▶️ Compute Wilcoxon Test", type="primary", key="run_wx"):
                clean = df[[b, a]].dropna()
                stat_val, p_val = stats.wilcoxon(clean[b], clean[a])

                c1_m, c2_m = st.columns(2)
                c1_m.metric("W-Statistic", f"{stat_val:.4f}}")
                c2_m.metric("P-Value", f"{p_val:.6f}}")

                st.markdown(generate_ai_interpretation("Wilcoxon Signed-Rank", p_val))
                log_test_result(f"Wilcoxon Signed-Rank ({b}} vs {a}})", p_val)
        else:
            st.info("Requires 2 paired continuous variables.")

    elif test == "Chi-Square Test":
        if len(cat_cols) >= 2:
            v1 = st.selectbox("Categorical Feature 1", cat_cols, key="chi_v1")
            v2 = st.selectbox("Categorical Feature 2", [c for c in cat_cols if c != v1], key="chi_v2")

            if st.button("▶️ Compute Chi-Square Test", type="primary", key="run_chi"):
                ct = pd.crosstab(df[v1], df[v2])
                chi2, p, dof, ex = stats.chi2_contingency(ct)
                n = ct.values.sum()
                min_dim = min(ct.shape[0] - 1, ct.shape[1] - 1)
                cramers_v = np.sqrt(chi2 / (n * min_dim)) if min_dim > 0 and n > 0 else 0.0

                c1_m, c2_m, c3_m = st.columns(3)
                c1_m.metric("Chi-Square (χ²)", f"{chi2:.4f}}")
                c2_m.metric("P-Value", f"{p:.6f}}")
                c3_m.metric("Cramér's V", f"{cramers_v:.4f}}")

                st.dataframe(ct, use_container_width=True)
                log_test_result(f"Chi-Square ({v1}} vs {v2}})", p, "Cramér's V", cramers_v)
        else:
            st.info("Requires at least 2 categorical variables.")

    elif test == "Spearman Correlation":
        if len(numeric_cols) >= 2:
            v1 = st.selectbox("Variable X", numeric_cols, key="sp_v1")
            v2 = st.selectbox("Variable Y", [c for c in numeric_cols if c != v1], key="sp_v2")

            if st.button("▶️ Compute Spearman ρ", type="primary", key="run_sp"):
                clean = df[[v1, v2]].dropna()
                rho, p = stats.spearmanr(clean[v1], clean[v2])

                c1_m, c2_m = st.columns(2)
                c1_m.metric("Spearman ρ", f"{rho:.4f}}")
                c2_m.metric("P-Value", f"{p:.6f}}")

                st.markdown(generate_ai_interpretation("Spearman Correlation", p, effect=rho, effect_label="Spearman ρ"))
                log_test_result(f"Spearman Correlation ({v1}} vs {v2}})", p, "ρ", rho)
        else:
            st.info("Requires at least 2 numeric variables.")

    elif test == "Fisher's Exact Test":
        if len(cat_cols) >= 2:
            v1 = st.selectbox("Binary Feature 1", cat_cols, key="fe_v1")
            v2 = st.selectbox("Binary Feature 2", [c for c in cat_cols if c != v1], key="fe_v2")

            if st.button("▶️ Compute Fisher's Exact Test", type="primary", key="run_fe"):
                ct = pd.crosstab(df[v1], df[v2])
                if ct.shape == (2, 2):
                    or_val, p_val = stats.fisher_exact(ct)
                    c1_m, c2_m = st.columns(2)
                    c1_m.metric("Odds Ratio", f"{or_val:.4f}}")
                    c2_m.metric("P-Value", f"{p_val:.6f}}")

                    st.markdown(generate_ai_interpretation("Fisher's Exact Test", p_val, effect=or_val, effect_label="Odds Ratio"))
                    log_test_result(f"Fisher's Exact ({v1}} vs {v2}})", p_val, "Odds Ratio", or_val)
                else:
                    st.error("Fisher's Exact Test strictly requires a 2x2 contingency table matrix.")
        else:
            st.info("Requires 2 categorical variables.")

    elif test == "McNemar's Test":
        available = binary_cats + list(df.select_dtypes(include=["bool"]).columns)
        if len(available) >= 2:
            b = st.selectbox("Pre-State", available, key="mn_before")
            a = st.selectbox("Post-State", [c for c in available if c != b], key="mn_after")

            if st.button("▶️ Compute McNemar's Test", type="primary", key="run_mn"):
                ct = pd.crosstab(df[b], df[a])
                if ct.shape == (2, 2):
                    res = stats.mcnemar(ct, exact=True)
                    c1_m, c2_m = st.columns(2)
                    c1_m.metric("Statistic", f"{res.statistic:.4f}}")
                    c2_m.metric("P-Value", f"{res.pvalue:.6f}}")

                    st.markdown(generate_ai_interpretation("McNemar's Test", res.pvalue))
                    log_test_result(f"McNemar's Test ({b}} vs {a}})", res.pvalue)
                else:
                    st.error("McNemar's Test requires paired 2x2 binary response data.")
        else:
            st.info("Requires 2 binary response features.")


def render_sensitivity_tab(df: pd.DataFrame):
    section_header("🔬 Specification-Curve Sensitivity Analysis", "Evaluate point estimate stability across multiple model designs, outlier filters, and covariate sets.")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if len(numeric_cols) < 2:
        st.info("Requires at least 2 numeric features to construct specification curves.")
        return

    c1, c2, c3 = st.columns(3)
    x_var = c1.selectbox("Independent Variable (X)", numeric_cols, index=0, key="spec_x")
    y_var = c2.selectbox("Dependent Variable (Y)", [c for c in numeric_cols if c != x_var], index=0, key="spec_y")
    control_vars = c3.multiselect("Control Variables (Covariates)", [c for c in numeric_cols if c not in [x_var, y_var]], key="spec_controls")

    if st.button("🚀 Run Specification-Curve Engine", type="primary", key="run_spec_curve"):
        clean_df = df[[x_var, y_var] + control_vars].dropna()
        if len(clean_df) < 10:
            st.error("Insufficient observation count ($N < 10$) for sensitivity testing.")
            return

        specifications = []

        # Raw Pearson
        r, p = stats.pearsonr(clean_df[x_var], clean_df[y_var])
        specifications.append({"Specification": "Raw - Pearson", "Estimate": r, "P-Value": p, "Type": "Parametric"})

        # Spearman Rank
        rho, p_sp = stats.spearmanr(clean_df[x_var], clean_df[y_var])
        specifications.append({"Specification": "Raw - Spearman Rank", "Estimate": rho, "P-Value": p_sp, "Type": "Non-Parametric"})

        # IQR Trimmed
        q1_x, q3_x = np.percentile(clean_df[x_var], 25), np.percentile(clean_df[x_var], 75)
        iqr_x = q3_x - q1_x
        q1_y, q3_y = np.percentile(clean_df[y_var], 25), np.percentile(clean_df[y_var], 75)
        iqr_y = q3_y - q1_y

        mask = clean_df[x_var].between(q1_x - 1.5 * iqr_x, q3_x + 1.5 * iqr_x) & clean_df[y_var].between(q1_y - 1.5 * iqr_y, q3_y + 1.5 * iqr_y)
        if mask.sum() >= 5:
            r_tr, p_tr = stats.pearsonr(clean_df.loc[mask, x_var], clean_df.loc[mask, y_var])
            specifications.append({"Specification": "1.5x IQR Outlier Trimmed", "Estimate": r_tr, "P-Value": p_tr, "Type": "Robust"})

        # Multivariate Controls
        if control_vars and STATSMODELS_AVAILABLE:
            for ctrl in control_vars:
                X_ctrl = sm.add_constant(clean_df[[ctrl]])
                res_x = sm.OLS(clean_df[x_var], X_ctrl).fit().resid
                res_y = sm.OLS(clean_df[y_var], X_ctrl).fit().resid
                r_p, p_p = stats.pearsonr(res_x, res_y)
                specifications.append({"Specification": f"Partial Corr (Controlling for {ctrl}})", "Estimate": r_p, "P-Value": p_p, "Type": "Multivariate"})

        res_df = pd.DataFrame(specifications)
        res_df["Significant (p < .05)"] = res_df["P-Value"] < 0.05
        res_df = res_df.sort_values(by="Estimate").reset_index(drop=True)

        sig_ratio = res_df["Significant (p < .05)"].mean() * 100
        mean_effect = res_df["Estimate"].mean()

        c1_m, c2_m = st.columns(2)
        c1_m.metric("Specification Consistency", f"{sig_ratio:.1f}}% Significant")
        c2_m.metric("Mean Effect Size Across Curves", f"{mean_effect:.4f}}")

        fig_spec = px.bar(
            res_df, 
            x="Specification", 
            y="Estimate", 
            color="Significant (p < .05)", 
            title="Specification Curve: Point Estimates across Analytical Choices",
            color_discrete_map={True: "#2ca02c", False: "#d62728"}
        )
        st.plotly_chart(fig_spec, use_container_width=True)

        st.dataframe(res_df, use_container_width=True, hide_index=True)
        render_export_buttons(res_df, base_name=f"specification_curve_{x_var}}_{y_var}}")


def render_power_tab():
    section_header("⚡ Statistical Power & Sample Size Estimator", "Prospective power estimation and minimal detectable effect size (MDE) calculations.")

    if not STATSMODELS_AVAILABLE:
        st.error("Statsmodels dependency unavailable for power calculations.")
        return

    analysis_type = st.radio("Power Mode", ["Sample Size Determination", "Post-Hoc Power Calculation"], horizontal=True)
    power_analysis = TTestIndPower()

    if analysis_type == "Sample Size Determination":
        c1, c2, c3 = st.columns(3)
        effect_size = c1.number_input("Target Effect Size (Cohen's d)", min_value=0.1, max_value=2.0, value=0.5, step=0.05)
        alpha = c2.number_input("Significance Threshold (α)", min_value=0.001, max_value=0.10, value=0.05, step=0.005)
        power = c3.number_input("Target Power (1 - β)", min_value=0.5, max_value=0.99, value=0.80, step=0.05)

        required_n = power_analysis.solve_power(effect_size=effect_size, alpha=alpha, power=power, ratio=1.0)
        st.metric("Required N Per Group", f"{int(np.ceil(required_n))}}")

    else:
        c1, c2, c3 = st.columns(3)
        effect_size = c1.number_input("Observed Effect Size (Cohen's d)", min_value=0.01, max_value=2.0, value=0.4, step=0.05)
        n_obs = c2.number_input("Sample Size Per Group", min_value=5, max_value=10000, value=50, step=5)
        alpha = c3.number_input("Alpha (α)", min_value=0.001, max_value=0.10, value=0.05, step=0.005)

        achieved_power = power_analysis.solve_power(effect_size=effect_size, nobs1=n_obs, alpha=alpha, ratio=1.0)
        st.metric("Achieved Statistical Power", f"{achieved_power * 100:.2f}}%")


def main():
    setup_page("Statistics Studio", "📊", initial_sidebar_state="expanded")

    from modules.user_preferences import render_readability_fix, render_accent_color_css
    render_readability_fix()
    render_accent_color_css()

    hero_card(
        "📊 Statistics Studio",
        "Perform statistical analyses, assumption validation, power analysis, and specification curves.",
        badge_text="STATISTICS STUDIO • ENTERPRISE TIER",
    )

    render_dataset_context_banner()

    df = get_df()

    tabs = st.tabs([
        "📈 Parametric Tests",
        "📉 Non-Parametric Tests",
        "🔬 Sensitivity Analysis",
        "⚡ Power Analysis",
        "📋 Multiple-Comparisons Ledger",
    ])

    with tabs[0]:
        render_param_tests(df)
    with tabs[1]:
        render_nonparam_tests(df)
    with tabs[2]:
        render_sensitivity_tab(df)
    with tabs[3]:
        render_power_tab()
    with tabs[4]:
        render_ledger_tab()

    render_standard_footer("STATISTICS STUDIO")


if __name__ == "__main__":
    main()
