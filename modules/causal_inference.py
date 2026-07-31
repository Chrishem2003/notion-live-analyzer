"""
Causal Inference Engine — Estimate causal effects from observational data.
Provides propensity score matching, difference-in-differences, instrumental variable
regression, regression discontinuity, DAG specification, and ATE/ATT/CATE estimation.
"""
from __future__ import annotations

from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
import math
import warnings
warnings.filterwarnings('ignore')

try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    from sklearn.linear_model import LogisticRegression, LinearRegression
    from sklearn.neighbors import NearestNeighbors
    from sklearn.ensemble import GradientBoostingRegressor
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    import statsmodels.api as sm
    from statsmodels.sandbox.regression.gmm import IV2SLS
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False


class CausalInferenceEngine:
    """
    Estimate causal effects from observational data using multiple methods.
    """

    def __init__(self):
        self._check_deps()

    def _check_deps(self):
        if not HAS_SKLEARN:
            raise ImportError("scikit-learn required. Install: pip install scikit-learn")

    # ─── Propensity Score Matching ─────────────────────────────────
    def propensity_score_matching(
        self,
        df: pd.DataFrame,
        treatment_col: str,
        outcome_col: str,
        covariates: List[str],
        method: str = "logistic",
        n_neighbors: int = 1,
        caliper: float = 0.05,
    ) -> Dict[str, Any]:
        """
        Estimate Average Treatment Effect on the Treated (ATT)
        using propensity score matching.

        Steps:
        1. Estimate propensity scores (P(treatment | covariates))
        2. Match each treated unit to nearest control(s)
        3. Compare outcomes within matched pairs
        """
        # Prepare data
        data = df[[treatment_col, outcome_col] + covariates].dropna()
        if len(data) < 10:
            return {"error": "Need at least 10 complete observations"}

        T = data[treatment_col].values
        Y = data[outcome_col].values
        X = data[covariates].values

        # Step 1: Estimate propensity scores
        if method == "logistic":
            model = LogisticRegression(max_iter=1000, random_state=42)
            model.fit(X, T)
            pscores = model.predict_proba(X)[:, 1]
        elif method == "gradient_boosting":
            model = GradientBoostingRegressor(n_estimators=100, random_state=42)
            model.fit(X, T)
            pscores = model.predict(X)
            pscores = np.clip(pscores, 0.01, 0.99)
        else:
            return {"error": f"Unknown method: {method}"}

        # Split treated and control
        treated_idx = np.where(T == 1)[0]
        control_idx = np.where(T == 0)[0]

        if len(treated_idx) == 0 or len(control_idx) == 0:
            return {"error": "Need both treated and control units"}

        ps_treated = pscores[treated_idx]
        ps_control = pscores[control_idx]

        # Step 2: Nearest neighbor matching
        nn = NearestNeighbors(n_neighbors=min(n_neighbors, len(control_idx)), metric='euclidean')
        nn.fit(ps_control.reshape(-1, 1))

        distances, matches = nn.kneighbors(ps_treated.reshape(-1, 1))

        # Apply caliper
        valid_matches = distances <= caliper
        matched_pairs = []

        for i, t_idx in enumerate(treated_idx):
            for j in range(n_neighbors):
                if valid_matches[i, j]:
                    c_idx = control_idx[matches[i, j]]
                    matched_pairs.append((t_idx, c_idx))

        if not matched_pairs:
            return {"error": "No matches found within caliper. Try increasing caliper."}

        # Step 3: Compute ATT
        treated_outcomes = np.array([Y[p[0]] for p in matched_pairs])
        control_outcomes = np.array([Y[p[1]] for p in matched_pairs])
        att = np.mean(treated_outcomes - control_outcomes)

        # Bootstrap SE
        n_bootstrap = 500
        boot_att = []
        for _ in range(n_bootstrap):
            idx = np.random.choice(len(matched_pairs), len(matched_pairs), replace=True)
            boot_att.append(np.mean(treated_outcomes[idx] - control_outcomes[idx]))
        att_se = np.std(boot_att)
        att_z = att / att_se if att_se > 0 else 0
        att_p = 2 * (1 - scipy_stats.norm.cdf(abs(att_z))) if HAS_SCIPY else 1.0

        # Balance check (standardized mean differences)
        balance = {}
        for i, cov in enumerate(covariates):
            treated_vals = data.iloc[[p[0] for p in matched_pairs]][cov].values
            control_vals = data.iloc[[p[1] for p in matched_pairs]][cov].values
            smd = (np.mean(treated_vals) - np.mean(control_vals)) / \
                  np.sqrt((np.var(treated_vals) + np.var(control_vals)) / 2) if \
                  (np.var(treated_vals) + np.var(control_vals)) > 0 else 0
            balance[cov] = round(float(abs(smd)), 4)

        return {
            "method": f"Propensity Score Matching ({method})",
            "estimand": "ATT",
            "att": round(float(att), 4),
            "se": round(float(att_se), 4),
            "z_value": round(float(att_z), 4),
            "p_value": round(float(att_p), 4),
            "n_matched_pairs": len(matched_pairs),
            "n_treated": int(np.sum(T)),
            "n_control": int(np.sum(1 - T)),
            "significant": float(att_p) < 0.05,
            "balance_smd": balance,
            "matched_pairs": matched_pairs[:10],  # Preview
            "interpretation": f"Treatment effect (ATT) = {att:.3f} (SE = {att_se:.3f}, p = {att_p:.4f})",
        }

    # ─── Difference-in-Differences ─────────────────────────────────
    def difference_in_differences(
        self,
        df: pd.DataFrame,
        treatment_col: str,
        time_col: str,
        outcome_col: str,
        unit_col: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Difference-in-Differences estimation.
        Requires: pre/post time periods, treated/control groups.
        y = β₀ + β₁*Treat + β₂*Post + β₃*(Treat×Post) + ε
        """
        if not HAS_STATSMODELS:
            return {"error": "statsmodels required for DiD. Install: pip install statsmodels"}

        data = df[[treatment_col, time_col, outcome_col]].dropna()

        # Create interaction term
        data['treat_x_post'] = data[treatment_col] * data[time_col]

        X = sm.add_constant(data[[treatment_col, time_col, 'treat_x_post']])
        y = data[outcome_col]

        model = sm.OLS(y, X).fit()

        # DiD coefficient is the interaction term
        did_coef = model.params.get('treat_x_post', 0)
        did_se = model.bse.get('treat_x_post', 0)
        did_p = model.pvalues.get('treat_x_post', 1.0)
        did_t = did_coef / did_se if did_se > 0 else 0

        # Means by group/time
        treated_pre = data[(data[treatment_col] == 1) & (data[time_col] == 0)][outcome_col].mean()
        treated_post = data[(data[treatment_col] == 1) & (data[time_col] == 1)][outcome_col].mean()
        control_pre = data[(data[treatment_col] == 0) & (data[time_col] == 0)][outcome_col].mean()
        control_post = data[(data[treatment_col] == 0) & (data[time_col] == 1)][outcome_col].mean()

        return {
            "method": "Difference-in-Differences",
            "estimand": "ATT",
            "did_estimate": round(float(did_coef), 4),
            "se": round(float(did_se), 4),
            "t_value": round(float(did_t), 4),
            "p_value": round(float(did_p), 4),
            "significant": float(did_p) < 0.05,
            "treated_pre_mean": round(float(treated_pre), 4),
            "treated_post_mean": round(float(treated_post), 4),
            "control_pre_mean": round(float(control_pre), 4),
            "control_post_mean": round(float(control_post), 4),
            "r_squared": round(float(model.rsquared), 4),
            "n_obs": int(model.nobs),
            "interpretation": f"DiD estimate = {did_coef:.3f} (SE = {did_se:.3f}, p = {did_p:.4f})",
        }

    # ─── Instrumental Variable Regression ──────────────────────────
    def instrumental_variable(
        self,
        df: pd.DataFrame,
        outcome_col: str,
        treatment_col: str,
        instrument_col: str,
        covariates: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Two-Stage Least Squares (2SLS) IV regression.
        """
        if not HAS_STATSMODELS:
            return {"error": "statsmodels required for IV regression"}

        data = df[[outcome_col, treatment_col, instrument_col] + (covariates or [])].dropna()

        try:
            # First stage: regress treatment on instrument
            X1 = data[[instrument_col] + (covariates or [])]
            X1 = sm.add_constant(X1)
            y1 = data[treatment_col]
            first_stage = sm.OLS(y1, X1).fit()
            data['treatment_hat'] = first_stage.fittedvalues

            # Second stage: regress outcome on predicted treatment
            X2 = data[['treatment_hat'] + (covariates or [])]
            X2 = sm.add_constant(X2)
            y2 = data[outcome_col]
            second_stage = sm.OLS(y2, X2).fit()

            iv_coef = second_stage.params.get('treatment_hat', 0)
            iv_se = second_stage.bse.get('treatment_hat', 0)
            iv_p = second_stage.pvalues.get('treatment_hat', 1.0)
            iv_t = iv_coef / iv_se if iv_se > 0 else 0

            # First stage F-statistic (weak instrument test)
            f_stat = first_stage.fvalue if hasattr(first_stage, 'fvalue') else 0

            return {
                "method": "Instrumental Variable (2SLS)",
                "iv_estimate": round(float(iv_coef), 4),
                "se": round(float(iv_se), 4),
                "t_value": round(float(iv_t), 4),
                "p_value": round(float(iv_p), 4),
                "significant": float(iv_p) < 0.05,
                "first_stage_f_stat": round(float(f_stat), 4),
                "first_stage_rsquared": round(float(first_stage.rsquared), 4),
                "second_stage_rsquared": round(float(second_stage.rsquared), 4),
                "n_obs": int(second_stage.nobs),
                "weak_instrument": f_stat < 10,
                "interpretation": f"IV estimate = {iv_coef:.3f} (SE = {iv_se:.3f}, p = {iv_p:.4f})",
            }
        except Exception as e:
            return {"error": f"IV regression failed: {str(e)}"}

    # ─── Regression Discontinuity ──────────────────────────────────
    def regression_discontinuity(
        self,
        df: pd.DataFrame,
        assignment_col: str,
        outcome_col: str,
        cutoff: float,
        bandwidth: Optional[float] = None,
        polynomial_order: int = 2,
    ) -> Dict[str, Any]:
        """
        Sharp Regression Discontinuity Design.
        Estimates treatment effect at the cutoff threshold.
        """
        if not HAS_STATSMODELS:
            return {"error": "statsmodels required for RDD"}

        data = df[[assignment_col, outcome_col]].dropna()
        x = data[assignment_col].values
        y = data[outcome_col].values

        # Automatic bandwidth (Imbens-Kalyanaraman)
        if bandwidth is None:
            n = len(x)
            h_ik = 2.0 * (x.std() / n ** 0.2) if n > 0 else 1.0
            bandwidth = h_ik

        # Focus on observations within bandwidth
        mask = (x >= cutoff - bandwidth) & (x <= cutoff + bandwidth)
        x_local = x[mask]
        y_local = y[mask]
        t_local = (x_local >= cutoff).astype(float)

        if len(x_local) < 10:
            return {"error": f"Need more observations within bandwidth. Only {len(x_local)} found."}

        # Centered assignment variable
        x_centered = x_local - cutoff

        # Build polynomial features
        X_poly = np.column_stack([x_centered ** (i + 1) for i in range(polynomial_order)])
        X_design = np.column_stack([np.ones(len(x_local)), t_local, X_poly, t_local[:, None] * X_poly])

        model = sm.OLS(y_local, X_design).fit()

        # RD estimate is the coefficient on treatment
        rd_coef = model.params[1]
        rd_se = model.bse[1]
        rd_p = model.pvalues[1]
        rd_t = rd_coef / rd_se if rd_se > 0 else 0

        # Mean outcomes just below and above cutoff
        below = y_local[x_local < cutoff]
        above = y_local[x_local >= cutoff]

        return {
            "method": "Regression Discontinuity (Sharp)",
            "cutoff": cutoff,
            "bandwidth": round(float(bandwidth), 4),
            "n_within_bandwidth": len(x_local),
            "rd_estimate": round(float(rd_coef), 4),
            "se": round(float(rd_se), 4),
            "t_value": round(float(rd_t), 4),
            "p_value": round(float(rd_p), 4),
            "significant": float(rd_p) < 0.05,
            "mean_below_cutoff": round(float(np.mean(below)), 4),
            "mean_above_cutoff": round(float(np.mean(above)), 4),
            "polynomial_order": polynomial_order,
            "r_squared": round(float(model.rsquared), 4),
            "interpretation": f"RDD estimate = {rd_coef:.3f} (SE = {rd_se:.3f}, p = {rd_p:.4f})",
        }

    # ─── ATE Estimation via IPW ────────────────────────────────────
    def inverse_probability_weighting(
        self,
        df: pd.DataFrame,
        treatment_col: str,
        outcome_col: str,
        covariates: List[str],
    ) -> Dict[str, Any]:
        """
        Inverse Probability Weighting (IPW) for ATE estimation.
        P(T=1|X) estimated via logistic regression.
        ATE = E[Y * T / e(X) - Y * (1-T) / (1-e(X))]
        """
        data = df[[treatment_col, outcome_col] + covariates].dropna()

        model = LogisticRegression(max_iter=1000, random_state=42)
        model.fit(data[covariates], data[treatment_col])
        pscores = model.predict_proba(data[covariates])[:, 1]
        pscores = np.clip(pscores, 0.01, 0.99)

        T = data[treatment_col].values
        Y = data[outcome_col].values

        # IPW estimator
        ate = np.mean(Y * T / pscores - Y * (1 - T) / (1 - pscores))

        # Bootstrap SE
        n_boot = 500
        boot_ate = []
        for _ in range(n_boot):
            idx = np.random.choice(len(data), len(data), replace=True)
            ps_boot = pscores[idx]
            T_boot = T[idx]
            Y_boot = Y[idx]
            boot_ate.append(np.mean(Y_boot * T_boot / ps_boot - Y_boot * (1 - T_boot) / (1 - ps_boot)))
        ate_se = np.std(boot_ate)
        ate_z = ate / ate_se if ate_se > 0 else 0
        ate_p = 2 * (1 - scipy_stats.norm.cdf(abs(ate_z))) if HAS_SCIPY else 1.0

        return {
            "method": "Inverse Probability Weighting (IPW)",
            "estimand": "ATE",
            "ate": round(float(ate), 4),
            "se": round(float(ate_se), 4),
            "z_value": round(float(ate_z), 4),
            "p_value": round(float(ate_p), 4),
            "significant": float(ate_p) < 0.05,
            "n": len(data),
            "interpretation": f"ATE (IPW) = {ate:.3f} (SE = {ate_se:.3f}, p = {ate_p:.4f})",
        }

    # ─── DAG-based Adjustment Sets ─────────────────────────────────
    def suggest_adjustment_set(
        self,
        treatment: str,
        outcome: str,
        all_variables: List[str],
        confounders: List[str],
        mediators: Optional[List[str]] = None,
        colliders: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Suggest which variables to adjust for based on DAG specification.
        Simple implementation: user specifies causal structure, engine recommends.
        """
        mediators = mediators or []
        colliders = colliders or []

        # Variables to adjust for = confounders only (not mediators or colliders)
        adjustment_set = [c for c in confounders if c not in mediators and c not in colliders]

        # Variables to NOT adjust for
        dont_adjust = mediators + colliders + [treatment, outcome]

        return {
            "treatment": treatment,
            "outcome": outcome,
            "recommended_adjustment_set": adjustment_set,
            "minimal_adjustment": len(adjustment_set) <= 3,
            "variables_to_exclude": dont_adjust,
            "rationale": {
                "confounders_to_adjust": confounders,
                "mediators_to_exclude": mediators,
                "colliders_to_exclude": colliders,
                "note": "Adjust for confounders to block backdoor paths. "
                        "Do NOT adjust for mediators (overcontrol bias) or colliders (selection bias)."
            },
            "backdoor_criterion_satisfied": len(confounders) > 0 or len(colliders) == 0,
        }

    # ─── CATE (Heterogeneous Treatment Effects) ────────────────────
    def estimate_cate(
        self,
        df: pd.DataFrame,
        treatment_col: str,
        outcome_col: str,
        covariates: List[str],
        method: str = "dr_learner",
    ) -> Dict[str, Any]:
        """
        Estimate Conditional Average Treatment Effects (CATE).
        Uses DR-learner: doubly robust estimation for heterogeneous effects.
        """
        data = df[[treatment_col, outcome_col] + covariates].dropna()
        T = data[treatment_col].values
        Y = data[outcome_col].values
        X = data[covariates].values

        # Propensity score model
        ps_model = LogisticRegression(max_iter=1000, random_state=42)
        ps_model.fit(X, T)
        pscores = ps_model.predict_proba(X)[:, 1]
        pscores = np.clip(pscores, 0.01, 0.99)

        # Outcome models (separate for treated and control)
        treated_mask = T == 1
        control_mask = T == 0

        mu1_model = LinearRegression()
        mu0_model = LinearRegression()

        if np.sum(treated_mask) > 5:
            mu1_model.fit(X[treated_mask], Y[treated_mask])
        if np.sum(control_mask) > 5:
            mu0_model.fit(X[control_mask], Y[control_mask])

        # Predict potential outcomes
        mu1 = mu1_model.predict(X)
        mu0 = mu0_model.predict(X)

        # Doubly robust scores
        dr_scores = mu1 - mu0 + \
                    T * (Y - mu1) / pscores - \
                    (1 - T) * (Y - mu0) / (1 - pscores)

        # CATE estimates per unit
        cate_estimates = dr_scores

        return {
            "method": f"CATE ({method})",
            "n_units": len(data),
            "mean_cate": round(float(np.mean(cate_estimates)), 4),
            "median_cate": round(float(np.median(cate_estimates)), 4),
            "std_cate": round(float(np.std(cate_estimates)), 4),
            "min_cate": round(float(np.min(cate_estimates)), 4),
            "max_cate": round(float(np.max(cate_estimates)), 4),
            "q25_cate": round(float(np.percentile(cate_estimates, 25)), 4),
            "q75_cate": round(float(np.percentile(cate_estimates, 75)), 4),
            "cate_distribution": cate_estimates.tolist(),
            "interpretation": f"Average CATE = {np.mean(cate_estimates):.3f} (SD = {np.std(cate_estimates):.3f}). "
                              f"Treatment effects range from {np.min(cate_estimates):.3f} to {np.max(cate_estimates):.3f}.",
        }


# ─── UI Renderer ─────────────────────────────────────────────────────
def render_causal_inference_ui():
    """Render the Causal Inference page in Streamlit."""
    import streamlit as st
    import plotly.graph_objects as go
    import plotly.express as px

    st.markdown("## 🔬 Causal Inference Engine")
    st.markdown("*Estimate causal effects from observational data — PSM, DiD, IV, RDD, IPW, CATE*")

    df = st.session_state.get("active_df")
    if df is None or df.empty:
        st.warning("No data loaded. Upload a file or connect a data source first.")
        return

    engine = CausalInferenceEngine()

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🎯 Propensity Score Matching",
        "📊 Diff-in-Diff",
        "📐 IV Regression",
        "✂️ RDD",
        "⚖️ IPW",
        "🔀 CATE",
        "🧩 DAG Advisor",
    ])

    # Get available columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    all_cols = df.columns.tolist()

    with tab1:
        st.subheader("🎯 Propensity Score Matching (PSM)")
        col1, col2 = st.columns(2)
        with col1:
            treat_col = st.selectbox("Treatment (binary 0/1)", options=numeric_cols, key="psm_treat")
            outcome_col = st.selectbox("Outcome variable", options=[c for c in numeric_cols if c != treat_col], key="psm_outcome")
        with col2:
            covs = st.multiselect("Covariates (confounders)", options=[c for c in numeric_cols if c not in (treat_col, outcome_col)], key="psm_covs")
            method = st.selectbox("PS estimation method", options=["logistic", "gradient_boosting"], key="psm_method")
            n_neighbors = st.slider("Neighbors per treated", 1, 10, 1, key="psm_nn")
            caliper = st.slider("Caliper (propensity score units)", 0.01, 0.5, 0.05, 0.01, key="psm_caliper")

        if st.button("🔬 Run PSM", type="primary", use_container_width=True) and covs:
            with st.spinner("Running propensity score matching..."):
                result = engine.propensity_score_matching(df, treat_col, outcome_col, covs, method, n_neighbors, caliper)
            if "error" in result:
                st.error(result["error"])
            else:
                st.success("✅ PSM complete!")
                col1, col2, col3, col4 = st.columns(4)
                with col1: st.metric("ATT Estimate", f"{result['att']:.4f}")
                with col2: st.metric("SE", f"{result['se']:.4f}")
                with col3: st.metric("p-value", f"{result['p_value']:.4f}")
                with col4: st.metric("Matched Pairs", result['n_matched_pairs'])
                st.info(result['interpretation'])

                if result.get("balance_smd"):
                    st.subheader("⚖️ Covariate Balance (SMD)")
                    bal_df = pd.DataFrame(list(result["balance_smd"].items()), columns=["Covariate", "SMD"])
                    st.dataframe(bal_df, use_container_width=True, hide_index=True)
                    fig = px.bar(bal_df, x="Covariate", y="SMD", title="Standardized Mean Differences After Matching",
                                 color="SMD", color_continuous_scale="RdYlGn", range_color=[0, 0.5])
                    fig.add_hline(y=0.1, line_dash="dash", line_color="red", annotation_text="Threshold: 0.1")
                    st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("📊 Difference-in-Differences (DiD)")
        st.info("Requires: treatment column (0/1), time column (0=pre, 1=post), outcome column")
        col1, col2 = st.columns(2)
        with col1:
            did_treat = st.selectbox("Treatment (0/1)", options=numeric_cols, key="did_treat")
            did_time = st.selectbox("Time (0=pre, 1=post)", options=numeric_cols, key="did_time")
        with col2:
            did_outcome = st.selectbox("Outcome", options=numeric_cols, key="did_outcome")

        if st.button("📊 Run DiD", type="primary", use_container_width=True):
            with st.spinner("Running difference-in-differences..."):
                result = engine.difference_in_differences(df, did_treat, did_time, did_outcome)
            if "error" in result:
                st.error(result["error"])
            else:
                st.success("✅ DiD complete!")
                col1, col2, col3, col4 = st.columns(4)
                with col1: st.metric("DiD Estimate", f"{result['did_estimate']:.4f}")
                with col2: st.metric("SE", f"{result['se']:.4f}")
                with col3: st.metric("p-value", f"{result['p_value']:.4f}")
                with col4: st.metric("R²", f"{result['r_squared']:.4f}")
                st.info(result['interpretation'])

                # Means plot
                means = pd.DataFrame({
                    "Group": ["Treated", "Treated", "Control", "Control"],
                    "Period": ["Pre", "Post", "Pre", "Post"],
                    "Mean": [result['treated_pre_mean'], result['treated_post_mean'],
                             result['control_pre_mean'], result['control_post_mean']]
                })
                fig = px.line(means, x="Period", y="Mean", color="Group", markers=True,
                             title="Difference-in-Differences: Group Means Over Time")
                st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("📐 Instrumental Variable Regression (2SLS)")
        st.info("Requires: outcome, treatment (endogenous), instrument (exogenous), optional covariates")
        col1, col2 = st.columns(2)
        with col1:
            iv_outcome = st.selectbox("Outcome", options=numeric_cols, key="iv_outcome")
            iv_treat = st.selectbox("Treatment (endogenous)", options=[c for c in numeric_cols if c != iv_outcome], key="iv_treat")
        with col2:
            iv_inst = st.selectbox("Instrument (exogenous)", options=[c for c in numeric_cols if c not in (iv_outcome, iv_treat)], key="iv_inst")
            iv_covs = st.multiselect("Covariates (optional)", options=[c for c in numeric_cols if c not in (iv_outcome, iv_treat, iv_inst)], key="iv_covs")

        if st.button("📐 Run IV Regression", type="primary", use_container_width=True):
            with st.spinner("Running 2SLS..."):
                result = engine.instrumental_variable(df, iv_outcome, iv_treat, iv_inst, iv_covs or None)
            if "error" in result:
                st.error(result["error"])
            else:
                st.success("✅ IV regression complete!")
                col1, col2, col3, col4 = st.columns(4)
                with col1: st.metric("IV Estimate", f"{result['iv_estimate']:.4f}")
                with col2: st.metric("SE", f"{result['se']:.4f}")
                with col3: st.metric("F-stat (1st stage)", f"{result['first_stage_f_stat']:.2f}")
                with col4: st.metric("Weak IV?", "⚠️ Yes" if result.get('weak_instrument') else "✅ No")
                st.info(result['interpretation'])

    with tab4:
        st.subheader("✂️ Regression Discontinuity (Sharp RDD)")
        col1, col2 = st.columns(2)
        with col1:
            rdd_assign = st.selectbox("Assignment variable (running)", options=numeric_cols, key="rdd_assign")
            rdd_outcome = st.selectbox("Outcome", options=numeric_cols, key="rdd_outcome")
        with col2:
            rdd_cutoff = st.number_input("Cutoff value", value=0.0, step=0.1, key="rdd_cutoff")
            rdd_bandwidth = st.number_input("Bandwidth (leave 0 for auto)", min_value=0.0, value=0.0, step=0.1, key="rdd_bandwidth")
            rdd_poly = st.slider("Polynomial order", 1, 4, 2, key="rdd_poly")

        if st.button("✂️ Run RDD", type="primary", use_container_width=True):
            bw = rdd_bandwidth if rdd_bandwidth > 0 else None
            with st.spinner("Running regression discontinuity..."):
                result = engine.regression_discontinuity(df, rdd_assign, rdd_outcome, rdd_cutoff, bw, rdd_poly)
            if "error" in result:
                st.error(result["error"])
            else:
                st.success("✅ RDD complete!")
                col1, col2, col3, col4 = st.columns(4)
                with col1: st.metric("RD Estimate", f"{result['rd_estimate']:.4f}")
                with col2: st.metric("SE", f"{result['se']:.4f}")
                with col3: st.metric("p-value", f"{result['p_value']:.4f}")
                with col4: st.metric("N (bandwidth)", result['n_within_bandwidth'])
                st.info(result['interpretation'])

    with tab5:
        st.subheader("⚖️ Inverse Probability Weighting (IPW)")
        col1, col2 = st.columns(2)
        with col1:
            ipw_treat = st.selectbox("Treatment (0/1)", options=numeric_cols, key="ipw_treat")
            ipw_outcome = st.selectbox("Outcome", options=numeric_cols, key="ipw_outcome")
        with col2:
            ipw_covs = st.multiselect("Covariates", options=[c for c in numeric_cols if c not in (ipw_treat, ipw_outcome)], key="ipw_covs")

        if st.button("⚖️ Run IPW", type="primary", use_container_width=True) and ipw_covs:
            with st.spinner("Running IPW..."):
                result = engine.inverse_probability_weighting(df, ipw_treat, ipw_outcome, ipw_covs)
            if "error" in result:
                st.error(result["error"])
            else:
                st.success("✅ IPW complete!")
                st.metric("ATE (IPW)", f"{result['ate']:.4f}")
                st.info(result['interpretation'])

    with tab6:
        st.subheader("🔀 Heterogeneous Treatment Effects (CATE)")
        col1, col2 = st.columns(2)
        with col1:
            cate_treat = st.selectbox("Treatment (0/1)", options=numeric_cols, key="cate_treat")
            cate_outcome = st.selectbox("Outcome", options=numeric_cols, key="cate_outcome")
        with col2:
            cate_covs = st.multiselect("Features for heterogeneity", options=[c for c in numeric_cols if c not in (cate_treat, cate_outcome)], key="cate_covs")

        if st.button("🔀 Estimate CATE", type="primary", use_container_width=True) and cate_covs:
            with st.spinner("Estimating CATE..."):
                result = engine.estimate_cate(df, cate_treat, cate_outcome, cate_covs)
            if "error" in result:
                st.error(result["error"])
            else:
                st.success("✅ CATE estimated!")
                col1, col2, col3 = st.columns(3)
                with col1: st.metric("Mean CATE", f"{result['mean_cate']:.4f}")
                with col2: st.metric("Median CATE", f"{result['median_cate']:.4f}")
                with col3: st.metric("Std CATE", f"{result['std_cate']:.4f}")
                st.info(result['interpretation'])

                # Distribution plot
                cate_vals = result.get("cate_distribution", [])
                if cate_vals:
                    fig = px.histogram(pd.DataFrame({"CATE": cate_vals}), x="CATE", nbins=50,
                                       title="Distribution of Conditional Average Treatment Effects",
                                       color_discrete_sequence=["#1d4ed8"])
                    fig.add_vline(x=0, line_dash="dash", line_color="red")
                    st.plotly_chart(fig, use_container_width=True)

    with tab7:
        st.subheader("🧩 DAG-Based Adjustment Set Advisor")
        st.info("Specify your assumed causal structure to get adjustment recommendations.")

        treat_var = st.selectbox("Treatment variable", options=all_cols, key="dag_treat")
        outcome_var = st.selectbox("Outcome variable", options=[c for c in all_cols if c != treat_var], key="dag_outcome")
        confounders = st.multiselect("Confounders (cause both treatment & outcome)",
                                     options=[c for c in all_cols if c not in (treat_var, outcome_var)], key="dag_conf")
        mediators = st.multiselect("Mediators (on causal path)",
                                   options=[c for c in all_cols if c not in (treat_var, outcome_var)], key="dag_med")
        colliders = st.multiselect("Colliders (caused by both)",
                                   options=[c for c in all_cols if c not in (treat_var, outcome_var)], key="dag_coll")

        if st.button("🧩 Get Adjustment Set", type="primary", use_container_width=True):
            result = engine.suggest_adjustment_set(treat_var, outcome_var, all_cols, confounders, mediators, colliders)
            st.success("✅ DAG analysis complete!")
            st.markdown(f"### Recommended Adjustment Set")
            if result["recommended_adjustment_set"]:
                for v in result["recommended_adjustment_set"]:
                    st.markdown(f"- **{v}**")
            else:
                st.info("No adjustment needed (or no confounders specified).")
            st.markdown("### Variables to Exclude")
            for v in result["variables_to_exclude"]:
                st.markdown(f"- ❌ {v}")

