"""
Research Methodology Advisor  CHRISHEM-powered expert system that recommends
study designs, statistical tests, sample sizes, and research methodologies
based on researcher's input questions and data characteristics.
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
import streamlit as st
import json

# ─── Knowledge Base ─────────────────────────────────────────────────

STUDY_DESIGNS = {
    "Experimental": {
        "description": "Randomly assign participants to conditions to establish causality",
        "best_for": "Testing causal hypotheses with controlled conditions",
        "statistical_tests": ["Independent T-Test", "One-Way ANOVA", "Two-Way ANOVA", "ANCOVA", "MANOVA"],
        "sample_size_formula": "t-test power analysis",
        "pros": ["Strong internal validity", "Can establish causality"],
        "cons": ["May lack external validity", "Ethical constraints", "Resource intensive"],
        "when_to_use": "When you can randomly assign participants to groups and control extraneous variables",
    },
    "Quasi-Experimental": {
        "description": "Compare groups without random assignment",
        "best_for": "Field studies where randomization is impractical",
        "statistical_tests": ["Independent T-Test", "Mann-Whitney U", "ANCOVA", "Propensity Score Matching"],
        "sample_size_formula": "t-test power analysis",
        "pros": ["More feasible than true experiments", "Higher external validity"],
        "cons": ["Threats to internal validity", "Selection bias"],
        "when_to_use": "When random assignment is not possible but you need to compare groups",
    },
    "Correlational": {
        "description": "Examine relationships between variables without manipulation",
        "best_for": "Exploring associations between naturally occurring variables",
        "statistical_tests": ["Pearson Correlation", "Spearman Correlation", "Multiple Regression", "Factor Analysis"],
        "sample_size_formula": "N ≥ 50 + 8 × predictors (for regression)",
        "pros": ["Can study many variables", "High external validity"],
        "cons": ["Cannot establish causality", "Directionality problem"],
        "when_to_use": "When you cannot or should not manipulate variables",
    },
    "Longitudinal": {
        "description": "Follow the same participants over time",
        "best_for": "Studying developmental changes, trajectories, and long-term effects",
        "statistical_tests": ["Repeated Measures ANOVA", "Mixed Effects Models", "Growth Curve Modeling", "Paired T-Test"],
        "sample_size_formula": "N = power analysis for repeated measures",
        "pros": ["Can study change over time", "Can establish temporal precedence"],
        "cons": ["Attrition", "Time-consuming", "Expensive", "Practice effects"],
        "when_to_use": "When studying developmental processes or long-term outcomes",
    },
    "Cross-Sectional": {
        "description": "Measure variables at a single point in time",
        "best_for": "Prevalence studies, surveys, and quick assessments",
        "statistical_tests": ["Descriptive Statistics", "Chi-Square", "T-Test", "ANOVA", "Correlation"],
        "sample_size_formula": "N = (Z² × p × (1-p)) / e² (for surveys)",
        "pros": ["Quick and efficient", "Good for prevalence", "Can study multiple outcomes"],
        "cons": ["Cannot study change", "Temporal ambiguity"],
        "when_to_use": "When you need a snapshot of a population at one time point",
    },
    "Case-Control": {
        "description": "Compare individuals with (cases) and without (controls) an outcome",
        "best_for": "Studying rare outcomes or diseases",
        "statistical_tests": ["Chi-Square", "Logistic Regression", "Mantel-Haenszel Test"],
        "sample_size_formula": "N = power analysis for logistic regression",
        "pros": ["Efficient for rare outcomes", "Less expensive than cohort"],
        "cons": ["Recall bias", "Selection of controls is critical"],
        "when_to_use": "When the outcome is rare and you need to identify risk factors",
    },
    "Cohort": {
        "description": "Follow groups based on exposure and compare outcomes",
        "best_for": "Studying incidence and natural history of conditions",
        "statistical_tests": ["Chi-Square", "Survival Analysis", "Cox Regression", "Log-Rank Test"],
        "sample_size_formula": "N = power analysis for survival analysis",
        "pros": ["Can establish temporality", "Can study multiple outcomes"],
        "cons": ["Expensive", "Time-consuming", "Loss to follow-up"],
        "when_to_use": "When studying incidence, prognosis, or multiple outcomes of an exposure",
    },
    "Survey Research": {
        "description": "Collect data using questionnaires or interviews",
        "best_for": "Measuring attitudes, opinions, beliefs, and behaviors",
        "statistical_tests": ["Descriptive Statistics", "Chi-Square", "T-Test", "ANOVA", "Factor Analysis", "Reliability Analysis"],
        "sample_size_formula": "N = (Z² × p × (1-p)) / e²",
        "pros": ["Can reach large samples", "Cost-effective", "Versatile"],
        "cons": ["Response bias", "Low response rates", "Limited depth"],
        "when_to_use": "When measuring subjective experiences, attitudes, or behaviors at scale",
    },
    "Qualitative": {
        "description": "Explore phenomena through interviews, observations, or text analysis",
        "best_for": "Understanding meanings, experiences, and social processes",
        "statistical_tests": ["Thematic Analysis", "Content Analysis", "Grounded Theory", "Discourse Analysis"],
        "sample_size_formula": "Saturation (typically 12-30 participants)",
        "pros": ["Rich, detailed data", "Flexible", "Participant perspectives"],
        "cons": ["Not generalizable", "Time-intensive analysis", "Researcher bias"],
        "when_to_use": "When exploring new phenomena or understanding lived experiences",
    },
}

STATISTICAL_TEST_GUIDE = {
    "Independent T-Test": {
        "purpose": "Compare means between two independent groups",
        "assumptions": ["Normality", "Homogeneity of variance", "Independence"],
        "alternative_if_violated": "Mann-Whitney U Test",
        "effect_size": "Cohen's d",
        "example_hypothesis": "H₁: There is a significant difference in test scores between Group A and Group B",
    },
    "Paired T-Test": {
        "purpose": "Compare means from the same group at two time points",
        "assumptions": ["Normality of differences", "Independence of pairs"],
        "alternative_if_violated": "Wilcoxon Signed-Rank Test",
        "effect_size": "Cohen's dz",
        "example_hypothesis": "H₁: There is a significant change in scores from pre-test to post-test",
    },
    "One-Way ANOVA": {
        "purpose": "Compare means across three or more groups",
        "assumptions": ["Normality", "Homogeneity of variance", "Independence"],
        "alternative_if_violated": "Kruskal-Wallis H Test",
        "effect_size": "Eta-squared (η²)",
        "post_hoc": "Tukey HSD, Bonferroni",
        "example_hypothesis": "H₁: There is a significant difference in scores across the four treatment groups",
    },
    "Two-Way ANOVA": {
        "purpose": "Examine effects of two factors and their interaction",
        "assumptions": ["Normality", "Homogeneity of variance", "Independence"],
        "alternative_if_violated": "Aligned Rank Transform",
        "effect_size": "Partial eta-squared (ηp²)",
        "example_hypothesis": "H₁: There is a significant interaction between treatment and gender",
    },
    "Repeated Measures ANOVA": {
        "purpose": "Compare means across three or more time points",
        "assumptions": ["Sphericity", "Normality", "Independence"],
        "alternative_if_violated": "Friedman Test",
        "effect_size": "Partial eta-squared",
        "example_hypothesis": "H₁: Scores change significantly over the four time points",
    },
    "Pearson Correlation": {
        "purpose": "Measure linear relationship between two continuous variables",
        "assumptions": ["Linearity", "Normality", "Homoscedasticity"],
        "alternative_if_violated": "Spearman Rank Correlation",
        "effect_size": "r (coefficient)",
        "example_hypothesis": "H₁: There is a significant correlation between age and income",
    },
    "Spearman Correlation": {
        "purpose": "Measure monotonic relationship between two variables",
        "assumptions": ["Monotonic relationship"],
        "alternative_if_violated": "Kendall's Tau",
        "effect_size": "Rho (ρ)",
        "example_hypothesis": "H₁: There is a significant monotonic relationship between rank and score",
    },
    "Chi-Square Test": {
        "purpose": "Test association between two categorical variables",
        "assumptions": ["Expected frequency ≥ 5 per cell", "Independence"],
        "alternative_if_violated": "Fisher's Exact Test",
        "effect_size": "Cramer's V, Phi coefficient",
        "example_hypothesis": "H₁: There is a significant association between gender and voting preference",
    },
    "Linear Regression": {
        "purpose": "Predict a continuous outcome from one or more predictors",
        "assumptions": ["Linearity", "Independence", "Homoscedasticity", "Normality of residuals"],
        "alternative_if_violated": "Robust Regression, Transformations",
        "effect_size": "R², Adjusted R²",
        "example_hypothesis": "H₁: The predictors significantly predict the outcome variable",
    },
    "Logistic Regression": {
        "purpose": "Predict a binary outcome from predictors",
        "assumptions": ["Linearity of logit", "Independence", "No multicollinearity"],
        "alternative_if_violated": "Probit Regression",
        "effect_size": "Odds Ratio, Pseudo R²",
        "example_hypothesis": "H₁: The predictors significantly predict the likelihood of the outcome",
    },
    "Mann-Whitney U": {
        "purpose": "Compare distributions between two independent groups (non-parametric)",
        "assumptions": ["Similar shape distributions", "Independence"],
        "effect_size": "Rank-biserial correlation",
        "example_hypothesis": "H₁: The distributions of the two groups are significantly different",
    },
    "Wilcoxon Signed-Rank": {
        "purpose": "Compare two related samples (non-parametric paired test)",
        "assumptions": ["Symmetric distribution of differences"],
        "effect_size": "Rank-biserial correlation",
        "example_hypothesis": "H₁: There is a significant difference between paired observations",
    },
    "Kruskal-Wallis H": {
        "purpose": "Compare three or more groups (non-parametric ANOVA alternative)",
        "assumptions": ["Independence", "Similar shape distributions"],
        "effect_size": "Epsilon-squared",
        "post_hoc": "Dunn's test",
        "example_hypothesis": "H₁: At least one group differs significantly from the others",
    },
    "Factor Analysis": {
        "purpose": "Identify underlying latent factors from observed variables",
        "assumptions": ["Sample size N ≥ 300", "Moderate correlations", "KMO ≥ 0.6"],
        "alternative_if_violated": "PCA (if assumptions violated)",
        "effect_size": "Factor loadings, Variance explained",
        "example_hypothesis": "H₁: The observed variables are explained by underlying latent factors",
    },
}


# ─── Recommender Functions ─────────────────────────────────────────

def recommend_study_design(
    research_question: str,
    has_random_assignment: Optional[bool] = None,
    has_control_group: Optional[bool] = None,
    is_longitudinal: Optional[bool] = None,
    data_type: str = "quantitative",
) -> List[Dict[str, Any]]:
    """
    Recommend study designs based on research parameters.
    """
    scores = {}
    rq_lower = research_question.lower()

    for name, design in STUDY_DESIGNS.items():
        score = 0

        # Keyword matching
        if any(kw in rq_lower for kw in ["difference", "effect", "impact", "cause", "influence"]):
            if "experimental" in name.lower():
                score += 3
            if "quasi" in name.lower():
                score += 2
        if any(kw in rq_lower for kw in ["relationship", "association", "correlation", "predict"]):
            if "correlational" in name.lower() or "regression" in design["description"].lower():
                score += 3
        if any(kw in rq_lower for kw in ["change", "over time", "develop", "growth", "trend"]):
            if "longitudinal" in name.lower():
                score += 3
        if any(kw in rq_lower for kw in ["prevalence", "frequency", "rate", "how many", "survey"]):
            if "cross-sectional" in name.lower() or "survey" in name.lower():
                score += 3
        if any(kw in rq_lower for kw in ["interview", "experience", "perception", "meaning", "qualitative"]):
            if "qualitative" in name.lower():
                score += 3

        # Parameter matching
        if has_random_assignment is True and "experimental" in name.lower():
            score += 2
        if has_random_assignment is False and "quasi" in name.lower():
            score += 2
        if has_control_group and "control" in design["description"].lower():
            score += 1
        if is_longitudinal and "longitudinal" in name.lower():
            score += 2
        if data_type == "qualitative" and "qualitative" in name.lower():
            score += 3

        scores[name] = score

    # Sort by score
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top = [name for name, score in ranked[:3] if score > 0]

    if not top:
        top = ["Cross-Sectional", "Correlational", "Survey Research"]

    recommendations = []
    for name in top:
        design = STUDY_DESIGNS.get(name, {})
        recommendations.append({
            "design": name,
            "description": design.get("description", ""),
            "best_for": design.get("best_for", ""),
            "statistical_tests": design.get("statistical_tests", []),
            "pros": design.get("pros", []),
            "cons": design.get("cons", []),
            "when_to_use": design.get("when_to_use", ""),
            "score": scores.get(name, 0),
        })

    return recommendations


def recommend_statistical_test(
    iv_type: str = "categorical",
    dv_type: str = "numeric",
    n_groups: int = 2,
    is_paired: bool = False,
    assumptions_met: bool = True,
    n_dvs: int = 1,
) -> List[Dict[str, Any]]:
    """
    Recommend appropriate statistical test based on variable types and design.
    """
    recommendations = []

    # One sample
    if n_groups == 1 and dv_type == "numeric":
        recommendations.append({
            "test": "One-Sample T-Test",
            "purpose": "Compare sample mean to a known population mean",
            "alternative": "Wilcoxon Signed-Rank Test (if normality violated)",
            "confidence": 90,
        })
        recommendations.append({
            "test": "One-Sample Wilcoxon Signed-Rank Test",
            "purpose": "Non-parametric alternative when normality is violated",
            "alternative": "",
            "confidence": 70,
        })

    # Two groups
    elif n_groups == 2:
        if iv_type == "categorical" and dv_type == "numeric":
            if is_paired:
                recommendations.append({
                    "test": "Paired Samples T-Test",
                    "purpose": "Compare two related measurements (before/after, matched pairs)",
                    "alternative": "Wilcoxon Signed-Rank Test",
                    "confidence": 95 if assumptions_met else 70,
                })
                recommendations.append({
                    "test": "Wilcoxon Signed-Rank Test",
                    "purpose": "Non-parametric alternative for paired data",
                    "alternative": "",
                    "confidence": 85 if not assumptions_met else 60,
                })
            else:
                recommendations.append({
                    "test": "Independent Samples T-Test",
                    "purpose": "Compare means between two independent groups",
                    "alternative": "Mann-Whitney U Test",
                    "confidence": 95 if assumptions_met else 70,
                })
                recommendations.append({
                    "test": "Mann-Whitney U Test",
                    "purpose": "Non-parametric alternative for two independent groups",
                    "alternative": "",
                    "confidence": 85 if not assumptions_met else 60,
                })

        elif iv_type == "categorical" and dv_type == "categorical":
            recommendations.append({
                "test": "Chi-Square Test of Independence",
                "purpose": "Test association between two categorical variables",
                "alternative": "Fisher's Exact Test (if expected frequencies < 5)",
                "confidence": 90,
            })

    # Three+ groups
    elif n_groups >= 3:
        if dv_type == "numeric":
            if is_paired:
                recommendations.append({
                    "test": "Repeated Measures ANOVA",
                    "purpose": "Compare means across three or more related measurements",
                    "alternative": "Friedman Test",
                    "confidence": 90 if assumptions_met else 65,
                })
                recommendations.append({
                    "test": "Friedman Test",
                    "purpose": "Non-parametric alternative for repeated measures",
                    "alternative": "",
                    "confidence": 80 if not assumptions_met else 55,
                })
            else:
                recommendations.append({
                    "test": "One-Way ANOVA",
                    "purpose": f"Compare means across {n_groups} independent groups",
                    "alternative": "Kruskal-Wallis H Test",
                    "confidence": 95 if assumptions_met else 70,
                })
                recommendations.append({
                    "test": "Kruskal-Wallis H Test",
                    "purpose": "Non-parametric alternative for multiple groups",
                    "alternative": "",
                    "confidence": 85 if not assumptions_met else 60,
                })
                recommendations.append({
                    "test": "ANCOVA",
                    "purpose": "Compare groups while controlling for covariates",
                    "alternative": "",
                    "confidence": 75,
                })

    # Correlation
    if dv_type == "numeric" and n_groups == 0:
        recommendations.append({
            "test": "Pearson Correlation",
            "purpose": "Measure linear relationship between two continuous variables",
            "alternative": "Spearman Rank Correlation",
            "confidence": 95 if assumptions_met else 70,
        })
        recommendations.append({
            "test": "Spearman Rank Correlation",
            "purpose": "Non-parametric correlation for ranked/ordinal data",
            "alternative": "",
            "confidence": 85 if not assumptions_met else 60,
        })

    # Multiple predictors
    if n_dvs == 1 and n_groups > 2:
        recommendations.append({
            "test": "Multiple Linear Regression",
            "purpose": "Predict continuous outcome from multiple predictors",
            "alternative": "Robust Regression",
            "confidence": 85 if assumptions_met else 60,
        })

    if n_dvs > 1:
        recommendations.append({
            "test": "MANOVA",
            "purpose": "Compare groups across multiple dependent variables",
            "alternative": "Separate ANOVAs with Bonferroni correction",
            "confidence": 75,
        })
        recommendations.append({
            "test": "Factor Analysis",
            "purpose": "Identify latent factors from multiple observed variables",
            "alternative": "PCA",
            "confidence": 70,
        })

    # Sort by confidence
    recommendations.sort(key=lambda x: x["confidence"], reverse=True)
    return recommendations[:5]


def estimate_sample_size(
    design_type: str = "t-test",
    effect_size: float = 0.5,
    alpha: float = 0.05,
    power: float = 0.80,
    n_groups: int = 2,
) -> Dict[str, Any]:
    """
    Estimate required sample size for various study designs.
    Uses simplified formulas (SPSS SamplePower-like).
    """
    from scipy import stats

    results = {"design": design_type, "effect_size": effect_size, "alpha": alpha, "power": power}

    if design_type == "t-test" or design_type == "Independent T-Test":
        # Using power analysis formula
        from statsmodels.stats.power import TTestIndPower
        analysis = TTestIndPower()
        n = analysis.solve_power(effect_size=effect_size, alpha=alpha, power=power)
        results["n_per_group"] = int(np.ceil(n))
        results["total_n"] = int(np.ceil(n * n_groups))
        results["formula"] = "Two-sample t-test power analysis (Cohen's d)"
        results["interpretation"] = (
            f"Need **{results['n_per_group']}** participants per group "
            f"({results['total_n']} total) to detect d={effect_size} with {power*100:.0f}% power"
        )

    elif design_type == "paired" or design_type == "Paired T-Test":
        from statsmodels.stats.power import TTestPower
        analysis = TTestPower()
        n = analysis.solve_power(effect_size=effect_size, alpha=alpha, power=power, alternative='two-sided')
        results["total_n"] = int(np.ceil(n))
        results["n_per_group"] = int(np.ceil(n))
        results["formula"] = "Paired t-test power analysis"
        results["interpretation"] = (
            f"Need **{results['total_n']}** paired observations to detect d={effect_size} "
            f"with {power*100:.0f}% power"
        )

    elif design_type == "anova" or design_type == "One-Way ANOVA":
        from statsmodels.stats.power import FTestAnovaPower
        analysis = FTestAnovaPower()
        n = analysis.solve_power(effect_size=effect_size, alpha=alpha, power=power, k_groups=n_groups)
        results["n_per_group"] = int(np.ceil(n))
        results["total_n"] = int(np.ceil(n * n_groups))
        results["formula"] = "One-way ANOVA power analysis (Cohen's f)"
        results["interpretation"] = (
            f"Need **{results['n_per_group']}** participants per group "
            f"({results['total_n']} total, {n_groups} groups) to detect f={effect_size} with {power*100:.0f}% power"
        )

    elif design_type == "correlation" or design_type == "Pearson Correlation":
        from statsmodels.stats.power import TTestPower
        # Fisher's z transformation
        z = np.arctanh(effect_size)
        se = 1 / np.sqrt(3)
        n = ((stats.norm.ppf(1 - alpha/2) + stats.norm.ppf(power)) / (z / se)) ** 2 + 3
        results["total_n"] = int(np.ceil(n))
        results["n_per_group"] = int(np.ceil(n))
        results["formula"] = "Correlation power analysis (Fisher's z)"
        results["interpretation"] = (
            f"Need **{results['total_n']}** observations to detect r={effect_size} with {power*100:.0f}% power"
        )

    elif design_type == "chi-square" or design_type == "Chi-Square":
        from statsmodels.stats.power import GofChisquarePower
        analysis = GofChisquarePower()
        n = analysis.solve_power(effect_size=effect_size, alpha=alpha, power=power, n_bins=n_groups)
        results["total_n"] = int(np.ceil(n))
        results["n_per_group"] = int(np.ceil(n))
        results["formula"] = "Chi-square power analysis (Cohen's w)"
        results["interpretation"] = (
            f"Need **{results['total_n']}** observations for chi-square test with {power*100:.0f}% power"
        )

    elif design_type == "survey":
        # Survey sample size formula
        z = stats.norm.ppf(1 - alpha/2)
        p = 0.5  # Maximum variability
        e = effect_size  # Using effect size as margin of error
        n = (z**2 * p * (1-p)) / (e**2)
        # Finite population correction
        N = 10000  # Assumed population
        n_adj = n / (1 + (n - 1) / N)
        results["total_n"] = int(np.ceil(n_adj))
        results["n_per_group"] = int(np.ceil(n_adj))
        results["formula"] = "Survey sample size (Cochran's formula)"
        results["interpretation"] = (
            f"Need **{results['total_n']}** survey responses (±{e*100:.1f}% margin of error, "
            f"{power*100:.0f}% confidence level)"
        )

    return results


def generate_methodology_section(
    design: str,
    tests: List[str],
    sample_size: Dict[str, Any],
    variables: Dict[str, List[str]],
) -> str:
    """
    Generate an APA-style methodology section based on parameters.
    """
    lines = ["## Method", ""]
    lines.append("### Research Design")
    design_info = STUDY_DESIGNS.get(design, {})
    lines.append(design_info.get("description", f"A {design} design was used."))
    lines.append("")

    # Participants
    lines.append("### Participants")
    total_n = sample_size.get("total_n", "N/A") if isinstance(sample_size, dict) else "N/A"
    lines.append(f"A total of {total_n} participants were recruited for this study. "
                 f"Power analysis indicated that this sample size was sufficient to detect "
                 f"the expected effects (α = {sample_size.get('alpha', 0.05)}, "
                 f"power = {sample_size.get('power', 0.80)}).")
    lines.append("")

    # Variables
    lines.append("### Variables")
    ivs = variables.get("independent", [])
    dvs = variables.get("dependent", [])
    if ivs:
        lines.append(f"**Independent Variable(s):** {', '.join(ivs)}")
    if dvs:
        lines.append(f"**Dependent Variable(s):** {', '.join(dvs)}")
    lines.append("")

    # Statistical Analysis
    lines.append("### Statistical Analysis")
    if tests:
        lines.append(f"Data were analyzed using {', '.join(tests)}. ")
        test_details = []
        for test in tests:
            guide = STATISTICAL_TEST_GUIDE.get(test, {})
            if guide:
                test_details.append(f"{test} was used to {guide.get('purpose', '').lower()}")
        if test_details:
            lines.extend([f"- {d}" for d in test_details])
    lines.append("")

    lines.append("All analyses were conducted using the Advanced Research Data Analyzer "
                 "(version 2.0). Statistical significance was set at α = .05 (two-tailed). "
                 "Effect sizes were interpreted using established guidelines (Cohen, 1988).")
    lines.append("")

    return "\n".join(lines)


# ─── UI ─────────────────────────────────────────────────────────────

def render_methodology_advisor_ui():
    """Render the methodology advisor UI."""
    st.markdown("## 📋 Research Methodology Advisor")
    st.markdown("*Expert system for study design, test selection, and sample size estimation*")

    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 Study Design", "🔬 Test Selector", "📏 Sample Size", "📝 Method Generator"
    ])

    with tab1:
        st.subheader("🎯 Recommend Study Design")
        st.caption("Describe your research to get design recommendations")

        research_question = st.text_area(
            "What is your research question?",
            placeholder="e.g., Does a new teaching method improve student performance compared to traditional methods?",
            height=100,
            key="mq_question"
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            has_random = st.selectbox("Random assignment possible?", options=["", "Yes", "No", "Unsure"], key="mq_random")
        with col2:
            has_control = st.selectbox("Control group?", options=["", "Yes", "No"], key="mq_control")
        with col3:
            data_type = st.selectbox("Data type", options=["quantitative", "qualitative", "mixed"], key="mq_data")

        if st.button("🔍 Get Recommendations", type="primary") and research_question:
            recommendations = recommend_study_design(
                research_question,
                has_random_assignment=(has_random == "Yes") if has_random else None,
                has_control_group=(has_control == "Yes") if has_control else None,
                data_type=data_type,
            )

            for i, rec in enumerate(recommendations):
                with st.container():
                    st.markdown(f"### {i+1}. **{rec['design']}**")
                    st.markdown(f"*{rec['description']}*")
                    st.markdown(f"**Best for:** {rec['best_for']}")
                    st.markdown(f"**When to use:** {rec['when_to_use']}")
                    st.markdown(f"**Recommended tests:** {', '.join(rec['statistical_tests'][:4])}")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Pros:**")
                        for p in rec['pros']:
                            st.markdown(f"- ✅ {p}")
                    with col2:
                        st.markdown("**Cons:**")
                        for c in rec['cons']:
                            st.markdown(f"- ⚠️ {c}")
                    st.markdown("---")

    with tab2:
        st.subheader("🔬 Statistical Test Selector")
        st.caption("Describe your variables to find the right statistical test")

        col1, col2 = st.columns(2)
        with col1:
            iv_type = st.selectbox("Independent Variable type", options=["categorical", "numeric", "none"], key="ts_iv")
            n_groups = st.number_input("Number of groups/levels", min_value=1, max_value=10, value=2, key="ts_groups")
        with col2:
            dv_type = st.selectbox("Dependent Variable type", options=["numeric", "categorical", "binary"], key="ts_dv")
            is_paired = st.checkbox("Paired/related measurements?", key="ts_paired")

        assumptions_met = st.checkbox("Parametric assumptions met? (normality, homogeneity)", value=True, key="ts_assumptions")

        if st.button("🔍 Find Best Test", type="primary"):
            tests = recommend_statistical_test(iv_type, dv_type, n_groups, is_paired, assumptions_met)

            if tests:
                for test in tests:
                    with st.container():
                        confidence_color = "🟢" if test["confidence"] >= 85 else "🟡" if test["confidence"] >= 70 else "🟠"
                        st.markdown(f"### {confidence_color} {test['test']} (Match: {test['confidence']}%)")
                        st.markdown(f"**Purpose:** {test['purpose']}")
                        if test.get("alternative"):
                            st.markdown(f"**If violated:** {test['alternative']}")
                        guide = STATISTICAL_TEST_GUIDE.get(test["test"], {})
                        if guide:
                            st.markdown(f"**Assumptions:** {', '.join(guide.get('assumptions', []))}")
                            if guide.get("effect_size"):
                                st.markdown(f"**Effect size:** {guide['effect_size']}")
                        st.markdown("---")
            else:
                st.info("No specific test recommendation. Try different variable types.")

    with tab3:
        st.subheader("📏 Sample Size Estimator")
        st.caption("Estimate required sample size (like SPSS SamplePower)")

        col1, col2 = st.columns(2)
        with col1:
            design_type = st.selectbox(
                "Analysis type",
                options=["t-test", "paired", "anova", "correlation", "chi-square", "survey"],
                format_func=lambda x: {
                    "t-test": "Independent T-Test", "paired": "Paired T-Test",
                    "anova": "One-Way ANOVA", "correlation": "Pearson Correlation",
                    "chi-square": "Chi-Square", "survey": "Survey Research"
                }[x],
                key="ss_design"
            )
            effect_size = st.slider("Expected effect size", 0.1, 2.0, 0.5, 0.05, key="ss_effect",
                                    help="d=0.2=small, 0.5=medium, 0.8=large")
        with col2:
            alpha = st.select_slider("Alpha (α)", options=[0.001, 0.01, 0.05, 0.10], value=0.05, key="ss_alpha")
            power = st.select_slider("Power (1-β)", options=[0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95], value=0.80, key="ss_power")

        if design_type == "anova":
            n_groups_ss = st.number_input("Number of groups", min_value=2, max_value=10, value=3, key="ss_anova_groups")
        else:
            n_groups_ss = 2

        if st.button("📊 Calculate Sample Size", type="primary"):
            result = estimate_sample_size(design_type, effect_size, alpha, power, n_groups=n_groups_ss)
            st.success(result.get("interpretation", ""))

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total N Needed", result.get("total_n", "N/A"))
            with col2:
                st.metric("Per Group", result.get("n_per_group", "N/A"))
            with col3:
                st.metric("Effect Size", effect_size)
            with col4:
                st.metric("Power", f"{power*100:.0f}%")

            st.info(f"**Formula**: {result.get('formula', '')}")

            # Interpretation guide
            st.markdown("""
            **Effect Size Guidelines (Cohen, 1988):**
            - **T-test**: d=0.2 (small), 0.5 (medium), 0.8 (large)
            - **ANOVA**: f=0.1 (small), 0.25 (medium), 0.4 (large)
            - **Correlation**: r=0.1 (small), 0.3 (medium), 0.5 (large)
            """)

    with tab4:
        st.subheader("📝 Methodology Section Generator")
        st.caption("Generate an APA-style Method section for your research proposal or paper")

        col1, col2 = st.columns(2)
        with col1:
            design_name = st.selectbox("Study design", options=list(STUDY_DESIGNS.keys()), key="mg_design")
            ivs = st.text_input("Independent variable(s) (comma-separated)", key="mg_ivs")
        with col2:
            dvs = st.text_input("Dependent variable(s) (comma-separated)", key="mg_dvs")
            tests = st.multiselect(
                "Statistical tests planned",
                options=list(STATISTICAL_TEST_GUIDE.keys()),
                key="mg_tests"
            )

        # Sample size info
        st.markdown("**Sample size information:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            total = st.number_input("Total N", min_value=1, value=100, key="mg_n")
        with col2:
            mg_alpha = st.select_slider("Alpha", options=[0.001, 0.01, 0.05, 0.10], value=0.05, key="mg_alpha")
        with col3:
            mg_power = st.select_slider("Power", options=[0.50, 0.60, 0.70, 0.80, 0.90, 0.95], value=0.80, key="mg_power")

        if st.button("📄 Generate Method Section", type="primary"):
            variables = {
                "independent": [v.strip() for v in ivs.split(",") if v.strip()],
                "dependent": [v.strip() for v in dvs.split(",") if v.strip()],
            }
            sample_size_info = {
                "total_n": total,
                "alpha": mg_alpha,
                "power": mg_power,
                "effect_size": 0.5,
                "n_per_group": total // 2,
            }
            section = generate_methodology_section(design_name, tests, sample_size_info, variables)
            st.markdown(section)

            # Copy button
            st.code(section, language="markdown")

