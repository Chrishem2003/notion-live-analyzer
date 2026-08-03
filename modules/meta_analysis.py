import security_guard

"""
Meta-Analysis Engine  Combine effect sizes across studies, assess heterogeneity,
detect publication bias, and generate publication-ready forest/funnel plots.

Core capabilities:
  - Fixed-effects and random-effects (DerSimonian-Laird) models
  - Forest plots with study-level and summary estimates
  - Funnel plots with Egger's regression test for publication bias
  - Heterogeneity analysis (Cochran's Q, IÂ², Ï„Â²)
  - Cumulative meta-analysis (evidence accumulation over time)
  - Meta-regression with moderators
  - Subgroup analysis
  - Leave-one-out sensitivity analysis
"""
from __future__ import annotations

from typing import Dict, List, Any, Optional, Tuple
import math
import statistics
import numpy as np
import pandas as pd
from datetime import datetime

# â”€â”€â”€ Imports â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
try:
    from scipy import stats as scipy_stats
    from scipy.stats import norm, chi2
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    norm = None
    chi2 = None

try:
    from statsmodels.regression.linear_model import OLS
    from statsmodels.tools import add_constant
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    OLS = None
    add_constant = None


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 1. EFFECT SIZE CONVERTERS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
class EffectSizeConverter:
    """Convert between various effect size metrics."""

    @staticmethod
    def cohens_d_from_means(m1: float, m2: float, sd1: float, sd2: float, n1: int, n2: int) -> float:
        """Cohen's d from group means and SDs."""
        pooled_sd = math.sqrt(((n1 - 1) * sd1**2  (n2 - 1) * sd2**2) / (n1  n2 - 2))
        if pooled_sd == 0:
            return 0.0
        return (m1 - m2) / pooled_sd

    @staticmethod
    def cohens_d_from_t(t_stat: float, n1: int, n2: int) -> float:
        """Cohen's d from independent t-test statistic."""
        return t_stat * math.sqrt(1/n1  1/n2)

    @staticmethod
    def cohens_d_from_r(r: float) -> float:
        """Cohen's d from Pearson correlation."""
        return 2 * r / math.sqrt(1 - r**2) if abs(r) < 1 else 10.0

    @staticmethod
    def r_from_cohens_d(d: float) -> float:
        """Pearson r from Cohen's d."""
        return d / math.sqrt(d**2  4)

    @staticmethod
    def odds_ratio_from_d(d: float) -> float:
        """Odds ratio from Cohen's d (logistic transformation)."""
        return math.exp(d * math.pi / math.sqrt(3))

    @staticmethod
    def d_from_odds_ratio(or_val: float) -> float:
        """Cohen's d from odds ratio."""
        return math.log(or_val) * math.sqrt(3) / math.pi

    @staticmethod
    def variance_of_d(n1: int, n2: int, d: float = 0) -> float:
        """Approximate variance of Cohen's d."""
        return (n1  n2) / (n1 * n2)  d**2 / (2 * (n1  n2))

    @staticmethod
    def se_from_ci(ci_lower: float, ci_upper: float, z: float = 1.96) -> float:
        """Standard error from confidence interval."""
        return (ci_upper - ci_lower) / (2 * z)

    @staticmethod
    def hedges_g(d: float, n1: int, n2: int) -> float:
        """Convert Cohen's d to Hedges' g (small sample correction)."""
        df = n1  n2 - 2
        correction = 1 - 3 / (4 * df - 1)
        return d * correction


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 2. META-ANALYSIS ENGINE
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
class MetaAnalysisEngine:
    """
    Perform meta-analysis on a collection of effect sizes.
    Supports fixed-effects and random-effects (DerSimonian-Laird) models.
    """

    def __init__(self):
        self._check_deps()

    def _check_deps(self):
        if not HAS_SCIPY:
            raise ImportError("scipy is required for meta-analysis. Install: pip install scipy")

    # â”€â”€â”€ Fixed Effects â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    @staticmethod
    def fixed_effects(effects: List[float], variances: List[float]) -> Dict[str, Any]:
        """
        Fixed-effects inverse-variance weighted meta-analysis.

        Parameters
        ----------
        effects : List[float]  effect sizes (e.g., Cohen's d, log OR)
        variances : List[float]  variance of each effect size

        Returns
        -------
        Dict with pooled estimate, SE, z, p, CI
        """
        if not effects or not variances or len(effects) != len(variances):
            return {"error": "Effects and variances must be non-empty and same length"}

        weights = [1 / v for v in variances]
        total_weight = sum(weights)
        pooled = sum(w * e for w, e in zip(weights, effects)) / total_weight
        se = math.sqrt(1 / total_weight)
        z = pooled / se if se > 0 else 0
        p = 2 * (1 - norm.cdf(abs(z)))
        ci_lower = pooled - 1.96 * se
        ci_upper = pooled  1.96 * se

        return {
            "model": "Fixed Effects",
            "k": len(effects),
            "pooled_effect": round(pooled, 4),
            "se": round(se, 4),
            "z_value": round(z, 4),
            "p_value": round(float(p), 4),
            "ci_lower": round(ci_lower, 4),
            "ci_upper": round(ci_upper, 4),
            "significant": float(p) < 0.05,
            "weights": weights,
            "total_weight": total_weight,
        }

    # â”€â”€â”€ Random Effects (DerSimonian-Laird) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    @staticmethod
    def random_effects(effects: List[float], variances: List[float]) -> Dict[str, Any]:
        """
        Random-effects meta-analysis using DerSimonian-Laird estimator.

        Parameters
        ----------
        effects : List[float]  effect sizes
        variances : List[float]  variance of each effect size

        Returns
        -------
        Dict with pooled estimate, Ï„Â², IÂ², Q, SE, z, p, CI
        """
        if not effects or not variances or len(effects) != len(variances):
            return {"error": "Effects and variances must be non-empty and same length"}

        k = len(effects)

        # Step 1: Fixed effects weights and pooled estimate
        fe_weights = [1 / v for v in variances]
        fe_total_weight = sum(fe_weights)
        fe_pooled = sum(w * e for w, e in zip(fe_weights, effects)) / fe_total_weight

        # Step 2: Cochran's Q
        q = sum(w * (e - fe_pooled)**2 for w, e in zip(fe_weights, effects))

        # Step 3: DerSimonian-Laird Ï„Â²
        df = k - 1
        c = fe_total_weight - sum(w**2 for w in fe_weights) / fe_total_weight
        tau2 = max(0, (q - df) / c) if c > 0 else 0

        # Step 4: IÂ²
        i2 = max(0, (q - df) / q * 100) if q > 0 else 0

        # Step 5: Random effects weights
        re_weights = [1 / (v  tau2) for v in variances]
        re_total_weight = sum(re_weights)
        re_pooled = sum(w * e for w, e in zip(re_weights, effects)) / re_total_weight
        re_se = math.sqrt(1 / re_total_weight)
        re_z = re_pooled / re_se if re_se > 0 else 0
        re_p = 2 * (1 - norm.cdf(abs(re_z)))
        re_ci_lower = re_pooled - 1.96 * re_se
        re_ci_upper = re_pooled  1.96 * re_se

        # Step 6: Q-test p-value
        q_p = 1 - chi2.cdf(q, df) if chi2 else 1.0

        return {
            "model": "Random Effects (DL)",
            "k": k,
            "pooled_effect": round(re_pooled, 4),
            "se": round(re_se, 4),
            "z_value": round(re_z, 4),
            "p_value": round(float(re_p), 4),
            "ci_lower": round(re_ci_lower, 4),
            "ci_upper": round(re_ci_upper, 4),
            "significant": float(re_p) < 0.05,
            "tau2": round(tau2, 4),
            "i2": round(i2, 2),
            "q_statistic": round(float(q), 4),
            "q_df": df,
            "q_p_value": round(float(q_p), 4),
            "heterogeneity": "high" if i2 >= 75 else "substantial" if i2 >= 50 else "moderate" if i2 >= 25 else "low",
            "weights": re_weights,
            "total_weight": re_total_weight,
        }

    # â”€â”€â”€ Full Meta-Analysis â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def meta_analyze(
        self,
        effects: List[float],
        variances: List[float],
        study_labels: Optional[List[str]] = None,
        method: str = "random",
    ) -> Dict[str, Any]:
        """
        Run full meta-analysis with both fixed and random effects models.

        Parameters
        ----------
        effects : List[float]  effect sizes
        variances : List[float]  variance of each effect
        study_labels : List[str], optional  labels for each study
        method : str  "random", "fixed", or "both"

        Returns
        -------
        Dict with model results, heterogeneity stats, forest plot data
        """
        if not effects or not variances:
            return {"error": "Need at least one effect size"}

        k = len(effects)
        if study_labels is None:
            study_labels = [f"Study {i1}" for i in range(k)]

        results = {"k": k, "method": method, "study_labels": study_labels}

        # Fixed effects
        if method in ("fixed", "both"):
            fe = self.fixed_effects(effects, variances)
            results["fixed"] = fe

        # Random effects
        if method in ("random", "both"):
            re = self.random_effects(effects, variances)
            results["random"] = re

        # Forest plot data
        forest_data = []
        for i, (e, v, label) in enumerate(zip(effects, variances, study_labels)):
            se_i = math.sqrt(v)
            forest_data.append({
                "study": label,
                "effect": e,
                "se": se_i,
                "variance": v,
                "ci_lower": e - 1.96 * se_i,
                "ci_upper": e  1.96 * se_i,
                "weight_fe": (1 / v) if v > 0 else 0,
                "weight_re": (1 / (v  results.get("random", {}).get("tau2", 0))) if v > 0 else 0,
            })

        results["forest_data"] = forest_data

        # Determine if effects are on log scale (for plotting)
        results["is_log_scale"] = any("log" in str(label).lower() or "or" in str(label).lower() or "rr" in str(label).lower() for label in study_labels[:3])

        return results

    # â”€â”€â”€ Publication Bias â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    @staticmethod
    def eggers_test(effects: List[float], variances: List[float]) -> Dict[str, Any]:
        """
        Egger's regression test for funnel plot asymmetry.
        Regresses standard normal deviate (effect/se) on precision (1/se).
        Significant intercept â†’ asymmetry â†’ possible publication bias.
        """
        if not effects or not variances or len(effects) < 3:
            return {"error": "Need at least 3 studies for Egger's test"}

        se = [math.sqrt(v) for v in variances]
        y = [e / s for e, s in zip(effects, se)]  # Standard normal deviate
        x = [1.0 / s for s in se]  # Precision

        # OLS regression: y = b0  b1 * x
        if HAS_STATSMODELS and OLS is not None:
            x_with_const = add_constant(x)
            model = OLS(y, x_with_const).fit()
            intercept = model.params.iloc[0]
            intercept_se = model.bse.iloc[0]
            intercept_t = intercept / intercept_se if intercept_se > 0 else 0
            intercept_p = model.pvalues.iloc[0] if hasattr(model, 'pvalues') else 2 * (1 - norm.cdf(abs(intercept_t)))
            slope = model.params.iloc[1]
        else:
            # Manual OLS fallback
            n = len(x)
            x_mean = statistics.mean(x)
            y_mean = statistics.mean(y)
            slope = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y)) / \
                    sum((xi - x_mean)**2 for xi in x) if sum((xi - x_mean)**2 for xi in x) > 0 else 0
            intercept = y_mean - slope * x_mean
            residuals = [yi - (intercept  slope * xi) for xi, yi in zip(x, y)]
            resid_var = sum(r**2 for r in residuals) / (n - 2) if n > 2 else 0
            intercept_se = math.sqrt(resid_var * (1/n  x_mean**2 / sum((xi - x_mean)**2 for xi in x))) \
                if sum((xi - x_mean)**2 for xi in x) > 0 else 0
            intercept_t = intercept / intercept_se if intercept_se > 0 else 0
            intercept_p = 2 * (1 - norm.cdf(abs(intercept_t)))

        return {
            "test": "Egger's Regression Test",
            "intercept": round(float(intercept), 4),
            "intercept_se": round(float(intercept_se), 4),
            "intercept_t": round(float(intercept_t), 4),
            "intercept_p": round(float(intercept_p), 4),
            "slope": round(float(slope), 4),
            "significant": float(intercept_p) < 0.05,
            "n_studies": len(effects),
            "interpretation": "Possible publication bias" if float(intercept_p) < 0.05
            else "No significant asymmetry detected",
        }

    @staticmethod
    def fail_safe_n(effects: List[float], p_values: List[float], alpha: float = 0.05) -> Dict[str, Any]:
        """
        Rosenthal's Fail-Safe N  number of null studies needed to nullify the overall effect.
        """
        if not effects or not p_values:
            return {"error": "Need effect sizes and p-values"}

        z_values = []
        for p in p_values:
            if p <= 0:
                z = 5.0  # Very significant
            elif p >= 1:
                z = 0.0
            else:
                try:
                    z = abs(norm.ppf(p / 2))
                except Exception:
                    z = 0.0
            z_values.append(z)

        sum_z = sum(z_values)
        k = len(effects)
        # Rosenthal's formula
        n_fs = (sum_z / 1.645)**2 - k if sum_z > 0 else 0
        n_fs = max(0, int(math.ceil(n_fs)))

        # Tolerance: 5k  10 (Rosenthal's rule of thumb)
        tolerance = 5 * k  10

        return {
            "test": "Rosenthal's Fail-Safe N",
            "fail_safe_n": n_fs,
            "tolerance": tolerance,
            "robust": n_fs >= tolerance,
            "interpretation": f"Would need {n_fs} null studies to nullify effect"
            f" (tolerance = {tolerance})",
        }

    @staticmethod
    def trim_and_fill(
        effects: List[float],
        variances: List[float],
        side: str = "left",
    ) -> Dict[str, Any]:
        """
        Duval & Tweedie's Trim and Fill method for publication bias.
        Simple implementation: imputes missing studies on the specified side.
        """
        if not effects or not variances or len(effects) < 3:
            return {"error": "Need at least 3 studies"}

        k = len(effects)
        # Estimate number of missing studies using rank-based method
        # Simplified: count studies on each side of the median
        median_effect = statistics.median(effects)
        if side == "left":
            missing_candidates = [e for e in effects if e < median_effect]
        else:
            missing_candidates = [e for e in effects if e > median_effect]

        n_missing = len(missing_candidates)
        if n_missing == 0:
            return {"adjusted_effect": None, "n_imputed": 0}

        # Impute missing studies by mirroring
        imputed_effects = list(effects)
        imputed_variances = list(variances)

        for i in range(min(n_missing, k // 2)):
            # Mirror around median
            if side == "left":
                imputed_effects.append(median_effect  (median_effect - missing_candidates[i]))
            else:
                imputed_effects.append(median_effect - (missing_candidates[i] - median_effect))
            imputed_variances.append(statistics.median(variances))

        # Re-run random effects with imputed studies
        engine = MetaAnalysisEngine()
        adjusted = engine.random_effects(imputed_effects, imputed_variances)

        return {
            "test": "Trim and Fill",
            "n_imputed": min(n_missing, k // 2),
            "side": side,
            "adjusted_pooled": adjusted.get("pooled_effect"),
            "adjusted_ci_lower": adjusted.get("ci_lower"),
            "adjusted_ci_upper": adjusted.get("ci_upper"),
            "adjusted_i2": adjusted.get("i2"),
        }

    # â”€â”€â”€ Heterogeneity Analysis â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    @staticmethod
    def heterogeneity_analysis(effects: List[float], variances: List[float]) -> Dict[str, Any]:
        """Cochran's Q, IÂ², Ï„Â², and HÂ²."""
        if not effects or not variances or len(effects) < 2:
            return {"error": "Need at least 2 studies"}

        re = MetaAnalysisEngine.random_effects(effects, variances)
        k = len(effects)

        # HÂ² = Q / (k-1)
        q = re.get("q_statistic", 0)
        h2 = q / max(k - 1, 1)

        return {
            "q_statistic": re.get("q_statistic"),
            "q_df": k - 1,
            "q_p_value": re.get("q_p_value"),
            "i2": re.get("i2"),
            "tau2": re.get("tau2"),
            "h2": round(float(h2), 4),
            "heterogeneity": re.get("heterogeneity"),
            "interpretation": {
                "i2_low": "IÂ² < 25%  Low heterogeneity",
                "i2_moderate": "IÂ² 25-50%  Moderate heterogeneity",
                "i2_substantial": "IÂ² 50-75%  Substantial heterogeneity",
                "i2_high": "IÂ² > 75%  High heterogeneity",
            },
        }

    # â”€â”€â”€ Subgroup Analysis â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    @staticmethod
    def subgroup_analysis(
        effects: List[float],
        variances: List[float],
        subgroups: List[str],
        study_labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Perform subgroup meta-analysis  separate random-effects models per subgroup.
        """
        from collections import OrderedDict
        if len(effects) != len(subgroups):
            return {"error": "Effects and subgroups must have same length"}

        unique_groups = list(OrderedDict.fromkeys(subgroups))
        results = {}
        forest_data = []

        for group in unique_groups:
            indices = [i for i, g in enumerate(subgroups) if g == group]
            group_effects = [effects[i] for i in indices]
            group_variances = [variances[i] for i in indices]
            group_labels = [f"{study_labels[i]} ({group})" if study_labels else f"Study {i1} ({group})"
                          for i in indices]

            engine = MetaAnalysisEngine()
            ma = engine.meta_analyze(group_effects, group_variances, group_labels, method="both")
            results[group] = {
                "k": len(indices),
                "random": ma.get("random"),
                "fixed": ma.get("fixed"),
            }
            forest_data.extend(ma.get("forest_data", []))

        # Between-group heterogeneity (Q_between)
        all_group_results = {}
        for group, res in results.items():
            re = res.get("random", {})
            all_group_results[group] = {
                "pooled": re.get("pooled_effect"),
                "variance": re.get("se", 0)**2,
            }

        return {
            "groups": results,
            "n_groups": len(unique_groups),
            "group_names": unique_groups,
            "forest_data": forest_data,
        }

    # â”€â”€â”€ Cumulative Meta-Analysis â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    @staticmethod
    def cumulative_meta_analysis(
        effects: List[float],
        variances: List[float],
        sort_by: Optional[List[float]] = None,
        study_labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Cumulative meta-analysis  add studies one by one in specified order.
        Shows how pooled estimate evolves as evidence accumulates.
        """
        if not effects:
            return {"error": "No effect sizes provided"}

        k = len(effects)
        if sort_by is not None:
            # Sort by the sort_by values
            sorted_indices = sorted(range(k), key=lambda i: sort_by[i])
        else:
            sorted_indices = list(range(k))

        cumulative = []
        engine = MetaAnalysisEngine()

        for i in range(1, k  1):
            indices = sorted_indices[:i]
            cum_effects = [effects[j] for j in indices]
            cum_variances = [variances[j] for j in indices]
            cum_label = study_labels[indices[-1]] if study_labels else f"Step {i}"

            if i == 1:
                # Single study
                se_i = math.sqrt(cum_variances[0])
                cumulative.append({
                    "step": i,
                    "last_study": cum_label,
                    "pooled": cum_effects[0],
                    "se": se_i,
                    "ci_lower": cum_effects[0] - 1.96 * se_i,
                    "ci_upper": cum_effects[0]  1.96 * se_i,
                    "k": 1,
                    "i2": 0,
                })
            else:
                re = engine.random_effects(cum_effects, cum_variances)
                cumulative.append({
                    "step": i,
                    "last_study": cum_label,
                    "pooled": re.get("pooled_effect"),
                    "se": re.get("se"),
                    "ci_lower": re.get("ci_lower"),
                    "ci_upper": re.get("ci_upper"),
                    "k": i,
                    "i2": re.get("i2"),
                    "p_value": re.get("p_value"),
                })

        return {"cumulative": cumulative, "k": k}

    # â”€â”€â”€ Leave-One-Out Sensitivity â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    @staticmethod
    def leave_one_out(
        effects: List[float],
        variances: List[float],
        study_labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Leave-one-out sensitivity analysis  re-run meta-analysis omitting one study at a time.
        """
        if not effects or len(effects) < 3:
            return {"error": "Need at least 3 studies"}

        k = len(effects)
        if study_labels is None:
            study_labels = [f"Study {i1}" for i in range(k)]

        engine = MetaAnalysisEngine()
        results = []

        for i in range(k):
            left_out = study_labels[i]
            remaining_effects = [effects[j] for j in range(k) if j != i]
            remaining_variances = [variances[j] for j in range(k) if j != i]
            remaining_labels = [study_labels[j] for j in range(k) if j != i]

            ma = engine.meta_analyze(remaining_effects, remaining_variances, remaining_labels, method="both")
            re = ma.get("random", {})
            fe = ma.get("fixed", {})

            results.append({
                "omitted_study": left_out,
                "random_pooled": re.get("pooled_effect"),
                "random_ci_lower": re.get("ci_lower"),
                "random_ci_upper": re.get("ci_upper"),
                "fixed_pooled": fe.get("pooled_effect"),
                "i2_without": re.get("i2"),
                "k_without": k - 1,
            })

        # Overall results (all studies)
        overall = engine.meta_analyze(effects, variances, study_labels, method="both")
        overall_re = overall.get("random", {})

        return {
            "results": results,
            "overall_pooled": overall_re.get("pooled_effect"),
            "overall_ci_lower": overall_re.get("ci_lower"),
            "overall_ci_upper": overall_re.get("ci_upper"),
            "k": k,
            "influential_studies": [
                r for r in results
                if r.get("random_ci_lower") and (
                    r["random_ci_lower"] > overall_re.get("ci_upper", 999)
                    or r["random_ci_upper"] < overall_re.get("ci_lower", -999)
                )
            ],
        }

    # â”€â”€â”€ Meta-Regression â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    @staticmethod
    def meta_regression(
        effects: List[float],
        variances: List[float],
        moderators: List[List[float]],
        moderator_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Simple meta-regression  weighted regression of effect on moderators.
        Uses inverse-variance weights.
        """
        if not effects or not variances or not moderators:
            return {"error": "Need effects, variances, and at least one moderator"}

        k = len(effects)
        if len(moderators[0]) != k:
            return {"error": "Each moderator must have same length as effects"}

        n_mods = len(moderators)
        if moderator_names is None:
            moderator_names = [f"Moderator {i1}" for i in range(n_mods)]

        # Build design matrix (including intercept)
        X = np.column_stack([[1.0] * k]  moderators)
        y = np.array(effects)
        w = 1.0 / np.array(variances)  # Inverse-variance weights
        W = np.diag(w)

        try:
            # Weighted least squares
            XWX = X.T @ W @ X
            XWy = X.T @ W @ y
            beta = np.linalg.solve(XWX, XWy)
            residuals = y - X @ beta
            mse = residuals.T @ W @ residuals / (k - n_mods - 1) if (k - n_mods - 1) > 0 else 0
            var_beta = np.linalg.inv(XWX) * mse if mse > 0 else np.linalg.inv(XWX)
            se_beta = np.sqrt(np.diag(var_beta))

            # Z-tests and p-values
            z_values = beta / se_beta
            p_values = [2 * (1 - norm.cdf(abs(z))) for z in z_values]

            # Model fit
            y_pred = X @ beta
            ss_res = sum(w_i * (y_i - yp_i)**2 for w_i, y_i, yp_i in zip(w, y, y_pred))
            ss_total = sum(w_i * (y_i - np.average(y, weights=w))**2 for w_i, y_i in zip(w, y))
            r2 = 1 - ss_res / ss_total if ss_total > 0 else 0

            coefficients = []
            for i in range(n_mods  1):
                name = "Intercept" if i == 0 else moderator_names[i - 1]
                coefficients.append({
                    "variable": name,
                    "coefficient": round(float(beta[i]), 4),
                    "se": round(float(se_beta[i]), 4),
                    "z": round(float(z_values[i]), 4),
                    "p_value": round(float(p_values[i]), 4),
                    "significant": float(p_values[i]) < 0.05,
                })

            return {
                "test": "Meta-Regression (WLS)",
                "k": k,
                "n_moderators": n_mods,
                "coefficients": coefficients,
                "r_squared": round(float(r2), 4),
                "model_fit_p": round(float(1 - chi2.cdf(ss_res, k - n_mods - 1)) if chi2 else 0, 4),
                "interpretation": f"Meta-regression with {n_mods} moderator(s). RÂ² = {r2:.2%}",
            }

        except np.linalg.LinAlgError:
            return {"error": "Singular matrix  moderators may be collinear"}
        except Exception as e:
            return {"error": f"Meta-regression failed: {str(e)}"}


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 3. PLOT DATA GENERATORS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
class MetaPlotData:
    """Generate data structures for forest plots and funnel plots."""

    @staticmethod
    def forest_plot_data(
        effects: List[float],
        variances: List[float],
        study_labels: List[str],
        pooled_re: Dict[str, Any],
        pooled_fe: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """Generate DataFrame for forest plot."""
        rows = []
        for i, (e, v, label) in enumerate(zip(effects, variances, study_labels)):
            se_i = math.sqrt(v)
            rows.append({
                "Study": label,
                "Effect": e,
                "SE": se_i,
                "CI Lower": e - 1.96 * se_i,
                "CI Upper": e  1.96 * se_i,
                "Weight (RE)": round(1 / (v  pooled_re.get("tau2", 0)), 2),
                "Weight (FE)": round(1 / v, 2),
                "Type": "Study",
            })

        # Add summary row
        if pooled_re:
            rows.append({
                "Study": f"RE Model (IÂ²={pooled_re.get('i2', '?')}%)",
                "Effect": pooled_re.get("pooled_effect"),
                "SE": pooled_re.get("se"),
                "CI Lower": pooled_re.get("ci_lower"),
                "CI Upper": pooled_re.get("ci_upper"),
                "Weight (RE)": None,
                "Weight (FE)": None,
                "Type": "Summary",
            })

        return pd.DataFrame(rows)

    @staticmethod
    def funnel_plot_data(effects: List[float], variances: List[float]) -> pd.DataFrame:
        """Generate DataFrame for funnel plot."""
        se = [math.sqrt(v) for v in variances]
        df = pd.DataFrame({
            "Effect": effects,
            "SE": se,
            "Precision": [1 / s for s in se],
            "Inverse_SE": [1 / s for s in se],
        })
        df["Type"] = "Observed"
        return df

    @staticmethod
    def cumulative_plot_data(cumulative: List[Dict]) -> pd.DataFrame:
        """Generate DataFrame for cumulative meta-analysis plot."""
        return pd.DataFrame(cumulative)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 4. UI RENDERER
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def render_meta_analysis_ui():
    """Render the Meta-Analysis page in Streamlit."""
    import streamlit as st

    st.markdown("##  Meta-Analysis Engine")
    st.markdown("*Combine effect sizes across studies, assess heterogeneity, detect publication bias*")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "ðŸ“¥ Input Studies",
        " Meta-Analysis Results",
        "ðŸ“ˆ Forest Plot",
        "ðŸ•³ï¸ Publication Bias",
        "ðŸ”¬ Advanced",
    ])

    # â”€â”€â”€ Session state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if "meta_studies" not in st.session_state:
        st.session_state["meta_studies"] = []
    if "meta_results" not in st.session_state:
        st.session_state["meta_results"] = None

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # TAB 1: INPUT STUDIES
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    with tab1:
        st.subheader("ðŸ“¥ Input Effect Sizes")

        input_method = st.radio(
            "Input method",
            options=[
                "âœï¸ Manual Entry",
                "ðŸ“‹ Paste from Clipboard",
                "ðŸ“ Load from Data",
            ],
            horizontal=True,
            key="meta_input_method",
        )

        if input_method == "âœï¸ Manual Entry":
            with st.form("meta_manual_form"):
                st.markdown("**Add a study:**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    study_name = st.text_input("Study name", placeholder="e.g., Smith et al. 2020", key="meta_sname")
                with col2:
                    effect_size = st.number_input("Effect size (d/g/r/logOR)", value=0.0, step=0.01, format="%.3f", key="meta_es")
                with col3:
                    variance_es = st.number_input("Variance", value=0.01, min_value=0.0001, step=0.001, format="%.4f", key="meta_var")

                col1, col2 = st.columns(2)
                with col1:
                    n1 = st.number_input("N1 (optional)", min_value=0, value=0, key="meta_n1")
                with col2:
                    n2 = st.number_input("N2 (optional)", min_value=0, value=0, key="meta_n2")

                if st.form_submit_button("âž• Add Study", type="primary"):
                    if study_name.strip() and effect_size != 0:
                        st.session_state["meta_studies"].append({
                            "study": study_name.strip(),
                            "effect": effect_size,
                            "variance": variance_es,
                            "n1": n1,
                            "n2": n2,
                        })
                        st.success(f"âœ… Added '{study_name}'")

        elif input_method == "ðŸ“‹ Paste from Clipboard":
            st.markdown("Paste data as: `Label, Effect, Variance` (one per line)")
            pasted = st.text_area("Paste data", height=150, placeholder="""Smith 2020, 0.45, 0.032
Jones 2019, 0.78, 0.045
Lee 2021, 0.23, 0.028""", key="meta_paste")
            if st.button("ðŸ“‹ Parse & Add", type="primary"):
                studies = []
                for line in pasted.strip().split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 3:
                        try:
                            studies.append({
                                "study": parts[0],
                                "effect": float(parts[1]),
                                "variance": float(parts[2]),
                                "n1": 0, "n2": 0,
                            })
                        except ValueError:
                            pass
                if studies:
                    # Merge with existing (avoid duplicates by name)
                    existing_names = {s["study"] for s in st.session_state["meta_studies"]}
                    new_count = 0
                    for s in studies:
                        if s["study"] not in existing_names:
                            st.session_state["meta_studies"].append(s)
                            existing_names.add(s["study"])
                            new_count = 1
                    st.success(f"âœ… Added {new_count} new studies ({len(studies) - new_count} duplicates skipped)")

        elif input_method == "ðŸ“ Load from Data":
            st.info("Load effect sizes from the active dataset.")
            df = st.session_state.get("active_df")
            if df is not None and not df.empty:
                numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                if len(numeric_cols) >= 2:
                    es_col = st.selectbox("Effect size column", options=numeric_cols, key="meta_es_col")
                    var_col = st.selectbox("Variance/SE column", options=[c for c in numeric_cols if c != es_col], key="meta_var_col")
                    label_col = st.selectbox("Study label column (optional)", options=[""]  df.columns.tolist(), key="meta_label_col")

                    if st.button("ðŸ“¥ Load from Data", type="primary"):
                        studies = []
                        for _, row in df.iterrows():
                            es_val = row[es_col]
                            var_val = row[var_col]
                            if pd.notna(es_val) and pd.notna(var_val) and var_val > 0:
                                label = str(row[label_col]) if label_col else f"Study {len(studies)  1}"
                                studies.append({
                                    "study": label,
                                    "effect": float(es_val),
                                    "variance": float(var_val),
                                    "n1": 0, "n2": 0,
                                })
                        if studies:
                            st.session_state["meta_studies"] = studies
                            st.success(f"âœ… Loaded {len(studies)} studies")
                else:
                    st.warning("Need at least 2 numeric columns (effect size  variance/SE)")
            else:
                st.warning("No data loaded. Upload a file or connect a data source first.")

        # â”€â”€â”€ Current Studies Table â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        studies = st.session_state.get("meta_studies", [])
        if studies:
            st.markdown("---")
            st.subheader(f"ðŸ“‹ Current Studies ({len(studies)})")

            studies_df = pd.DataFrame(studies)
            col_config = {
                "study": "Study Name",
                "effect": st.column_config.NumberColumn("Effect Size", format="%.3f"),
                "variance": st.column_config.NumberColumn("Variance", format="%.4f"),
                "n1": "N1",
                "n2": "N2",
            }
            st.dataframe(studies_df, use_container_width=True, hide_index=True,
                        column_config=col_config)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("ðŸ—‘ï¸ Clear All Studies", use_container_width=True):
                    st.session_state["meta_studies"] = []
                    st.session_state["meta_results"] = None
                    st.rerun()
            with col2:
                if st.button("ðŸš€ Run Meta-Analysis", type="primary", use_container_width=True):
                    if len(studies) >= 2:
                        with st.spinner("Running meta-analysis..."):
                            engine = MetaAnalysisEngine()
                            effects = [s["effect"] for s in studies]
                            variances = [s["variance"] for s in studies]
                            labels = [s["study"] for s in studies]
                            results = engine.meta_analyze(effects, variances, labels, method="both")
                            results["raw_effects"] = effects
                            results["raw_variances"] = variances
                            results["raw_labels"] = labels

                            # Publication bias
                            if len(studies) >= 3:
                                results["eggers"] = engine.eggers_test(effects, variances)
                                results["fail_safe"] = engine.fail_safe_n(effects, [0.05]*len(effects))
                                results["trim_fill"] = engine.trim_and_fill(effects, variances)

                            # Heterogeneity
                            results["heterogeneity"] = engine.heterogeneity_analysis(effects, variances)

                            # Leave-one-out
                            if len(studies) >= 3:
                                results["loo"] = engine.leave_one_out(effects, variances, labels)

                            st.session_state["meta_results"] = results
                        st.success("âœ… Meta-analysis complete!")
                        st.rerun()
                    else:
                        st.warning("Need at least 2 studies for meta-analysis")
        else:
            st.info("ðŸ‘† Add at least 2 studies to run a meta-analysis")

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # TAB 2: META-ANALYSIS RESULTS
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    with tab2:
        results = st.session_state.get("meta_results")
        if not results:
            st.info("Run a meta-analysis first in the **Input Studies** tab.")
        else:
            st.subheader(" Meta-Analysis Results")

            # â”€â”€â”€ Model Comparison â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            col1, col2 = st.columns(2)

            with col1:
                fe = results.get("fixed", {})
                if fe and "error" not in fe:
                    fe_sig = fe.get("significant", False)
                    fe_color = "#2ecc71" if fe_sig else "#64748b"
                    st.markdown(f"""
                    <div style="padding:1rem;border-radius:12px;border:1px solid {fe_color}40;
                                background:{fe_color}10;text-align:center;">
                        <h3 style="color:{fe_color};margin:0;">Fixed Effects</h3>
                        <div style="font-size:2rem;font-weight:900;color:{fe_color};">{fe.get('pooled_effect', 0):.3f}</div>
                        <div style="font-size:0.85rem;color:#64748b;">
                            [{fe.get('ci_lower', 0):.3f}, {fe.get('ci_upper', 0):.3f}]
                        </div>
                        <div style="font-size:0.85rem;">
                            z = {fe.get('z_value', 0):.2f}, {'âœ…' if fe_sig else 'âŒ'} p = {fe.get('p_value', 1):.4f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            with col2:
                re = results.get("random", {})
                if re and "error" not in re:
                    re_sig = re.get("significant", False)
                    re_color = "#1d4ed8" if re_sig else "#64748b"
                    st.markdown(f"""
                    <div style="padding:1rem;border-radius:12px;border:1px solid {re_color}40;
                                background:{re_color}10;text-align:center;">
                        <h3 style="color:{re_color};margin:0;">Random Effects (DL)</h3>
                        <div style="font-size:2rem;font-weight:900;color:{re_color};">{re.get('pooled_effect', 0):.3f}</div>
                        <div style="font-size:0.85rem;color:#64748b;">
                            [{re.get('ci_lower', 0):.3f}, {re.get('ci_upper', 0):.3f}]
                        </div>
                        <div style="font-size:0.85rem;">
                            z = {re.get('z_value', 0):.2f}, {'âœ…' if re_sig else 'âŒ'} p = {re.get('p_value', 1):.4f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            # â”€â”€â”€ Heterogeneity â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            het = results.get("heterogeneity", {})
            if het and "error" not in het:
                st.subheader("ðŸ“ˆ Heterogeneity")
                het_color = "#2ecc71" if het.get("i2", 0) < 25 else "#e67e22" if het.get("i2", 0) < 50 else "#e74c3c"
                st.markdown(f"""
                <div style="padding:0.8rem;border-radius:12px;border:1px solid {het_color}40;
                            background:{het_color}08;margin:0.5rem 0;">
                    <span style="font-weight:600;">IÂ² = {het.get('i2', 0):.1f}%</span>  {het.get('heterogeneity', 'unknown').title()}
                    <span style="margin-left:1rem;color:#64748b;">Q({het.get('q_df', 0)}) = {het.get('q_statistic', 0):.2f}, p = {het.get('q_p_value', 1):.4f}</span>
                    <span style="margin-left:1rem;color:#64748b;">Ï„Â² = {het.get('tau2', 0):.4f}</span>
                </div>
                """, unsafe_allow_html=True)

            # â”€â”€â”€ Study Details â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            st.subheader("ðŸ“‹ Study-Level Details")
            forest_data = results.get("forest_data", [])
            if forest_data:
                detail_rows = []
                for fd in forest_data:
                    detail_rows.append({
                        "Study": fd["study"],
                        "Effect": fd["effect"],
                        "SE": fd["se"],
                        "95% CI": f"[{fd['ci_lower']:.3f}, {fd['ci_upper']:.3f}]",
                        "Weight (FE)": f"{fd['weight_fe']:.1%}" if fd.get("weight_fe") else "",
                        "Weight (RE)": f"{fd['weight_re']:.1%}" if fd.get("weight_re") else "",
                    })
                st.dataframe(pd.DataFrame(detail_rows), use_container_width=True, hide_index=True)

            # â”€â”€â”€ Key Stats â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            st.subheader(" Key Statistics")
            re_stats = results.get("random", {})
            fe_stats = results.get("fixed", {})

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Studies (k)", results.get("k", 0))
            with col2:
                st.metric("Pooled Effect (RE)", f"{re_stats.get('pooled_effect', 0):.3f}" if re_stats else "N/A")
            with col3:
                st.metric("IÂ² Heterogeneity", f"{het.get('i2', 0):.1f}%" if het else "N/A")
            with col4:
                st.metric("Ï„Â² (tau-squared)", f"{het.get('tau2', 0):.4f}" if het else "N/A")

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # TAB 3: FOREST PLOT
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    with tab3:
        results = st.session_state.get("meta_results")
        if not results:
            st.info("Run a meta-analysis first.")
        else:
            st.subheader("ðŸ“ˆ Forest Plot")

            forest_data = results.get("forest_data", [])
            if forest_data:
                import plotly.graph_objects as go

                fig = go.Figure()

                # Study-level data
                study_data = [d for d in forest_data if d.get("type", "Study") == "Study"]
                summary_data = [d for d in forest_data if d.get("type", "Study") == "Summary"]

                y_positions = list(range(len(study_data), 0, -1))  # Bottom to top
                y_labels = [d["study"] for d in study_data]

                # Add study-level effects
                fig.add_trace(go.Scatter(
                    x=[d["effect"] for d in study_data],
                    y=y_positions,
                    mode="markers",
                    marker=dict(
                        symbol="square",
                        size=12,
                        color="#1d4ed8",
                        line=dict(color="white", width=1),
                    ),
                    error_x=dict(
                        type="data",
                        symmetric=True,
                        array=[d["effect"] - d["ci_lower"] for d in study_data],
                        arrayminus=[d["effect"] - d["ci_lower"] for d in study_data],
                        visible=True,
                        thickness=1.5,
                        width=8,
                        color="rgba(29,78,216,0.4)",
                    ),
                    name="Studies",
                    text=[f"{d['study']}: {d['effect']:.3f} [{d['ci_lower']:.3f}, {d['ci_upper']:.3f}]"
                          for d in study_data],
                    hoverinfo="text",
                    showlegend=False,
                ))

                # Add summary diamond
                for sd in summary_data:
                    if sd.get("effect") is not None:
                        summary_y = -1  # Below all studies
                        # Diamond as scatter
                        diamond_x = [sd["effect"], sd["ci_upper"], sd["effect"], sd["ci_lower"], sd["effect"]]
                        diamond_y = [summary_y, summary_y  0.3, summary_y  0.6, summary_y  0.3, summary_y]
                        fig.add_trace(go.Scatter(
                            x=diamond_x,
                            y=diamond_y,
                            mode="linesmarkers",
                            fill="toself",
                            fillcolor="rgba(29,78,216,0.3)",
                            line=dict(color="#1d4ed8", width=2),
                            marker=dict(size=6, color="#1d4ed8"),
                            name=f"RE Model: {sd['effect']:.3f} [{sd['ci_lower']:.3f}, {sd['ci_upper']:.3f}]",
                            hoverinfo="text",
                            text=f"Pooled Effect: {sd['effect']:.3f} [{sd['ci_lower']:.3f}, {sd['ci_upper']:.3f}]",
                        ))

                # Add reference line at 0
                fig.add_vline(x=0, line=dict(color="gray", width=1, dash="dash"))

                fig.update_layout(
                    title="Forest Plot",
                    xaxis_title="Effect Size",
                    yaxis=dict(
                        tickvals=y_positions  ([-1] if summary_data else []),
                        ticktext=y_labels  ([s["study"] for s in summary_data] if summary_data else []),
                        autorange="reversed",
                        tickfont=dict(size=11),
                    ),
                    height=max(400, 50  40 * len(study_data)),
                    margin=dict(l=150, r=50, t=50, b=50),
                    hovermode="y unified",
                )

                st.plotly_chart(fig, use_container_width=True)

                # Data table
                with st.expander("ðŸ“‹ Forest Plot Data"):
                    forest_df = pd.DataFrame(forest_data)
                    st.dataframe(forest_df, use_container_width=True, hide_index=True)
            else:
                st.info("No forest plot data available.")

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # TAB 4: PUBLICATION BIAS
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    with tab4:
        results = st.session_state.get("meta_results")
        if not results:
            st.info("Run a meta-analysis first.")
        else:
            st.subheader("ðŸ•³ï¸ Publication Bias Assessment")

            eggers = results.get("eggers", {})
            fail_safe = results.get("fail_safe", {})
            trim_fill = results.get("trim_fill", {})

            col1, col2 = st.columns(2)

            with col1:
                if eggers and "error" not in eggers:
                    egger_sig = eggers.get("significant", False)
                    egger_color = "#e74c3c" if egger_sig else "#2ecc71"
                    st.markdown(f"""
                    <div style="padding:1rem;border-radius:12px;border:1px solid {egger_color}40;
                                background:{egger_color}08;text-align:center;">
                        <h4>Egger's Regression Test</h4>
                        <div style="font-size:1.5rem;font-weight:700;color:{egger_color};">
                            {'ðŸ”´ Bias Detected' if egger_sig else 'ðŸŸ¢ No Significant Bias'}
                        </div>
                        <div style="font-size:0.9rem;color:#64748b;">
                            Intercept = {eggers.get('intercept', 0):.3f} (SE = {eggers.get('intercept_se', 0):.3f})<br>
                            t = {eggers.get('intercept_t', 0):.2f}, p = {eggers.get('intercept_p', 1):.4f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("Egger's test requires â‰¥3 studies")

            with col2:
                if fail_safe and "error" not in fail_safe:
                    fs_robust = fail_safe.get("robust", False)
                    fs_color = "#2ecc71" if fs_robust else "#e67e22"
                    st.markdown(f"""
                    <div style="padding:1rem;border-radius:12px;border:1px solid {fs_color}40;
                                background:{fs_color}08;text-align:center;">
                        <h4>Rosenthal's Fail-Safe N</h4>
                        <div style="font-size:1.5rem;font-weight:700;color:{fs_color};">{fail_safe.get('fail_safe_n', 0)}</div>
                        <div style="font-size:0.85rem;color:#64748b;">
                            {'âœ… Robust (N > tolerance of '  str(fail_safe.get('tolerance', 0))  ')' if fs_robust else 'âš ï¸ Below tolerance'}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            if trim_fill and "error" not in trim_fill:
                st.subheader("Trim and Fill (Duval & Tweedie)")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Imputed Studies", trim_fill.get("n_imputed", 0))
                with col2:
                    st.metric("Adjusted Effect", f"{trim_fill.get('adjusted_pooled', 'N/A'):.3f}" if trim_fill.get("adjusted_pooled") else "N/A")
                with col3:
                    st.metric("Adjusted CI", f"[{trim_fill.get('adjusted_ci_lower', 0):.3f}, {trim_fill.get('adjusted_ci_upper', 0):.3f}]")

            # â”€â”€â”€ Funnel Plot â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            st.subheader(" Funnel Plot")
            effects = results.get("raw_effects", [])
            variances = results.get("raw_variances", [])

            if effects and len(effects) >= 3:
                import plotly.graph_objects as go

                se = [math.sqrt(v) for v in variances]
                re_result = results.get("random", {})

                fig = go.Figure()

                # Scatter points
                fig.add_trace(go.Scatter(
                    x=effects,
                    y=se,
                    mode="markers",
                    marker=dict(
                        symbol="circle",
                        size=10,
                        color="#1d4ed8",
                        opacity=0.7,
                        line=dict(color="white", width=1),
                    ),
                    name="Studies",
                    text=results.get("raw_labels", [f"Study {i1}" for i in range(len(effects))]),
                    hovertemplate="<b>%{text}</b><br>Effect: %{x:.3f}<br>SE: %{y:.4f}<extra></extra>",
                ))

                # Pooled effect line
                pooled = re_result.get("pooled_effect", 0)
                fig.add_vline(x=pooled, line=dict(color="red", width=2, dash="dash"),
                             annotation_text=f"RE Pooled: {pooled:.3f}")

                # Pseudo-confidence intervals (95%)
                max_se = max(se) * 1.3
                se_range = np.linspace(0, max_se, 100)

                for z_val, color, label in [
                    (1.96, "rgba(0,0,0,0.15)", "95% CI"),
                    (2.58, "rgba(0,0,0,0.08)", "99% CI"),
                ]:
                    lower = pooled - z_val * se_range
                    upper = pooled  z_val * se_range
                    fig.add_trace(go.Scatter(
                        x=list(lower)  list(upper)[::-1],
                        y=list(se_range)  list(se_range)[::-1],
                        fill="toself",
                        fillcolor=color,
                        line=dict(color="rgba(0,0,0,0)", width=0),
                        showlegend=False,
                        hoverinfo="skip",
                    ))

                fig.add_trace(go.Scatter(
                    x=[pooled - 1.96 * s for s in se_range],
                    y=se_range,
                    mode="lines",
                    line=dict(color="rgba(0,0,0,0.3)", width=1, dash="dot"),
                    showlegend=False,
                    hoverinfo="skip",
                ))
                fig.add_trace(go.Scatter(
                    x=[pooled  1.96 * s for s in se_range],
                    y=se_range,
                    mode="lines",
                    line=dict(color="rgba(0,0,0,0.3)", width=1, dash="dot"),
                    showlegend=False,
                    hoverinfo="skip",
                ))

                fig.update_layout(
                    title="Funnel Plot (Effect Size vs. Standard Error)",
                    xaxis_title="Effect Size",
                    yaxis_title="Standard Error",
                    yaxis=dict(autorange="reversed"),
                    height=500,
                    hovermode="closest",
                )

                st.plotly_chart(fig, use_container_width=True)

                # Interpretation
                if eggers and "error" not in eggers:
                    interp_color = "#e74c3c" if eggers.get("significant") else "#2ecc71"
                    st.markdown(f"""
                    <div style="padding:0.6rem;border-radius:8px;border-left:4px solid {interp_color};
                                background:{interp_color}08;">
                        <strong>Interpretation:</strong> {eggers.get('interpretation', '')}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Need at least 3 studies for funnel plot")

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # TAB 5: ADVANCED
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    with tab5:
        results = st.session_state.get("meta_results")
        raw_effects = results.get("raw_effects", []) if results else []
        raw_variances = results.get("raw_variances", []) if results else []
        raw_labels = results.get("raw_labels", []) if results else []

        if not raw_effects or len(raw_effects) < 2:
            st.info("Run a meta-analysis first to access advanced features.")
        else:
            engine = MetaAnalysisEngine()
            st.subheader("ðŸ”¬ Advanced Meta-Analysis Tools")

            # â”€â”€â”€ Cumulative Meta-Analysis â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            with st.expander("ðŸ“ˆ Cumulative Meta-Analysis", expanded=False):
                st.markdown("Add studies one by one to see how evidence accumulates.")

                sort_method = st.radio("Sort studies by", options=["Year (chronological)", "Effect Size", "Precision"],
                                      horizontal=True, key="cumul_sort")

                if sort_method == "Year (chronological)":
                    sort_by = list(range(len(raw_effects)))
                elif sort_method == "Effect Size":
                    sort_by = raw_effects
                else:
                    sort_by = [1 / math.sqrt(v) for v in raw_variances]

                if st.button(" Run Cumulative Analysis", use_container_width=True):
                    cumul = engine.cumulative_meta_analysis(
                        raw_effects, raw_variances, sort_by, raw_labels
                    )
                    cumul_data = cumul.get("cumulative", [])

                    if cumul_data:
                        import plotly.graph_objects as go

                        fig = go.Figure()

                        steps = [d["step"] for d in cumul_data]
                        pooled = [d["pooled"] for d in cumul_data]
                        ci_lower = [d["ci_lower"] for d in cumul_data]
                        ci_upper = [d["ci_upper"] for d in cumul_data]
                        labels_cumul = [d["last_study"][:30] for d in cumul_data]

                        fig.add_trace(go.Scatter(
                            x=steps,
                            y=pooled,
                            mode="linesmarkers",
                            line=dict(color="#1d4ed8", width=2),
                            marker=dict(size=8, color="#1d4ed8"),
                            error_y=dict(
                                type="data",
                                symmetric=False,
                                array=[u - p for p, u in zip(pooled, ci_upper)],
                                arrayminus=[p - l for p, l in zip(pooled, ci_lower)],
                                visible=True,
                                thickness=1.5,
                                width=4,
                                color="rgba(29,78,216,0.3)",
                            ),
                            text=labels_cumul,
                            hovertemplate="Step %{x}<br>Pooled: %{y:.3f}<br>Last study: %{text}<extra></extra>",
                            name="Cumulative Pooled Effect",
                        ))

                        fig.add_hline(y=0, line=dict(color="gray", width=1, dash="dash"))

                        fig.update_layout(
                            title="Cumulative Meta-Analysis",
                            xaxis_title="Studies Added (Cumulative)",
                            yaxis_title="Pooled Effect Size",
                            height=400,
                            hovermode="x unified",
                        )

                        st.plotly_chart(fig, use_container_width=True)

            # â”€â”€â”€ Leave-One-Out Sensitivity â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            with st.expander("ðŸ” Leave-One-Out Sensitivity Analysis", expanded=False):
                st.markdown("Omit one study at a time to check robustness.")

                if len(raw_effects) >= 3:
                    if st.button("ðŸ”¬ Run Sensitivity Analysis", use_container_width=True):
                        loo = engine.leave_one_out(raw_effects, raw_variances, raw_labels)

                        overall = loo.get("overall_pooled", 0)
                        overall_ci_lower = loo.get("overall_ci_lower", 0)
                        overall_ci_upper = loo.get("overall_ci_upper", 0)

                        st.markdown(f"**Overall (all studies):** {overall:.3f} [{overall_ci_lower:.3f}, {overall_ci_upper:.3f}]")

                        loo_results = loo.get("results", [])
                        loo_df = pd.DataFrame(loo_results)
                        st.dataframe(loo_df, use_container_width=True, hide_index=True)

                        # Visualization
                        import plotly.graph_objects as go

                        fig = go.Figure()
                        for r in loo_results:
                            if r.get("random_pooled") is not None:
                                fig.add_trace(go.Scatter(
                                    x=[r["random_pooled"]],
                                    y=[r["omitted_study"][:40]],
                                    mode="markerslines",
                                    marker=dict(size=10, color="#e67e22"),
                                    error_x=dict(
                                        type="data",
                                        symmetric=True,
                                        array=[r["random_pooled"] - r["random_ci_lower"]],
                                        visible=True,
                                        thickness=1.5,
                                        width=8,
                                        color="rgba(230,126,34,0.4)",
                                    ),
                                    name=r["omitted_study"][:40],
                                    showlegend=False,
                                ))

                        fig.add_vline(x=overall, line=dict(color="red", width=2, dash="dash"),
                                     annotation_text=f"Overall: {overall:.3f}")
                        fig.add_vrect(x0=overall_ci_lower, x1=overall_ci_upper,
                                     fillcolor="red", opacity=0.05, line_width=0)

                        fig.update_layout(
                            title="Leave-One-Out Sensitivity Analysis",
                            xaxis_title="Pooled Effect (95% CI)",
                            height=max(300, 40 * len(loo_results)),
                            margin=dict(l=200),
                        )

                        st.plotly_chart(fig, use_container_width=True)

                        if loo.get("influential_studies"):
                            st.warning(f"âš ï¸ {len(loo['influential_studies'])} influential study(ies) detected!")
                else:
                    st.info("Need at least 3 studies for leave-one-out analysis")

            # â”€â”€â”€ Subgroup Analysis â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            with st.expander("ðŸ“‚ Subgroup Analysis", expanded=False):
                st.markdown("Define subgroups to compare pooled effects across groups.")

                n_studies = len(raw_effects)
                subgroup_input = st.text_area(
                    "Enter subgroup for each study (comma-separated, e.g., Male, Female, Male, ...)",
                    placeholder="e.g., Treatment, Control, Treatment, Control",
                    key="meta_subgroup_input",
                )
                subgroup_names = [s.strip() for s in subgroup_input.split(",") if s.strip()]

                if st.button(" Run Subgroup Analysis") and len(subgroup_names) == n_studies:
                    sg = engine.subgroup_analysis(raw_effects, raw_variances, subgroup_names, raw_labels)
                    sg_groups = sg.get("groups", {})

                    for group_name, group_res in sg_groups.items():
                        re = group_res.get("random", {})
                        st.markdown(f"**{group_name}** (k = {group_res.get('k', 0)})")
                        st.markdown(f"Pooled (RE): {re.get('pooled_effect', 'N/A'):.3f} "
                                   f"[{re.get('ci_lower', 0):.3f}, {re.get('ci_upper', 0):.3f}]"
                                   f"  IÂ² = {re.get('i2', 0):.1f}%")
                elif subgroup_names and len(subgroup_names) != n_studies:
                    st.error(f"Expected {n_studies} subgroup labels, got {len(subgroup_names)}")

            # â”€â”€â”€ Meta-Regression â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            with st.expander("ðŸ“ Meta-Regression", expanded=False):
                st.markdown("Test continuous moderators (e.g., year, sample size, mean age).")

                st.info("Enter a numeric moderator value for each study (comma-separated):")
                moderator_input = st.text_input(
                    "Moderator values (e.g., year of publication)",
                    placeholder="2020, 2019, 2021, ...",
                    key="meta_mod_input",
                )
                mod_name = st.text_input("Moderator name", value="Moderator", key="meta_mod_name")

                mod_values = []
                for v in moderator_input.split(","):
                    v = v.strip()
                    try:
                        mod_values.append(float(v))
                    except ValueError:
                        pass

                if st.button("ðŸ“ Run Meta-Regression") and len(mod_values) == n_studies:
                    mr = engine.meta_regression(
                        raw_effects, raw_variances,
                        [mod_values],
                        [mod_name],
                    )
                    if "error" in mr:
                        st.error(mr["error"])
                    else:
                        st.markdown(f"**RÂ² = {mr.get('r_squared', 0):.3f}**")
                        coeff_df = pd.DataFrame(mr.get("coefficients", []))
                        st.dataframe(coeff_df, use_container_width=True, hide_index=True)
                elif mod_values and len(mod_values) != n_studies:
                    st.error(f"Expected {n_studies} values, got {len(mod_values)}")

    # â”€â”€â”€ Sidebar: Download Results â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    results = st.session_state.get("meta_results")
    if results:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### ðŸ“¥ Export Meta-Analysis")

        report_lines = [
            "# Meta-Analysis Results",
            f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}",
            f"k = {results.get('k', 0)} studies",
            "",
            "## Fixed Effects Model",
        ]
        fe = results.get("fixed", {})
        if fe:
            report_lines.extend([
                f"Pooled Effect: {fe.get('pooled_effect', 'N/A')}",
                f"95% CI: [{fe.get('ci_lower', 'N/A')}, {fe.get('ci_upper', 'N/A')}]",
                f"z = {fe.get('z_value', 'N/A')}, p = {fe.get('p_value', 'N/A')}",
                "",
            ])

        re = results.get("random", {})
        report_lines.append("## Random Effects Model (DerSimonian-Laird)")
        if re:
            report_lines.extend([
                f"Pooled Effect: {re.get('pooled_effect', 'N/A')}",
                f"95% CI: [{re.get('ci_lower', 'N/A')}, {re.get('ci_upper', 'N/A')}]",
                f"z = {re.get('z_value', 'N/A')}, p = {re.get('p_value', 'N/A')}",
                "",
            ])

        het = results.get("heterogeneity", {})
        report_lines.append("## Heterogeneity")
        if het:
            report_lines.extend([
                f"IÂ² = {het.get('i2', 'N/A')}%",
                f"Q({het.get('q_df', 'N/A')}) = {het.get('q_statistic', 'N/A')}, p = {het.get('q_p_value', 'N/A')}",
                f"Ï„Â² = {het.get('tau2', 'N/A')}",
                "",
            ])

        report_text = "\n".join(report_lines)
        # Escape backticks for embedding in JS onclick handler
        report_text_escaped = report_text.replace("`", "\\`")

        st.sidebar.markdown(
            f"""<button onclick="navigator.clipboard.writeText(`{report_text_escaped}`).then(
                () => {{this.innerHTML='âœ… Copied!';setTimeout(()=>this.innerHTML='ðŸ“‹ Copy Report',2000)}})"
                style="padding:8px 16px;background:#1d4ed8;color:white;border:none;border-radius:6px;
                cursor:pointer;font-weight:600;width:100%;">ðŸ“‹ Copy Report</button>""",
            unsafe_allow_html=True,
        )

