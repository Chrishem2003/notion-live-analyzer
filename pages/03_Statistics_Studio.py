import streamlit as st
st.set_page_config(page_title="Statistics Studio", page_icon="📈", layout="wide")

import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
"""
 Statistics Studio â€” Consolidated Statistical Analysis Hub (Premium)
Pre-flight assumption validation, comprehensive effect sizes, a genuine specification-curve
sensitivity analysis, a session-wide multiple-comparisons ledger, causal econometrics, interactive
Bayesian updating, exact power analysis, and exportable methodology reports.
"""

import numpy as np
import pandas as pd
import scipy.stats as stats
import streamlit as st

try:
    import statsmodels.api as sm
    from statsmodels.formula.api import ols
    from statsmodels.stats.power import TTestIndPower
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


def get_df():
    df = get_active_dataframe()
    if df is None:
        np.random.seed(42)
        return pd.DataFrame({
            "CategoryGroup": np.random.choice(["Group A", "Group B", "Group C"], 150),
            "BinaryGroup": np.random.choice(["Yes", "No"], 150),
            "Score_Numeric": np.random.normal(75, 12, 150),
            "Metric_Value": np.random.normal(50, 8, 150),
            "Predictor_X": np.random.normal(30, 5, 150),
            "Binary_Outcome": np.random.choice([0, 1], 150),
            "Condition_Before": np.random.normal(60, 10, 150),
            "Condition_After": np.random.normal(65, 10, 150),
        })
    return df


def generate_ai_interpretation(test_name, p_value, effect=None, effect_label="Effect Size", assumption_warning=None):
    sig = p_value < 0.05
    narrative = (
        f"> **Executive Summary:** The **{test_name}** result is "
        f"{'**statistically significant** (p < 0.05)' if sig else 'not statistically significant (p â‰¥ 0.05)'} "
        f"with p = **{p_value:.5f}**."
    )
    narrative += "\n> **Key Takeaway:** " + ("Reject $H_0$ â€” sufficient evidence of a reliable effect." if sig else "Fail to reject $H_0$ â€” insufficient evidence of an effect.")
    if effect is not None:
        narrative += f"\n> **{effect_label}:** `{effect:.4f}`"
    if assumption_warning:
        narrative += f"\n> **âš  Assumption Notice:** {assumption_warning}"
    return narrative


def check_normality_shapiro(series):
    clean = series.dropna()
    if len(clean) < 3:
        return True, "Insufficient data for normality check."
    if len(clean) > 5000:
        clean = clean.sample(5000, random_state=42)
    stat, p = stats.shapiro(clean)
    is_normal = p > 0.05
    msg = f"Shapiro-Wilk p = {p:.4f} ({'Normal distribution assumed' if is_normal else 'Departure from normality detected'})"
    return is_normal, msg


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Session-wide multiple-comparisons ledger
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def log_test_result(test_name, p_value, effect_label=None, effect_value=None):
    if "stats_test_ledger" not in st.session_state:
        st.session_state["stats_test_ledger"] = []
    st.session_state["stats_test_ledger"].append({
        "Test": test_name,
        "P-Value (Raw)": float(p_value),
        "Effect Label": effect_label or "â€”",
        "Effect Value": float(effect_value) if effect_value is not None else None,
        "Timestamp": pd.Timestamp.now().strftime("%H:%M:%S"),
    })


def benjamini_hochberg(pvals: np.ndarray) -> np.ndarray:
    """Standard BH step-up procedure. Returns FDR-adjusted p-values, monotonic and clipped to [0,1]."""
    m = len(pvals)
    order = np.argsort(pvals)
    ranked = np.asarray(pvals)[order]
    adj = ranked * m / (np.arange(m) + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    adj = np.clip(adj, 0, 1)
    out = np.empty(m)
    out[order] = adj
    return out


def render_ledger_tab():
    section_header(" Multiple-Comparisons Ledger", "Every hypothesis test you run this session, with Bonferroni and Benjamini-Hochberg FDR correction applied across the whole set.")

    ledger = st.session_state.get("stats_test_ledger", [])
    if not ledger:
        st.info("â„¹ No tests logged yet this session. Run any test in the Parametric, Non-Parametric, or Advanced tabs â€” each result is automatically added here.")
        return

    ledger_df = pd.DataFrame(ledger)
    m = len(ledger_df)
    raw_p = ledger_df["P-Value (Raw)"].values
    ledger_df["Bonferroni p"] = np.clip(raw_p * m, 0, 1)
    ledger_df["BH-FDR p"] = benjamini_hochberg(raw_p)
    ledger_df["Significant (raw Î±=.05)"] = raw_p < 0.05
    ledger_df["Significant (Bonferroni)"] = ledger_df["Bonferroni p"] < 0.05
    ledger_df["Significant (BH-FDR)"] = ledger_df["BH-FDR p"] < 0.05

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tests Logged", m)
    c2.metric("Significant (raw Î±=.05)", int(ledger_df["Significant (raw Î±=.05)"].sum()))
    c3.metric("Survive Bonferroni", int(ledger_df["Significant (Bonferroni)"].sum()))
    c4.metric("Survive BH-FDR", int(ledger_df["Significant (BH-FDR)"].sum()))

    if int(ledger_df["Significant (raw Î±=.05)"].sum()) > int(ledger_df["Significant (BH-FDR)"].sum()):
        st.warning("âš  Some results that look significant at the raw Î±=.05 threshold do **not** survive correction for multiple comparisons across this session's tests. Treat those with caution.")

    st.dataframe(ledger_df, use_container_width=True, hide_index=True)
    render_export_buttons(ledger_df, base_name="multiple_comparisons_ledger")

    if st.button(" Clear Ledger", key="clear_ledger"):
        st.session_state["stats_test_ledger"] = []
        st.rerun()


def render_param_tests(df):
    section_header("Parametric Hypothesis Tests", "t-tests, ANOVA, correlation, and regression with automated assumption diagnostics.")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    binary_cats = [c for c in cat_cols if df[c].dropna().nunique() == 2]

    test = st.selectbox("Select Parametric Test", [
        "Independent t-Test", "Paired t-Test", "One-Way ANOVA", "Two-Way ANOVA",
        "Pearson Correlation", "Linear Regression",
    ], key="param_test_sel")

    if test == "Independent t-Test":
        if binary_cats and numeric_cols:
            c1, c2 = st.columns(2)
            g = c1.selectbox("Group variable (2 groups)", binary_cats, key="t_group")
            v = c2.selectbox("Test variable", numeric_cols, key="t_val")

            groups = [x[v].dropna().values for _, x in df.groupby(g)]
            if len(groups) == 2:
                _, norm_msg1 = check_normality_shapiro(pd.Series(groups[0]))
                _, norm_msg2 = check_normality_shapiro(pd.Series(groups[1]))
                levene_stat, levene_p = stats.levene(groups[0], groups[1])
                homog_msg = f"Levene's Test p = {levene_p:.4f} ({'Homogeneity of variance met' if levene_p > 0.05 else 'Variance heterogeneity detected'})"

                with st.expander(" Pre-flight Statistical Assumptions"):
                    st.write(f"- Group 1 Normality: {norm_msg1}")
                    st.write(f"- Group 2 Normality: {norm_msg2}")
                    st.write(f"- Variance Homogeneity: {homog_msg}")

            if st.button("â–¶ Run t-Test", type="primary", key="run_ttest"):
                if len(groups) == 2:
                    equal_var = levene_p > 0.05
                    stat_val, p_val = stats.ttest_ind(groups[0], groups[1], equal_var=equal_var)

                    n1, n2 = len(groups[0]), len(groups[1])
                    s1, s2 = np.std(groups[0], ddof=1), np.std(groups[1], ddof=1)
                    pooled_sd = np.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2)) if (n1 + n2 - 2) > 0 else 1.0
                    cohens_d = (np.mean(groups[0]) - np.mean(groups[1])) / pooled_sd if pooled_sd > 0 else 0.0

                    se_d = np.sqrt((n1 + n2) / (n1 * n2) + (cohens_d ** 2) / (2 * (n1 + n2)))
                    d_ci = (cohens_d - 1.96 * se_d, cohens_d + 1.96 * se_d)

                    col_m1, col_m2 = st.columns(2)
                    col_m1.metric("t-Statistic", f"{stat_val:.4f}")
                    col_m2.metric("P-Value", f"{p_val:.6f}")
                    st.metric("Cohen's d Effect Size", f"{cohens_d:.4f}", delta=f"95% CI [{d_ci[0]:.3f}, {d_ci[1]:.3f}]")

                    warning = None if equal_var else "Equal variance assumption violated; Welch's t-test variant applied."
                    st.markdown(generate_ai_interpretation("Independent t-Test", p_val, effect=cohens_d, effect_label="Cohen's d", assumption_warning=warning))
                    log_test_result(f"Independent t-Test ({v} by {g})", p_val, "Cohen's d", cohens_d)
        else:
            st.info("Need a binary categorical + numeric variable.")

    elif test == "Paired t-Test":
        if len(numeric_cols) >= 2:
            c1, c2 = st.columns(2)
            before = c1.selectbox("Before measure", numeric_cols, key="pair_before")
            after = c2.selectbox("After measure", [c for c in numeric_cols if c != before], key="pair_after")

            diffs = df[after].dropna() - df[before].dropna()
            _, diff_norm_msg = check_normality_shapiro(diffs)
            with st.expander(" Pre-flight Statistical Assumptions"):
                st.write(f"- Difference Score Normality: {diff_norm_msg}")

            if st.button("â–¶ Run Paired t-Test", type="primary", key="run_paired"):
                clean_df = df[[before, after]].dropna()
                stat_val, p_val = stats.ttest_rel(clean_df[before], clean_df[after])
                diff_series = clean_df[after] - clean_df[before]
                cohens_d_paired = diff_series.mean() / diff_series.std(ddof=1) if diff_series.std(ddof=1) > 0 else 0.0

                st.metric("t-Statistic", f"{stat_val:.4f}")
                st.metric("P-Value", f"{p_val:.6f}")
                st.metric("Cohen's d (Paired)", f"{cohens_d_paired:.4f}")
                st.markdown(generate_ai_interpretation("Paired t-Test", p_val, effect=cohens_d_paired, effect_label="Cohen's d (paired)"))
                log_test_result(f"Paired t-Test ({before} vs {after})", p_val, "Cohen's d", cohens_d_paired)
        else:
            st.info("Need at least 2 numeric variables.")

    elif test == "One-Way ANOVA":
        if cat_cols and numeric_cols:
            c1, c2 = st.columns(2)
            g = c1.selectbox("Factor", cat_cols, key="anova_group")
            v = c2.selectbox("Dependent variable", numeric_cols, key="anova_val")
            if st.button("â–¶ Run One-Way ANOVA", type="primary", key="run_anova"):
                groups = [x[v].dropna().values for _, x in df.groupby(g)]
                if len(groups) >= 2:
                    f_val, p_val = stats.f_oneway(*groups)
                    k = len(groups)
                    n = sum(len(gr) for gr in groups)
                    eta_sq = (f_val * (k - 1)) / (f_val * (k - 1) + (n - k)) if (n - k) > 0 else np.nan

                    c1.metric("F-Statistic", f"{f_val:.4f}")
                    c2.metric("P-Value", f"{p_val:.6f}")
                    st.metric("Eta-Squared (Î·Â²)", f"{eta_sq:.4f}", help="Proportion of variance in the outcome explained by group membership.")
                    st.markdown(generate_ai_interpretation("One-Way ANOVA", p_val, effect=eta_sq, effect_label="Eta-Squared (Î·Â²)"))
                    log_test_result(f"One-Way ANOVA ({v} by {g})", p_val, "Eta-Squared", eta_sq)
        else:
            st.info("Need a categorical + numeric variable.")

    elif test == "Two-Way ANOVA":
        if len(cat_cols) >= 2 and numeric_cols and STATSMODELS_AVAILABLE:
            f1 = st.selectbox("Factor 1", cat_cols, key="twoway_f1")
            f2 = st.selectbox("Factor 2", [c for c in cat_cols if c != f1], key="twoway_f2")
            dep = st.selectbox("Dependent", numeric_cols, key="twoway_dep")
            if st.button("â–¶ Run Two-Way ANOVA", type="primary", key="run_twoway"):
                try:
                    model = ols(f"{dep} ~ C({f1}) * C({f2})", data=df).fit()
                    anova_table = sm.stats.anova_lm(model, typ=2)
                    st.dataframe(anova_table, use_container_width=True)

                    ss_resid = anova_table.loc["Residual", "sum_sq"]
                    breakdown = []
                    for term in anova_table.index:
                        if term == "Residual":
                            continue
                        ss_term = anova_table.loc[term, "sum_sq"]
                        partial_eta = ss_term / (ss_term + ss_resid) if (ss_term + ss_resid) > 0 else np.nan
                        p_term = anova_table.loc[term, "PR(>F)"]
                        breakdown.append({"Term": term, "F": anova_table.loc[term, "F"], "P-Value": p_term, "Partial Î·Â²": partial_eta})
                        log_test_result(f"Two-Way ANOVA â€” {term} ({dep})", p_term, "Partial Î·Â²", partial_eta)

                    breakdown_df = pd.DataFrame(breakdown)
                    st.markdown("#### Per-Term Breakdown (including interaction)")
                    st.dataframe(breakdown_df, use_container_width=True, hide_index=True)

                    interaction_row = breakdown_df[breakdown_df["Term"].str.contains(":")]
                    if not interaction_row.empty:
                        interaction_p = interaction_row.iloc[0]["P-Value"]
                        if interaction_p < 0.05:
                            st.warning(f"âš  Significant interaction effect (p = {interaction_p:.5f}) â€” interpret the main effects of `{f1}` and `{f2}` with caution; their effect on `{dep}` depends on the level of the other factor.")
                        st.markdown(generate_ai_interpretation(f"Two-Way ANOVA Interaction ({f1}  {f2})", interaction_p, effect=interaction_row.iloc[0]["Partial Î·Â²"], effect_label="Partial Î·Â² (interaction)"))
                except Exception as e:
                    st.error(f"Two-Way ANOVA computation error: {e}")
        else:
            st.info("Need 2 categorical + 1 numeric variable and statsmodels installed.")

    elif test == "Pearson Correlation":
        if len(numeric_cols) >= 2:
            c1, c2 = st.columns(2)
            v1 = c1.selectbox("Variable 1", numeric_cols, key="corr_v1")
            v2 = c2.selectbox("Variable 2", [c for c in numeric_cols if c != v1], key="corr_v2")
            if st.button("â–¶ Run Correlation", type="primary", key="run_corr"):
                r, p = stats.pearsonr(df[v1].dropna(), df[v2].dropna())
                st.metric("Pearson r", f"{r:.4f}")
                st.metric("P-Value", f"{p:.6f}")
                st.markdown(generate_ai_interpretation("Pearson Correlation", p, effect=r, effect_label="Pearson r"))
                log_test_result(f"Pearson Correlation ({v1} vs {v2})", p, "r", r)
        else:
            st.info("Need at least 2 numeric variables.")

    elif test == "Linear Regression":
        if len(numeric_cols) >= 2 and STATSMODELS_AVAILABLE:
            target = st.selectbox("Target variable", numeric_cols, key="reg_target")
            features = st.multiselect("Predictors", [c for c in numeric_cols if c != target], key="reg_feats")
            if features and st.button("â–¶ Run Regression", type="primary", key="run_reg"):
                try:
                    X = sm.add_constant(df[features].dropna())
                    y = df.loc[X.index, target]
                    model = sm.OLS(y, X).fit()
                    st.text(str(model.summary()))

                    r_sq = model.rsquared
                    adj_r_sq = model.rsquared_adj
                    f_p = model.f_pvalue
                    st.metric("R-Squared", f"{r_sq:.4f}")
                    st.metric("Adjusted R-Squared", f"{adj_r_sq:.4f}")
                    st.markdown(generate_ai_interpretation("Multiple OLS Regression", f_p, effect=r_sq, effect_label="RÂ²"))
                    log_test_result(f"OLS Regression ({target} ~ {'+'.join(features)})", f_p, "RÂ²", r_sq)
                except Exception as e:
                    st.error(f"Regression error: {e}")
        else:
            st.info("Need at least 2 numeric variables and statsmodels.")


def render_nonparam_tests(df):
    section_header("Non-Parametric Tests", "Distribution-free hypothesis testing with exact test options.")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    binary_cats = [c for c in cat_cols if df[c].dropna().nunique() == 2]

    test = st.selectbox("Select Non-Parametric Test", [
        "Mann-Whitney U", "Kruskal-Wallis H", "Wilcoxon Signed-Rank",
        "Spearman Correlation", "Chi-Square Test", "Fisher's Exact Test", "McNemar's Test",
    ], key="nonparam_test_sel")

    if test == "Mann-Whitney U":
        if binary_cats and numeric_cols:
            g = st.selectbox("Group (2 groups)", binary_cats, key="mw_group")
            v = st.selectbox("Test variable", numeric_cols, key="mw_val")
            if st.button("â–¶ Run Mann-Whitney U", type="primary", key="run_mw"):
                groups = [x[v].dropna().values for _, x in df.groupby(g)]
                if len(groups) == 2:
                    stat_val, p_val = stats.mannwhitneyu(groups[0], groups[1])
                    n1, n2 = len(groups[0]), len(groups[1])
                    rank_biserial = 1 - (2 * stat_val) / (n1 * n2)
                    st.metric("U-Statistic", f"{stat_val:.4f}")
                    st.metric("P-Value", f"{p_val:.6f}")
                    st.metric("Rank-Biserial Correlation", f"{rank_biserial:.4f}")
                    st.markdown(generate_ai_interpretation("Mann-Whitney U", p_val, effect=rank_biserial, effect_label="Rank-Biserial r"))
                    log_test_result(f"Mann-Whitney U ({v} by {g})", p_val, "Rank-Biserial r", rank_biserial)
        else:
            st.info("Need binary categorical + numeric.")

    elif test == "Kruskal-Wallis H":
        if cat_cols and numeric_cols:
            g = st.selectbox("Group", cat_cols, key="kw_group")
            v = st.selectbox("Test variable", numeric_cols, key="kw_val")
            if st.button("â–¶ Run Kruskal-Wallis", type="primary", key="run_kw"):
                groups = [x[v].dropna().values for _, x in df.groupby(g)]
                stat_val, p_val = stats.kruskal(*groups)
                k = len(groups)
                n = sum(len(gr) for gr in groups)
                eta_sq_h = (stat_val - k + 1) / (n - k) if (n - k) > 0 else np.nan
                st.metric("H-Statistic", f"{stat_val:.4f}")
                st.metric("P-Value", f"{p_val:.6f}")
                st.metric("Eta-Squared (H)", f"{eta_sq_h:.4f}")
                st.markdown(generate_ai_interpretation("Kruskal-Wallis H", p_val, effect=eta_sq_h, effect_label="Eta-Squared (H)"))
                log_test_result(f"Kruskal-Wallis H ({v} by {g})", p_val, "Eta-Squared (H)", eta_sq_h)
        else:
            st.info("Need categorical + numeric.")

    elif test == "Wilcoxon Signed-Rank":
        if len(numeric_cols) >= 2:
            b = st.selectbox("Before", numeric_cols, key="wx_before")
            a = st.selectbox("After", [c for c in numeric_cols if c != b], key="wx_after")
            if st.button("â–¶ Run Wilcoxon", type="primary", key="run_wx"):
                stat_val, p_val = stats.wilcoxon(df[b].dropna(), df[a].dropna())
                st.metric("Statistic", f"{stat_val:.4f}")
                st.metric("P-Value", f"{p_val:.6f}")
                st.markdown(generate_ai_interpretation("Wilcoxon Signed-Rank", p_val))
                log_test_result(f"Wilcoxon Signed-Rank ({b} vs {a})", p_val)
        else:
            st.info("Need 2 numeric variables.")

    elif test == "Chi-Square Test":
        if len(cat_cols) >= 2:
            v1 = st.selectbox("Variable 1", cat_cols, key="chi_v1")
            v2 = st.selectbox("Variable 2", [c for c in cat_cols if c != v1], key="chi_v2")
            if st.button("â–¶ Run Chi-Square", type="primary", key="run_chi"):
                ct = pd.crosstab(df[v1], df[v2])
                chi2, p, dof, ex = stats.chi2_contingency(ct)
                n = ct.values.sum()
                min_dim = min(ct.shape[0] - 1, ct.shape[1] - 1)
                cramers_v = np.sqrt(chi2 / (n * min_dim)) if min_dim > 0 and n > 0 else np.nan

                st.metric("Chi-Square", f"{chi2:.4f}")
                st.metric("P-Value", f"{p:.6f}")
                st.metric("Cram V", f"{cramers_v:.4f}", help="0.1 small, 0.3 medium, 0.5+ large association.")

                low_exp = (ex < 5).sum()
                total_cells = ex.size
                warning = None
                if low_exp > 0:
                    warning = f"Expected frequency count: {low_exp}/{total_cells} cells have < 5 expected counts."
                    if ct.shape == (2, 2):
                        warning += " Consider Fisher's Exact Test instead â€” it doesn't rely on this asymptotic assumption."

                st.markdown(generate_ai_interpretation("Chi-Square Test of Independence", p, effect=cramers_v, effect_label="Cram V", assumption_warning=warning))
                st.dataframe(ct, use_container_width=True)
                log_test_result(f"Chi-Square ({v1} vs {v2})", p, "Cram V", cramers_v)
        else:
            st.info("Need 2 categorical variables.")

    elif test == "Spearman Correlation":
        if len(numeric_cols) >= 2:
            v1 = st.selectbox("Variable 1", numeric_cols, key="sp_v1")
            v2 = st.selectbox("Variable 2", [c for c in numeric_cols if c != v1], key="sp_v2")
            if st.button("â–¶ Run Spearman", type="primary", key="run_sp"):
                rho, p = stats.spearmanr(df[v1].dropna(), df[v2].dropna())
                st.metric("Spearman Ï", f"{rho:.4f}")
                st.metric("P-Value", f"{p:.6f}")
                st.markdown(generate_ai_interpretation("Spearman Correlation", p, effect=rho, effect_label="Spearman Ï"))
                log_test_result(f"Spearman Correlation ({v1} vs {v2})", p, "Ï", rho)
        else:
            st.info("Need 2 numeric variables.")

    elif test == "Fisher's Exact Test":
        if len(cat_cols) >= 2:
            v1 = st.selectbox("Variable 1", cat_cols, key="fe_v1")
            v2 = st.selectbox("Variable 2", [c for c in cat_cols if c != v1], key="fe_v2")
            if st.button("â–¶ Run Fisher's Exact", type="primary", key="run_fe"):
                ct = pd.crosstab(df[v1], df[v2])
                if ct.shape == (2, 2):
                    or_val, p_val = stats.fisher_exact(ct)
                    st.metric("Odds Ratio", f"{or_val:.4f}")
                    st.metric("P-Value", f"{p_val:.6f}")
                    st.markdown(generate_ai_interpretation("Fisher's Exact Test", p_val, effect=or_val, effect_label="Odds Ratio"))
                    log_test_result(f"Fisher's Exact ({v1} vs {v2})", p_val, "Odds Ratio", or_val)
                else:
                    st.error("Requires 2 table dimensions.")
        else:
            st.info("Need 2 categorical variables.")

    elif test == "McNemar's Test":
        available = binary_cats + list(df.select_dtypes(include=["bool"]).columns)
        if len(available) >= 2:
            b = st.selectbox("Before", available, key="mn_before")
            a = st.selectbox("After", [c for c in available if c != b], key="mn_after")
            if st.button("â–¶ Run McNemar", type="primary", key="run_mn"):
                ct = pd.crosstab(df[b], df[a])
                if ct.shape == (2, 2):
                    res = stats.mcnemar(ct, exact=True)
                    st.metric("Statistic", f"{res.statistic:.4f}")
                    st.metric("P-Value", f"{res.pvalue:.6f}")
                    st.markdown(generate_ai_interpretation("McNemar's Test", res.pvalue))
                    log_test_result(f"McNemar's Test ({b} vs {a})", res.pvalue)
                else:
                    st.error("Requires 2 binary table.")
        else:
            st.info("Need 2 binary categorical variables.")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Real specification-curve sensitivity analysis
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _iqr_clean_pair(x: pd.Series, y: pd.Series):
    def bounds(s):
        q1, q3 = np.percentile(s, 25), np.percentile(s, 75)
        iqr = q3 - q1
        return q1 - 1.5 * iqr, q3 + 1.5 * iqr

    xl, xh = bounds(x)
    yl, yh = bounds(y)
    mask = x.between(xl, xh) & y.between(yl, yh)
    return x[mask], y[mask]


def _winsorize(s: pd.Series, limits=(0.05, 0.05)):
    lo, hi = np.percentile(s, [limits[0] * 100, 100 - limits[1] * 100])
    return s.clip(lo, hi)


def _partial_corr(x: np.ndarray, y: np.ndarray, z: np.ndarray):
    r_xy = np.corrcoef(x, y)[0, 1]
    r_xz = np.corrcoef(x, z)[0, 1]
    r_yz = np.corrcoef(y, z)[0, 1]
    denom = np.sqrt((1 - r_xz**2) * (1 - r_yz**2))
    if denom == 0 or np.isnan(denom):
        return np.nan, np.nan
    r = (r_xy - r_xz * r_yz) / denom
    n = len(x)
    df_ = n - 3
    if df_ <= 0 or abs(r) >= 1:
        return r, np.nan
    t = r * np.sqrt(df_ / (1 - r**2))
    p = 2 * (1 - stats.t.cdf(abs(t), df_))
    return r, p


def render_sensitivity_tab(df):
    st.markdown("#### Specification Curve Sensitivity Analysis")
    st.caption("Tests whether an association survives across the reasonable analytic choices a researcher could defensibly make â€” not synthetic noise.")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    if len(numeric_cols) < 2:
        st.info("Need at least 2 numeric variables.")
        return

    y = st.selectbox("Outcome", numeric_cols, key="sens_y")
    x = st.selectbox("Predictor", [c for c in numeric_cols if c != y], key="sens_x")
    subgroup_col = st.selectbox("Optional subgroup breakdown", ["(None)"] + cat_cols, key="sens_subgroup")

    if st.button("â–¶ Execute Specification Curve", type="primary", key="run_sens"):
        clean = df[[x, y]].dropna()
        xs, ys = clean[x], clean[y]
        specs = []

        r, p = stats.pearsonr(xs, ys)
        specs.append({"Specification": "Pearson, full sample", "Coefficient": round(r, 4), "P-Value": round(p, 4), "N": len(xs)})

        rho, p = stats.spearmanr(xs, ys)
        specs.append({"Specification": "Spearman, full sample", "Coefficient": round(rho, 4), "P-Value": round(p, 4), "N": len(xs)})

        xc, yc = _iqr_clean_pair(xs, ys)
        if len(xc) > 3:
            r, p = stats.pearsonr(xc, yc)
            specs.append({"Specification": "Pearson, IQR outliers excluded", "Coefficient": round(r, 4), "P-Value": round(p, 4), "N": len(xc)})

        xw, yw = _winsorize(xs), _winsorize(ys)
        r, p = stats.pearsonr(xw, yw)
        specs.append({"Specification": "Pearson, winsorized 5%/95%", "Coefficient": round(r, 4), "P-Value": round(p, 4), "N": len(xw)})

        other_numeric = [c for c in numeric_cols if c not in (x, y)][:5]
        for z_col in other_numeric:
            z_clean = df[[x, y, z_col]].dropna()
            if len(z_clean) > 5:
                r, p = _partial_corr(z_clean[x].values, z_clean[y].values, z_clean[z_col].values)
                if not np.isnan(r):
                    specs.append({"Specification": f"Partial correlation, controlling for {z_col}", "Coefficient": round(r, 4), "P-Value": round(p, 4) if not np.isnan(p) else None, "N": len(z_clean)})

        if subgroup_col != "(None)":
            for level, sub in df.groupby(subgroup_col):
                sub_clean = sub[[x, y]].dropna()
                if len(sub_clean) >= 10:
                    r, p = stats.pearsonr(sub_clean[x], sub_clean[y])
                    specs.append({"Specification": f"Pearson, subgroup {subgroup_col}={level}", "Coefficient": round(r, 4), "P-Value": round(p, 4), "N": len(sub_clean)})

        res_df = pd.DataFrame(specs)
        res_df["Robust (p<0.05)"] = res_df["P-Value"].apply(lambda v: v is not None and v < 0.05)
        st.dataframe(res_df, use_container_width=True, hide_index=True)

        robust_pct = res_df["Robust (p<0.05)"].mean() * 100
        sign_consistent = (res_df["Coefficient"] > 0).all() or (res_df["Coefficient"] < 0).all()
        c1, c2 = st.columns(2)
        c1.metric("Specifications Significant", f"{robust_pct:.1f}%")
        c2.metric("Sign Consistent Across Specs", "Yes" if sign_consistent else "No")

        if robust_pct == 100 and sign_consistent:
            st.success("âœ… The association holds in direction and significance across every reasonable specification tested.")
        elif robust_pct == 0:
            st.error(" The association is not significant under any specification tested â€” treat the raw correlation as fragile.")
        else:
            st.warning("âš  The association is sensitive to analytic choices â€” significant under some specifications but not others. Report this range, not just the most favorable one.")

        render_export_buttons(res_df, base_name="specification_curve_results")


def render_advanced_tests(df):
    section_header("Advanced Inference Engines", "Causal econometrics, interactive Bayesian updates, real specification-curve sensitivity, bootstrap CIs, and power calculations.")

    tab_causal, tab_bayes, tab_sens, tab_boot, tab_power = st.tabs([
        " Causal Inference", "  Bayesian", " Sensitivity", " Bootstrap", " Power & Sample Size",
    ])

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    with tab_causal:
        st.markdown("#### Causal Inference & Econometric Control Engine")
        st.info("Evaluate adjusted treatment effects controlling for measured confounding variables. Note: this identifies *associational* effects adjusted for observed covariates â€” it cannot rule out unmeasured confounding, and unmeasured confounding is common outside randomized designs.")
        if len(numeric_cols) >= 3 and STATSMODELS_AVAILABLE:
            outcome = st.selectbox("Outcome variable", numeric_cols, key="causal_y")
            predictor = st.selectbox("Treatment / Predictor", [c for c in numeric_cols if c != outcome], key="causal_x")
            confounders = st.multiselect("Confounders (Control covariates)", [c for c in numeric_cols if c not in [outcome, predictor]], key="causal_z")
            if st.button("â–¶ Run Causal Regression Model", type="primary", key="run_causal"):
                try:
                    cols = [predictor] + confounders
                    X = sm.add_constant(df[cols].dropna())
                    y = df.loc[X.index, outcome]
                    model = sm.OLS(y, X).fit()
                    st.text(str(model.summary()))
                    coef, p_val = model.params[predictor], model.pvalues[predictor]
                    st.markdown(generate_ai_interpretation(f"Adjusted effect of {predictor} on {outcome}", p_val, effect=coef, effect_label=f"Î² ({predictor})"))
                    log_test_result(f"Causal Regression ({predictor} â†’ {outcome}, controlling for {len(confounders)} covariates)", p_val, "Î²", coef)
                except Exception as e:
                    st.error(f"Causal regression error: {e}")
        else:
            st.info("Need at least 3 numeric variables and statsmodels installed.")

    with tab_bayes:
        st.markdown("#### Interactive Bayesian Inference Engine")
        st.caption("Conjugate Normal-Normal analytical updating for continuous parameter estimation.")
        if len(numeric_cols) >= 1:
            col = st.selectbox("Variable for Bayesian estimation", numeric_cols, key="bayes_col")
            c1, c2 = st.columns(2)
            prior_mean = c1.number_input("Prior Mean (Î¼â‚€)", value=50.0, key="bayes_prior_mean")
            prior_var = c2.number_input("Prior Variance (Ïƒâ‚€Â²)", value=10.0, key="bayes_prior_var")

            if st.button("â–¶ Compute Exact Posterior", type="primary", key="run_bayes"):
                data = df[col].dropna()
                n = len(data)
                sample_mean = data.mean()
                sample_var = data.var(ddof=1) if n > 1 else 1.0

                if prior_var > 0 and sample_var > 0:
                    precision_prior = 1.0 / prior_var
                    precision_data = n / sample_var
                    posterior_precision = precision_prior + precision_data
                    posterior_var = 1.0 / posterior_precision
                    posterior_mean = posterior_var * (precision_prior * prior_mean + precision_data * sample_mean)

                    st.metric("Sample Mean", f"{sample_mean:.3f}")
                    st.metric("Posterior Mean (Î¼â‚™)", f"{posterior_mean:.3f}")
                    st.metric("Posterior Variance (Ïƒâ‚™Â²)", f"{posterior_var:.4f}")
                    st.markdown(
                        f"> **Bayesian Update Summary:** Prior ~ N({prior_mean}, {prior_var}) updated with "
                        f"N={n}, sample mean {sample_mean:.3f} â†’ Posterior N({posterior_mean:.3f}, {posterior_var:.4f})."
                    )
                else:
                    st.error("Variance parameters must be strictly greater than zero.")
        else:
            st.info("Need a numeric variable.")

    with tab_sens:
        render_sensitivity_tab(df)

    with tab_boot:
        st.markdown("#### Bootstrap Non-Parametric Resampling")
        st.caption("Generate empirical confidence intervals via iterative bootstrap resampling.")
        if len(numeric_cols) >= 1:
            col = st.selectbox("Variable to bootstrap", numeric_cols, key="boot_col")
            n_boot = st.slider("Bootstrap iterations", 200, 5000, 1000, key="boot_n")
            if st.button("â–¶ Run Bootstrap Engine", type="primary", key="run_boot"):
                data = df[col].dropna().values
                rng = np.random.RandomState(42)
                means = [rng.choice(data, size=len(data), replace=True).mean() for _ in range(n_boot)]
                ci_low, ci_high = np.percentile(means, [2.5, 97.5])
                st.metric("Observed Mean", f"{data.mean():.3f}")
                st.metric("Bootstrap 95% CI Lower", f"{ci_low:.3f}")
                st.metric("Bootstrap 95% CI Upper", f"{ci_high:.3f}")
                st.markdown(f"> **Empirical 95% Confidence Interval:** [{ci_low:.3f}, {ci_high:.3f}]")
        else:
            st.info("Need a numeric variable.")

    with tab_power:
        st.markdown("#### A Priori Power & Sample Size Calculator")
        st.caption("Determine necessary sample sizes for target statistical power thresholds.")
        effect_size = st.selectbox("Expected Effect Size", ["Small (d=0.2)", "Medium (d=0.5)", "Large (d=0.8)", "Custom"], key="power_effect")
        d = {"Small (d=0.2)": 0.2, "Medium (d=0.5)": 0.5, "Large (d=0.8)": 0.8}.get(effect_size)
        if effect_size == "Custom":
            d = st.number_input("Custom Cohen's d", 0.01, 3.0, 0.5, 0.01, key="power_custom_d")
        alpha = st.selectbox("Significance Level (Î±)", [0.01, 0.05, 0.10], index=1, key="power_alpha")
        power = st.slider("Target Statistical Power (1 - Î²)", 0.70, 0.99, 0.80, 0.05, key="power_target")

        if st.button("â–¶ Calculate Required N", type="primary", key="run_power"):
            if STATSMODELS_AVAILABLE:
                n_per_group = TTestIndPower().solve_power(effect_size=d, alpha=alpha, power=power, ratio=1.0, alternative="two-sided")
                n_per_group = int(np.ceil(n_per_group))
                method_label = "Exact (noncentral-t, statsmodels)"
            else:
                z_alpha = stats.norm.ppf(1 - alpha / 2)
                z_beta = stats.norm.ppf(power)
                n_per_group = int(np.ceil(2 * ((z_alpha + z_beta) ** 2) / (d ** 2)))
                method_label = "Normal Approximation (statsmodels not installed)"

            st.metric("Required Sample Size Per Group", f"{n_per_group:,}")
            st.metric("Total Study Sample Size", f"{n_per_group * 2:,}")
            st.caption(f"Method: {method_label}")
            st.markdown(f"> **Design Parameters:** Cohen's d={d}, Î±={alpha}, Target Power={power:.2f}")


def render_methodology_tab():
    section_header("  Methodology Advisor & Decision Tree", "Automated research design matching and test recommendation engine.")

    st.markdown("### Research Design Parameters")
    c1, c2 = st.columns(2)
    with c1:
        objective = st.selectbox("Primary Research Objective", [
            "Compare Group Means/Medians",
            "Measure Association / Correlation",
            "Predict Outcome (Regression)",
            "Analyze Categorical Frequencies",
        ], key="meth_obj")
        n_groups = st.selectbox("Number of Groups", ["2 Groups", "3+ Groups", "Not Applicable"], key="meth_groups")
    with c2:
        distribution = st.selectbox("Data Distribution", ["Normal (Parametric)", "Non-Normal (Non-Parametric)", "Categorical"], key="meth_dist")
        pairing = st.selectbox("Sample Dependency", ["Independent", "Paired / Repeated"], key="meth_pair")

    if st.button(" Recommend Statistical Procedure", type="primary", key="run_meth"):
        rec, rationale = "", ""
        if "Compare Group Means" in objective:
            if "2 Groups" in n_groups:
                if "Normal" in distribution:
                    rec = "Independent Samples t-Test" if "Independent" in pairing else "Paired Samples t-Test"
                    rationale = "Continuous normally distributed data compared across two levels."
                else:
                    rec = "Mann-Whitney U Test" if "Independent" in pairing else "Wilcoxon Signed-Rank Test"
                    rationale = "Non-normal or ordinal continuous data compared across two levels."
            else:
                if "Normal" in distribution:
                    rec, rationale = "One-Way ANOVA", "Parametric comparison across 3 or more independent groups."
                else:
                    rec, rationale = "Kruskal-Wallis H Test", "Non-parametric comparison across 3 or more independent groups."
        elif "Association" in objective:
            if "Normal" in distribution:
                rec, rationale = "Pearson Correlation Coefficient", "Linear association between continuous normally distributed variables."
            else:
                rec, rationale = "Spearman Rank Correlation", "Monotonic association for non-normal or ordinal data."
        elif "Predict" in objective:
            rec, rationale = "Multiple Linear Regression (Continuous) / Logistic Regression (Binary)", "Multivariate modeling to estimate expected values or probabilities."
        else:
            rec, rationale = "Chi-Square Test of Independence / Fisher's Exact Test", "Frequency analysis for contingency table categorical distributions."

        st.success(f"âœ… **Recommended Procedure:** {rec}")
        st.info(f" **Methodological Rationale:** {rationale}")

        st.session_state["last_methodology_rec"] = {
            "objective": objective, "recommendation": rec, "rationale": rationale,
            "timestamp": pd.Timestamp.now().isoformat(),
        }

    if "last_methodology_rec" in st.session_state:
        st.markdown("---")
        st.markdown("####  Export Methodology Decision Report")
        report_df = pd.DataFrame([st.session_state["last_methodology_rec"]])
        render_export_buttons(report_df, base_name="methodology_recommendation_report")


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription(hub_id="statistics")

    setup_page("Statistics Studio", " initial_sidebar_state="expanded")

    from modules.user_preferences import render_readability_fix, render_accent_color_css
    render_readability_fix()
    render_accent_color_css()

    hero_card(
        " Enterprise Statistics Studio (Premium)",
        "Consolidated statistical hub featuring pre-flight assumption validation, comprehensive effect sizes, a genuine specification-curve sensitivity analysis, session-wide multiple-comparisons correction, causal econometrics, interactive Bayesian updating, and exact power analysis.",
        badge_text="STATISTICS STUDIO â€¢ PREMIUM TIER",
    )

    render_dataset_context_banner()

    df = get_df()

    tabs = st.tabs([
        " Parametric Tests",
        " Non-Parametric Tests",
        "âš¡ Advanced Inference",
        " Test Ledger",
        "  Methodology Advisor",
    ])

    with tabs[0]:
        render_param_tests(df)
    with tabs[1]:
        render_nonparam_tests(df)
    with tabs[2]:
        render_advanced_tests(df)
    with tabs[3]:
        render_ledger_tab()
    with tabs[4]:
        render_methodology_tab()

    render_standard_footer("STATISTICS STUDIO")


if __name__ == "__main__":
    main()
