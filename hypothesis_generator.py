
"""
Automated Hypothesis Generator  discovers patterns, formulates research hypotheses,
and prioritizes them by statistical support and novelty.
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
import math
import re
import warnings
warnings.filterwarnings('ignore')

from modules.data_processor import infer_column_types, profile_dataset
from modules.statistical_engine import StatisticalEngine
from scipy import stats as scipy_stats


# ─── Literature Effect Size Benchmarks ─────────────────────────────
DEFAULT_BENCHMARKS = {
    "psychology": {"small": 0.20, "medium": 0.50, "large": 0.80},
    "education": {"small": 0.15, "medium": 0.40, "large": 0.65},
    "medicine": {"small": 0.10, "medium": 0.30, "large": 0.50},
    "neuroscience": {"small": 0.25, "medium": 0.55, "large": 0.85},
    "social_science": {"small": 0.15, "medium": 0.35, "large": 0.60},
    "business": {"small": 0.15, "medium": 0.35, "large": 0.55},
    "biology": {"small": 0.30, "medium": 0.60, "large": 0.90},
    "default": {"small": 0.20, "medium": 0.50, "large": 0.80},
}

class HypothesisGenerator:
    """CHRISHEM-powered research hypothesis discovery and formulation engine."""

    def __init__(self):
        self.stats = StatisticalEngine()
        self.generated_hypotheses = []

    def discover_hypotheses(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Run full hypothesis discovery pipeline."""
        if df is None or df.empty:
            return {"error": "No data available", "hypotheses": []}

        col_types = infer_column_types(df)
        hypotheses = []

        # 1. Mean-difference hypotheses (categorical → numeric)
        cat_cols = [c for c, t in col_types.items() if t in ("categorical", "string")]
        num_cols = [c for c, t in col_types.items() if t in ("numeric", "integer")]

        for cat in cat_cols[:5]:
            for num in num_cols[:5]:
                hyps = self._test_mean_difference(df, cat, num)
                hypotheses.extend(hyps)

        # 2. Correlation hypotheses (numeric → numeric)
        for i, num1 in enumerate(num_cols[:6]):
            for num2 in num_cols[i1:6]:
                hyps = self._test_correlation(df, num1, num2)
                hypotheses.extend(hyps)

        # 3. Association hypotheses (categorical → categorical)
        for i, cat1 in enumerate(cat_cols[:5]):
            for cat2 in cat_cols[i1:5]:
                hyps = self._test_association(df, cat1, cat2)
                hypotheses.extend(hyps)

        # 4. Change-over-time hypotheses (if temporal cols exist)
        temp_cols = [c for c, t in col_types.items() if t == "temporal"]
        if temp_cols and num_cols:
            for temp in temp_cols[:2]:
                for num in num_cols[:3]:
                    hyps = self._test_trend(df, temp, num)
                    hypotheses.extend(hyps)

        # 5. Group-difference hypotheses (multi-group)
        for cat in cat_cols[:3]:
            if df[cat].nunique() >= 3:
                for num in num_cols[:3]:
                    hyps = self._test_group_difference(df, cat, num)
                    hypotheses.extend(hyps)

        # Score and rank
        hypotheses = self._score_hypotheses(hypotheses)
        hypotheses.sort(key=lambda h: h.get("priority_score", 0), reverse=True)

        # Assign IDs and generate narrative
        for i, h in enumerate(hypotheses):
            h["id"] = f"H{i1:03d}"
            h["narrative"] = self._generate_narrative(h)

        self.generated_hypotheses = hypotheses

        return {
            "total_discovered": len(hypotheses),
            "hypotheses": hypotheses[:30],
            "summary": f"Discovered {len(hypotheses)} potential hypotheses from your data",
            "top_hypothesis": hypotheses[0] if hypotheses else None,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def _test_mean_difference(self, df: pd.DataFrame, cat: str, num: str) -> List[Dict]:
        """Test if mean of num differs across cat groups."""
        hypotheses = []
        groups = df[cat].dropna().unique()
        if len(groups) < 2 or len(groups) > 10:
            return hypotheses

        try:
            if len(groups) == 2:
                result = self.stats.independent_ttest(df, cat, num)
                if "error" not in result:
                    hypotheses.append({
                        "type": "mean_difference",
                        "independent_variable": cat,
                        "dependent_variable": num,
                        "test": "Independent T-Test",
                        "group_1": str(result.get("group_1", "")),
                        "group_2": str(result.get("group_2", "")),
                        "mean_1": result.get("mean_1", 0),
                        "mean_2": result.get("mean_2", 0),
                        "effect_size": result.get("cohens_d", 0),
                        "p_value": result.get("p_value", 1),
                        "significant": result.get("significant", False),
                        "direction": f"{result.get('group_1', '')} > {result.get('group_2', '')}" if result.get("mean_1", 0) > result.get("mean_2", 0) else f"{result.get('group_2', '')} > {result.get('group_1', '')}",
                    })
            else:
                result = self.stats.anova_one_way(df, cat, num)
                if "error" not in result:
                    hypotheses.append({
                        "type": "group_difference",
                        "independent_variable": cat,
                        "dependent_variable": num,
                        "test": "One-Way ANOVA",
                        "num_groups": len(groups),
                        "effect_size": result.get("eta_squared", 0),
                        "p_value": result.get("p_value", 1),
                        "significant": result.get("significant", False),
                        "f_statistic": result.get("f_statistic", 0),
                    })
        except Exception:
            pass

        return hypotheses

    def _test_correlation(self, df: pd.DataFrame, num1: str, num2: str) -> List[Dict]:
        """Test correlation between two numeric variables."""
        hypotheses = []
        try:
            result = self.stats.pearson_correlation(df, num1, num2)
            if "error" not in result:
                hypotheses.append({
                    "type": "correlation",
                    "variable_1": num1,
                    "variable_2": num2,
                    "test": "Pearson Correlation",
                    "r": result.get("r", 0),
                    "r_squared": result.get("r_squared", 0),
                    "p_value": result.get("p_value", 1),
                    "significant": result.get("significant", False),
                    "strength": result.get("strength", "weak"),
                    "direction": "positive" if result.get("r", 0) > 0 else "negative",
                })
        except Exception:
            pass
        return hypotheses

    def _test_association(self, df: pd.DataFrame, cat1: str, cat2: str) -> List[Dict]:
        """Test association between categorical variables."""
        hypotheses = []
        try:
            result = self.stats.chi_square_test(df, cat1, cat2)
            if "error" not in result:
                hypotheses.append({
                    "type": "association",
                    "variable_1": cat1,
                    "variable_2": cat2,
                    "test": "Chi-Square Test",
                    "chi_square": result.get("chi_square", 0),
                    "p_value": result.get("p_value", 1),
                    "significant": result.get("significant", False),
                    "cramers_v": result.get("cramers_v", 0),
                    "strength": "strong" if result.get("cramers_v", 0) >= 0.5 else "moderate" if result.get("cramers_v", 0) >= 0.3 else "weak",
                })
        except Exception:
            pass
        return hypotheses

    def _test_trend(self, df: pd.DataFrame, temp: str, num: str) -> List[Dict]:
        """Test for trends over time."""
        hypotheses = []
        try:
            # Use Spearman correlation between time (as ordinal) and value
            temp_ordinal = pd.to_datetime(df[temp]).astype('int64') // 10**9
            r, p = scipy_stats.spearmanr(temp_ordinal.dropna(), df[num].dropna())
            if not np.isnan(r):
                hypotheses.append({
                    "type": "trend",
                    "temporal_variable": temp,
                    "dependent_variable": num,
                    "test": "Spearman Trend Test",
                    "rho": round(float(r), 4),
                    "p_value": round(float(p), 4) if not np.isnan(p) else 1,
                    "significant": p < 0.05 if not np.isnan(p) else False,
                    "direction": "increasing" if r > 0 else "decreasing",
                    "strength": "strong" if abs(r) >= 0.6 else "moderate" if abs(r) >= 0.3 else "weak",
                })
        except Exception:
            pass
        return hypotheses

    def _test_group_difference(self, df: pd.DataFrame, cat: str, num: str) -> List[Dict]:
        """Test for multi-group differences using ANOVA."""
        hypotheses = []
        try:
            result = self.stats.anova_one_way(df, cat, num)
            if "error" not in result:
                hypotheses.append({
                    "type": "multi_group_difference",
                    "group_variable": cat,
                    "dependent_variable": num,
                    "test": "One-Way ANOVA",
                    "num_groups": result.get("num_groups", 0),
                    "f_statistic": result.get("f_statistic", 0),
                    "p_value": result.get("p_value", 1),
                    "significant": result.get("significant", False),
                    "effect_size": result.get("eta_squared", 0),
                    "post_hoc_available": not result.get("post_hoc", pd.DataFrame()).empty,
                })
        except Exception:
            pass
        return hypotheses

    # ─── Literature Gap Analysis ───────────────────────────────────

    def compare_against_literature(
        self,
        hypotheses: List[Dict],
        literature_effect_sizes: Optional[List[Dict]] = None,
        discipline: str = "default",
    ) -> List[Dict]:
        """
        Compare discovered hypotheses against published effect size benchmarks
        or literature-extracted effect sizes to identify:
          - Novel findings (effect differs from literature norms)
          - Replication support (effect matches literature)
          - Knowledge gaps (patterns not found in literature)

        Args:
            hypotheses: List of hypothesis dicts from discover_hypotheses()
            literature_effect_sizes: Optional list of dicts with keys:
                'variable_pair', 'effect_size', 'ci_lower', 'ci_upper', 'n', 'source'
                If None, uses generic discipline benchmarks.
            discipline: Academic discipline for benchmark selection

        Returns:
            Hypotheses with added gap analysis fields
        """
        benchmarks = DEFAULT_BENCHMARKS.get(discipline, DEFAULT_BENCHMARKS["default"])

        for h in hypotheses:
            gap_analysis = {}

            # Extract the effect size and variable pair label
            es = abs(h.get("effect_size", h.get("r", h.get("cramers_v", h.get("rho", 0)))))
            htype = h.get("type", "")

            # Build a variable pair key for matching against literature
            if htype == "mean_difference":
                var_pair = f"{h.get('independent_variable','')}__{h.get('dependent_variable','')}"
            elif htype == "correlation":
                var_pair = f"{h.get('variable_1','')}__{h.get('variable_2','')}"
            elif htype == "association":
                var_pair = f"{h.get('variable_1','')}__{h.get('variable_2','')}"
            elif htype == "trend":
                var_pair = f"{h.get('dependent_variable','')}__time"
            elif htype == "multi_group_difference":
                var_pair = f"{h.get('group_variable','')}__{h.get('dependent_variable','')}"
            else:
                var_pair = "unknown"

            # 1. Compare against discipline benchmarks
            if es < benchmarks["small"] * 0.8:
                benchmark_label = "very_small"
            elif es < benchmarks["medium"] * 0.8:
                benchmark_label = "small"
            elif es < benchmarks["large"] * 0.8:
                benchmark_label = "medium"
            else:
                benchmark_label = "large"

            h["effect_size_label"] = benchmark_label
            gap_analysis["benchmark_vs_discipline"] = {
                "discipline": discipline,
                "your_effect": round(es, 3),
                "small_threshold": benchmarks["small"],
                "medium_threshold": benchmarks["medium"],
                "large_threshold": benchmarks["large"],
                "label": benchmark_label,
            }

            # 2. Compare against literature-extracted effect sizes (if provided)
            literature_match = None
            if literature_effect_sizes and var_pair != "unknown":
                for lit in literature_effect_sizes:
                    lit_pair = lit.get("variable_pair", "")
                    # Fuzzy match: check if variable names overlap
                    if self._variable_pairs_match(var_pair, lit_pair):
                        literature_match = lit
                        break

            if literature_match:
                lit_es = abs(literature_match.get("effect_size", 0))
                lit_ci_lower = literature_match.get("ci_lower", lit_es * 0.7)
                lit_ci_upper = literature_match.get("ci_upper", lit_es * 1.3)

                # Compute overlap: does our effect fall within literature CI?
                our_ci_lower, our_ci_upper = self._approximate_ci(
                    es, n=h.get("n", literature_match.get("n", 100))
                )

                # Check if our CI overlaps with literature CI
                overlap_low = max(our_ci_lower, lit_ci_lower)
                overlap_high = min(our_ci_upper, lit_ci_upper)
                overlaps = overlap_low <= overlap_high

                # Effect size discrepancy
                es_diff = abs(es - lit_es)
                es_diff_pct = (es_diff / max(lit_es, 0.01)) * 100

                if overlaps:
                    gap_type = "replication"
                    gap_label = "✅ Consistent with literature"
                    novelty_score = 20  # Low novelty
                elif es > lit_es * 1.5:
                    gap_type = "novel_larger"
                    gap_label = "🔬 Novel finding  larger than reported"
                    novelty_score = 85
                elif es < lit_es * 0.5:
                    gap_type = "novel_smaller"
                    gap_label = "🔬 Novel finding  smaller than reported"
                    novelty_score = 75
                else:
                    gap_type = "inconsistent"
                    gap_label = "⚠️ Inconsistent with literature"
                    novelty_score = 60

                gap_analysis["literature_comparison"] = {
                    "type": gap_type,
                    "label": gap_label,
                    "novelty_score": novelty_score,
                    "literature_effect": round(lit_es, 3),
                    "your_effect": round(es, 3),
                    "effect_difference": round(es_diff, 3),
                    "effect_difference_pct": round(es_diff_pct, 1),
                    "ci_overlap": overlaps,
                    "source": literature_match.get("source", "unknown"),
                }

                # Adjust priority score with novelty
                current_score = h.get("priority_score", 50)
                if gap_type == "novel_larger" or gap_type == "novel_smaller":
                    adjusted = min(100, current_score + 15)
                elif gap_type == "replication":
                    adjusted = min(100, current_score + 5)
                else:
                    adjusted = max(0, current_score - 10)
                h["priority_score"] = adjusted
                h["priority_label"] = self._score_to_label(adjusted)

            else:
                # No literature match  this is a potential knowledge gap
                gap_analysis["literature_comparison"] = {
                    "type": "knowledge_gap",
                    "label": "💡 Potential knowledge gap  no literature comparison found",
                    "novelty_score": 70,
                    "literature_effect": None,
                    "your_effect": round(es, 3),
                    "effect_difference": None,
                    "effect_difference_pct": None,
                    "ci_overlap": None,
                    "source": None,
                }
                # Boost score for unexplored patterns
                h["priority_score"] = min(100, h.get("priority_score", 50) + 10)
                h["priority_label"] = self._score_to_label(h["priority_score"])

            h["gap_analysis"] = gap_analysis
            h["has_literature_context"] = literature_match is not None

        return hypotheses

    def _variable_pairs_match(self, pair_a: str, pair_b: str) -> bool:
        """Check if two variable pair strings refer to similar variables."""
        vars_a = set(pair_a.lower().replace("__", " ").replace("_", " ").split())
        vars_b = set(pair_b.lower().replace("__", " ").replace("_", " ").split())
        if not vars_a or not vars_b:
            return False
        shorter = min(len(vars_a), len(vars_b))
        if shorter == 0:
            return False
        overlap = len(vars_a & vars_b)
        return overlap / shorter >= 0.5

    def _approximate_ci(self, effect_size: float, n: int = 100, alpha: float = 0.05) -> Tuple[float, float]:
        """Approximate confidence interval for an effect size using normal approximation."""
        if n < 2:
            return (effect_size * 0.5, effect_size * 1.5)
        se = math.sqrt((1 - effect_size**2) / (n - 2)) if abs(effect_size) < 1 else 1.0 / math.sqrt(n - 2)
        z = scipy_stats.norm.ppf(1 - alpha / 2)
        return (effect_size - z * se, effect_size + z * se)

    def _score_to_label(self, score: int) -> str:
        if score >= 80: return "Critical"
        if score >= 60: return "High"
        if score >= 40: return "Medium"
        return "Low"

    def generate_gap_narrative(self, h: Dict) -> str:
        """Generate an enhanced narrative that includes literature gap context."""
        base_narrative = h.get("narrative", self._generate_narrative(h))
        gap = h.get("gap_analysis", {}).get("literature_comparison", {})
        gap_type = gap.get("type", "")

        if gap_type == "replication":
            return base_narrative + f" ✅ This finding is consistent with published literature (source: {gap.get('source', 'unknown')})."
        elif gap_type in ("novel_larger", "novel_smaller"):
            direction = "larger" if gap_type == "novel_larger" else "smaller"
            return base_narrative + f" 🔬 This effect is notably {direction} than previously reported (d_lit={gap.get('literature_effect', 0):.2f}). This may represent a novel finding."
        elif gap_type == "knowledge_gap":
            return base_narrative + " 💡 This pattern has not been found in the literature review  potential knowledge gap worth exploring."
        elif gap_type == "inconsistent":
            return base_narrative + f" ⚠️ This finding diverges from published literature (d_lit={gap.get('literature_effect', 0):.2f}). Consider contextual or methodological factors."
        return base_narrative

    def _score_hypotheses(self, hypotheses: List[Dict]) -> List[Dict]:
        """Score and rank hypotheses by statistical support and novelty."""
        for h in hypotheses:
            score = 0

            # Significance
            if h.get("significant"):
                score = 40

            # Effect size magnitude
            es = abs(h.get("effect_size", h.get("r", h.get("cramers_v", h.get("rho", 0)))))
            if es >= 0.8:
                score = 30
            elif es >= 0.5:
                score = 20
            elif es >= 0.2:
                score = 10

            # P-value precision
            p = h.get("p_value", 1)
            if p < 0.001:
                score = 20
            elif p < 0.01:
                score = 15
            elif p < 0.05:
                score = 10

            # Type bonus (causal-sounding hypotheses score higher)
            if h.get("type") in ("mean_difference", "group_difference"):
                score = 5  # More actionable
            elif h.get("type") == "trend":
                score = 8  # Temporal patterns are valuable
            elif h.get("type") == "correlation":
                score = 3

            h["priority_score"] = min(score, 100)
            h["priority_label"] = "Critical" if score >= 80 else "High" if score >= 60 else "Medium" if score >= 40 else "Low"

        return hypotheses

    def _generate_narrative(self, h: Dict) -> str:
        """Generate a plain-English narrative for a hypothesis."""
        htype = h.get("type", "")
        p_val = h.get("p_value", 1)
        p_str = "< .001" if p_val < 0.001 else f"= {p_val:.3f}"

        if htype == "mean_difference":
            iv = h.get("independent_variable", "X")
            dv = h.get("dependent_variable", "Y")
            g1 = h.get("group_1", "Group A")
            g2 = h.get("group_2", "Group B")
            m1 = h.get("mean_1", 0)
            m2 = h.get("mean_2", 0)
            es = abs(h.get("effect_size", 0))
            es_label = "large" if es >= 0.8 else "medium" if es >= 0.5 else "small"
            direction = "higher" if h.get("direction", "").startswith(g1) else "lower"
            test = h.get("test", "T-Test")
            return f"**{iv}** significantly predicts **{dv}**: {g1} (M={m1:.2f}) has {direction} scores than {g2} (M={m2:.2f}), with a {es_label} effect (d = {h.get('effect_size', 0):.2f}, {test})."

        elif htype == "correlation":
            v1 = h.get("variable_1", "X")
            v2 = h.get("variable_2", "Y")
            r = h.get("r", 0)
            r2 = h.get("r_squared", 0)
            strength = "strong" if abs(r) >= 0.6 else "moderate" if abs(r) >= 0.3 else "weak"
            direction = h.get("direction", "")
            return f"**{v1}** and **{v2}** show a {strength} {direction} linear relationship (r = {r:.2f}, r² = {r2:.2f}, p {p_str})."

        elif htype == "association":
            v1 = h.get("variable_1", "X")
            v2 = h.get("variable_2", "Y")
            chi2 = h.get("chi_square", 0)
            v = h.get("cramers_v", 0)
            strength = h.get("strength", "")
            return f"**{v1}** and **{v2}** have a {strength} association (χ² = {chi2:.2f}, V = {v:.2f}, p {p_str})."

        elif htype == "trend":
            dv = h.get("dependent_variable", "Y")
            rho = h.get("rho", 0)
            strength = h.get("strength", "")
            direction = h.get("direction", "")
            return f"**{dv}** shows a {strength} {direction} trend over time (ρ = {rho:.2f}, p {p_str})."

        elif htype == "multi_group_difference":
            dv = h.get("dependent_variable", "Y")
            gv = h.get("group_variable", "X")
            ng = h.get("num_groups", 0)
            fstat = h.get("f_statistic", 0)
            eta2 = h.get("effect_size", 0)
            return f"**{dv}** differs significantly across {ng} groups of **{gv}** (F = {fstat:.2f}, η² = {eta2:.2f}, p {p_str})."

        return f"Hypothesis: {h.get('type', 'unknown')} relationship discovered (score: {h.get('priority_score', 0)})"


# ─── UI ─────────────────────────────────────────────────────────────

def render_hypothesis_generator_ui(df: pd.DataFrame):
    """Render the hypothesis generator UI."""
    import streamlit as st
    from modules.ui_components import section_header, insight_card

    st.markdown("## 💡 Automated Hypothesis Generator")
    st.markdown("*Discovers patterns, formulates research hypotheses, and prioritizes them by statistical support*")

    if df is None or df.empty:
        st.warning("No data available. Load data first.")
        return

    hg = HypothesisGenerator()

    col1, col2 = st.columns([2, 1])
    with col1:
        st.info(f" Dataset: {len(df)} rows × {len(df.columns)} columns  ready for hypothesis discovery")
    with col2:
        if st.button("🚀 Run Hypothesis Discovery", type="primary", use_container_width=True):
            with st.spinner("🔍 Discovering patterns and formulating hypotheses..."):
                results = hg.discover_hypotheses(df)

            if "error" in results:
                st.error(results["error"])
            else:
                st.session_state["generated_hypotheses"] = results.get("hypotheses", [])
                st.rerun()

    # Display results
    hypotheses = st.session_state.get("generated_hypotheses", [])

    if not hypotheses:
        st.info("👆 Click **'Run Hypothesis Discovery'** to automatically discover patterns and generate research hypotheses from your data.")

        st.markdown("""
        ### 🔍 How It Works
        The hypothesis generator systematically tests:

        1. **Mean Differences**  Does a categorical variable predict differences in a numeric outcome?
        2. **Correlations**  Are two numeric variables linearly related?
        3. **Associations**  Are two categorical variables related?
        4. **Trends**  Does a variable change systematically over time?
        5. **Group Differences**  Do multiple groups differ on a numeric measure?

        Each hypothesis is scored by: significance, effect size, p-value precision, and type.
        """)
        return

    # Summary
    top = hypotheses[0] if hypotheses else None
    if top:
        priority_color = "#e74c3c" if top.get("priority_label") == "Critical" else "#e67e22" if top.get("priority_label") == "High" else "#f1c40f" if top.get("priority_label") == "Medium" else "#95a5a6"
        st.markdown(f"""
        <div style="text-align:center;padding:1.2rem;border-radius:14px;
                     border:2px solid {priority_color};background:{priority_color}10;margin-bottom:1rem;">
            <div style="font-size:1.1rem;color:#64748b;">🏆 Top Hypothesis</div>
            <div style="font-size:1.3rem;font-weight:700;color:{priority_color};margin:0.3rem 0;">
                {top.get('narrative', '')}
            </div>
            <div style="display:flex;justify-content:center;gap:1.5rem;margin-top:0.5rem;">
                <span style="background:{priority_color}20;padding:0.2rem 0.6rem;border-radius:6px;font-size:0.85rem;">
                    Priority: {top.get('priority_label', 'N/A')} ({top.get('priority_score', 0)}/100)
                </span>
                <span style="background:rgba(29,78,216,0.1);padding:0.2rem 0.6rem;border-radius:6px;font-size:0.85rem;">
                    {top.get('test', 'N/A')}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        min_score = st.slider("Minimum priority score", 0, 100, 30, key="hyp_min_score")
    with col2:
        show_only_sig = st.checkbox("Show only significant results", value=False, key="hyp_only_sig")
    with col3:
        hyp_type_filter = st.selectbox("Filter by type", options=["All", "mean_difference", "correlation", "association", "trend", "multi_group_difference"], key="hyp_type_filter")

    filtered = [h for h in hypotheses if h.get("priority_score", 0) >= min_score]
    if show_only_sig:
        filtered = [h for h in filtered if h.get("significant")]
    if hyp_type_filter != "All":
        filtered = [h for h in filtered if h.get("type") == hyp_type_filter]

    st.markdown(f"**Showing {len(filtered)} of {len(hypotheses)} hypotheses**")

    for i, h in enumerate(filtered):
        priority_label = h.get("priority_label", "Medium")
        priority_score = h.get("priority_score", 0)
        priority_color = "#e74c3c" if priority_label == "Critical" else "#e67e22" if priority_label == "High" else "#f1c40f" if priority_label == "Medium" else "#95a5a6"

        with st.container():
            st.markdown(f"""
            <div style="padding:0.8rem 1rem;margin:0.4rem 0;border-radius:12px;
                        border:1px solid {priority_color}40;background:{priority_color}08;
                        border-left:4px solid {priority_color};">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-weight:600;font-size:1rem;">{h.get('id', f'H{i1}')}</span>
                    <span style="background:{priority_color};color:white;padding:0.15rem 0.6rem;
                              border-radius:999px;font-size:0.75rem;font-weight:700;">
                        {priority_label} ({priority_score})
                    </span>
                </div>
                <div style="margin-top:0.3rem;">{h.get('narrative', '')}</div>
                <div style="margin-top:0.2rem;font-size:0.8rem;color:#64748b;">
                    {h.get('test', '')} | {h.get('type', '').replace('_', ' ').title()}
                    {' | ✅ Significant' if h.get('significant') else ' | ❌ Not significant'}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Export
    st.markdown("---")
    st.subheader("📥 Export Hypotheses")
    if st.button("📋 Copy All as Markdown"):
        lines = ["# Generated Hypotheses", f"**Generated**: {datetime.now():%Y-%m-%d %H:%M:%S}", ""]
        for h in filtered:
            lines.append(f"### {h.get('id', '')}  {h.get('priority_label', '')}")
            lines.append(h.get('narrative', ''))
            lines.append(f"*Test: {h.get('test', '')} | Type: {h.get('type', '')} | Score: {h.get('priority_score', 0)}*")
            lines.append("")
        import streamlit as st
        st.code("\n".join(lines), language="markdown")

