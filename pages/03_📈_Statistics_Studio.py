import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

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
        f"{'**statistically significant** (p < 0.05)' if sig else 'not statistically significant (p ≥ 0.05)'} "
        f"with p = **{p_value:.5f}**."
    )
    narrative += "\n> **Key Takeaway:** " + ("Reject $H_0$ — sufficient evidence of a reliable effect." if sig else "Fail to reject $H_0$ — insufficient evidence of an effect.")
    if effect is not None:
        narrative += f"\n> **{effect_label}:** `{effect:.4f}`"
    if assumption_warning:
        narrative += f"\n> **⚠️ Assumption Notice:** {assumption_warning}"
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


def log_test_result(test_name, p_value, effect_label=None, effect_value=None):
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


def render_ledger_tab():
    section_header("📋 Multiple-Comparisons Ledger", "Bonferroni and Benjamini-Hochberg FDR correction applied across the whole test set.")

    ledger = st.session_state.get("stats_test_ledger", [])
    if not ledger:
        st.info("ℹ️ No tests logged yet this session.")
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
    c1.metric("Tests Logged", m)
    c2.metric("Significant (raw α=.05)", int(ledger_df["Significant (raw α=.05)"].sum()))
    c3.metric("Survive Bonferroni", int(ledger_df["Significant (Bonferroni)"].sum()))
    c4.metric("Survive BH-FDR", int(ledger_df["Significant (BH-FDR)"].sum()))

    if int(ledger_df["Significant (raw α=.05)"].sum()) > int(ledger_df["Significant (BH-FDR)"].sum()):
        st.warning("⚠️ Some results significant at raw α=.05 do **not** survive correction for multiple comparisons.")

    st.dataframe(ledger_df, use_container_width=True, hide_index=True)
    render_export_buttons(ledger_df, base_name="multiple_comparisons_ledger")

    if st.button("🗑️ Clear Ledger", key="clear_ledger"):
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

                with st.expander("🔍 Pre-flight Statistical Assumptions"):
                    st.write(f"- Group 1 Normality: {norm_msg1}")
                    st.write(f"- Group 2 Normality: {norm_msg2}")
                    st.write(f"- Variance Homogeneity: {homog_msg}")

                if st.button("▶️ Run t-Test", type="primary", key="run_ttest"):
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

                    warning = None if equal_var else "Equal variance assumption violated; Welch's t-test applied."
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
            with st.expander("🔍 Pre-flight Statistical Assumptions"):
                st.write(f"- Difference Score Normality: {diff_norm_msg}")

            if st.button("▶️ Run Paired t-Test", type="primary", key="run_paired"):
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
            if st.button("▶️ Run One-Way ANOVA", type="primary", key="run_anova"):
                groups = [x[v].dropna().values for _, x in df.groupby(g)]
                if len(groups) >= 2:
                    f_val, p_val = stats.f_oneway(*groups)
                    k = len(groups)
                    n = sum(len(gr) for gr in groups)
                    eta_sq = (f_val * (k - 1)) / (f_val * (k - 1) + (n - k)) if (n - k) > 0 else np.nan

                    c1.metric("F-Statistic", f"{f_val:.4f}")
                    c2.metric("P-Value", f"{p_val:.6f}")
                    st.metric("Eta-Squared (η²)", f"{eta_sq:.4f}")
                    st.markdown(generate_ai_interpretation("One-Way ANOVA", p_val, effect=eta_sq, effect_label="Eta-Squared (η²)"))
                    log_test_result(f"One-Way ANOVA ({v} by {g})", p_val, "Eta-Squared", eta_sq)
        else:
            st.info("Need a categorical + numeric variable.")

    elif test == "Two-Way ANOVA":
        if len(cat_cols) >= 2 and numeric_cols and STATSMODELS_AVAILABLE:
            f1 = st.selectbox("Factor 1", cat_cols, key="twoway_f1")
            f2 = st.selectbox("Factor 2", [c for c in cat_cols if c != f1], key="twoway_f2")
            dep = st.selectbox("Dependent", numeric_cols, key="twoway_dep")
            if st.button("▶️ Run Two-Way ANOVA", type="primary", key="run_twoway"):
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
                        breakdown.append({"Term": term, "F": anova_table.loc[term, "F"], "P-Value": p_term, "Partial η²": partial_eta})
                        log_test_result(f"Two-Way ANOVA — {term} ({dep})", p_term, "Partial η²", partial_eta)

                    breakdown_df = pd.DataFrame(breakdown)
                    st.markdown("#### Per-Term Breakdown (including interaction)")
                    st.dataframe(breakdown_df, use_container_width=True, hide_index=True)
                except Exception as e:
                    st.error(f"Two-Way ANOVA computation error: {e}")
        else:
            st.info("Need 2 categorical + 1 numeric variable and statsmodels installed.")

    elif test == "Pearson Correlation":
        if len(numeric_cols) >= 2:
            c1, c2 = st.columns(2)
            v1 = c1.selectbox("Variable 1", numeric_cols, key="corr_v1")
            v2 = c2.selectbox("Variable 2", [c for c in numeric_cols if c != v1], key="corr_v2")
            if st.button("▶️ Run Correlation", type="primary", key="run_corr"):
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
            if features and st.button("▶️ Run Regression", type="primary", key="run_reg"):
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
                    st.markdown(generate_ai_interpretation("Multiple OLS Regression", f_p, effect=r_sq, effect_label="R²"))
                    log_test_result(f"OLS Regression ({target} ~ {'+'.join(features)})", f_p, "R²", r_sq)
                except Exception as e:
                    st.error(f"Regression error: {e}")
        else:
            st.info("Need at least 2 numeric variables and statsmodels.")


def render_nonparam_tests(df):
    section_header("Non-Parametric Tests", "Distribution-free hypothesis testing.")

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
            if st.button("▶️ Run Mann-Whitney U", type="primary", key="run_mw"):
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
            if st.button("▶️ Run Kruskal-Wallis", type="primary", key="run_kw"):
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
            if st.button("▶️ Run Wilcoxon", type="primary", key="run_wx"):
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
            if st.button("▶️ Run Chi-Square", type="primary", key="run_chi"):
                ct = pd.crosstab(df[v1], df[v2])
                chi2, p, dof, ex = stats.chi2_contingency(ct)
                n = ct.values.sum()
                min_dim = min(ct.shape[0] - 1, ct.shape[1] - 1)
                cramers_v = np.sqrt(chi2 / (n * min_dim)) if min_dim > 0 and n > 0 else np.nan

                st.metric("Chi-Square", f"{chi2:.4f}")
                st.metric("P-Value", f"{p:.6f}")
                st.metric("Cramér's V", f"{cramers_v:.4f}")
                st.dataframe(ct, use_container_width=True)
                log_test_result(f"Chi-Square ({v1} vs {v2})", p, "Cramér's V", cramers_v)
        else:
            st.info("Need 2 categorical variables.")

    elif test == "Spearman Correlation":
        if len(numeric_cols) >= 2:
            v1 = st.selectbox("Variable 1", numeric_cols, key="sp_v1")
            v2 = st.selectbox("Variable 2", [c for c in numeric_cols if c != v1], key="sp_v2")
            if st.button("▶️ Run Spearman", type="primary", key="run_sp"):
                rho, p = stats.spearmanr(df[v1].dropna(), df[v2].dropna())
                st.metric("Spearman ρ", f"{rho:.4f}")
                st.metric("P-Value", f"{p:.6f}")
                st.markdown(generate_ai_interpretation("Spearman Correlation", p, effect=rho, effect_label="Spearman ρ"))
                log_test_result(f"Spearman Correlation ({v1} vs {v2})", p, "ρ", rho)
        else:
            st.info("Need 2 numeric variables.")

    elif test == "Fisher's Exact Test":
        if len(cat_cols) >= 2:
            v1 = st.selectbox("Variable 1", cat_cols, key="fe_v1")
            v2 = st.selectbox("Variable 2", [c for c in cat_cols if c != v1], key="fe_v2")
            if st.button("▶️ Run Fisher's Exact", type="primary", key="run_fe"):
                ct = pd.crosstab(df[v1], df[v2])
                if ct.shape == (2, 2):
                    or_val, p_val = stats.fisher_exact(ct)
                    st.metric("Odds Ratio", f"{or_val:.4f}")
                    st.metric("P-Value", f"{p_val:.6f}")
                    st.markdown(generate_ai_interpretation("Fisher's Exact Test", p_val, effect=or_val, effect_label="Odds Ratio"))
                    log_test_result(f"Fisher's Exact ({v1} vs {v2})", p_val, "Odds Ratio", or_val)
                else:
                    st.error("Requires 2×2 table dimensions.")
        else:
            st.info("Need 2 categorical variables.")

    elif test == "McNemar's Test":
        available = binary_cats + list(df.select_dtypes(include=["bool"]).columns)
        if len(available) >= 2:
            b = st.selectbox("Before", available, key="mn_before")
            a = st.selectbox("After", [c for c in available if c != b], key="mn_after")
            if st.button("▶️ Run McNemar", type="primary", key="run_mn"):
                ct = pd.crosstab(df[b], df[a])
                if ct.shape == (2, 2):
                    res = stats.mcnemar(ct, exact=True)
                    st.metric("Statistic", f"{res.statistic:.4f}")
                    st.metric("P-Value", f"{res.pvalue:.6f}")
                    st.markdown(generate_ai_interpretation("McNemar's Test", res.pvalue))
                    log_test_result(f"McNemar's Test ({b} vs {a})", res.pvalue)
                else:
                    st.error("Requires 2×2 binary table.")
        else:
            st.info("Need 2 binary categorical variables.")


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
    """Calculates partial correlation coefficient and associated two-tailed p-value."""
    n = len(x)
    r_xy = np.corrcoef(x, y)[0, 1]
    r_xz = np.corrcoef(x, z)[0, 1]
    r_yz = np.corrcoef(y, z)[0, 1]
    
    denom = np.sqrt((1 - r_xz**2) * (1 - r_yz**2))
    if denom == 0 or np.isnan(denom):
        return np.nan, np.nan

    r_partial = (r_xy - r_xz * r_yz) / denom
    r_partial = np.clip(r_partial, -1.0, 1.0)
    
    df_deg = n - 3
    if df_deg <= 0 or abs(r_partial) == 1.0:
        return r_partial, 0.0

    t_stat = r_partial * np.sqrt(df_deg / (1.0 - r_partial**2))
    p_val = 2 * (1 - stats.t.cdf(abs(t_stat), df=df_deg))
    
    return r_partial, p_val


def render_sensitivity_tab(df):
    section_header("🔬 Specification-Curve Sensitivity Analysis", "Test relationship robustness across analytical choices.")
    
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if len(numeric_cols) < 2:
        st.info("Need at least 2 numeric variables for specification-curve analysis.")
        return

    c1, c2, c3 = st.columns(3)
    x_var = c1.selectbox("Independent Variable (X)", numeric_cols, index=0, key="spec_x")
    y_var = c2.selectbox("Dependent Variable (Y)", [c for c in numeric_cols if c != x_var], index=0, key="spec_y")
    control_vars = c3.multiselect("Control Variables (Covariates)", [c for c in numeric_cols if c not in [x_var, y_var]], key="spec_controls")

    if st.button("🚀 Run Specification-Curve Engine", type="primary", key="run_spec_curve"):
        clean_df = df[[x_var, y_var] + control_vars].dropna()
        if len(clean_df) < 10:
            st.error("Insufficient complete cases (<10) for specification curve testing.")
            return

        specifications = []

        # Spec 1: Raw Pearson
        r, p = stats.pearsonr(clean_df[x_var], clean_df[y_var])
        specifications.append({"Specification": "Raw - Pearson", "Estimate": r, "P-Value": p, "Type": "Parametric"})

        # Spec 2: Spearman Rank
        rho, p_sp = stats.spearmanr(clean_df[x_var], clean_df[y_var])
        specifications.append({"Specification": "Raw - Spearman Rank", "Estimate": rho, "P-Value": p_sp, "Type": "Non-Parametric"})

        # Spec 3: IQR Trimmed
        x_trim, y_trim = _iqr_clean_pair(clean_df[x_var], clean_df[y_var])
        if len(x_trim) >= 5:
            r_tr, p_tr = stats.pearsonr(x_trim, y_trim)
            specifications.append({"Specification": "1.5x IQR Outlier Trimmed", "Estimate": r_tr, "P-Value": p_tr, "Type": "Robust"})

        # Spec 4: Winsorized
        x_win = _winsorize(clean_df[x_var])
        y_win = _winsorize(clean_df[y_var])
        r_win, p_win = stats.pearsonr(x_win, y_win)
        specifications.append({"Specification": "5% Winsorized", "Estimate": r_win, "P-Value": p_win, "Type": "Robust"})

        # Spec 5: Log-Transformed
        if (clean_df[x_var] > 0).all() and (clean_df[y_var] > 0).all():
            r_log, p_log = stats.pearsonr(np.log(clean_df[x_var]), np.log(clean_df[y_var]))
            specifications.append({"Specification": "Log-Log Transformed", "Estimate": r_log, "P-Value": p_log, "Type": "Transformation"})

        # Spec 6+: Partial Correlations
        for ctrl in control_vars:
            r_p, p_p = _partial_corr(clean_df[x_var].values, clean_df[y_var].values, clean_df[ctrl].values)
            if not np.isnan(r_p):
                specifications.append({"Specification": f"Partial Corr (Controlling for {ctrl})", "Estimate": r_p, "P-Value": p_p, "Type": "Multivariate"})

        res_df = pd.DataFrame(specifications)
        res_df["Significant (p < .05)"] = res_df["P-Value"] < 0.05

        sig_ratio = res_df["Significant (p < .05)"].mean() * 100
        mean_effect = res_df["Estimate"].mean()

        st.metric("Specification Consistency", f"{sig_ratio:.1f}% Significant", delta=f"Mean Effect: {mean_effect:.4f}")
        st.dataframe(res_df, use_container_width=True, hide_index=True)
        render_export_buttons(res_df, base_name=f"specification_curve_{x_var}_{y_var}")


def main():
    setup_page("Statistics Studio", "📊", initial_sidebar_state="expanded")

    from modules.user_preferences import render_readability_fix, render_accent_color_css
    render_readability_fix()
    render_accent_color_css()

    hero_card(
        "📊 Statistics Studio",
        "Perform statistical analyses, assumption validation, and specification-curve testing.",
        badge_text="STATISTICS STUDIO • ENTERPRISE TIER",
    )

    render_dataset_context_banner()

    df = get_df()

    tabs = st.tabs([
        "📈 Parametric Tests",
        "📉 Non-Parametric Tests",
        "🔬 Sensitivity Analysis",
        "📋 Multiple-Comparisons Ledger",
    ])

    with tabs[0]:
        render_param_tests(df)
    with tabs[1]:
        render_nonparam_tests(df)
    with tabs[2]:
        render_sensitivity_tab(df)
    with tabs[3]:
        render_ledger_tab()

    render_standard_footer("STATISTICS STUDIO")


if __name__ == "__main__":
    main()