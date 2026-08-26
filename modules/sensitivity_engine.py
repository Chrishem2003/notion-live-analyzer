
"""
Sensitivity & Robustness Analysis Engine  Influence diagnostics, subgroup analysis,
specification curve analysis, multiverse analysis, and robustness value analysis.
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
    from sklearn.linear_model import LinearRegression
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    import statsmodels.api as sm
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False


class SensitivityEngine:
    """Assess robustness of statistical findings to alternative specifications."""

    def influence_diagnostics(
        self,
        df: pd.DataFrame,
        outcome: str,
        predictors: List[str],
    ) -> Dict[str, Any]:
        """
        Compute influence diagnostics: Cook's distance, DFBETAS, DFFITS.
        """
        if not HAS_STATSMODELS:
            return {"error": "statsmodels required"}
        data = df[[outcome] + predictors].dropna()
        y = data[outcome].values
        X = sm.add_constant(data[predictors].values)
        model = sm.OLS(y, X).fit()

        # Cook's distance
        influence = model.get_influence()
        cooks_d = influence.cooks_distance[0]
        dffits = influence.dffits[0]
        leverage = influence.hat_matrix_diag
        studentized_residuals = influence.resid_studentized_internal

        n = len(data)
        k = len(predictors) + 1

        # Flag influential observations
        cooks_threshold = 4 / (n - k - 1)
        influential = {
            "cooks_d": [round(float(cd), 4) for cd in cooks_d],
            "dffits": [round(float(df), 4) for df in dffits],
            "leverage": [round(float(lv), 4) for lv in leverage],
            "studentized_residuals": [round(float(sr), 4) for sr in studentized_residuals],
            "cooks_threshold": round(cooks_threshold, 4),
            "n_influential_cooks": int(np.sum(cooks_d > cooks_threshold)),
            "flagged_indices": np.where(cooks_d > cooks_threshold)[0].tolist(),
        }

        return {
            "method": "Influence Diagnostics",
            "n": n,
            "n_predictors": len(predictors),
            "influential": influential,
            "interpretation": f"{influential['n_influential_cooks']} of {n} observations have Cook's D > {cooks_threshold:.4f}",
        }

    def specification_curve(
        self,
        df: pd.DataFrame,
        outcome: str,
        treatment: str,
        controls: List[str],
    ) -> Dict[str, Any]:
        """
        Specification curve analysis  run all possible model specifications
        and show how the treatment coefficient changes.
        """
        if not HAS_STATSMODELS:
            return {"error": "statsmodels required"}

        data = df[[outcome, treatment] + controls].dropna()
        results = []

        # Generate all subsets of controls (limit to 5 controls to avoid explosion)
        max_controls = min(5, len(controls))
        selected_controls = controls[:max_controls]
        n_controls = len(selected_controls)

        for r in range(1, n_controls + 1):
            from itertools import combinations
            for combo in combinations(selected_controls, r):
                X = sm.add_constant(data[[treatment] + list(combo)].values)
                y = data[outcome].values
                try:
                    model = sm.OLS(y, X).fit()
                    coef = model.params[1]
                    se = model.bse[1]
                    p_val = model.pvalues[1]
                    ci_lower = coef - 1.96 * se
                    ci_upper = coef + 1.96 * se
                    results.append({
                        "controls": "".join(combo),
                        "n_controls": len(combo),
                        "coefficient": round(float(coef), 4),
                        "se": round(float(se), 4),
                        "p_value": round(float(p_val), 4),
                        "ci_lower": round(float(ci_lower), 4),
                        "ci_upper": round(float(ci_upper), 4),
                        "significant": p_val < 0.05,
                    })
                except Exception:
                    continue

        if not results:
            return {"error": "No specifications could be estimated"}

        results_df = pd.DataFrame(results)
        median_coef = results_df["coefficient"].median()
        pct_significant = results_df["significant"].mean() * 100

        return {
            "method": "Specification Curve Analysis",
            "n_specifications": len(results),
            "results": results_df,
            "median_coefficient": round(float(median_coef), 4),
            "pct_significant": round(float(pct_significant), 1),
            "min_coefficient": round(float(results_df["coefficient"].min()), 4),
            "max_coefficient": round(float(results_df["coefficient"].max()), 4),
            "sd_coefficient": round(float(results_df["coefficient"].std()), 4),
            "interpretation": f"Across {len(results)} specifications, median effect = {median_coef:.3f} "
                              f"({pct_significant:.0f}% significant)",
        }

    def robustness_value(
        self,
        df: pd.DataFrame,
        outcome: str,
        treatment: str,
        controls: List[str],
    ) -> Dict[str, Any]:
        """
        Compute Robustness of an inference to replacement (RIR) and
        impact threshold for confounding variables.
        """
        if not HAS_STATSMODELS:
            return {"error": "statsmodels required"}

        data = df[[outcome, treatment] + controls].dropna()
        y = data[outcome].values
        X_list = [treatment] + controls
        X = sm.add_constant(data[X_list].values)
        model = sm.OLS(y, X).fit()

        beta = model.params[1]
        se = model.bse[1]
        t_val = beta / se if se > 0 else 0
        r2 = model.rsquared
        n = len(data)
        k = len(X_list)

        # Impact threshold for confounding (Frank, 2000)
        if beta != 0:
            r_yz = math.sqrt(t_val**2 / (t_val**2 + n - k - 1))
            r_xz = r_yz
            impact = r_yz * r_xz
        else:
            impact = 0

        # Robustness of inference to replacement (RIR)
        if beta > 0:
            rir = math.ceil((n - k - 1) * (beta / se)**2 / ((beta / se)**2 + (n - k - 1)))
            rir_pct = rir / n * 100 if n > 0 else 0
        else:
            rir = 0
            rir_pct = 0

        return {
            "method": "Robustness Value Analysis",
            "coefficient": round(float(beta), 4),
            "se": round(float(se), 4),
            "r_squared": round(float(r2), 4),
            "impact_threshold": round(float(impact), 4),
            "rir_count": rir,
            "rir_percentage": round(float(rir_pct), 1),
            "interpretation": f"A confound would need {rir} ({rir_pct:.0f}%) replacement cases to nullify the effect. "
                              f"Impact threshold = {impact:.3f}.",
        }

    def subgroup_analysis(
        self,
        df: pd.DataFrame,
        outcome: str,
        treatment: str,
        subgroup_col: str,
        controls: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Run model within each subgroup and compare effects.
        """
        if not HAS_STATSMODELS:
            return {"error": "statsmodels required"}

        subgroups = df[subgroup_col].dropna().unique()
        controls = controls or []
        results = []

        for subgroup in subgroups:
            sub = df[df[subgroup_col] == subgroup][[outcome, treatment] + controls].dropna()
            if len(sub) < len(controls) + 5:
                continue
            X = sm.add_constant(sub[treatment].values if not controls else sub[[treatment] + controls].values)
            y = sub[outcome].values
            try:
                model = sm.OLS(y, X).fit()
                results.append({
                    "subgroup": str(subgroup),
                    "n": len(sub),
                    "coefficient": round(float(model.params[1]), 4),
                    "se": round(float(model.bse[1]), 4),
                    "p_value": round(float(model.pvalues[1]), 4),
                    "ci_lower": round(float(model.params[1] - 1.96 * model.bse[1]), 4),
                    "ci_upper": round(float(model.params[1] + 1.96 * model.bse[1]), 4),
                    "significant": model.pvalues[1] < 0.05,
                })
            except Exception:
                continue

        if not results:
            return {"error": "No subgroups could be estimated"}

        return {
            "method": "Subgroup Analysis",
            "outcome": outcome,
            "treatment": treatment,
            "subgroup_variable": subgroup_col,
            "n_subgroups": len(results),
            "results": pd.DataFrame(results),
            "interpretation": f"Effect varies across {len(results)} subgroups. "
                              f"Range: [{min(r['coefficient'] for r in results):.3f}, {max(r['coefficient'] for r in results):.3f}]",
        }

    def multiverse_analysis(
        self,
        df: pd.DataFrame,
        outcome: str,
        treatment: str,
        controls: List[str],
        exclusion_rules: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Multiverse analysis  estimate the same model across many reasonable
        analytic choices simultaneously.
        """
        if not HAS_STATSMODELS:
            return {"error": "statsmodels required"}

        base_specs = [
            {"controls": controls[:i], "name": f"Controls_{i}"}
            for i in range(len(controls) + 1)
        ]
        specs = base_specs[:]  # Limit to base specs for performance

        results = []
        for spec in specs:
            preds = [treatment] + spec["controls"]
            data = df[[outcome] + preds].dropna()
            X = sm.add_constant(data[preds].values)
            y = data[outcome].values
            try:
                model = sm.OLS(y, X).fit()
                results.append({
                    "specification": spec["name"],
                    "n_controls": len(spec["controls"]),
                    "n_obs": int(model.nobs),
                    "coefficient": round(float(model.params[1]), 4),
                    "se": round(float(model.bse[1]), 4),
                    "p_value": round(float(model.pvalues[1]), 4),
                    "ci_lower": round(float(model.params[1] - 1.96 * model.bse[1]), 4),
                    "ci_upper": round(float(model.params[1] + 1.96 * model.bse[1]), 4),
                    "significant": model.pvalues[1] < 0.05,
                })
            except Exception:
                continue

        if not results:
            return {"error": "No models converged"}

        return {
            "method": "Multiverse Analysis",
            "n_specifications": len(results),
            "results": pd.DataFrame(results),
            "median_coefficient": round(float(np.median([r["coefficient"] for r in results])), 4),
            "sd_coefficient": round(float(np.std([r["coefficient"] for r in results])), 4),
            "pct_positive": round(sum(1 for r in results if r["coefficient"] > 0) / len(results) * 100, 1),
            "pct_significant": round(sum(1 for r in results if r["significant"]) / len(results) * 100, 1),
        }


# â”€â”€â”€ UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def render_sensitivity_analysis_ui():
    """Render the Sensitivity Analysis page."""
    import streamlit as st
    import plotly.express as px

    st.markdown("## ðŸ” Sensitivity & Robustness Analysis")
    st.markdown("*Assess how robust your findings are to alternative specifications*")

    df = st.session_state.get("active_df")
    if df is None or df.empty:
        st.warning("No data loaded.")
        return

    engine = SensitivityEngine()
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        " Influence Diagnostics", "ðŸ“ Spec Curve",
        "ðŸ›¡ï¸ Robustness Value", "ðŸ“‚ Subgroup Analysis", "ðŸŒŒ Multiverse"
    ])

    with tab1:
        st.subheader(" Influence Diagnostics (Cook's D, DFBETAS, DFFITS)")
        col1, col2 = st.columns(2)
        with col1:
            inf_outcome = st.selectbox("Outcome", options=numeric_cols, key="inf_outcome")
            inf_preds = st.multiselect("Predictors", options=[c for c in numeric_cols if c != inf_outcome], key="inf_preds")

        if st.button(" Compute Diagnostics", type="primary", width='stretch') and inf_preds:
            result = engine.influence_diagnostics(df, inf_outcome, inf_preds)
            if "error" in result:
                st.error(result["error"])
            else:
                inf = result.get("influential", {})
                st.metric("Influential Observations", inf.get("n_influential_cooks", 0))
                st.info(result["interpretation"])

                # Plot Cook's D
                if inf.get("cooks_d"):
                    cooks_df = pd.DataFrame({"Observation": range(len(inf["cooks_d"])), "Cook's D": inf["cooks_d"]})
                    fig = px.bar(cooks_df, x="Observation", y="Cook's D", title="Cook's Distance")
                    fig.add_hline(y=inf.get("cooks_threshold", 0), line_dash="dash", line_color="red",
                                  annotation_text=f"Threshold: {inf.get('cooks_threshold', 0):.4f}")
                    st.plotly_chart(fig, width='stretch')

    with tab2:
        st.subheader("ðŸ“ Specification Curve Analysis")
        col1, col2 = st.columns(2)
        with col1:
            sc_outcome = st.selectbox("Outcome", options=numeric_cols, key="sc_outcome")
            sc_treatment = st.selectbox("Treatment variable", options=[c for c in numeric_cols if c != sc_outcome], key="sc_treatment")
        with col2:
            sc_controls = st.multiselect("Control variables", options=[c for c in numeric_cols if c not in (sc_outcome, sc_treatment)], key="sc_controls")

        if st.button("ðŸ“ Run Spec Curve", type="primary", width='stretch') and sc_controls:
            result = engine.specification_curve(df, sc_outcome, sc_treatment, sc_controls)
            if "error" in result:
                st.error(result["error"])
            else:
                st.info(result["interpretation"])
                results_df = result.get("results", pd.DataFrame())
                if not results_df.empty:
                    fig = px.scatter(results_df, x="n_controls", y="coefficient",
                                     error_y="se", color="significant",
                                     title="Specification Curve", hover_data=["controls"])
                    fig.add_hline(y=0, line_dash="dash", line_color="gray")
                    st.plotly_chart(fig, width='stretch')

    with tab3:
        st.subheader("ðŸ›¡ï¸ Robustness Value Analysis")
        col1, col2 = st.columns(2)
        with col1:
            rv_outcome = st.selectbox("Outcome", options=numeric_cols, key="rv_outcome")
            rv_treatment = st.selectbox("Treatment", options=[c for c in numeric_cols if c != rv_outcome], key="rv_treatment")
        with col2:
            rv_controls = st.multiselect("Controls", options=[c for c in numeric_cols if c not in (rv_outcome, rv_treatment)], key="rv_controls")

        if st.button("ðŸ›¡ï¸ Compute Robustness", type="primary", width='stretch'):
            result = engine.robustness_value(df, rv_outcome, rv_treatment, rv_controls)
            if "error" in result:
                st.error(result["error"])
            else:
                col1, col2, col3 = st.columns(3)
                with col1: st.metric("Coefficient", f"{result['coefficient']:.4f}")
                with col2: st.metric("Impact Threshold", f"{result['impact_threshold']:.4f}")
                with col3: st.metric("RIR (count)", result['rir_count'])
                st.info(result["interpretation"])

    with tab4:
        st.subheader("ðŸ“‚ Subgroup Analysis")
        col1, col2 = st.columns(2)
        with col1:
            sg_outcome = st.selectbox("Outcome", options=numeric_cols, key="sg_outcome")
            sg_treatment = st.selectbox("Treatment", options=[c for c in numeric_cols if c != sg_outcome], key="sg_treatment")
        with col2:
            sg_subgroup = st.selectbox("Subgroup variable", options=[c for c in df.columns if c not in (sg_outcome, sg_treatment) and df[c].nunique() <= 10], key="sg_subgroup")
            sg_controls = st.multiselect("Controls (optional)", options=[c for c in numeric_cols if c not in (sg_outcome, sg_treatment)], key="sg_controls")

        if st.button("ðŸ“‚ Run Subgroup Analysis", type="primary", width='stretch'):
            result = engine.subgroup_analysis(df, sg_outcome, sg_treatment, sg_subgroup, sg_controls)
            if "error" in result:
                st.error(result["error"])
            else:
                st.info(result["interpretation"])
                results_df = result.get("results", pd.DataFrame())
                if not results_df.empty:
                    fig = px.scatter(results_df, x="subgroup", y="coefficient",
                                     error_y="se", color="significant",
                                     title="Subgroup Effects", size="n")
                    fig.add_hline(y=0, line_dash="dash", line_color="gray")
                    st.plotly_chart(fig, width='stretch')

    with tab5:
        st.subheader("ðŸŒŒ Multiverse Analysis")
        col1, col2 = st.columns(2)
        with col1:
            mv_outcome = st.selectbox("Outcome", options=numeric_cols, key="mv_outcome")
            mv_treatment = st.selectbox("Treatment", options=[c for c in numeric_cols if c != mv_outcome], key="mv_treatment")
        with col2:
            mv_controls = st.multiselect("Control variables", options=[c for c in numeric_cols if c not in (mv_outcome, mv_treatment)], key="mv_controls")

        if st.button("ðŸŒŒ Run Multiverse", type="primary", width='stretch'):
            result = engine.multiverse_analysis(df, mv_outcome, mv_treatment, mv_controls)
            if "error" in result:
                st.error(result["error"])
            else:
                st.info(result["interpretation"])
                col1, col2, col3 = st.columns(3)
                with col1: st.metric("Median Coef", f"{result['median_coefficient']:.4f}")
                with col2: st.metric("SD Coef", f"{result['sd_coefficient']:.4f}")
                with col3: st.metric("% Significant", f"{result['pct_significant']}%")


