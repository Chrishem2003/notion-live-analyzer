
"""
Research Quality & Reproducibility Checker  detects p-hacking, QRPs,
assesses reproducibility, and provides transparency checks.
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
import warnings

from modules.pandas_compat import is_text_dtype
warnings.filterwarnings('ignore')


class ResearchQualityChecker:
    """Detect questionable research practices and assess reproducibility."""

    @staticmethod
    def check_p_hacking(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect potential p-hacking in a set of statistical results."""
        if not results:
            return {"risk": "unknown", "findings": [], "score": 100}

        findings = []
        total_tests = len(results)
        significant = sum(1 for r in results if r.get("significant", False))
        p_values = [r.get("p_value", 1) for r in results if "p_value" in r]
        borderline = sum(1 for p in p_values if 0.04 <= p <= 0.06)

        # 1. Too many significant results
        sig_ratio = significant / max(total_tests, 1)
        if sig_ratio > 0.8 and total_tests >= 5:
            findings.append({
                "type": "p_hacking",
                "severity": "high",
                "detail": f"{significant}/{total_tests} tests are significant ({sig_ratio:.0%}). This unusually high rate may indicate p-hacking or selective reporting.",
                "recommendation": "Consider adjusting for multiple comparisons (Bonferroni, FDR). Report all tests conducted, not just significant ones.",
            })

        # 2. Borderline p-values clustering
        if borderline >= 3:
            findings.append({
                "type": "p_hacking",
                "severity": "medium",
                "detail": f"{borderline} p-values cluster just below .05 ({[f'{p:.3f}' for p in sorted(p_values) if 0.04 <= p <= 0.06]}). This may indicate rounding down or optional stopping.",
                "recommendation": "Report exact p-values, not thresholds. Preregister analyses.",
            })

        # 3. Just-significant with small samples
        for r in results:
            if r.get("significant") and r.get("p_value", 1) > 0.01:
                n = r.get("n", r.get("total_n", r.get("n_pairs", 0)))
                if n and n < 30:
                    findings.append({
                        "type": "low_power",
                        "severity": "medium",
                        "detail": f"Significant result (p = {r.get('p_value', 0):.3f}) with small sample (N = {n}). Likely overestimated effect size.",
                        "recommendation": "Report effect sizes with confidence intervals. Conduct a power analysis.",
                    })

        # 4. Missing effect sizes
        missing_es = sum(1 for r in results if "cohens_d" not in r and "eta_squared" not in r and "r" not in r and "cramers_v" not in r)
        if missing_es > total_tests * 0.5:
            findings.append({
                "type": "reporting",
                "severity": "medium",
                "detail": f"{missing_es}/{total_tests} results missing effect sizes. APA 7th edition requires effect sizes for all statistical tests.",
                "recommendation": "Report and interpret effect sizes for all statistical tests (d, η², r, V, etc.).",
            })

        # Score
        score = 100
        for f in findings:
            if f["severity"] == "high":
                score -= 25
            elif f["severity"] == "medium":
                score -= 15
            elif f["severity"] == "low":
                score -= 5
        score = max(0, score)

        risk = "low" if score >= 80 else "moderate" if score >= 60 else "high"

        return {
            "risk": risk,
            "score": score,
            "findings": findings,
            "total_tests": total_tests,
            "significant_count": significant,
            "borderline_count": borderline,
            "summary": f"p-Hacking Risk: {'🟢 Low' if risk == 'low' else '🟡 Moderate' if risk == 'moderate' else '🔴 High'} ({score}/100)",
        }

    @staticmethod
    def check_reproducibility(df: pd.DataFrame, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Assess reproducibility readiness of a dataset."""
        findings = []
        score = 100

        # 1. Missing data documentation
        if df.isna().sum().sum() > 0:
            missing_pct = df.isna().mean().mean() * 100
            if missing_pct > 20:
                findings.append({
                    "type": "missing_data",
                    "severity": "high",
                    "detail": f"{missing_pct:.1f}% of values are missing. Reproducibility requires clear documentation of missing data handling.",
                    "recommendation": "Document missing data mechanisms (MCAR, MAR, MNAR). Describe imputation methods.",
                })
                score -= 20

        # 2. Variable naming clarity
        unclear_names = [c for c in df.columns if len(c) < 2 or len(c) > 50]
        if unclear_names:
            findings.append({
                "type": "variable_naming",
                "severity": "low",
                "detail": f"{len(unclear_names)} columns have unclear names ({unclear_names[:5]}). Clear naming improves reproducibility.",
                "recommendation": "Use descriptive, standardized variable names with codebook.",
            })
            score -= 5

        # 3. Data types consistency
        mixed_types = []
        for col in df.columns:
            if is_text_dtype(df[col]):
                numeric_ratio = pd.to_numeric(df[col], errors='coerce').notna().mean()
                if 0.2 < numeric_ratio < 0.8:
                    mixed_types.append(col)
        if mixed_types:
            findings.append({
                "type": "data_type",
                "severity": "medium",
                "detail": f"{len(mixed_types)} columns have mixed types ({mixed_types[:3]}). Clear data types are essential for reproducibility.",
                "recommendation": "Standardize data types. Document coding schemes for categorical variables.",
            })
            score -= 15

        # 4. Sample size transparency
        n = len(df)
        if n < 30:
            findings.append({
                "type": "sample_size",
                "severity": "medium",
                "detail": f"Small sample (N = {n}). Reproducibility is harder with small samples due to instability.",
                "recommendation": "Report confidence intervals. Consider bootstrap for robust inference. Preregister sample size justification.",
            })
            score -= 15
        elif n < 100:
            findings.append({
                "type": "sample_size",
                "severity": "low",
                "detail": f"Moderate sample (N = {n}). Consider power analysis documentation.",
                "recommendation": "Document power analysis or sample size justification.",
            })
            score -= 5

        # 5. Codebook availability
        findings.append({
            "type": "documentation",
            "severity": "low",
            "detail": "Automated check: Ensure a codebook or data dictionary is available alongside the dataset.",
            "recommendation": "Create a data dictionary with variable names, descriptions, types, and value labels.",
        })

        score = max(0, score)
        quality = "excellent" if score >= 80 else "good" if score >= 60 else "fair" if score >= 40 else "poor"

        return {
            "score": score,
            "quality": quality,
            "findings": findings,
            "n_rows": n,
            "n_cols": len(df.columns),
            "missing_pct": round(float(df.isna().mean().mean() * 100), 1),
            "summary": f"Reproducibility: {'🟢 Excellent' if quality == 'excellent' else '🟡 Good' if quality == 'good' else '🟠 Fair' if quality == 'fair' else '🔴 Poor'} ({score}/100)",
        }

    @staticmethod
    def check_qrps(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect Questionable Research Practices."""
        findings = []
        score = 100

        if not results:
            return {"risk": "unknown", "findings": [], "score": 100}

        # HARKing (Hypothesizing After Results are Known)
        # Proxy: very specific hypotheses that perfectly match results
        for r in results:
            if r.get("p_value", 1) < 0.001 and r.get("effect_size", 0) > 0.8:
                findings.append({
                    "type": "harking",
                    "severity": "low",
                    "detail": f"Very strong result (p < .001, d > 0.8). Ensure this hypothesis was preregistered, not derived post-hoc.",
                    "recommendation": "Clearly distinguish confirmatory vs. exploratory analyses. Preregister hypotheses.",
                })
                score -= 10
                break

        # Cherry-picking (selective reporting)
        if len(results) >= 5:
            es_values = [abs(r.get("cohens_d", r.get("r", r.get("eta_squared", 0)))) for r in results]
            if es_values:
                mean_es = np.mean(es_values)
                max_es = max(es_values)
                if max_es > mean_es * 3 and len([e for e in es_values if e > mean_es * 2]) <= 1:
                    findings.append({
                        "type": "cherry_picking",
                        "severity": "medium",
                        "detail": f"One effect size ({max_es:.2f}) is {max_es/mean_es:.1f}x the average ({mean_es:.2f}). May indicate selective reporting of favorable results.",
                        "recommendation": "Report all analyses conducted. Consider correction for multiple comparisons.",
                    })
                    score -= 20

        # Optional stopping (data peeking)
        for r in results:
            n = r.get("n", r.get("total_n", 0))
            if n and n < 20 and r.get("significant"):
                findings.append({
                    "type": "optional_stopping",
                    "severity": "medium",
                    "detail": f"Significant result with small sample (N = {n}). May indicate data-dependent stopping.",
                    "recommendation": "Preregister sample size. Use sequential analysis if interim looks are necessary.",
                })
                score -= 20
                break

        score = max(0, score)
        risk = "low" if score >= 80 else "moderate" if score >= 60 else "high"

        return {
            "risk": risk,
            "score": score,
            "findings": findings,
            "summary": f"QRP Risk: {'🟢 Low' if risk == 'low' else '🟡 Moderate' if risk == 'moderate' else '🔴 High'} ({score}/100)",
        }

    @staticmethod
    def generate_transparency_checklist() -> List[Dict[str, Any]]:
        """Generate a transparency and reproducibility checklist."""
        return [
            {"item": "Preregistration", "description": "Was the study preregistered? (OSF, AsPredicted, ClinicalTrials.gov)", "category": "planning"},
            {"item": "Sample Size Justification", "description": "Was a power analysis or sample size rationale provided?", "category": "planning"},
            {"item": "Data Availability", "description": "Is the raw data publicly available in a repository?", "category": "data"},
            {"item": "Code Availability", "description": "Is the analysis code publicly available?", "category": "data"},
            {"item": "Materials Availability", "description": "Are study materials (stimuli, questionnaires) available?", "category": "materials"},
            {"item": "Analysis Plan", "description": "Was the analysis plan preregistered or clearly specified?", "category": "analysis"},
            {"item": "Exclusion Criteria", "description": "Are participant/data exclusion criteria clearly documented?", "category": "methods"},
            {"item": "Missing Data Handling", "description": "Is the handling of missing data clearly described?", "category": "analysis"},
            {"item": "Multiple Comparisons", "description": "Was adjustment for multiple comparisons applied?", "category": "analysis"},
            {"item": "Effect Sizes", "description": "Are effect sizes with confidence intervals reported?", "category": "reporting"},
            {"item": "Sensitivity Analyses", "description": "Were sensitivity analyses conducted?", "category": "analysis"},
            {"item": "Conflicts of Interest", "description": "Are funding sources and conflicts disclosed?", "category": "ethics"},
            {"item": "Ethical Approval", "description": "Was ethical approval obtained and reported?", "category": "ethics"},
            {"item": "Author Contributions", "description": "Are author contributions specified?", "category": "reporting"},
        ]


# ─── UI ─────────────────────────────────────────────────────────────

def render_research_quality_ui(statistical_results: List[Dict] = None, df=None):
    """Render the research quality checker UI."""
    import streamlit as st
    from modules.ui_components import section_header, insight_card

    st.markdown("## ✅ Research Quality & Reproducibility Checker")
    st.markdown("*Detect p-hacking, QRPs, assess reproducibility, and ensure transparency*")

    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 p-Hacking Detection", "📋 Reproducibility", "⚠️ QRP Detection", "📝 Transparency Checklist"
    ])

    checker = ResearchQualityChecker()

    with tab1:
        st.subheader("🔍 p-Hacking Detection")
        st.caption("Analyzes statistical results for signs of p-hacking")

        if statistical_results:
            if st.button("🚀 Run p-Hacking Check", type="primary"):
                result = checker.check_p_hacking(statistical_results)
                risk = result.get("risk", "unknown")
                score = result.get("score", 0)
                risk_color = "#2ecc71" if risk == "low" else "#e67e22" if risk == "moderate" else "#e74c3c"

                st.markdown(f"""
                <div style="text-align:center;padding:1.2rem;border-radius:14px;
                    border:2px solid {risk_color};background:{risk_color}10;margin-bottom:1rem;">
                    <div style="font-size:2.5rem;font-weight:900;color:{risk_color};">{score}</div>
                    <div style="font-size:1.2rem;font-weight:700;color:{risk_color};">{risk.upper()} RISK</div>
                    <div>p-Hacking Risk Score</div>
                </div>
                """, unsafe_allow_html=True)

                for f in result.get("findings", []):
                    sev_color = "#e74c3c" if f["severity"] == "high" else "#e67e22" if f["severity"] == "medium" else "#f1c40f"
                    st.markdown(f"""
                    <div style="padding:0.8rem;margin:0.5rem 0;border-radius:10px;
                        border-left:4px solid {sev_color};background:{sev_color}08;">
                        <strong style="color:{sev_color};">⚠️ {f['detail']}</strong><br>
                        <span style="font-size:0.9rem;">💡 {f['recommendation']}</span>
                    </div>
                    """, unsafe_allow_html=True)

            # Summary stats
            st.markdown("###  Results Summary")
            n_sig = sum(1 for r in statistical_results if r.get("significant"))
            n_total = len(statistical_results)
            st.metric("Total Tests", n_total)
            st.metric("Significant", n_sig, delta=f"{n_sig/max(n_total,1):.0%}")
        else:
            st.info("No statistical results available. Run analyses on the **🔬 Statistical Tests** page first.")

    with tab2:
        st.subheader("📋 Reproducibility Check")
        st.caption("Assess how reproducible your research is")

        if df is not None:
            if st.button("🔍 Check Reproducibility", type="primary"):
                result = checker.check_reproducibility(df)
                quality = result.get("quality", "unknown")
                score = result.get("score", 0)
                qual_color = "#2ecc71" if quality == "excellent" else "#e67e22" if quality == "good" else "#e74c3c"

                st.markdown(f"""
                <div style="text-align:center;padding:1.2rem;border-radius:14px;
                    border:2px solid {qual_color};background:{qual_color}10;margin-bottom:1rem;">
                    <div style="font-size:2.5rem;font-weight:900;color:{qual_color};">{score}</div>
                    <div style="font-size:1.2rem;font-weight:700;color:{qual_color};">{quality.upper()}</div>
                    <div>Reproducibility Score</div>
                </div>
                """, unsafe_allow_html=True)

                for f in result.get("findings", []):
                    sev_color = "#e74c3c" if f["severity"] == "high" else "#e67e22" if f["severity"] == "medium" else "#f1c40f"
                    st.markdown(f"""
                    <div style="padding:0.8rem;margin:0.5rem 0;border-radius:10px;
                        border-left:4px solid {sev_color};background:{sev_color}08;">
                        <strong>{f['detail']}</strong><br>
                        <span style="font-size:0.9rem;color:#64748b;">💡 {f['recommendation']}</span>
                    </div>
                    """, unsafe_allow_html=True)

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Rows", f"{result.get('n_rows', 0):,}")
                with col2:
                    st.metric("Columns", result.get("n_cols", 0))
                with col3:
                    st.metric("Missing %", f"{result.get('missing_pct', 0)}%")
                with col4:
                    st.metric("Quality", quality.title())
        else:
            st.info("Load data first to check reproducibility readiness.")

    with tab3:
        st.subheader("⚠️ Questionable Research Practices (QRP) Detection")
        st.caption("Detects HARKing, cherry-picking, optional stopping, and other QRPs")

        if statistical_results:
            if st.button("🔍 Check QRPs", type="primary"):
                result = checker.check_qrps(statistical_results)
                risk = result.get("risk", "unknown")
                score = result.get("score", 0)
                risk_color = "#2ecc71" if risk == "low" else "#e67e22" if risk == "moderate" else "#e74c3c"

                st.markdown(f"""
                <div style="text-align:center;padding:1.2rem;border-radius:14px;
                    border:2px solid {risk_color};background:{risk_color}10;margin-bottom:1rem;">
                    <div style="font-size:2.5rem;font-weight:900;color:{risk_color};">{score}</div>
                    <div style="font-size:1.2rem;font-weight:700;color:{risk_color};">{risk.upper()} RISK</div>
                    <div>QRP Risk Score</div>
                </div>
                """, unsafe_allow_html=True)

                for f in result.get("findings", []):
                    sev_color = "#e74c3c" if f["severity"] == "high" else "#e67e22" if f["severity"] == "medium" else "#f1c40f"
                    st.markdown(f"""
                    <div style="padding:0.8rem;margin:0.5rem 0;border-radius:10px;
                        border-left:4px solid {sev_color};background:{sev_color}08;">
                        <strong>{f['detail']}</strong><br>
                        <span style="font-size:0.9rem;color:#64748b;">💡 {f['recommendation']}</span>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No statistical results available. Run analyses first.")

    with tab4:
        st.subheader("📝 Transparency & Reproducibility Checklist")
        st.caption("Essential items for transparent, reproducible research")

        checklist = checker.generate_transparency_checklist()

        categories = {}
        for item in checklist:
            cat = item["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)

        for cat, items in categories.items():
            st.markdown(f"### {cat.capitalize()}")
            for item in items:
                checked = st.checkbox(item["item"], key=f"check_{item['item']}")
                if checked:
                    st.caption(f"✅ {item['description']}")
                else:
                    st.caption(f"📋 {item['description']}")

        if st.button("📥 Download Checklist"):
            import base64
            lines = ["# Transparency & Reproducibility Checklist", ""]
            for cat, items in categories.items():
                lines.append(f"## {cat.capitalize()}")
                for item in items:
                    lines.append(f"- [ ] {item['item']}: {item['description']}")
                lines.append("")
            text = "\n".join(lines)
            b64 = base64.b64encode(text.encode()).decode()
            st.markdown(f'<a href="data:text/markdown;base64,{b64}" download="transparency_checklist.md">📥 Download Checklist</a>', unsafe_allow_html=True)


