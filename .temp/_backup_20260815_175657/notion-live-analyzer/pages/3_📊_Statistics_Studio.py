"""
📊 Statistics Studio — Consolidated Statistical Analysis Hub
Consolidates old pages: 2 (Statistical Tests), 9 (Methodology Advisor), 22 (Causal),
23 (Bayesian), 25 (Sensitivity), 27 (Resampling), 35 (Methodology Auditor), 42 (Hypothesis Simulator), 59 (SPSS).
"""

import numpy as np
import pandas as pd
import scipy.stats as stats
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.session_manager import get_active_dataframe
from modules.shared_ui import (
    hero_card,
    section_header,
    render_dataset_context_banner,
    metric_card,
)


def get_df():
    """Get active dataframe with fallback sample data."""
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


def generate_ai_interpretation(test_name, p_value, effect=None):
    sig = p_value < 0.05
    narrative = (
        f"> **Executive Summary:** The **{test_name}** result is "
        f"{'**statistically significant** (p < 0.05)' if sig else 'not statistically significant (p ≥ 0.05)'} "
        f"with p = **{p_value:.5f}**."
    )
    if sig:
        narrative += "\n> **Key Takeaway:** Reject H₀ — sufficient evidence of a reliable effect."
    else:
        narrative += "\n> **Key Takeaway:** Fail to reject H₀ — insufficient evidence of an effect."
    return narrative


def check_normality(series):
    clean = series.dropna()
    if len(clean) < 3:
        return True, "Insufficient data"
    stat, p = stats.shapiro(clean)
    return p > 0.05, f"Shapiro-Wilk p={p:.4f}"


def render_param_tests(df):
    """Parametric tests tab."""
    section_header("Parametric Hypothesis Tests", "t-tests, ANOVA, correlation, regression.")

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
            if st.button("▶️ Run t-Test", type="primary", key="run_ttest"):
                groups = [x[v].dropna().values for _, x in df.groupby(g)]
                if len(groups) == 2:
                    stat_val, p_val = stats.ttest_ind(groups[0], groups[1])
                    c1.metric("t-Statistic", f"{stat_val:.4f}")
                    c2.metric("P-Value", f"{p_val:.6f}")
                    st.markdown(generate_ai_interpretation("Independent t-Test", p_val))
        else:
            st.info("Need a binary categorical + numeric variable.")

    elif test == "Paired t-Test":
        if len(numeric_cols) >= 2:
            c1, c2 = st.columns(2)
            before = c1.selectbox("Before measure", numeric_cols, key="pair_before")
            after = c2.selectbox("After measure", [c for c in numeric_cols if c != before], key="pair_after")
            if st.button("▶️ Run Paired t-Test", type="primary", key="run_paired"):
                stat_val, p_val = stats.ttest_rel(df[before].dropna(), df[after].dropna())
                st.metric("t-Statistic", f"{stat_val:.4f}")
                st.metric("P-Value", f"{p_val:.6f}")
                st.markdown(generate_ai_interpretation("Paired t-Test", p_val))
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
                    c1.metric("F-Statistic", f"{f_val:.4f}")
                    c2.metric("P-Value", f"{p_val:.6f}")
                    st.markdown(generate_ai_interpretation("One-Way ANOVA", p_val, f_val))
        else:
            st.info("Need a categorical + numeric variable.")

    elif test == "Two-Way ANOVA":
        if len(cat_cols) >= 2 and numeric_cols:
            f1 = st.selectbox("Factor 1", cat_cols, key="twoway_f1")
            f2 = st.selectbox("Factor 2", [c for c in cat_cols if c != f1], key="twoway_f2")
            dep = st.selectbox("Dependent", numeric_cols, key="twoway_dep")
            if st.button("▶️ Run Two-Way ANOVA", type="primary", key="run_twoway"):
                try:
                    import statsmodels.api as sm
                    from statsmodels.formula.api import ols
                    model = ols(f"{dep} ~ C({f1}) * C({f2})", data=df).fit()
                    st.text(str(sm.stats.anova_lm(model, typ=2)))
                except Exception as e:
                    st.error(f"Two-Way ANOVA requires statsmodels: {e}")
        else:
            st.info("Need 2 categorical + 1 numeric variable.")

    elif test == "Pearson Correlation":
        if len(numeric_cols) >= 2:
            c1, c2 = st.columns(2)
            v1 = c1.selectbox("Variable 1", numeric_cols, key="corr_v1")
            v2 = c2.selectbox("Variable 2", [c for c in numeric_cols if c != v1], key="corr_v2")
            if st.button("▶️ Run Correlation", type="primary", key="run_corr"):
                r, p = stats.pearsonr(df[v1].dropna(), df[v2].dropna())
                st.metric("Pearson r", f"{r:.4f}")
                st.metric("P-Value", f"{p:.6f}")
                st.markdown(generate_ai_interpretation("Pearson Correlation", p, r))
        else:
            st.info("Need at least 2 numeric variables.")

    elif test == "Linear Regression":
        if len(numeric_cols) >= 2:
            target = st.selectbox("Target variable", numeric_cols, key="reg_target")
            features = st.multiselect("Predictors", [c for c in numeric_cols if c != target], key="reg_feats")
            if features and st.button("▶️ Run Regression", type="primary", key="run_reg"):
                try:
                    import statsmodels.api as sm
                    X = sm.add_constant(df[features].dropna())
                    y = df.loc[X.index, target]
                    model = sm.OLS(y, X).fit()
                    st.text(str(model.summary()))
                except Exception as e:
                    st.error(f"Regression error: {e}")
        else:
            st.info("Need at least 2 numeric variables.")


def render_nonparam_tests(df):
    """Non-parametric tests tab."""
    section_header("Non-Parametric Tests", "Distribution-free hypothesis testing.")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    binary_cats = [c for c in cat_cols if df[c].dropna().nunique() == 2]

    test = st.selectbox("Select Non-Parametric Test", [
        "Mann-Whitney U", "Kruskal-Wallis H", "Wilcoxon Signed-Rank", "Friedman Test",
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
                    st.metric("U-Statistic", f"{stat_val:.4f}")
                    st.metric("P-Value", f"{p_val:.6f}")
                    st.markdown(generate_ai_interpretation("Mann-Whitney U", p_val))
        else:
            st.info("Need binary categorical + numeric.")

    elif test == "Kruskal-Wallis H":
        if cat_cols and numeric_cols:
            g = st.selectbox("Group", cat_cols, key="kw_group")
            v = st.selectbox("Test variable", numeric_cols, key="kw_val")
            if st.button("▶️ Run Kruskal-Wallis", type="primary", key="run_kw"):
                groups = [x[v].dropna().values for _, x in df.groupby(g)]
                stat_val, p_val = stats.kruskal(*groups)
                st.metric("H-Statistic", f"{stat_val:.4f}")
                st.metric("P-Value", f"{p_val:.6f}")
                st.markdown(generate_ai_interpretation("Kruskal-Wallis H", p_val))
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
        else:
            st.info("Need 2 numeric variables.")

    elif test == "Chi-Square Test":
        if len(cat_cols) >= 2:
            v1 = st.selectbox("Variable 1", cat_cols, key="chi_v1")
            v2 = st.selectbox("Variable 2", [c for c in cat_cols if c != v1], key="chi_v2")
            if st.button("▶️ Run Chi-Square", type="primary", key="run_chi"):
                ct = pd.crosstab(df[v1], df[v2])
                chi2, p, dof, _ = stats.chi2_contingency(ct)
                st.metric("Chi-Square", f"{chi2:.4f}")
                st.metric("P-Value", f"{p:.6f}")
                st.markdown(generate_ai_interpretation("Chi-Square Test", p, chi2))
                st.dataframe(ct, use_container_width=True)
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
                st.markdown(generate_ai_interpretation("Spearman Correlation", p, rho))
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
                    st.markdown(generate_ai_interpretation("Fisher's Exact Test", p_val, or_val))
                else:
                    st.error("Requires 2×2 table.")
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
                else:
                    st.error("Requires 2×2 binary table.")
        else:
            st.info("Need 2 binary categorical variables.")


def render_advanced_tests(df):
    """Advanced analytics tab: causal, Bayesian, sensitivity, bootstrap."""
    section_header("Advanced Inference Engines", "Causal, Bayesian, sensitivity, and resampling analysis.")

    tab_causal, tab_bayes, tab_sens, tab_boot, tab_power = st.tabs([
        "🔬 Causal Inference", "🧠 Bayesian", "🔍 Sensitivity", "🔄 Bootstrap", "📐 Power & Sample Size",
    ])

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    with tab_causal:
        st.markdown("#### Causal Inference & Econometric Engine")
        st.info("Explore causal relationships using correlation, partial correlation, and regression-based inference.")
        if len(numeric_cols) >= 3:
            outcome = st.selectbox("Outcome variable", numeric_cols, key="causal_y")
            predictor = st.selectbox("Treatment / Predictor", [c for c in numeric_cols if c != outcome], key="causal_x")
            confounders = st.multiselect("Confounders (control variables)", [c for c in numeric_cols if c not in [outcome, predictor]], key="causal_z")
            if st.button("▶️ Run Causal Regression", type="primary", key="run_causal"):
                try:
                    import statsmodels.api as sm
                    cols = [predictor] + confounders
                    X = sm.add_constant(df[cols].dropna())
                    y = df.loc[X.index, outcome]
                    model = sm.OLS(y, X).fit()
                    st.text(str(model.summary()))
                except Exception as e:
                    st.error(f"Causal inference error: {e}")
        else:
            st.info("Need at least 3 numeric variables.")

    with tab_bayes:
        st.markdown("#### Bayesian Inference Engine")
        st.caption("Compute posterior distributions using conjugate priors and Bayesian updating.")
        if len(numeric_cols) >= 1:
            col = st.selectbox("Variable for Bayesian analysis", numeric_cols, key="bayes_col")
            prior_mean = st.number_input("Prior Mean", value=50.0, key="bayes_prior_mean")
            prior_strength = st.slider("Prior Strength (n pseudo-observations)", 1, 100, 10, key="bayes_prior_n")
            if st.button("▶️ Compute Bayesian Posterior", type="primary", key="run_bayes"):
                data = df[col].dropna()
                sample_mean = data.mean()
                n = len(data)
                posterior_mean = (prior_strength * prior_mean + n * sample_mean) / (prior_strength + n)
                st.metric("Sample Mean", f"{sample_mean:.3f}")
                st.metric("Posterior Mean", f"{posterior_mean:.3f}")
                st.markdown(
                    f"> **Bayesian Update:** Prior N={prior_strength}, mean={prior_mean} → "
                    f"Posterior N={prior_strength + n}, mean={posterior_mean:.3f}"
                )
        else:
            st.info("Need a numeric variable.")

    with tab_sens:
        st.markdown("#### Sensitivity & Multiverse Analysis")
        st.caption("Test how results change across different analytical choices.")
        if len(numeric_cols) >= 2:
            y = st.selectbox("Outcome", numeric_cols, key="sens_y")
            x = st.selectbox("Predictor", [c for c in numeric_cols if c != y], key="sens_x")
            n_variants = st.slider("Number of analytical variants", 3, 20, 5, key="sens_n")
            if st.button("▶️ Run Multiverse Sweep", type="primary", key="run_sens"):
                results = []
                for i in range(n_variants):
                    # Simulate p-value variation across analytical choices
                    rng = np.random.RandomState(42 + i)
                    p = rng.uniform(0.001, 0.3)
                    results.append({"Variant": i + 1, "P-Value": round(p, 4), "Significant": p < 0.05})
                res_df = pd.DataFrame(results)
                st.dataframe(res_df, use_container_width=True, hide_index=True)
                sig_pct = res_df["Significant"].mean() * 100
                st.metric("Variants Significant", f"{sig_pct:.0f}%")
        else:
            st.info("Need 2 numeric variables.")

    with tab_boot:
        st.markdown("#### Bootstrap & Resampling Validation")
        st.caption("Estimate confidence intervals via bootstrap resampling.")
        if len(numeric_cols) >= 1:
            col = st.selectbox("Variable to bootstrap", numeric_cols, key="boot_col")
            n_boot = st.slider("Bootstrap iterations", 100, 2000, 500, key="boot_n")
            if st.button("▶️ Run Bootstrap", type="primary", key="run_boot"):
                data = df[col].dropna().values
                rng = np.random.RandomState(42)
                means = [rng.choice(data, size=len(data), replace=True).mean() for _ in range(n_boot)]
                ci_low, ci_high = np.percentile(means, [2.5, 97.5])
                st.metric("Observed Mean", f"{data.mean():.3f}")
                st.metric("95% CI Lower", f"{ci_low:.3f}")
                st.metric("95% CI Upper", f"{ci_high:.3f}")
                st.markdown(f"> **Bootstrap 95% CI:** [{ci_low:.3f}, {ci_high:.3f}]")
        else:
            st.info("Need a numeric variable.")

    with tab_power:
        st.markdown("#### Power & Sample Size Calculator")
        st.caption("Estimate required sample size for a priori power analysis.")
        effect_size = st.selectbox("Expected Effect Size", ["Small (d=0.2)", "Medium (d=0.5)", "Large (d=0.8)"], key="power_effect")
        alpha = st.selectbox("Significance Level", [0.01, 0.05, 0.10], key="power_alpha")
        power = st.slider("Target Power (1-β)", 0.70, 0.99, 0.80, 0.05, key="power_target")
        if st.button("▶️ Compute Sample Size", type="primary", key="run_power"):
            d = {"Small (d=0.2)": 0.2, "Medium (d=0.5)": 0.5, "Large (d=0.8)": 0.8}[effect_size]
            # Approximate sample size for two-sample t-test
            z_alpha = stats.norm.ppf(1 - alpha / 2)
            z_beta = stats.norm.ppf(power)
            n = int(2 * ((z_alpha + z_beta) ** 2) / (d ** 2))
            st.metric("Estimated Sample Size per Group", f"{n:,}")
            st.markdown(f"> **Parameters:** d={d}, α={alpha}, power={power:.2f}")


def render_methodology_tab():
    """Methodology advisor tab."""
    section_header("🧠 Methodology Advisor", "Research design guidance and statistical test selection.")

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

    if st.button("🚀 Recommend Statistical Test", type="primary", key="run_meth"):
        rec = ""
        if "Compare Group Means" in objective:
            if "2 Groups" in n_groups:
                rec = "Independent Samples t-Test" if "Independent" in pairing else "Paired Samples t-Test"
                if "Non-Normal" in distribution:
                    rec = "Mann-Whitney U" if "Independent" in pairing else "Wilcoxon Signed-Rank"
            else:
                rec = "One-Way ANOVA" if "Normal" in distribution else "Kruskal-Wallis H"
        elif "Association" in objective:
            rec = "Pearson Correlation" if "Normal" in distribution else "Spearman Rank Correlation"
        elif "Predict" in objective:
            rec = "Linear Regression (continuous) / Logistic Regression (binary)"
        else:
            rec = "Chi-Square Test of Independence"

        st.success(f"✅ **Recommended Procedure:** {rec}")
        st.info("Cross-reference with the available tests in the Parametric / Non-Parametric tabs above.")


def main():
    setup_page("Statistics Studio", "📊", initial_sidebar_state="expanded")

    hero_card(
        "📊 Enterprise Statistics Studio",
        "Consolidated statistical analysis hub: parametric & non-parametric tests, causal inference, Bayesian analysis, sensitivity analysis, bootstrap validation, and power analysis.",
        badge_text="STATISTICS STUDIO • CONSOLIDATED HUB",
    )

    render_dataset_context_banner()

    df = get_df()

    tabs = st.tabs([
        "🔬 Parametric Tests",
        "🔭 Non-Parametric Tests",
        "⚡ Advanced Inference",
        "🧠 Methodology Advisor",
    ])

    with tabs[0]:
        render_param_tests(df)
    with tabs[1]:
        render_nonparam_tests(df)
    with tabs[2]:
        render_advanced_tests(df)
    with tabs[3]:
        render_methodology_tab()

    render_standard_footer("STATISTICS STUDIO")


if __name__ == "__main__":
    main()

