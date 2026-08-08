"""
📊 Statistics Studio — Consolidated Statistical Analysis Hub (Upgraded)
Consolidated pages with enhanced execution safety, robust assumption pre-flight checks, 
comprehensive regression diagnostics, interactive Bayesian updating, and exportable methodology reports.
"""

import numpy as np
import pandas as pd
import scipy.stats as stats
import streamlit as st

try:
    import statsmodels.api as sm
    from statsmodels.formula.api import ols
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


def generate_ai_interpretation(test_name, p_value, effect=None, assumption_warning=None):
    sig = p_value < 0.05
    narrative = (
        f"> **Executive Summary:** The **{test_name}** result is "
        f"{'**statistically significant** (p < 0.05)' if sig else 'not statistically significant (p ≥ 0.05)'} "
        f"with p = **{p_value:.5f}**."
    )
    if sig:
        narrative += "\n> **Key Takeaway:** Reject $H_0$ — sufficient evidence of a reliable effect."
    else:
        narrative += "\n> **Key Takeaway:** Fail to reject $H_0$ — insufficient evidence of an effect."
    
    if effect is not None:
        narrative += f"\n> **Effect Size / Metric:** `{effect:.4f}`"
        
    if assumption_warning:
        narrative += f"\n> **⚠️ Assumption Notice:** {assumption_warning}"
        
    return narrative


def check_normality_shapiro(series):
    """Runs Shapiro-Wilk normality test on clean numeric series."""
    clean = series.dropna()
    if len(clean) < 3:
        return True, "Insufficient data for normality check."
    if len(clean) > 5000:
        # Shapiro-Wilk can be overly sensitive on very large N, sample or use alternative
        clean = clean.sample(5000, random_state=42)
    stat, p = stats.shapiro(clean)
    is_normal = p > 0.05
    msg = f"Shapiro-Wilk p = {p:.4f} ({'Normal distribution assumed' if is_normal else 'Departure from normality detected'})"
    return is_normal, msg


def render_param_tests(df):
    """Parametric tests tab with pre-flight assumption validation."""
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
            
            # Pre-flight checks
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
                if len(groups) == 2:
                    equal_var = levene_p > 0.05
                    stat_val, p_val = stats.ttest_ind(groups[0], groups[1], equal_var=equal_var)
                    
                    # Compute Cohen's d effect size
                    n1, n2 = len(groups[0]), len(groups[1])
                    s1, s2 = np.std(groups[0], ddof=1), np.std(groups[1], ddof=1)
                    pooled_sd = np.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2)) if (n1 + n2 - 2) > 0 else 1.0
                    cohens_d = (np.mean(groups[0]) - np.mean(groups[1])) / pooled_sd if pooled_sd > 0 else 0.0

                    col_m1, col_m2 = st.columns(2)
                    col_m1.metric("t-Statistic", f"{stat_val:.4f}")
                    col_m2.metric("P-Value", f"{p_val:.6f}")
                    st.metric("Cohen's d Effect Size", f"{cohens_d:.4f}")
                    
                    warning = None if equal_var else "Equal variance assumption violated; Welch's t-test variant applied."
                    st.markdown(generate_ai_interpretation("Independent t-Test", p_val, effect=cohens_d, assumption_warning=warning))
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
                
                # Effect size: Cohen's d for paired samples (mean difference / std of differences)
                diff_series = clean_df[after] - clean_df[before]
                cohens_d_paired = diff_series.mean() / diff_series.std(ddof=1) if diff_series.std(ddof=1) > 0 else 0.0

                st.metric("t-Statistic", f"{stat_val:.4f}")
                st.metric("P-Value", f"{p_val:.6f}")
                st.metric("Cohen's d (Paired)", f"{cohens_d_paired:.4f}")
                st.markdown(generate_ai_interpretation("Paired t-Test", p_val, effect=cohens_d_paired))
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
                    st.markdown(generate_ai_interpretation("One-Way ANOVA", p_val, effect=f_val))
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
                    st.markdown(generate_ai_interpretation("Two-Way ANOVA", anova_table["PR(>F)"].iloc[0]))
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
                st.markdown(generate_ai_interpretation("Pearson Correlation", p, effect=r))
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
                    
                    # Additional diagnostic summary
                    r_sq = model.rsquared
                    adj_r_sq = model.rsquared_adj
                    f_stat = model.fvalue
                    f_p = model.f_pvalue
                    st.metric("R-Squared", f"{r_sq:.4f}")
                    st.metric("Adjusted R-Squared", f"{adj_r_sq:.4f}")
                    st.markdown(generate_ai_interpretation("Multiple OLS Regression", f_p, effect=r_sq))
                except Exception as e:
                    st.error(f"Regression error: {e}")
        else:
            st.info("Need at least 2 numeric variables and statsmodels.")


def render_nonparam_tests(df):
    """Non-parametric tests tab."""
    section_header("Non-Parametric Tests", "Distribution-free hypothesis testing with exact test options.")

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
                chi2, p, dof, ex = stats.chi2_contingency(ct)
                st.metric("Chi-Square", f"{chi2:.4f}")
                st.metric("P-Value", f"{p:.6f}")
                
                # Check expected frequencies assumption (> 5 in 80% of cells)
                low_exp = (ex < 5).sum()
                total_cells = ex.size
                warning = f"Expected frequency count: {low_exp}/{total_cells} cells have < 5 expected counts." if low_exp > 0 else None
                
                st.markdown(generate_ai_interpretation("Chi-Square Test of Independence", p, effect=chi2, assumption_warning=warning))
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
                st.markdown(generate_ai_interpretation("Spearman Correlation", p, effect=rho))
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
                    st.markdown(generate_ai_interpretation("Fisher's Exact Test", p_val, effect=or_val))
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
                else:
                    st.error("Requires 2×2 binary table.")
        else:
            st.info("Need 2 binary categorical variables.")


def render_advanced_tests(df):
    """Advanced analytics tab: causal, Bayesian, sensitivity, bootstrap, power."""
    section_header("Advanced Inference Engines", "Causal econometrics, interactive Bayesian updates, sensitivity sweeps, bootstrap CIs, and power calculations.")

    tab_causal, tab_bayes, tab_sens, tab_boot, tab_power = st.tabs([
        "🔬 Causal Inference", "🧠 Bayesian", "🔍 Sensitivity", "🔄 Bootstrap", "📐 Power & Sample Size",
    ])

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    with tab_causal:
        st.markdown("#### Causal Inference & Econometric Control Engine")
        st.info("Evaluate adjusted treatment effects controlling for measured confounding variables.")
        if len(numeric_cols) >= 3 and STATSMODELS_AVAILABLE:
            outcome = st.selectbox("Outcome variable", numeric_cols, key="causal_y")
            predictor = st.selectbox("Treatment / Predictor", [c for c in numeric_cols if c != outcome], key="causal_x")
            confounders = st.multiselect("Confounders (Control covariates)", [c for c in numeric_cols if c not in [outcome, predictor]], key="causal_z")
            if st.button("▶️ Run Causal Regression Model", type="primary", key="run_causal"):
                try:
                    cols = [predictor] + confounders
                    X = sm.add_constant(df[cols].dropna())
                    y = df.loc[X.index, outcome]
                    model = sm.OLS(y, X).fit()
                    st.text(str(model.summary()))
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
            prior_mean = c1.number_input("Prior Mean ($\mu_0$)", value=50.0, key="bayes_prior_mean")
            prior_var = c2.number_input("Prior Variance ($\sigma_0^2$)", value=10.0, key="bayes_prior_var")
            
            if st.button("▶️ Compute Exact Posterior", type="primary", key="run_bayes"):
                data = df[col].dropna()
                n = len(data)
                sample_mean = data.mean()
                sample_var = data.var(ddof=1) if n > 1 else 1.0
                
                # Normal-Normal Conjugate Update formulas
                if prior_var > 0 and sample_var > 0:
                    precision_prior = 1.0 / prior_var
                    precision_data = n / sample_var
                    posterior_precision = precision_prior + precision_data
                    posterior_var = 1.0 / posterior_precision
                    posterior_mean = posterior_var * (precision_prior * prior_mean + precision_data * sample_mean)
                    
                    st.metric("Sample Mean", f"{sample_mean:.3f}")
                    st.metric("Posterior Mean ($\mu_n$)", f"{posterior_mean:.3f}")
                    st.metric("Posterior Variance ($\sigma_n^2$)", f"{posterior_var:.4f}")
                    st.markdown(
                        f"> **Bayesian Update Summary:** Prior $\sim N({prior_mean}, {prior_var})$ updated with "
                        f"$N={n}$, sample mean ${sample_mean:.3f} \\rightarrow$ Posterior $N({posterior_mean:.3f}, {posterior_var:.4f})$."
                    )
                else:
                    st.error("Variance parameters must be strictly greater than zero.")
        else:
            st.info("Need a numeric variable.")

    with tab_sens:
        st.markdown("#### Sensitivity & Multiverse Analysis Sweep")
        st.caption("Stress-test statistical findings across multiple specification variants.")
        if len(numeric_cols) >= 2:
            y = st.selectbox("Outcome", numeric_cols, key="sens_y")
            x = st.selectbox("Predictor", [c for c in numeric_cols if c != y], key="sens_x")
            n_variants = st.slider("Specification count", 5, 30, 10, key="sens_n")
            if st.button("▶️ Execute Multiverse Sweep", type="primary", key="run_sens"):
                results = []
                for i in range(n_variants):
                    rng = np.random.RandomState(42 + i)
                    # Simulated specification variation
                    r_val, p_val = stats.pearsonr(df[y].dropna() + rng.normal(0, 0.1 * i, len(df[y].dropna())), df[x].dropna())
                    results.append({"Specification": i + 1, "Coefficient": round(r_val, 4), "P-Value": round(p_val, 4), "Robust": p_val < 0.05})
                res_df = pd.DataFrame(results)
                st.dataframe(res_df, use_container_width=True, hide_index=True)
                robust_pct = res_df["Robust"].mean() * 100
                st.metric("Specification Robustness Rate", f"{robust_pct:.1f}%")
        else:
            st.info("Need 2 numeric variables.")

    with tab_boot:
        st.markdown("#### Bootstrap Non-Parametric Resampling")
        st.caption("Generate empirical confidence intervals via iterative bootstrap resampling.")
        if len(numeric_cols) >= 1:
            col = st.selectbox("Variable to bootstrap", numeric_cols, key="boot_col")
            n_boot = st.slider("Bootstrap iterations", 200, 5000, 1000, key="boot_n")
            if st.button("▶️ Run Bootstrap Engine", type="primary", key="run_boot"):
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
        effect_size = st.selectbox("Expected Effect Size", ["Small (d=0.2)", "Medium (d=0.5)", "Large (d=0.8)"], key="power_effect")
        alpha = st.selectbox("Significance Level ($\alpha$)", [0.01, 0.05, 0.10], key="power_alpha")
        power = st.slider("Target Statistical Power ($1 - \beta$)", 0.70, 0.99, 0.80, 0.05, key="power_target")
        if st.button("▶️ Calculate Required N", type="primary", key="run_power"):
            d = {"Small (d=0.2)": 0.2, "Medium (d=0.5)": 0.5, "Large (d=0.8)": 0.8}[effect_size]
            z_alpha = stats.norm.ppf(1 - alpha / 2)
            z_beta = stats.norm.ppf(power)
            n_per_group = int(2 * ((z_alpha + z_beta) ** 2) / (d ** 2))
            st.metric("Required Sample Size Per Group", f"{n_per_group:,}")
            st.metric("Total Study Sample Size", f"{n_per_group * 2:,}")
            st.markdown(f"> **Design Parameters:** Cohen's $d={d}$, $\alpha={alpha}$, Target Power={power:.2f}")


def render_methodology_tab():
    """Methodology advisor tab with report export."""
    section_header("🧠 Methodology Advisor & Decision Tree", "Automated research design matching and test recommendation engine.")

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

    if st.button("🚀 Recommend Statistical Procedure", type="primary", key="run_meth"):
        rec = ""
        rationale = ""
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
                    rec = "One-Way ANOVA"
                    rationale = "Parametric comparison across 3 or more independent groups."
                else:
                    rec = "Kruskal-Wallis H Test"
                    rationale = "Non-parametric comparison across 3 or more independent groups."
        elif "Association" in objective:
            if "Normal" in distribution:
                rec = "Pearson Correlation Coefficient"
                rationale = "Linear association between continuous normally distributed variables."
            else:
                rec = "Spearman Rank Correlation"
                rationale = "Monotonic association for non-normal or ordinal data."
        elif "Predict" in objective:
            rec = "Multiple Linear Regression (Continuous) / Logistic Regression (Binary)"
            rationale = "Multivariate modeling to estimate expected values or probabilities."
        else:
            rec = "Chi-Square Test of Independence / Fisher's Exact Test"
            rationale = "Frequency analysis for contingency table categorical distributions."

        st.success(f"✅ **Recommended Procedure:** {rec}")
        st.info(f"💡 **Methodological Rationale:** {rationale}")
        
        # Save to session state for export
        st.session_state["last_methodology_rec"] = {
            "objective": objective,
            "recommendation": rec,
            "rationale": rationale,
            "timestamp": pd.Timestamp.now().isoformat()
        }

    if "last_methodology_rec" in st.session_state:
        st.markdown("---")
        st.markdown("#### 📥 Export Methodology Decision Report")
        rec_data = st.session_state["last_methodology_rec"]
        report_df = pd.DataFrame([rec_data])
        render_export_buttons(report_df, base_name="methodology_recommendation_report")


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription()

    setup_page("Statistics Studio", "📊", initial_sidebar_state="expanded")

    hero_card(
        "📊 Enterprise Statistics Studio (Upgraded)",
        "Consolidated statistical hub featuring pre-flight assumption validation, effect size computations, causal econometrics, interactive Bayesian updating, and exportable methodology reports.",
        badge_text="STATISTICS STUDIO • PREMIUM BEST TIER",
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