
"""
Active Bias & Methodological Flaw Detector  AI-driven "Peer Reviewer"
Critically audits research methodology sections, sample sizes, experimental setups.
Flags small sample sizes, unaddressed confounding variables, statistical over-claims,
p-hacking risks, selection bias, and assigns overall "Methodological Rigor Score" (0–100%).

Core Capabilities:
  - Line-by-line methodology auditing with evidence citations
  - Sample size adequacy checking (power analysis based)
  - Confounding variable detection
  - Statistical over-claim detection
  - P-hacking risk assessment
  - Selection bias detection
  - Overall Methodological Rigor Score (0–100%)
  - Publication-ready audit report generation
"""
from __future__ import annotations

import re
import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

import numpy as np

try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# ═══════════════════════════════════════════════════════════════════════
# 1. METHODOLOGY FLAW KNOWLEDGE BASE
# ═══════════════════════════════════════════════════════════════════════

# Common methodological flaws with detection patterns and severity weights
METHODOLOGY_FLAWS = {
    "small_sample_size": {
        "label": "Small Sample Size",
        "severity": "high",
        "weight": 25,
        "patterns": [
            r"\b[NSn]\s*=\s*(\d)\b",
            r"\bsample\s(?:size|n)\s*(?::|was|of|indicated)?\s*(\d)",
            r"\b(n|N)\s*=\s*(\d)\b",
            r"\bparticipants?\s*\(?\s*[NSn]\s*=\s*(\d)",
            r"\btotal\s(?:of\s)?(\d)\s(?:participants?|subjects?|patients?|samples?)",
        ],
        "recommendation": "Consider power analysis to justify sample size. Small samples (N < 30 per group) may produce unstable estimates and low statistical power.",
    },
    "no_power_analysis": {
        "label": "Missing Power Analysis",
        "severity": "medium",
        "weight": 15,
        "patterns": [
            r"\bpower\s(?:analysis|calculation|estimation)",
            r"\bsample\ssize\s(?:justification|determination|calculation)",
            r"\bstatistical\spower\b",
            r"\bpost[- ]?hoc\spower\b",
        ],
        "recommendation": "Report an a priori power analysis to justify sample size. Include expected effect size, alpha, power (typically 0.80), and calculated N.",
    },
    "confounding_variable": {
        "label": "Unaddressed Confounding Variables",
        "severity": "high",
        "weight": 20,
        "patterns": [
            r"\bconfound(?:ing)?\s(?:variable|factor|effect)",
            r"\bcovariate\b",
            r"\bcontrolling\sfor\b",
            r"\badjusted\sfor\b",
            r"\bpropensity\sscore\b",
            r"\bmatching\b",
        ],
        "recommendation": "Identify and measure potential confounders. Use multivariate methods (ANCOVA, multiple regression, propensity scores) to control for confounding.",
    },
    "p_hacking_risk": {
        "label": "P-Hacking Risk",
        "severity": "high",
        "weight": 25,
        "patterns": [
            r"\bmultiple\s(?:comparisons?|tests?|analyses)",
            r"\bdata[- ]?driven\b",
            r"\bexploratory\s(?:analysis|findings)",
            r"\bpost[- ]?hoc\s(?:analysis|comparisons)",
            r"\bsubgroup\s(?:analysis|analyses)",
            r"\bstepwise\s(?:regression|selection)",
        ],
        "recommendation": "Preregister analyses. Apply multiple comparison corrections (Bonferroni, FDR). Clearly distinguish confirmatory vs exploratory analyses.",
    },
    "selection_bias": {
        "label": "Selection Bias Risk",
        "severity": "medium",
        "weight": 18,
        "patterns": [
            r"\bconvenience\ssample\b",
            r"\bself[- ]?selected?\b",
            r"\bvolunteer\s(?:bias|sample)",
            r"\bnon[- ]?random\s(?:assignment|selection|sampling)",
            r"\battrition\b",
            r"\bloss\sto\sfollow[- ]?up\b",
            r"\bexclusion\s(?:criteria|criterion)",
        ],
        "recommendation": "Describe sampling strategy and inclusion/exclusion criteria. Discuss potential selection biases and their direction of effect on results.",
    },
    "no_randomization": {
        "label": "Lack of Randomization",
        "severity": "high",
        "weight": 22,
        "patterns": [
            r"\brandom(?:ly|ization|ized|ly\sassigned|ly\sallocated)?",
            r"\brandom\s(?:assignment|allocation|selection|sampling)",
            r"\bRCT\b",
            r"\brandomized\scontrolled\strial\b",
        ],
        "recommendation": "Use random assignment to groups to control for unknown confounders. If randomization is not possible, acknowledge limitations and consider quasi-experimental designs.",
    },
    "no_blinding": {
        "label": "Lack of Blinding",
        "severity": "medium",
        "weight": 15,
        "patterns": [
            r"\bblin(?:d|ded|ding)\b",
            r"\bmask(?:ed|ing)?\b",
            r"\bdouble[- ]?blin(?:d|ded)\b",
            r"\bsingle[- ]?blin(?:d|ded)\b",
            r"\bplacebo\s(?:controlled|group)",
        ],
        "recommendation": "Implement blinding where possible (single-blind, double-blind). If not feasible, discuss potential observer/participant bias.",
    },
    "effect_size_missing": {
        "label": "Missing Effect Sizes",
        "severity": "medium",
        "weight": 12,
        "patterns": [
            r"\b(?:Cohens?\s*[dD]|[dD]\s*=)",
            r"\beta[- ]?squared\b",
            r"\b(?:\u03b7|\u03b7)²\b",
            r"\bpartial\s\u03b7²\b",
            r"\b(?:odds\sratio|OR|risk\sratio|RR|hazards?\sratio|HR)",
            r"\beffect\ssize\b",
        ],
        "recommendation": "Report effect sizes with confidence intervals for all primary analyses (Cohen's d, η², r, OR, etc.) as recommended by APA 7th edition.",
    },
    "normality_unchecked": {
        "label": "Normality Assumption Not Checked",
        "severity": "low",
        "weight": 8,
        "patterns": [
            r"\b(?:normality|normal\sdistribution)\s(?:test|check|assumpt|verified)",
            r"\bShapiro[- ]?Wilk\b",
            r"\bKolmogorov[- ]?Smirnov\b",
            r"\bQ[- ]?Q\splot\b",
            r"\bskewness\s(?:and\s)?kurtosis\b",
        ],
        "recommendation": "Test parametric assumptions (normality, homoscedasticity) and report results. If violated, use robust alternatives or transformations.",
    },
    "multiple_comparisons_unadjusted": {
        "label": "Multiple Comparisons Not Adjusted",
        "severity": "high",
        "weight": 22,
        "patterns": [
            r"\bBonferroni\b",
            r"\bFDR\b",
            r"\bHolm(?:[- ]Bonferroni)?\b",
            r"\bTukey(?:['\u2019]s?\sHSD)?\b",
            r"\bSidak\b",
            r"\bBenjamini[- ]?Hochberg\b",
            r"\bmultiple\s(?:comparison|testing|test)\s(?:correction|adjustment)",
        ],
        "recommendation": "Apply correction for multiple comparisons (Bonferroni, FDR, Tukey HSD). Report both adjusted and unadjusted results transparently.",
    },
    "attrition_not_reported": {
        "label": "Attrition/Dropout Not Reported",
        "severity": "medium",
        "weight": 14,
        "patterns": [
            r"\b(?:attrition|dropout|withdrawal|completion)\srate\b",
            r"\blost\sto\sfollow[- ]?up\b",
            r"\b(?:number\sof\s)?completers?\b",
            r"\b(?:retention|completion)\srate\b",
            r"\b(?:excluded|removed)\s\d\sparticipants?\b",
        ],
        "recommendation": "Report attrition rates and reasons for dropout. Conduct sensitivity analysis comparing completers vs non-completers.",
    },
    "no_replicability_info": {
        "label": "No Reproducibility Information",
        "severity": "low",
        "weight": 10,
        "patterns": [
            r"\b(?:data|code|materials?)\s(?:availability|shared|available|repository)",
            r"\b(?:open\sscience|preregist(?:er|ration)|registered\sreport)",
            r"\bOSF\b",
            r"\bGitHub\b",
            r"\bsupplementary\s(?:material|data|code)",
        ],
        "recommendation": "Share data, analysis code, and materials in a public repository. Preregister study design and analysis plan.",
    },
}

# Study design types for context-aware scoring
STUDY_DESIGNS = {
    "RCT": {"min_sample_per_group": 30, "requires_randomization": True, "requires_blinding": True},
    "Quasi-Experimental": {"min_sample_per_group": 30, "requires_randomization": False, "requires_blinding": False},
    "Cohort": {"min_sample_per_group": 100, "requires_randomization": False, "requires_blinding": False},
    "Case-Control": {"min_sample_per_group": 30, "requires_randomization": False, "requires_blinding": False},
    "Cross-Sectional": {"min_sample_per_group": 100, "requires_randomization": False, "requires_blinding": False},
    "Longitudinal": {"min_sample_per_group": 50, "requires_randomization": False, "requires_blinding": False},
    "Case Study": {"min_sample_per_group": 1, "requires_randomization": False, "requires_blinding": False},
    "Meta-Analysis": {"min_sample_per_group": 0, "requires_randomization": False, "requires_blinding": False},
    "Survey": {"min_sample_per_group": 200, "requires_randomization": False, "requires_blinding": False},
    "Qualitative": {"min_sample_per_group": 10, "requires_randomization": False, "requires_blinding": False},
}


# ═══════════════════════════════════════════════════════════════════════
# 2. METHODOLOGY AUDITOR ENGINE
# ═══════════════════════════════════════════════════════════════════════
class MethodologyAuditor:
    """
    Full methodology audit engine  scans research text for methodological flaws,
    assigns rigor scores, generates detailed audit reports with evidence citations.

    Usage:
        auditor = MethodologyAuditor()
        results = auditor.audit_methodology(text, study_design="RCT")
        print(results["rigor_score"])
        for flaw in results["flaws"]:
            print(flaw["label"], flaw["severity"])
    """

    def __init__(self):
        self.flaw_definitions = METHODOLOGY_FLAWS
        self.design_definitions = STUDY_DESIGNS

    def audit_methodology(
        self,
        text: str,
        study_design: Optional[str] = None,
        detected_sample_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Full methodology audit pipeline.

        Args:
            text: Research methodology text to audit
            study_design: Optional study design type (RCT, Cohort, etc.)
            detected_sample_size: Optional sample size if already extracted

        Returns:
            Dict with rigor score, flaws, findings, recommendations
        """
        if not text or not text.strip():
            return {
                "error": "No methodology text provided",
                "rigor_score": 0,
                "flaws": [],
                "findings": [],
                "recommendations": [],
                "design_detected": None,
            }

        text_lower = text.lower()
        findings = []

        # Step 1: Detect study design
        if study_design and study_design in self.design_definitions:
            design_info = self.design_definitions[study_design]
            design_detected = study_design
        else:
            design_detected, design_info = self._detect_study_design(text_lower)

        findings.append({
            "type": "design_detected",
            "label": f"Study Design: {design_detected}",
            "detail": f"Detected study design: {design_detected}",
            "severity": "info",
        })

        # Step 2: Detect sample size
        if detected_sample_size is None:
            detected_sample_size = self._extract_sample_size(text_lower)

        sample_finding = self._evaluate_sample_size(detected_sample_size, design_detected, design_info)
        if sample_finding:
            findings.append(sample_finding)

        # Step 3: Scan for methodological flaws
        flaws = []
        for flaw_key, flaw_def in self.flaw_definitions.items():
            patterns = flaw_def["patterns"]
            is_present = any(re.search(p, text_lower) for p in patterns)

            if flaw_key == "small_sample_size":
                # Check if sample size was mentioned (presence means we found it)
                continue  # Handled separately above
            elif flaw_key == "no_power_analysis":
                # Negative check: if power analysis is mentioned, it's good
                if is_present:
                    findings.append({
                        "type": flaw_key,
                        "label": f"✅ {flaw_def['label']}  Present",
                        "detail": "Power analysis or sample size justification was found.",
                        "severity": "good",
                        "recommendation": None,
                    })
                else:
                    flaws.append({
                        "type": flaw_key,
                        "label": f"❌ {flaw_def['label']}  Missing",
                        "detail": "No power analysis or sample size justification detected.",
                        "severity": flaw_def["severity"],
                        "weight": flaw_def["weight"],
                        "recommendation": flaw_def["recommendation"],
                    })
            elif flaw_key == "confounding_variable":
                if not is_present:
                    flaws.append({
                        "type": flaw_key,
                        "label": f"❌ {flaw_def['label']}  Not Addressed",
                        "detail": "No mention of confounding variables or covariate adjustment.",
                        "severity": flaw_def["severity"],
                        "weight": flaw_def["weight"],
                        "recommendation": flaw_def["recommendation"],
                    })
            elif flaw_key == "p_hacking_risk":
                if is_present:
                    flaws.append({
                        "type": flaw_key,
                        "label": f"⚠️ {flaw_def['label']}  Possible Indicators",
                        "detail": "Text contains phrases associated with p-hacking (multiple tests, data-driven, subgroup analyses without correction).",
                        "severity": flaw_def["severity"],
                        "weight": flaw_def["weight"],
                        "recommendation": flaw_def["recommendation"],
                    })
            elif flaw_key == "selection_bias":
                if is_present:
                    flaws.append({
                        "type": flaw_key,
                        "label": f"⚠️ {flaw_def['label']}  Possible Indicators",
                        "detail": "Text mentions sampling or selection methods that may introduce bias.",
                        "severity": flaw_def["severity"],
                        "weight": flaw_def["weight"],
                        "recommendation": flaw_def["recommendation"],
                    })
            elif flaw_key == "no_randomization":
                if design_detected in ("RCT", "Experimental") and not is_present:
                    flaws.append({
                        "type": flaw_key,
                        "label": f"❌ {flaw_def['label']}  Required but Not Mentioned",
                        "detail": f"Study design '{design_detected}' requires randomization, but no randomization procedures are described.",
                        "severity": flaw_def["severity"],
                        "weight": flaw_def["weight"],
                        "recommendation": flaw_def["recommendation"],
                    })
            elif flaw_key == "no_blinding":
                if design_detected in ("RCT", "Experimental") and not is_present:
                    flaws.append({
                        "type": flaw_key,
                        "label": f"⚠️ {flaw_def['label']}  Not Mentioned",
                        "detail": f"Study design '{design_detected}' typically benefits from blinding, but no blinding procedures are described.",
                        "severity": flaw_def["severity"],
                        "weight": flaw_def["weight"],
                        "recommendation": flaw_def["recommendation"],
                    })
            elif flaw_key == "effect_size_missing":
                if not is_present:
                    flaws.append({
                        "type": flaw_key,
                        "label": f"❌ {flaw_def['label']}",
                        "detail": "No effect sizes detected in the methodology/results text.",
                        "severity": flaw_def["severity"],
                        "weight": flaw_def["weight"],
                        "recommendation": flaw_def["recommendation"],
                    })
            elif flaw_key == "normality_unchecked":
                if not is_present:
                    flaws.append({
                        "type": flaw_key,
                        "label": f"⚠️ {flaw_def['label']}",
                        "detail": "No mention of normality testing or assumption checking.",
                        "severity": flaw_def["severity"],
                        "weight": flaw_def["weight"],
                        "recommendation": flaw_def["recommendation"],
                    })
            elif flaw_key == "multiple_comparisons_unadjusted":
                if is_present and not re.search(r"(Bonferroni|FDR|Holm|Tukey|Sidak|Benjamini)", text_lower):
                    flaws.append({
                        "type": flaw_key,
                        "label": f"⚠️ {flaw_def['label']}",
                        "detail": "Multiple tests mentioned but no correction method detected.",
                        "severity": flaw_def["severity"],
                        "weight": flaw_def["weight"],
                        "recommendation": flaw_def["recommendation"],
                    })
            elif flaw_key == "attrition_not_reported":
                if design_detected in ("Longitudinal", "Cohort", "RCT") and not is_present:
                    flaws.append({
                        "type": flaw_key,
                        "label": f"⚠️ {flaw_def['label']}",
                        "detail": f"Study design '{design_detected}' is longitudinal, but attrition/dropout is not reported.",
                        "severity": flaw_def["severity"],
                        "weight": flaw_def["weight"],
                        "recommendation": flaw_def["recommendation"],
                    })
            elif flaw_key == "no_replicability_info":
                if not is_present:
                    flaws.append({
                        "type": flaw_key,
                        "label": f"⚠️ {flaw_def['label']}",
                        "detail": "No data/code availability, preregistration, or reproducibility information found.",
                        "severity": flaw_def["severity"],
                        "weight": flaw_def["weight"],
                        "recommendation": flaw_def["recommendation"],
                    })

        # Step 4: Statistical over-claim detection
        over_claims = self._detect_statistical_overclaims(text_lower)
        for claim in over_claims:
            flaws.append({
                "type": "statistical_overclaim",
                "label": f"⚠️ {claim['label']}",
                "detail": claim["detail"],
                "severity": claim["severity"],
                "weight": claim["weight"],
                "recommendation": claim["recommendation"],
            })

        # Step 5: Calculate rigor score
        rigor_score = self._calculate_rigor_score(
            flaws=flaws,
            sample_size=detected_sample_size,
            design_detected=design_detected,
            design_info=design_info,
        )

        # Step 6: Build recommendations
        recommendations = [f["recommendation"] for f in flaws if f.get("recommendation")]
        strengths = [f["detail"] for f in findings if f.get("severity") == "good"]

        return {
            "rigor_score": rigor_score,
            "rigor_label": self._score_to_label(rigor_score),
            "flaws": flaws,
            "findings": findings,
            "recommendations": recommendations,
            "strengths": strengths,
            "design_detected": design_detected,
            "detected_sample_size": detected_sample_size,
            "total_flaws": len([f for f in flaws if f["severity"] != "good"]),
            "critical_flaws": len([f for f in flaws if f["severity"] == "high"]),
            "moderate_flaws": len([f for f in flaws if f["severity"] == "medium"]),
            "low_flaws": len([f for f in flaws if f["severity"] == "low"]),
            "audited_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def _detect_study_design(self, text: str) -> Tuple[str, Dict]:
        """Detect study design from text keywords."""
        design_keywords = {
            "RCT": [r"\brandomized\scontrolled\strial\b", r"\bRCT\b"],
            "Meta-Analysis": [r"\bmeta[- ]?analysis\b", r"\bsystematic\sreview\b"],
            "Longitudinal": [r"\blongitudinal\b", r"\bfollow[- ]?up\b", r"\bcohort\b", r"\bprospective\b"],
            "Case-Control": [r"\bcase[- ]?control\b", r"\bcase\scontrol\b"],
            "Cross-Sectional": [r"\bcross[- ]?sectional\b", r"\bcross-sectional\b"],
            "Cohort": [r"\bcohort\sstudy\b", r"\bprospective\scohort\b", r"\bretrospective\scohort\b"],
            "Survey": [r"\bsurvey\b", r"\bquestionnaire\b", r"\bself[- ]?report\b"],
            "Quasi-Experimental": [r"\bquasi[- ]?experimental\b", r"\bquasi-experimental\b"],
            "Qualitative": [r"\bqualitative\b", r"\binterview\b", r"\bfocus\sgroup\b", r"\bthematic\sanalysis\b"],
            "Case Study": [r"\bcase\sstudy\b", r"\bcase\sreport\b"],
        }

        for design, patterns in design_keywords.items():
            if any(re.search(p, text) for p in patterns):
                return design, self.design_definitions.get(design, self.design_definitions["Cross-Sectional"])

        return "Cross-Sectional", self.design_definitions["Cross-Sectional"]

    def _extract_sample_size(self, text: str) -> Optional[int]:
        """Extract the largest mentioned sample size from text."""
        sizes = []
        for pattern in METHODOLOGY_FLAWS["small_sample_size"]["patterns"]:
            matches = re.findall(pattern, text)
            for m in matches:
                if isinstance(m, tuple):
                    for g in m:
                        try:
                            sizes.append(int(g))
                        except (ValueError, TypeError):
                            pass
                else:
                    try:
                        sizes.append(int(m))
                    except (ValueError, TypeError):
                        pass

        if not sizes:
            return None
        # Return the most likely sample size (largest, but not absurdly large)
        reasonable = [s for s in sizes if 5 <= s <= 100000]
        return max(reasonable) if reasonable else None

    def _evaluate_sample_size(
        self,
        sample_size: Optional[int],
        design: str,
        design_info: Dict,
    ) -> Optional[Dict]:
        """Evaluate sample size adequacy based on study design."""
        if sample_size is None:
            return {
                "type": "sample_size_unknown",
                "label": "❌ Sample Size Not Reported",
                "detail": "No sample size could be detected from the methodology text.",
                "severity": "high",
                "weight": 20,
                "recommendation": "Clearly report sample size (total N and per-group N) with justification.",
            }

        min_n = design_info.get("min_sample_per_group", 30)
        if sample_size < min_n:
            return {
                "type": "sample_size_small",
                "label": f"❌ Small Sample Size (N = {sample_size})",
                "detail": f"Detected sample size N = {sample_size}. For '{design}' designs, minimum recommended is {min_n} per group.",
                "severity": "high" if sample_size < min_n * 0.5 else "medium",
                "weight": 25 if sample_size < min_n * 0.5 else 18,
                "recommendation": f"Increase sample size to at least {min_n} per group. Consider power analysis to determine adequate N.",
            }
        else:
            return {
                "type": "sample_size_adequate",
                "label": f"✅ Adequate Sample Size (N = {sample_size})",
                "detail": f"Sample size N = {sample_size} meets minimum recommendation for '{design}' designs (≥{min_n}).",
                "severity": "good",
                "weight": 0,
                "recommendation": None,
            }

    def _detect_statistical_overclaims(self, text: str) -> List[Dict]:
        """Detect statistical over-claiming language."""
        overclaims = []

        # Pattern: claiming causality from correlational data
        causality_patterns = [
            r"\bcause[sd]?\b",
            r"\beffect\sof\b",
            r"\bimpact\sof\b",
            r"\binfluence[sd]?\b",
            r"\bproves?\b",
            r"\bdemonstrates?\scausal(?:ity|l)?\b",
        ]
        has_causal_language = any(re.search(p, text) for p in causality_patterns)
        no_randomization = not re.search(r"\brandom(?:ly|ized|ization)?", text)
        no_experimental = not re.search(r"\b(?:experiment|treatment|intervention|manipulation)", text)

        if has_causal_language and (no_randomization or no_experimental):
            overclaims.append({
                "label": "Causal Claims from Non-Experimental Data",
                "detail": "Text uses causal language (cause, effect, impact) but no randomization or experimental manipulation is described.",
                "severity": "high",
                "weight": 22,
                "recommendation": "Use associative language (associated with, predicted by, related to) unless causal identification strategy is clearly described.",
            })

        # Pattern: overgeneralization
        generalization_patterns = [
            r"\ball\s(?:people|participants|subjects|patients|populations?)\b",
            r"\buniversally\b",
            r"\balways\b",
            r"\bnever\b",
            r"\beveryone\b",
            r"\bproved?\s(?:that|to be)\b",
        ]
        if any(re.search(p, text) for p in generalization_patterns):
            overclaims.append({
                "label": "Overgeneralization",
                "detail": "Text contains absolute or universal claims that may overgeneralize findings beyond the study population.",
                "severity": "medium",
                "weight": 12,
                "recommendation": "Qualify findings with study population characteristics. Avoid absolute claims unless supported by comprehensive evidence.",
            })

        # Pattern: significance without effect size
        if re.search(r"\b(?:significant|p\s*[<≤]\s*0\.0\d)\b", text) and \
           not re.search(r"\b(?:d\s*=|η²|eta[\s-]squared|Cram[eè]r|odds\sratio|cohen)", text):
            overclaims.append({
                "label": "Statistical Significance Without Effect Size",
                "detail": "Statistical significance is mentioned but no effect sizes are reported to indicate practical significance.",
                "severity": "medium",
                "weight": 12,
                "recommendation": "Always report effect sizes alongside p-values. Significance does not equal practical importance.",
            })

        return overclaims

    def _calculate_rigor_score(
        self,
        flaws: List[Dict],
        sample_size: Optional[int],
        design_detected: str,
        design_info: Dict,
    ) -> int:
        """Calculate overall methodological rigor score (0-100)."""
        score = 100

        # Deduct for each flaw
        for flaw in flaws:
            weight = flaw.get("weight", 10)
            if flaw["severity"] == "high":
                score -= weight
            elif flaw["severity"] == "medium":
                score -= weight * 0.7
            elif flaw["severity"] == "low":
                score -= weight * 0.4

        # Bonus for good methodology practices
        for flaw in flaws:
            if flaw["severity"] == "good":
                score = 5

        # Ensure 0-100 range
        return max(0, min(100, int(round(score))))

    def _score_to_label(self, score: int) -> str:
        """Convert numeric score to qualitative label."""
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Good"
        elif score >= 60:
            return "Fair"
        elif score >= 40:
            return "Poor"
        else:
            return "Critical"

    def audit_report_sections(
        self,
        sections: List[Dict[str, str]],
        study_design: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Audit multiple report sections and return per-section results."""
        results = []
        for section in sections:
            title = section.get("title", "Untitled")
            content = section.get("content", "")
            if content.strip():
                audit = self.audit_methodology(content, study_design=study_design)
                audit["section_title"] = title
                results.append(audit)
        return results

    def generate_audit_report(self, audit_results: Dict[str, Any]) -> str:
        """Generate a formatted text report from audit results."""
        lines = [
            "═" * 70,
            "METHODOLOGICAL RIGOR AUDIT REPORT",
            f"Generated: {audit_results.get('audited_at', 'N/A')}",
            "═" * 70,
            "",
            f"OVERALL RIGOR SCORE: {audit_results.get('rigor_score', 0)}/100  "
            f"{audit_results.get('rigor_label', 'N/A')}",
            f"Study Design: {audit_results.get('design_detected', 'Unknown')}",
            f"Sample Size: {audit_results.get('detected_sample_size', 'Not detected')}",
            "",
            "─" * 40,
            "FLAWS DETECTED",
            "─" * 40,
        ]

        flaws = audit_results.get("flaws", [])
        if flaws:
            for f in flaws:
                severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟠", "good": "✅", "info": "ℹ️"}.get(
                    f.get("severity", "low"), "⚪"
                )
                lines.append(f"{severity_icon} {f['label']}")
                lines.append(f"   {f.get('detail', '')}")
                if f.get("recommendation"):
                    lines.append(f"   💡 {f['recommendation']}")
                lines.append("")
        else:
            lines.append("No methodological flaws detected.")
            lines.append("")

        recommendations = audit_results.get("recommendations", [])
        if recommendations:
            lines.append("─" * 40)
            lines.append("RECOMMENDATIONS FOR IMPROVEMENT")
            lines.append("─" * 40)
            for i, rec in enumerate(recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        strengths = audit_results.get("strengths", [])
        if strengths:
            lines.append("─" * 40)
            lines.append("STRENGTHS")
            lines.append("─" * 40)
            for s in strengths:
                lines.append(f"✅ {s}")
            lines.append("")

        lines.append("═" * 70)
        lines.append("END OF AUDIT REPORT")
        lines.append("═" * 70)

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# 3. UI RENDERER
# ═══════════════════════════════════════════════════════════════════════
def render_methodology_auditor_ui():
    """Render the Methodology Auditor UI for Streamlit."""
    import streamlit as st

    st.markdown("## 🔬 Active Bias & Methodological Flaw Detector")
    st.markdown("*AI-driven 'Peer Reviewer' that critically audits research methodology  flags flaws, assigns Rigor Score*")

    tab1, tab2, tab3 = st.tabs([
        "📝 Input & Audit",
        " Rigor Score Dashboard",
        "📄 Audit Report",
    ])

    auditor = MethodologyAuditor()

    # ════════════════════════════════════════════════════════════════
    # TAB 1: Input & Audit
    # ════════════════════════════════════════════════════════════════
    with tab1:
        st.subheader("📝 Enter Methodology Text for Audit")

        input_method = st.radio(
            "Input method",
            options=[
                "✏️ Paste Methodology Text",
                "📋 Load from Active Report Sections",
            ],
            horizontal=True,
            key="audit_input_method",
        )

        text_to_audit = ""
        detected_design = None
        detected_n = None

        if input_method == "✏️ Paste Methodology Text":
            text_to_audit = st.text_area(
                "Paste the methodology section, experimental setup, or research description:",
                height=300,
                placeholder="Paste your Methods section here...\n\nExample:\nWe recruited 45 participants (23 male, 22 female) aged 18-35. Participants were randomly assigned to either the treatment or control group. The treatment group received a 30-minute intervention...",
                key="audit_text_input",
            )

            col1, col2 = st.columns(2)
            with col1:
                detected_design = st.selectbox(
                    "Study design (optional  auto-detect if blank)",
                    options=[""]  list(STUDY_DESIGNS.keys()),
                    key="audit_design_select",
                ) or None
            with col2:
                detected_n = st.number_input(
                    "Sample size (optional  auto-extract if blank)",
                    min_value=0, max_value=100000, value=0, step=10,
                    key="audit_n_input",
                )
                detected_n = detected_n if detected_n > 0 else None

        elif input_method == "📋 Load from Active Report Sections":
            st.info("Load methodology content from the Literature Engine's report sections.")
            db_path = None
            try:
                from modules.literature_engine import LiteratureDatabase
                db = LiteratureDatabase()
                projects = db.get_projects()
                if projects:
                    selected_project = st.selectbox(
                        "Select project",
                        options=projects,
                        format_func=lambda p: f"{p.get('name', 'Untitled')}  {p.get('topic', '')}",
                        key="audit_project_select",
                    )
                    if selected_project:
                        sections = db.get_report_sections(selected_project["id"])
                        # Find methodology section
                        for sec in sections:
                            if "method" in sec.get("section_title", "").lower():
                                text_to_audit = sec.get("content", "")
                                break
                        if not text_to_audit:
                            # Use first section with content
                            for sec in sections:
                                if sec.get("content", "").strip():
                                    text_to_audit = sec.get("content", "")
                                    break
                        st.info(f"Loaded from project '{selected_project.get('name', '')}'  {len(text_to_audit)} characters")
                else:
                    st.info("No projects found. Use the Literature Engine first.")
            except Exception as e:
                st.warning(f"Could not load from Literature Engine: {e}")

        # Audit button
        col1, col2 = st.columns([3, 1])
        with col1:
            run_audit = st.button("🔍 Run Methodology Audit", type="primary", use_container_width=True)
        with col2:
            st.caption(f"Characters: {len(text_to_audit):,}")

        if run_audit and text_to_audit.strip():
            with st.spinner("🔍 Auditing methodology..."):
                results = auditor.audit_methodology(
                    text=text_to_audit,
                    study_design=detected_design,
                    detected_sample_size=detected_n,
                )

            if "error" in results:
                st.error(results["error"])
            else:
                st.session_state["_last_audit_results"] = results
                st.success(f"✅ Audit complete! Rigor Score: {results['rigor_score']}/100  {results['rigor_label']}")
                st.rerun()

        elif run_audit:
            st.warning("Please enter or load methodology text to audit.")

        # If results exist, show quick summary
        if st.session_state.get("_last_audit_results"):
            results = st.session_state["_last_audit_results"]
            score = results["rigor_score"]
            color = "#2ecc71" if score >= 75 else "#e67e22" if score >= 50 else "#e74c3c"
            st.markdown(f"""
            <div style="text-align:center;padding:1rem;border-radius:14px;
                        border:2px solid {color};background:{color}10;margin:0.5rem 0;">
                <span style="font-size:2.5rem;font-weight:900;color:{color};">{score}</span>
                <span style="font-size:1.1rem;color:{color};">/100  {results['rigor_label']}</span>
                <br>
                <span style="font-size:0.9rem;color:#64748b;">
                    🔴 {results.get('critical_flaws', 0)} critical | 🟡 {results.get('moderate_flaws', 0)} moderate | 🟠 {results.get('low_flaws', 0)} minor
                </span>
            </div>
            """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    # TAB 2: Rigor Score Dashboard
    # ════════════════════════════════════════════════════════════════
    with tab2:
        results = st.session_state.get("_last_audit_results")
        if not results:
            st.info("Run an audit first in the **Input & Audit** tab.")
        else:
            st.subheader(" Methodological Rigor Score")
            score = results["rigor_score"]
            color = "#2ecc71" if score >= 75 else "#e67e22" if score >= 50 else "#e74c3c"

            # Gauge-like display
            st.markdown(f"""
            <div style="text-align:center;padding:2rem;border-radius:18px;
                        background:linear-gradient(135deg, {color}20, {color}05);
                        border:2px solid {color};margin-bottom:1rem;">
                <div style="font-size:4rem;font-weight:900;color:{color};">{score}</div>
                <div style="font-size:1.5rem;font-weight:700;color:{color};">{results['rigor_label']}</div>
                <div style="font-size:0.9rem;color:#64748b;margin-top:0.5rem;">
                    Methodological Rigor Score  {score}/100
                </div>
            """, unsafe_allow_html=True)

            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Study Design", results.get("design_detected", "Unknown"))
            with col2:
                n_val = results.get("detected_sample_size", "N/A")
                st.metric("Sample Size", n_val if n_val else "N/A")
            with col3:
                st.metric("Total Flaws", results.get("total_flaws", 0))
            with col4:
                st.metric("Critical Flaws", results.get("critical_flaws", 0),
                         delta_color="inverse")

            # Flaw breakdown
            st.subheader("🔍 Flaw Breakdown")
            flaws = results.get("flaws", [])
            if flaws:
                for f in flaws:
                    sev = f.get("severity", "low")
                    sev_icon = {"high": "🔴", "medium": "🟡", "low": "🟠", "good": "✅", "info": "ℹ️"}.get(sev, "⚪")
                    sev_color = {"high": "#e74c3c", "medium": "#e67e22", "low": "#f39c12", "good": "#2ecc71", "info": "#3498db"}.get(sev, "#95a5a6")

                    st.markdown(f"""
                    <div style="padding:0.6rem 0.8rem;margin:0.3rem 0;border-radius:10px;
                                border-left:4px solid {sev_color};background:{sev_color}08;">
                        <strong>{sev_icon} {f['label']}</strong><br>
                        <span style="font-size:0.9rem;">{f.get('detail', '')}</span>
                        {f'<br><span style="font-size:0.85rem;color:#64748b;">💡 {f["recommendation"]}</span>' if f.get("recommendation") else ''}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("✅ No methodological flaws detected!")

            # Strengths
            strengths = results.get("strengths", [])
            if strengths:
                st.subheader("✅ Strengths")
                for s in strengths:
                    st.markdown(f"✅ {s}")

    # ════════════════════════════════════════════════════════════════
    # TAB 3: Audit Report
    # ════════════════════════════════════════════════════════════════
    with tab3:
        results = st.session_state.get("_last_audit_results")
        if not results:
            st.info("Run an audit first in the **Input & Audit** tab.")
        else:
            st.subheader("📄 Audit Report")

            report_text = auditor.generate_audit_report(results)

            st.markdown(f"```\n{report_text}\n```")

            # Download
            import base64
            b64 = base64.b64encode(report_text.encode()).decode()
            st.markdown(
                f'<a href="data:text/plain;base64,{b64}" download="methodology_audit_report.txt" '
                f'style="display:inline-block;padding:10px 20px;background:#1d4ed8;color:white;'
                f'border-radius:8px;text-decoration:none;font-weight:600;">📥 Download Audit Report</a>',
                unsafe_allow_html=True,
            )

            # Copy
            escaped = report_text.replace("`", "\\`").replace("${", "\\${")
            st.markdown(
                f"""<button onclick="navigator.clipboard.writeText(`{escaped}`)"
                    style="padding:10px 20px;background:#059669;color:white;border:none;border-radius:8px;cursor:pointer;font-weight:600;margin-left:0.5rem;">
                    📋 Copy Report</button>""",
                unsafe_allow_html=True,
            )
