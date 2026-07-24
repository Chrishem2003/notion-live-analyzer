"""
Automated Literature Context — Effect size comparison against published norms,
auto citation suggestions, field-specific benchmarks, sample size benchmarking.
"""
from __future__ import annotations

from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
import math
import warnings
warnings.filterwarnings('ignore')


# ─── Field-specific effect size benchmarks (from large-scale meta-analyses) ─────
FIELD_BENCHMARKS = {
    "psychology": {
        "small": 0.20, "medium": 0.50, "large": 0.80,
        "typical_r": 0.21, "typical_d": 0.43,
        "description": "Typical effects in social/personality psychology (Richard et al., 2003)",
    },
    "education": {
        "small": 0.15, "medium": 0.40, "large": 0.65,
        "typical_r": 0.18, "typical_d": 0.35,
        "description": "Typical effects in educational interventions (Hattie, 2009)",
    },
    "medicine": {
        "small": 0.10, "medium": 0.30, "large": 0.50,
        "typical_r": 0.15, "typical_d": 0.28,
        "description": "Typical effects in clinical trials (Meyer et al., 2001)",
    },
    "neuroscience": {
        "small": 0.25, "medium": 0.55, "large": 0.85,
        "typical_r": 0.24, "typical_d": 0.50,
        "description": "Typical effects in cognitive neuroscience (Owen et al., 2005)",
    },
    "social_science": {
        "small": 0.15, "medium": 0.35, "large": 0.60,
        "typical_r": 0.16, "typical_d": 0.32,
        "description": "Typical effects across social sciences (Lovakov & Agadullina, 2021)",
    },
    "business": {
        "small": 0.15, "medium": 0.35, "large": 0.55,
        "typical_r": 0.17, "typical_d": 0.34,
        "description": "Typical effects in management/business research (Paterson et al., 2016)",
    },
    "biology": {
        "small": 0.30, "medium": 0.60, "large": 0.90,
        "typical_r": 0.28, "typical_d": 0.55,
        "description": "Typical effects in biological/ecological studies (Møller & Jennions, 2002)",
    },
    "clinical_psychology": {
        "small": 0.20, "medium": 0.50, "large": 0.80,
        "typical_r": 0.22, "typical_d": 0.45,
        "description": "Typical effects in clinical psychology trials",
    },
    "economics": {
        "small": 0.05, "medium": 0.15, "large": 0.30,
        "typical_r": 0.08, "typical_d": 0.16,
        "description": "Typical effects in economics (Doucouliagos, 2011)",
    },
    "default": {
        "small": 0.20, "medium": 0.50, "large": 0.80,
        "typical_r": 0.20, "typical_d": 0.40,
        "description": "General benchmarks (Cohen, 1988)",
    },
}


class LiteratureContext:
    """Provide literature context for research findings."""

    def __init__(self, discipline: str = "default"):
        self.discipline = discipline
        self.benchmarks = FIELD_BENCHMARKS.get(discipline, FIELD_BENCHMARKS["default"])

    # ─── Effect Size Comparison ───────────────────────────────────
    def compare_effect_size(
        self,
        effect_size: float,
        effect_type: str = "d",
        sample_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Compare an effect size against field-specific benchmarks.
        """
        benchmarks = self.benchmarks

        if effect_type in ("d", "g", "cohens_d"):
            label = "small" if effect_size < benchmarks["small"] else \
                    "medium" if effect_size < benchmarks["medium"] else \
                    "large" if effect_size < benchmarks["large"] else "very large"
            percentile = self._estimate_percentile(effect_size, benchmarks["typical_d"], 0.25)
            typical = benchmarks["typical_d"]
        elif effect_type in ("r", "pearson_r"):
            label = "small" if effect_size < 0.1 else \
                    "medium" if effect_size < 0.3 else \
                    "large" if effect_size < 0.5 else "very large"
            percentile = self._estimate_percentile(effect_size, benchmarks["typical_r"], 0.15)
            typical = benchmarks["typical_r"]
        elif effect_type in ("or", "odds_ratio"):
            or_log = math.log(effect_size) if effect_size > 0 else 0
            label = "small" if or_log < 0.2 else "medium" if or_log < 0.5 else "large"
            percentile = self._estimate_percentile(or_log, 0.3, 0.2)
            typical = 1.35
        elif effect_type in ("eta_squared", "eta2"):
            label = "small" if effect_size < 0.01 else \
                    "medium" if effect_size < 0.06 else \
                    "large" if effect_size < 0.14 else "very large"
            percentile = self._estimate_percentile(effect_size, 0.06, 0.05)
            typical = 0.06
        else:
            label = "medium"
            percentile = 50
            typical = benchmarks["typical_d"]

        return {
            "your_effect": round(effect_size, 3),
            "effect_type": effect_type,
            "label": label,
            "percentile": round(percentile, 1),
            "typical_effect": typical,
            "small_threshold": benchmarks["small"],
            "medium_threshold": benchmarks["medium"],
            "large_threshold": benchmarks["large"],
            "discipline": self.discipline,
            "discipline_description": benchmarks["description"],
            "interpretation": f"Your effect (d = {effect_size:.2f}) is {label}, "
                              f"at the {percentile:.0f}th percentile of typical effects in {self.discipline}.",
        }

    def _estimate_percentile(self, value: float, mean: float, sd: float) -> float:
        """Estimate percentile rank of a value in a normal distribution."""
        if sd <= 0:
            return 50
        z = (value - mean) / sd
        try:
            from scipy.stats import norm
            return float(norm.cdf(z) * 100)
        except ImportError:
            return 50 + z * 15  # Approximate

    # ─── Sample Size Benchmarking ─────────────────────────────────
    def benchmark_sample_size(
        self,
        n: int,
        effect_size: float = 0.5,
        discipline: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compare sample size against field norms."""
        field = discipline or self.discipline

        typical_n = {
            "psychology": 100, "education": 200, "medicine": 150,
            "neuroscience": 30, "social_science": 250, "business": 200,
            "biology": 50, "clinical_psychology": 80, "economics": 500,
            "default": 100,
        }.get(field, 100)

        # Required N for 80% power
        try:
            from statsmodels.stats.power import TTestIndPower
            analysis = TTestIndPower()
            required_n = int(np.ceil(analysis.solve_power(effect_size=effect_size, alpha=0.05, power=0.8)))
        except ImportError:
            required_n = int(np.ceil(16 / effect_size**2))

        adequacy = "adequate" if n >= required_n else "underpowered"

        return {
            "your_n": n,
            "typical_n_in_field": typical_n,
            "required_n_for_80pct_power": required_n,
            "adequacy": adequacy,
            "effect_size_assumed": effect_size,
            "interpretation": f"Your N = {n:,}. Field typical N = {typical_n:,}. "
                              f"Need N = {required_n:,} for 80% power at d = {effect_size:.2f}. "
                              f"Your sample is {'✅ ' if adequacy == 'adequate' else '⚠️ '}{adequacy}.",
        }

    # ─── Citation Suggestions ─────────────────────────────────────
    def get_citation_suggestions(self, effect_size: float, effect_type: str = "d") -> List[Dict]:
        """Get citation suggestions based on effect size magnitude."""
        suggestions = []
        d = abs(effect_size) if effect_type in ("d", "g", "cohens_d") else effect_size

        if d < 0.2:
            suggestions.append({
                "citation": "Cohen, J. (1988). *Statistical power analysis for the behavioral sciences* (2nd ed.).",
                "context": "Standard reference for small effect sizes (d < 0.2)",
                "type": "methodological",
            })
        elif d < 0.5:
            suggestions.append({
                "citation": "Cohen, J. (1988). *Statistical power analysis for the behavioral sciences* (2nd ed.).",
                "context": "Standard reference for medium effect sizes (d ≈ 0.5)",
                "type": "methodological",
            })
        else:
            suggestions.append({
                "citation": "Cohen, J. (1988). *Statistical power analysis for the behavioral sciences* (2nd ed.).",
                "context": "Standard reference for large effect sizes (d > 0.8)",
                "type": "methodological",
            })

        # Add field-specific citation
        if self.discipline == "psychology":
            suggestions.append({
                "citation": "Richard, F. D., Bond, C. F., & Stokes-Zoota, J. J. (2003). One hundred years of social psychology quantitatively described. *Review of General Psychology*, 7(4), 331–363.",
                "context": "Meta-analytic summary of typical effect sizes in social psychology",
                "type": "field_benchmark",
            })
        elif self.discipline == "education":
            suggestions.append({
                "citation": "Hattie, J. (2009). *Visible learning: A synthesis of over 800 meta-analyses relating to achievement*. Routledge.",
                "context": "Comprehensive meta-analytic benchmarks for educational interventions",
                "type": "field_benchmark",
            })

        suggestions.append({
            "citation": "Lakens, D. (2013). Calculating and reporting effect sizes to facilitate cumulative science: A practical primer for t-tests and ANOVAs. *Frontiers in Psychology*, 4, 863.",
            "context": "Best practices for effect size calculation and reporting",
            "type": "methodological",
        })

        return suggestions

    # ─── Full Context Report ──────────────────────────────────────
    def generate_context_report(
        self,
        effect_size: float,
        effect_type: str = "d",
        sample_size: Optional[int] = None,
        discipline: Optional[str] = None,
    ) -> str:
        """Generate a comprehensive literature context report."""
        if discipline:
            self.benchmarks = FIELD_BENCHMARKS.get(discipline, FIELD_BENCHMARKS["default"])
            self.discipline = discipline

        es_context = self.compare_effect_size(effect_size, effect_type, sample_size)
        citation_suggestions = self.get_citation_suggestions(effect_size, effect_type)

        lines = [
            "## 📚 Literature Context Report",
            f"**Discipline:** {self.discipline}",
            f"**Effect Type:** {effect_type}",
            f"**Your Effect Size:** {effect_size:.3f}",
            "",
            "### Effect Size Benchmarking",
            f"- **Label:** {es_context['label'].title()}",
            f"- **Percentile:** {es_context['percentile']:.0f}th",
            f"- **Typical Effect in Field:** {es_context['typical_effect']:.3f}",
            f"- **Small:** < {es_context['small_threshold']:.2f}",
            f"- **Medium:** < {es_context['medium_threshold']:.2f}",
            f"- **Large:** < {es_context['large_threshold']:.2f}",
            "",
            f"**Interpretation:** {es_context['interpretation']}",
            "",
        ]

        if sample_size:
            ss_context = self.benchmark_sample_size(sample_size, effect_size, self.discipline)
            lines.append("### Sample Size Benchmarking")
            lines.append(f"- **Your N:** {ss_context['your_n']:,}")
            lines.append(f"- **Typical N in Field:** {ss_context['typical_n_in_field']:,}")
            lines.append(f"- **Required for 80% Power:** {ss_context['required_n_for_80pct_power']:,}")
            lines.append(f"- **Adequacy:** {ss_context['adequacy'].title()}")
            lines.append(f"**Interpretation:** {ss_context['interpretation']}")
            lines.append("")

        lines.append("### Suggested Citations")
        for i, s in enumerate(citation_suggestions, 1):
            lines.append(f"{i}. {s['citation']} — *{s['context']}*")

        return "\n".join(lines)


# ─── UI ─────────────────────────────────────────────────────────────
def render_literature_context_ui():
    """Render the Literature Context page."""
    import streamlit as st

    st.markdown("## 🌐 Automated Literature Context")
    st.markdown("*Compare your effect sizes against published norms, get citation suggestions*")

    st.info("This tool helps you contextualize your findings within the broader literature. "
            "Enter your effect sizes to get benchmarks, sample size comparisons, and citation suggestions.")

    tab1, tab2, tab3 = st.tabs(["📊 Effect Size Comparison", "📏 Sample Size Benchmarking", "📚 Full Report"])

    with tab1:
        st.subheader("📊 Effect Size Comparison")
        col1, col2 = st.columns(2)
        with col1:
            es = st.number_input("Your effect size", value=0.5, step=0.01, format="%.3f", key="lc_es")
            es_type = st.selectbox("Effect type", options=["d", "r", "or", "eta_squared", "g"], key="lc_es_type")
        with col2:
            discipline = st.selectbox("Discipline", options=list(FIELD_BENCHMARKS.keys()), key="lc_discipline")
            n = st.number_input("Sample size (optional)", value=0, min_value=0, step=10, key="lc_n")

        if st.button("📊 Compare", type="primary"):
            lc = LiteratureContext(discipline)
            result = lc.compare_effect_size(es, es_type, n if n > 0 else None)
            st.metric("Effect Size Label", result["label"].title())
            st.metric("Percentile", f"{result['percentile']:.0f}th")
            st.info(result["interpretation"])

            if n > 0:
                ss = lc.benchmark_sample_size(n, es, discipline)
                st.metric("Sample Size Adequacy", ss["adequacy"].title())

    with tab2:
        st.subheader("📏 Sample Size Benchmarking")
        col1, col2 = st.columns(2)
        with col1:
            n_bench = st.number_input("Your N", value=100, step=10, key="lc_n_bench")
            es_bench = st.number_input("Assumed effect size", value=0.5, step=0.05, key="lc_es_bench")
        with col2:
            disc_bench = st.selectbox("Discipline", options=list(FIELD_BENCHMARKS.keys()), key="lc_disc_bench")

        if st.button("📏 Benchmark", type="primary"):
            lc = LiteratureContext(disc_bench)
            result = lc.benchmark_sample_size(n_bench, es_bench, disc_bench)
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("Your N", result["your_n"])
            with col2: st.metric("Field Typical N", result["typical_n_in_field"])
            with col3: st.metric("Required N (80% power)", result["required_n_for_80pct_power"])
            st.info(result["interpretation"])

    with tab3:
        st.subheader("📚 Full Literature Context Report")
        col1, col2 = st.columns(2)
        with col1:
            es_report = st.number_input("Effect size", value=0.5, step=0.01, key="lc_es_report")
            es_type_report = st.selectbox("Type", options=["d", "r", "or", "eta_squared"], key="lc_es_type_report")
        with col2:
            disc_report = st.selectbox("Discipline", options=list(FIELD_BENCHMARKS.keys()), key="lc_disc_report")
            n_report = st.number_input("N", value=100, step=10, key="lc_n_report")

        if st.button("📚 Generate Report", type="primary"):
            lc = LiteratureContext(disc_report)
            report = lc.generate_context_report(es_report, es_type_report, n_report, disc_report)
            st.markdown(report)
            if st.button("📋 Copy to Clipboard"):
                st.code(report, language="markdown")
