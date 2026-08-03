
"""
Dynamic Hypothesis & Parameter Simulator
Converts mathematical formulas and statistical relationships described in papers
into interactive visual sliders. Users can vary parameters like sample size,
confidence intervals, or dosage levels to see predicted outcomes.
"""
from __future__ import annotations

import math, re
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import pandas as pd


class HypothesisSimulator:
    """
    Interactive mathematical and conceptual modeler for paper findings.
    Converts formulas/relationships into visual sliders.
    """

    def __init__(self):
        self.simulations: Dict[str, Any] = {}

    def simulate_power_analysis(self, effect_size: float = 0.5, alpha: float = 0.05,
                                 power: float = 0.80, n_per_group: int = 30) -> Dict[str, Any]:
        """Simulate statistical power for a two-sample t-test."""
        from scipy import stats as scipy_stats
        from statsmodels.stats.power import TTestIndPower

        analysis = TTestIndPower()
        n_range = range(5, min(500, max(50, n_per_group * 3)), 5)
        power_curve = []
        for n in n_range:
            p = analysis.solve_power(effect_size=effect_size, alpha=alpha, power=None, nobs1=n)
            power_curve.append({"sample_size": n, "power": round(float(p), 4)})

        required_n = analysis.solve_power(effect_size=effect_size, alpha=alpha, power=power)
        detected_effect = analysis.solve_power(effect_size=None, alpha=alpha, power=power, nobs1=n_per_group)

        return {
            "type": "Power Analysis",
            "parameters": {"effect_size": effect_size, "alpha": alpha, "power": power, "n_per_group": n_per_group},
            "required_n_per_group": int(np.ceil(required_n)) if not np.isnan(required_n) else None,
            "detectable_effect_size": round(float(detected_effect), 3) if not np.isnan(detected_effect) else None,
            "power_curve": power_curve,
            "interpretation": f"Need {int(np.ceil(required_n))} participants per group to detect d={effect_size} with {power*100:.0f}% power (Î±={alpha})" if not np.isnan(required_n) else "Adjust parameters to compute required sample size",
        }

    def simulate_dosage_response(self, base_effect: float = 0.3, max_dose: float = 100,
                                  ec50: float = 50, hill_coefficient: float = 1.0,
                                  noise_level: float = 0.05) -> Dict[str, Any]:
        """Simulate a dose-response curve using the Hill equation."""
        doses = np.linspace(0, max_dose, 50)
        responses = base_effect  (1 - base_effect) / (1  (ec50 / (doses  1e-10)) ** hill_coefficient)
        noise = np.random.normal(0, noise_level, len(doses))
        noisy_responses = responses  noise

        curve_data = [{"dose": float(d), "response": float(r), "noisy_response": float(nr)}
                      for d, r, nr in zip(doses, responses, noisy_responses)]

        return {
            "type": "Dose-Response",
            "parameters": {"base_effect": base_effect, "max_dose": max_dose, "ec50": ec50, "hill_coefficient": hill_coefficient},
            "curve_data": curve_data,
            "ec50_effect": float(base_effect  (1 - base_effect) / 2),
            "interpretation": f"EC50 = {ec50} (half-maximal effect at dose {ec50})",
        }

    def simulate_correlation(self, n: int = 100, r: float = 0.5, noise: float = 1.0) -> Dict[str, Any]:
        """Simulate correlated bivariate data."""
        mean = [0, 0]; cov = [[1, r], [r, 1]]
        data = np.random.multivariate_normal(mean, cov, size=n)
        df = pd.DataFrame({"X": data[:, 0], "Y": data[:, 1]})
        observed_r = np.corrcoef(data[:, 0], data[:, 1])[0, 1]
        return {
            "type": "Correlation Simulation",
            "parameters": {"n": n, "true_r": r, "noise": noise},
            "simulated_data": df,
            "observed_r": round(float(observed_r), 3),
            "interpretation": f"Simulated {n} observations with true r={r}. Observed r={observed_r:.3f}",
        }

    def simulate_confidence_interval(self, effect_size: float = 0.5, n: int = 50,
                                      ci_level: float = 0.95, n_simulations: int = 1000) -> Dict[str, Any]:
        """Simulate confidence interval coverage."""
        from scipy import stats as scipy_stats
        coverages = []
        for _ in range(n_simulations):
            data = np.random.normal(effect_size, 1, n)
            ci = scipy_stats.t.interval(ci_level, df=n-1, loc=np.mean(data), scale=scipy_stats.sem(data))
            covers = ci[0] <= effect_size <= ci[1]
            coverages.append(covers)
        coverage_rate = sum(coverages) / n_simulations
        return {
            "type": "Confidence Interval Simulation",
            "parameters": {"effect_size": effect_size, "n": n, "ci_level": ci_level, "n_simulations": n_simulations},
            "coverage_rate": round(float(coverage_rate), 3),
            "expected_coverage": ci_level,
            "interpretation": f"CI coverage: {coverage_rate:.1%} (expected {ci_level:.0%})",
        }

    def simulate_regression(self, n: int = 100, beta_0: float = 0.0, beta_1: float = 1.5,
                             noise_sd: float = 1.0) -> Dict[str, Any]:
        """Simulate simple linear regression data."""
        X = np.random.normal(0, 1, n)
        y = beta_0  beta_1 * X  np.random.normal(0, noise_sd, n)
        df = pd.DataFrame({"X": X, "Y": y})
        from scipy import stats as scipy_stats
        slope, intercept, r_val, p_val, std_err = scipy_stats.linregress(X, y)
        r2 = r_val ** 2
        return {
            "type": "Regression Simulation",
            "parameters": {"n": n, "intercept": beta_0, "slope": beta_1, "noise_sd": noise_sd},
            "simulated_data": df,
            "estimated_slope": round(float(slope), 3),
            "estimated_intercept": round(float(intercept), 3),
            "r_squared": round(float(r2), 3),
            "p_value": round(float(p_val), 4),
            "interpretation": f"Simulated Y = {beta_0}  {beta_1}Â·X  Îµ. Estimated slope = {slope:.3f} (p={p_val:.4f}), RÂ² = {r2:.3f}",
        }

    def simulate_bias_impact(self, true_effect: float = 0.5, bias_strength: float = 0.2,
                               n_studies: int = 50, publication_bias: bool = True) -> Dict[str, Any]:
        """Simulate how bias affects meta-analytic estimates."""
        np.random.seed(42)
        studies = []
        published_only = []
        for i in range(n_studies):
            se = np.random.uniform(0.1, 0.5)
            bias = np.random.normal(bias_strength, 0.1)
            observed = np.random.normal(true_effect  bias, se)
            p_value = 2 * (1 - __import__('scipy').stats.norm.cdf(abs(observed) / se))
            study = {"study": f"Study {i1}", "observed_effect": round(float(observed), 3),
                     "se": round(float(se), 3), "p_value": round(float(p_value), 4),
                     "significant": p_value < 0.05}
            studies.append(study)
            if not publication_bias or p_value < 0.05:
                published_only.append(study)

        # Average effects
        all_mean = np.mean([s["observed_effect"] for s in studies])
        pub_mean = np.mean([s["observed_effect"] for s in published_only]) if published_only else 0

        return {
            "type": "Bias Simulation",
            "parameters": {"true_effect": true_effect, "bias_strength": bias_strength,
                          "n_studies": n_studies, "publication_bias": publication_bias},
            "all_studies_mean": round(float(all_mean), 3),
            "published_mean": round(float(pub_mean), 3),
            "true_effect": true_effect,
            "bias_impact": round(float(pub_mean - true_effect), 3),
            "studies": studies,
            "published_only": published_only,
            "interpretation": f"True effect={true_effect}. Published mean={pub_mean:.3f}"  (f" (bias: {pub_mean-true_effect:.3f})" if publication_bias else ""),
        }


def render_hypothesis_simulator_ui():
    """Render the Hypothesis Simulator UI."""
    import streamlit as st
    import plotly.graph_objects as go
    import plotly.express as px

    st.markdown("## ðŸ§® Dynamic Hypothesis & Parameter Simulator")
    st.markdown("*Interactive mathematical modeler  vary parameters to see predicted outcomes*")

    sim = HypothesisSimulator()

    sim_type = st.radio("Select simulation type", [
        " Power Analysis", "ðŸ’Š Dose-Response", "ðŸ”— Correlation",
        "ðŸ“ Confidence Intervals", "ðŸ“ˆ Regression", "âš ï¸ Bias Impact"
    ], horizontal=True, key="sim_type_hyp")

    if sim_type == " Power Analysis":
        st.subheader(" Statistical Power Analysis Simulator")
        col1, col2 = st.columns(2)
        with col1:
            es = st.slider("Effect size (Cohen's d)", 0.1, 2.0, 0.5, 0.05, key="sim_power_es")
            alpha = st.select_slider("Alpha (Î±)", options=[0.001, 0.01, 0.05, 0.10], value=0.05, key="sim_power_alpha")
        with col2:
            power_target = st.slider("Target power (1-Î²)", 0.50, 0.99, 0.80, 0.05, key="sim_power_target")
            n_current = st.slider("Current N per group", 5, 500, 30, 5, key="sim_power_n")

        if st.button("â–¶ï¸ Run Power Simulation", type="primary"):
            result = sim.simulate_power_analysis(es, alpha, power_target, n_current)
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Required N per group", result.get("required_n_per_group", "N/A"))
            with col2:
                st.metric("Detectable effect size", result.get("detectable_effect_size", "N/A"))
            st.info(result["interpretation"])
            power_df = pd.DataFrame(result["power_curve"])
            if not power_df.empty:
                fig = px.line(power_df, x="sample_size", y="power", title="Power Curve")
                fig.add_hline(y=power_target, line_dash="dash", line_color="red", annotation_text=f"Target: {power_target:.0%}")
                fig.update_layout(xaxis_title="Sample Size (per group)", yaxis_title="Power")
                st.plotly_chart(fig, use_container_width=True)

    elif sim_type == "ðŸ’Š Dose-Response":
        st.subheader("ðŸ’Š Dose-Response Curve Simulator")
        col1, col2 = st.columns(2)
        with col1:
            base = st.slider("Baseline effect", 0.0, 0.5, 0.3, 0.05, key="sim_dose_base")
            max_d = st.slider("Max dose", 10, 500, 100, 10, key="sim_dose_max")
        with col2:
            ec50 = st.slider("EC50 (half-max dose)", 5, 200, 50, 5, key="sim_dose_ec50")
            hill = st.slider("Hill coefficient (steepness)", 0.5, 5.0, 1.0, 0.1, key="sim_dose_hill")

        if st.button("â–¶ï¸ Run Dose-Response Simulation", type="primary"):
            result = sim.simulate_dosage_response(base, max_d, ec50, hill)
            curve_df = pd.DataFrame(result["curve_data"])
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=curve_df["dose"], y=curve_df["response"], mode="lines", name="True curve", line=dict(width=3)))
            fig.add_trace(go.Scatter(x=curve_df["dose"], y=curve_df["noisy_response"], mode="markers", name="Observed (with noise)", marker=dict(size=4, opacity=0.6)))
            fig.add_vline(x=ec50, line_dash="dash", line_color="red", annotation_text=f"EC50={ec50}")
            fig.update_layout(title="Dose-Response Curve", xaxis_title="Dose", yaxis_title="Response")
            st.plotly_chart(fig, use_container_width=True)
            st.info(result["interpretation"])

    elif sim_type == "ðŸ”— Correlation":
        st.subheader("ðŸ”— Correlation Simulator")
        col1, col2 = st.columns(2)
        with col1:
            n_corr = st.slider("Sample size (N)", 10, 500, 100, 10, key="sim_corr_n")
        with col2:
            r_true = st.slider("True correlation (Ï)", -1.0, 1.0, 0.5, 0.05, key="sim_corr_r")

        if st.button("â–¶ï¸ Generate Simulated Correlation", type="primary"):
            result = sim.simulate_correlation(n_corr, r_true)
            df_sim = result["simulated_data"]
            fig = px.scatter(df_sim, x="X", y="Y", trendline="ols", title=f"Simulated: r = {r_true:.2f}, Observed: r = {result['observed_r']:.3f}")
            st.plotly_chart(fig, use_container_width=True)
            st.metric("Observed r", f"{result['observed_r']:.3f}")
            st.info(result["interpretation"])

    elif sim_type == "ðŸ“ Confidence Intervals":
        st.subheader("ðŸ“ Confidence Interval Coverage Simulator")
        col1, col2 = st.columns(2)
        with col1:
            es_ci = st.slider("True effect size", 0.0, 2.0, 0.5, 0.05, key="sim_ci_es")
            n_ci = st.slider("Sample size", 5, 200, 50, 5, key="sim_ci_n")
        with col2:
            ci_level = st.select_slider("Confidence level", options=[0.80, 0.90, 0.95, 0.99], value=0.95, key="sim_ci_level")
            n_sim = st.slider("Number of simulations", 100, 5000, 1000, 100, key="sim_ci_nsim")

        if st.button("â–¶ï¸ Run CI Simulation", type="primary"):
            result = sim.simulate_confidence_interval(es_ci, n_ci, ci_level, n_sim)
            col1, col2 = st.columns(2)
            with col1: st.metric("Coverage Rate", f"{result['coverage_rate']:.1%}")
            with col2: st.metric("Expected", f"{result['expected_coverage']:.0%}")
            st.info(result["interpretation"])

    elif sim_type == "ðŸ“ˆ Regression":
        st.subheader("ðŸ“ˆ Linear Regression Simulator")
        col1, col2 = st.columns(2)
        with col1:
            n_reg = st.slider("Sample size", 10, 500, 100, 10, key="sim_reg_n")
            b0 = st.number_input("True intercept (Î²â‚€)", value=0.0, step=0.5, key="sim_reg_b0")
        with col2:
            b1 = st.number_input("True slope (Î²â‚)", value=1.5, step=0.5, key="sim_reg_b1")
            noise = st.slider("Noise (Ïƒ)", 0.1, 5.0, 1.0, 0.1, key="sim_reg_noise")

        if st.button("â–¶ï¸ Generate Regression Data", type="primary"):
            result = sim.simulate_regression(n_reg, b0, b1, noise)
            df_reg = result["simulated_data"]
            fig = px.scatter(df_reg, x="X", y="Y", trendline="ols", title=f"True: Y = {b0}  {b1}X | Estimated: slope = {result['estimated_slope']:.3f}")
            st.plotly_chart(fig, use_container_width=True)
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("Estimated Slope", f"{result['estimated_slope']:.3f}")
            with col2: st.metric("RÂ²", f"{result['r_squared']:.3f}")
            with col3: st.metric("P-value", f"{result['p_value']:.4f}")
            st.info(result["interpretation"])

    elif sim_type == "âš ï¸ Bias Impact":
        st.subheader("âš ï¸ Publication Bias Simulator")
        col1, col2 = st.columns(2)
        with col1:
            true_eff = st.slider("True effect size", 0.0, 1.0, 0.5, 0.05, key="sim_bias_true")
            bias_str = st.slider("Bias strength", 0.0, 1.0, 0.2, 0.05, key="sim_bias_str")
        with col2:
            n_studies_bias = st.slider("Number of studies", 10, 200, 50, 5, key="sim_bias_n")
            pub_bias = st.checkbox("Apply publication bias (only sig. results published)", value=True, key="sim_bias_pub")

        if st.button("â–¶ï¸ Run Bias Simulation", type="primary"):
            result = sim.simulate_bias_impact(true_eff, bias_str, n_studies_bias, pub_bias)
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("True Effect", f"{result['true_effect']:.3f}")
            with col2: st.metric("All Studies Mean", f"{result['all_studies_mean']:.3f}")
            with col3: st.metric("Published Mean", f"{result['published_mean']:.3f}")
            if pub_bias:
                st.warning(f"âš ï¸ Publication bias inflates estimate by {result['bias_impact']:.3f}")
            st.info(result["interpretation"])

