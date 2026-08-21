"""
spss_suite.py
SPSS-Grade Advanced Statistical Suite.

Extends the existing StatisticalEngine with advanced procedures commonly
performed in SPSS: ANCOVA, MANOVA, survey weighting, factor retention,
bootstrapped confidence intervals, and .sav export (via pyreadstat).

Dependencies (optional): statsmodels, pingouin, factor_analyzer, pyreadstat.
Graceful degradation when dependencies are missing.
"""
from __future__ import annotations

import io
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

try:
    import statsmodels.api as sm
    from statsmodels.formula.api import ols as sm_ols

    HAS_STATSMODELS = True
except Exception:
    HAS_STATSMODELS = False

try:
    import pingouin as pg

    HAS_PINGOUIN = True
except Exception:
    HAS_PINGOUIN = False

try:
    from scipy import stats as scipy_stats
    from scipy.stats import f as f_dist

    HAS_SCIPY = True
except Exception:
    HAS_SCIPY = False


class SPSSSuite:
    """Advanced SPSS-style statistical procedures."""

    # ------------------------------------------------------------------
    # ANCOVA
    # ------------------------------------------------------------------
    def ancova(
        self,
        df: pd.DataFrame,
        group_col: str,
        value_col: str,
        covariate_col: str,
    ) -> Dict[str, Any]:
        """Analysis of Covariance using statsmodels."""
        if not HAS_STATSMODELS:
            return {"error": "statsmodels required for ANCOVA"}
        try:
            model = sm_ols(
                f"{value_col} ~ C({group_col}) + {covariate_col}", data=df
            ).fit()
            anova = sm.stats.anova_lm(model, typ=2)
            return {
                "test": "ANCOVA",
                "groups": group_col,
                "covariate": covariate_col,
                "anova_table": anova.round(4),
                "r_squared": round(float(model.rsquared), 4),
                "params": model.params.round(4).to_dict(),
                "p_value_group": round(float(anova.loc["C(%s)" % group_col, "PR(>F)"]), 4),
            }
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # MANOVA (via pingouin)
    # ------------------------------------------------------------------
    def manova(
        self,
        df: pd.DataFrame,
        group_col: str,
        dependent_cols: List[str],
    ) -> Dict[str, Any]:
        """Multivariate ANOVA using pingouin."""
        if not HAS_PINGOUIN:
            return {"error": "pingouin required for MANOVA"}
        try:
            aov = pg.mova(dv=dependent_cols, between=group_col, data=df)
            return {"test": "MANOVA", "summary": aov.round(4)}
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # Survey weighting
    # ------------------------------------------------------------------
    @staticmethod
    def survey_weight(
        df: pd.DataFrame,
        category_col: str,
        population_totals: Dict[str, float],
    ) -> pd.DataFrame:
        """Compute and apply post-stratification survey weights."""
        counts = df[category_col].value_counts()
        total_pop = sum(population_totals.values())
        weights = {}
        for cat, pop in population_totals.items():
            n = counts.get(cat, 0)
            if n > 0:
                weights[cat] = (pop / total_pop) / (n / len(df))
        df_out = df.copy()
        df_out["survey_weight"] = df_out[category_col].map(weights)
        return df_out

    # ------------------------------------------------------------------
    # Factor retention (KMO + Bartlett + eigenvalues)
    # ------------------------------------------------------------------
    def factor_retention(self, df: pd.DataFrame, variables: List[str]) -> Dict[str, Any]:
        """KMO, Bartlett's test, and eigenvalue-based factor counts."""
        try:
            from factor_analyzer.factor_analyzer import calculate_kmo, calculate_bartlett_sphericity

            kmo_all, kmo_per = calculate_kmo(df[variables])
            chi2, pval = calculate_bartlett_sphericity(df[variables])
            corr = df[variables].corr()
            eigvals, _ = np.linalg.eigh(corr)
            eigvals = np.sort(eigvals)[::-1]
            n_above_1 = int((eigvals > 1).sum())
            cum_var = (eigvals / eigvals.sum()).cumsum()
            return {
                "test": "Factor Retention Diagnostics",
                "kmo_overall": round(float(kmo_all), 4),
                "kmo_per_variable": dict(zip(variables, [round(float(v), 4) for v in kmo_per])),
                "bartlett_chi2": round(float(chi2), 4),
                "bartlett_p": round(float(pval), 4),
                "eigenvalues": [round(float(e), 4) for e in eigvals],
                "factors_above_1": n_above_1,
                "cumulative_variance": [round(float(v), 4) for v in cum_var],
                "recommended_factors": max(1, n_above_1),
            }
        except ImportError:
            return {"error": "factor_analyzer required. pip install factor-analyzer"}
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # Bootstrapped confidence intervals
    # ------------------------------------------------------------------
    def bootstrap_statistic(
        self,
        df: pd.DataFrame,
        col: str,
        stat_fn="mean",
        n_boot: int = 1000,
        ci: float = 0.95,
    ) -> Dict[str, Any]:
        """Bootstrap a statistic (mean/median/std) with CI."""
        series = df[col].dropna().values
        if len(series) < 2:
            return {"error": "Need at least 2 observations"}
        fns = {"mean": np.mean, "median": np.median, "std": np.std}
        fn = fns.get(stat_fn, np.mean)
        rng = np.random.default_rng(42)
        boot = np.array([fn(rng.choice(series, size=len(series), replace=True)) for _ in range(n_boot)])
        alpha = (1 - ci) / 2
        lo, hi = np.percentile(boot, [alpha * 100, (1 - alpha) * 100])
        return {
            "test": f"Bootstrapped {stat_fn}",
            "statistic": round(float(fn(series)), 4),
            "ci_lower": round(float(lo), 4),
            "ci_upper": round(float(hi), 4),
            "ci_level": ci,
            "n_bootstrap": n_boot,
            "samples": n_boot,
        }

    # ------------------------------------------------------------------
    # .sav export (SPSS)
    # ------------------------------------------------------------------
    @staticmethod
    def export_sav(df: pd.DataFrame) -> Optional[bytes]:
        """Write a DataFrame to an SPSS .sav binary file."""
        try:
            import pyreadstat

            buf = io.BytesIO()
            pyreadstat.write_sav(df, buf)
            buf.seek(0)
            return buf.getvalue()
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Automated APA write-up for a test result
    # ------------------------------------------------------------------
    @staticmethod
    def apa_writeup(test_name: str, stats: Dict[str, Any]) -> str:
        """Generate a publication-ready APA 7th sentence from a stats dict."""
        sig = stats.get("significant", False)
        parts = []
        if "t_statistic" in stats:
            parts.append(
                f"An independent-samples t-test revealed "
                f"{'a significant' if sig else 'no significant'} difference, "
                f"t = {stats.get('t_statistic')}, p = {stats.get('p_value')}, "
                f"d = {stats.get('cohens_d', 'N/A')}."
            )
        elif "f_statistic" in stats:
            parts.append(
                f"A one-way ANOVA revealed {'a significant' if sig else 'no significant'} effect, "
                f"F = {stats.get('f_statistic')}, p = {stats.get('p_value')}, "
                f"Î·Â² = {stats.get('eta_squared', 'N/A')}."
            )
        else:
            parts.append(f"{test_name}: {json_safe(stats)}")
        return " ".join(parts)


def json_safe(obj: Any) -> str:
    import json

    try:
        return json.dumps(obj, default=str)
    except Exception:
        return str(obj)

