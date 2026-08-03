import security_guard

"""
Novelty & Unexplored Research Gap Finder
A cross-synthesis engine that analyzes clusters of papers to identify unaddressed
questions, conflicting findings, and unexplored hypotheses. Auto-drafts research proposals.

Core Capabilities:
  - Cross-paper synthesis to identify conflicting findings
  - Automated gap mapping (what hasn't been studied)
  - Research proposal outline generation
  - Novelty scoring for proposed research directions
"""
from __future__ import annotations

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

import numpy as np
import pandas as pd


class ResearchGapFinder:
    """
    Cross-synthesis engine that analyzes clusters of papers to identify
    research gaps, conflicting findings, and unexplored hypotheses.
    """

    GAP_INDICATORS = [
        r"(?:however|nevertheless|nonetheless|yet|but|although|despite)",
        r"(?:limited|insufficient|inadequate|scarce|sparse|lacking)\s(?:research|evidence|studies|data|knowledge)",
        r"(?:further|future|additional|more)\s(?:research|studies|investigation|examination|exploration)",
        r"(?:unclear|unknown|not\swell\sunderstood|poorly\sunderstood|remains\selusive)",
        r"(?:warrant|require|need|calls?\sfor)\s(?:further|future|additional)\s(?:research|study|investigation)",
        r"(?:has\snot\sbeen\s(?:examined|studied|explored|investigated|addressed))",
        r"(?:open\squestion|unanswered\squestion|outstanding\squestion|research\sgap)",
        r"(?:little\sis\sknown|not\smuch\sis\sknown|remains\sto\sbe\sdetermined)",
    ]

    CONTRADICTION_PHRASES = [
        r"(?:in\scontrast|contrary|conflicting|contradict|discrepancy|inconsistent)",
        r"(?:however|conversely|on\sthe\sother\shand|yet)",
        r"(?:while\ssome|whereas|although)",
        r"(?:differ(?:ent|ing)|divergent|disparate)\s(?:results?|findings?|conclusions?|outcomes?)",
        r"(?:debate|controversy|disagreement|unresolved)",
    ]

    DOMAIN_KEYWORDS = {
        "clinical_trial": ["RCT", "randomized", "clinical trial", "patient", "treatment", "intervention"],
        "molecular_biology": ["gene", "protein", "expression", "pathway", "signaling", "transcription", "knockout"],
        "neuroscience": ["brain", "neuron", "cortical", "fMRI", "EEG", "cognitive", "behavioral"],
        "epidemiology": ["cohort", "case-control", "population", "incidence", "prevalence", "risk factor"],
        "social_science": ["survey", "participant", "questionnaire", "self-report", "demographic"],
        "computational": ["algorithm", "model", "simulation", "machine learning", "deep learning", "neural"],
        "ecology": ["species", "population", "ecosystem", "biodiversity", "habitat", "conservation"],
        "chemistry": ["synthesis", "compound", "reaction", "catalyst", "spectroscopy", "molecule"],
        "physics": ["quantum", "particle", "field", "wave", "energy", "temperature", "measurement"],
    }

    def __init__(self):
        pass

    def analyze_papers(self, papers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze a cluster of papers to identify research gaps."""
        if not papers:
            return {"error": "No papers provided for analysis"}
        if len(papers) < 3:
            return {"error": "Need at least 3 papers for meaningful gap analysis"}

        corpus = []
        for p in papers:
            text = f"{p.get('title', '')} {p.get('abstract', '')} {p.get('findings', '')}"
            corpus.append({
                "title": p.get("title", "Untitled"),
                "text": text.lower(),
                "year": p.get("year"),
                "authors": p.get("authors", ""),
                "journal": p.get("journal", ""),
                "domain": self._detect_domain(text),
            })

        domains = self._detect_all_domains(corpus)
        primary_domain = max(domains, key=domains.get) if domains else "general"

        gaps = self._identify_gaps(corpus)
        conflicts = self._detect_conflicts(corpus)
        unexplored = self._map_unexplored_hypotheses(corpus, conflicts, gaps)
        novelty_scores = self._score_novelty(gaps, conflicts, unexplored)
        proposal = self._generate_proposal_outline(primary_domain, gaps, conflicts, unexplored, corpus)

        return {
            "n_papers": len(papers),
            "primary_domain": primary_domain,
            "domains": domains,
            "gaps": gaps,
            "conflicting_findings": conflicts,
            "unexplored_hypotheses": unexplored,
            "novelty_scores": novelty_scores,
            "proposal_outline": proposal,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def _detect_domain(self, text: str) -> str:
        """Detect the research domain of a paper."""
        text_lower = text.lower()
        scores = {}
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[domain] = score
        return max(scores, key=scores.get) if scores else "general"

    def _detect_all_domains(self, corpus: List[Dict]) -> Dict[str, int]:
        """Aggregate domain detection across all papers."""
        all_domains = {}
        for paper in corpus:
            domain = paper.get("domain", "general")
            all_domains[domain] = all_domains.get(domain, 0)  1
        return dict(sorted(all_domains.items(), key=lambda x: -x[1]))

    def _identify_gaps(self, corpus: List[Dict]) -> List[Dict]:
        """Identify research gaps mentioned in papers."""
        gaps = []
        seen_gaps = set()

        for paper in corpus:
            text = paper["text"]
            sentences = re.split(r'[.!?]\s', text)

            for sent in sentences:
                sent_lower = sent.lower().strip()
                if len(sent_lower) < 30:
                    continue

                for pattern in self.GAP_INDICATORS:
                    if re.search(pattern, sent_lower):
                        gap_text = sent_lower[:300]
                        label = self._generate_gap_label(gap_text)
                        if label not in seen_gaps:
                            seen_gaps.add(label)
                            gaps.append({
                                "label": label,
                                "evidence": gap_text,
                                "source_paper": paper["title"],
                                "category": self._categorize_gap(gap_text),
                                "confidence": self._estimate_gap_confidence(gap_text),
                            })
                        break

        return gaps[:20]

    def _generate_gap_label(self, text: str) -> str:
        """Generate a concise label for a research gap."""
        patterns = [
            r"(?:role|effect|impact|relationship|association|mechanism)\sof\s([^,;])",
            r"(?:limited|insufficient|lack of)\s(?:research|evidence|studies|data|knowledge)\son\s([^,;])",
            r"(?:further|more)\s(?:research|studies)\s(?:is\s)?(?:needed|required|warranted)\s(?:to\s)?(?:understand|examine|determine|investigate|elucidate|clarify)\s([^,;])",
            r"(?:unknown|unclear|not well understood)\s(?:are|is|the)\s([^,;])",
            r"(?:how|what|whether|why)\s([^,;?])",
        ]
        for pattern in patterns:
            m = re.search(pattern, text)
            if m:
                return m.group(1).strip().capitalize()
        return text[:80].strip().capitalize()

    def _categorize_gap(self, text: str) -> str:
        """Categorize the type of research gap."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["mechanism", "pathway", "molecular", "cellular"]):
            return "mechanistic"
        if any(w in text_lower for w in ["clinical", "patient", "treatment", "therapy", "intervention"]):
            return "clinical"
        if any(w in text_lower for w in ["population", "demographic", "diversity", "generaliz"]):
            return "population"
        if any(w in text_lower for w in ["method", "technique", "approach", "measurement"]):
            return "methodological"
        if any(w in text_lower for w in ["longitudinal", "long-term", "follow-up"]):
            return "temporal"
        if any(w in text_lower for w in ["replicat", "reproducib"]):
            return "reproducibility"
        return "theoretical"

    def _estimate_gap_confidence(self, text: str) -> float:
        """Estimate confidence that this is a genuine research gap (0-1)."""
        score = 0.5
        if re.search(r"(?:research\sgap|unanswered\squestion|has\snot\sbeen)", text):
            score = 0.3
        if re.search(r"(?:warrant|require|need|calls?\sfor)\s(?:further|future)", text):
            score = 0.2
        if re.search(r"(?:unknown|unclear|poorly\sunderstood)", text):
            score = 0.15
        return min(1.0, round(score, 2))

    def _detect_conflicts(self, corpus: List[Dict]) -> List[Dict]:
        """Detect conflicting or contradictory findings across papers."""
        conflicts = []

        all_findings = []
        for paper in corpus:
            findings = self._extract_findings(paper["text"])
            all_findings.extend([(f, paper["title"]) for f in findings])

        for i, (finding1, source1) in enumerate(all_findings):
            for j, (finding2, source2) in enumerate(all_findings):
                if i >= j:
                    continue
                if source1 == source2:
                    continue
                contradiction_score = self._check_contradiction(finding1, finding2)
                if contradiction_score > 0.5:
                    conflicts.append({
                        "finding_1": finding1[:200],
                        "source_1": source1,
                        "finding_2": finding2[:200],
                        "source_2": source2,
                        "contradiction_score": round(contradiction_score, 2),
                        "description": f"Papers disagree on: {finding1[:60]} vs {finding2[:60]}",
                        "resolution_needed": self._suggest_resolution(finding1, finding2),
                    })

        seen = set()
        unique_conflicts = []
        for c in conflicts:
            key = tuple(sorted([c["source_1"], c["source_2"]]))
            if key not in seen:
                seen.add(key)
                unique_conflicts.append(c)
        return unique_conflicts[:10]

    def _extract_findings(self, text: str) -> List[str]:
        """Extract key findings from text."""
        findings = []
        sentences = re.split(r'[.!?]\s', text)
        finding_indicators = [
            r"\b(found|observed|discovered|demonstrated|showed|revealed|identified|detected|reported)\b",
            r"\b(significant|significantly|increased|decreased|associated|correlated|predicted)\b",
            r"\b(results?\s(?:indicate|suggest|demonstrate|show|reveal))\b",
            r"\b(these\s(?:data|findings|results|observations)\s(?:indicate|suggest|demonstrate))\b",
        ]
        for sent in sentences:
            sent_lower = sent.lower().strip()
            if len(sent_lower) < 40:
                continue
            for pattern in finding_indicators:
                if re.search(pattern, sent_lower, re.IGNORECASE):
                    findings.append(sent_lower[:300])
                    break
        return findings[:5]

    def _check_contradiction(self, finding1: str, finding2: str) -> float:
        """Check if two findings are contradictory."""
        score = 0.0
        directional_pairs = [
            (r"\bincreased?\b", r"\bdecreased?\b"),
            (r"\bpositive\b", r"\bnegative\b"),
            (r"\bhigher\b", r"\blower\b"),
            (r"\bgreater\b", r"\blesser?\b"),
            (r"\benhance\w*", r"\breduc\w*"),
            (r"\bactivate\w*", r"\binhibit\w*"),
            (r"\bpromote\w*", r"\bsuppress\w*"),
            (r"\bupregulat\w*", r"\bdownregulat\w*"),
        ]
        for pos_pattern, neg_pattern in directional_pairs:
            has_pos1 = bool(re.search(pos_pattern, finding1, re.IGNORECASE))
            has_neg1 = bool(re.search(neg_pattern, finding1, re.IGNORECASE))
            has_pos2 = bool(re.search(pos_pattern, finding2, re.IGNORECASE))
            has_neg2 = bool(re.search(neg_pattern, finding2, re.IGNORECASE))
            if (has_pos1 and has_neg2) or (has_neg1 and has_pos2):
                score = 0.3
        for phrase in self.CONTRADICTION_PHRASES:
            if re.search(phrase, finding1, re.IGNORECASE) or re.search(phrase, finding2, re.IGNORECASE):
                score = 0.2
                break
        return min(1.0, score)

    def _suggest_resolution(self, finding1: str, finding2: str) -> str:
        """Suggest how to resolve conflicting findings."""
        suggestions = []
        if re.search(r"\b(mice|rats|animal|in\svitro)\b", finding1) and \
           re.search(r"\b(human|patient|in\svivo|clinical)\b", finding2):
            suggestions.append("Model system differences (in vitro vs in vivo / animal vs human)")
        if not suggestions:
            suggestions.append("Consider a systematic review or meta-analysis to reconcile findings")
            suggestions.append("Examine sample size, statistical power, and effect size differences")
        return "; ".join(suggestions[:2])

    def _map_unexplored_hypotheses(self, corpus, conflicts, gaps):
        """Map unexplored hypotheses based on gaps and conflicts."""
        hypotheses = []
        seen = set()
        for gap in gaps:
            label = gap.get("label", "")
            if label and label not in seen:
                seen.add(label)
                hypotheses.append({
                    "hypothesis": f"The relationship between {label} remains unexplored in current literature.",
                    "source": "gap_analysis",
                    "category": gap.get("category", "theoretical"),
                    "confidence": gap.get("confidence", 0.5),
                    "proposed_approach": self._suggest_approach(gap.get("category", "theoretical")),
                })
        for conflict in conflicts:
            h = f"Reconciling discrepancy between {conflict.get('finding_1','')[:60]} and {conflict.get('finding_2','')[:60]}"
            if h not in seen:
                seen.add(h)
                hypotheses.append({
                    "hypothesis": f"Controlled study needed to resolve: {conflict.get('description','')}",
                    "source": "conflict_resolution",
                    "category": "methodological",
                    "confidence": 0.7,
                    "proposed_approach": "Design study that directly compares conflicting conditions with sufficient power.",
                })
        return hypotheses[:15]

    def _suggest_approach(self, category: str) -> str:
        """Suggest a research approach based on gap category."""
        approaches = {
            "mechanistic": "Use molecular biology techniques (CRISPR, RNA-seq, ChIP-seq) to elucidate underlying mechanisms.",
            "clinical": "Design a prospective clinical trial or observational cohort study with appropriate controls.",
            "population": "Conduct a multi-site, diverse population study to improve generalizability.",
            "methodological": "Develop or validate new measurement techniques with rigorous benchmarking.",
            "temporal": "Implement a longitudinal study design with multiple time points.",
            "reproducibility": "Perform a direct replication study with pre-registered analysis plan.",
            "theoretical": "Develop a computational model or theoretical framework integrating existing findings.",
        }
        return approaches.get(category, "Conduct a systematic investigation with appropriate controls and sufficient power.")

    def _score_novelty(self, gaps, conflicts, unexplored):
        """Score the novelty of identified gaps and hypotheses."""
        n_gaps = len(gaps)
        n_conflicts = len(conflicts)
        n_hypotheses = len(unexplored)
        if n_gaps == 0 and n_conflicts == 0:
            return {"overall_novelty": 0, "label": "No gaps identified"}
        gap_score = min(1.0, n_gaps * 0.1)
        conflict_score = min(1.0, n_conflicts * 0.15)
        hypothesis_score = min(1.0, n_hypotheses * 0.08)
        overall = round((gap_score * 0.4  conflict_score * 0.35  hypothesis_score * 0.25) * 100, 1)
        label = "Highly Novel" if overall >= 75 else "Novel" if overall >= 50 else "Moderately Novel" if overall >= 25 else "Low Novelty"
        return {"overall_novelty": overall, "label": label, "gap_density": round(gap_score*100,1),
                "conflict_density": round(conflict_score*100,1), "hypothesis_potential": round(hypothesis_score*100,1)}

    def _generate_proposal_outline(self, domain, gaps, conflicts, unexplored, corpus):
        """Generate a research proposal outline from identified gaps."""
        if not gaps and not conflicts:
            return {"title": "General Research Proposal", "sections": []}
        if gaps:
            top_gap = gaps[0].get("label", "Research Gap")
            title = f"Investigating {top_gap}: A Comprehensive Investigation"
        elif conflicts:
            title = f"Resolving Contradictory Evidence in {domain.replace('_', ' ').title()}"
        else:
            title = f"Novel Approaches in {domain.replace('_', ' ').title()} Research"

        sections = [
            {"title": "Background & Rationale",
             "prompt": f"Current literature in {domain.replace('_',' ').title()} reveals significant gaps.",
             "key_gaps": [g.get("label","") for g in gaps[:3]], "word_count": 300},
            {"title": "Research Questions & Hypotheses",
             "prompt": "Based on identified gaps, the following research questions are proposed:",
             "questions": [f"RQ{i1}: {h.get('hypothesis','')[:100]}" for i, h in enumerate(unexplored[:3])],
             "word_count": 200},
            {"title": "Methodology",
             "prompt": self._suggest_approach(domain),
             "approach": self._suggest_approach(gaps[0].get("category","theoretical")) if gaps else "Multi-modal investigation",
             "word_count": 400},
            {"title": "Expected Outcomes & Impact",
             "prompt": "This research will contribute novel insights to the field.",
             "expected_outcomes": ["Novel findings addressing research gaps", "Resolution of conflicting evidence"],
             "word_count": 200},
            {"title": "Timeline & Milestones",
             "prompt": "Proposed timeline:",
             "phases": [
                 {"phase":"Phase 1","duration":"Months 1-6","description":"Literature review, design, ethics"},
                 {"phase":"Phase 2","duration":"Months 7-18","description":"Data collection and analysis"},
                 {"phase":"Phase 3","duration":"Months 19-24","description":"Manuscript preparation and dissemination"}],
             "word_count": 150},
        ]
        return {"title": title, "domain": domain, "sections": sections,
                "disclaimer": "AI-generated proposal outline based on research gaps. Review before submission."}


def render_research_gap_finder_ui():
    """Render the Research Gap Finder UI."""
    import streamlit as st

    st.markdown("##  Novelty & Unexplored Research Gap Finder")
    st.markdown("*Cross-synthesis engine that analyzes clusters of papers to identify unaddressed questions and conflicting findings*")

    tab1, tab2, tab3 = st.tabs([" Input Papers", " Gap Analysis", " Proposal Outline"])
    gap_finder = ResearchGapFinder()

    with tab1:
        st.subheader(" Input Research Papers")
        input_method = st.radio("Paper source", options=[" Paste Paper Details", " Load from Literature Engine Project"], horizontal=True, key="gap_input_method")
        papers = []

        if input_method == " Paste Paper Details":
            paper_text = st.text_area("Paper details", height=300,
                placeholder='''Title: The role of X in Y\nAbstract: This study investigated...\nAuthors: Smith et al.\nYear: 2023\n\n---\n\nTitle: Z modulates Y...\nAbstract: Our results show...\nAuthors: Jones et al.\nYear: 2022''',
                key="gap_paper_text")
            if paper_text.strip():
                blocks = paper_text.split("---")
                for block in blocks:
                    paper = {}
                    for line in block.strip().split("\n"):
                        if ":" in line:
                            key, value = line.split(":", 1)
                            paper[key.strip().lower()] = value.strip()
                    if paper.get("title"):
                        papers.append({"title": paper.get("title",""), "abstract": paper.get("abstract",""), "authors": paper.get("authors",""), "year": paper.get("year")})
                if papers:
                    st.success(f" Parsed {len(papers)} papers")
        else:
            try:
                from modules.literature_engine import LiteratureDatabase
                db = LiteratureDatabase()
                projects = db.get_projects()
                if projects:
                    selected = st.selectbox("Select project", projects, format_func=lambda p: f"{p.get('name','')} ({p.get('topic','')})", key="gap_proj_sel")
                    if selected:
                        db_papers, _ = db.get_papers(selected["id"], checked_only=True)
                        for p in db_papers[:15]:
                            papers.append({"title": p.get("title",""), "abstract": p.get("abstract",""), "findings": p.get("user_findings",""), "authors": p.get("authors",""), "year": p.get("year")})
                        if papers:
                            st.success(f" Loaded {len(papers)} papers")
            except Exception as e:
                st.warning(f"Could not load: {e}")

        if papers and len(papers) >= 3:
            if st.button(" Analyze Research Gaps", type="primary", use_container_width=True):
                with st.spinner(f"Analyzing {len(papers)} papers..."):
                    results = gap_finder.analyze_papers(papers)
                if "error" in results:
                    st.error(results["error"])
                else:
                    st.session_state["_gap_analysis_results"] = results
                    st.success(" Analysis complete!")
        elif papers and len(papers) < 3:
            st.warning(f"Need at least 3 papers (have {len(papers)}).")

    with tab2:
        results = st.session_state.get("_gap_analysis_results")
        if not results:
            st.info("Run a gap analysis first.")
            return

        st.subheader(" Research Gap Analysis Results")
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("Papers", results.get("n_papers",0))
        with col2: st.metric("Gaps", len(results.get("gaps",[])))
        with col3: st.metric("Conflicts", len(results.get("conflicting_findings",[])))
        with col4: st.metric("Hypotheses", len(results.get("unexplored_hypotheses",[])))

        novelty = results.get("novelty_scores", {})
        st.markdown(f"**Novelty Score:** {novelty.get('overall_novelty',0)}/100  {novelty.get('label','N/A')}")
        st.progress(novelty.get("overall_novelty",0)/100)

        st.subheader(" Identified Research Gaps")
        for i, gap in enumerate(results.get("gaps",[])):
            conf_pct = int(gap.get("confidence",0.5)*100)
            st.info(f"**Gap {i1}: {gap.get('label','')}** (Conf: {conf_pct}% | Cat: {gap.get('category','theoretical')})\n\n{gap.get('evidence','')[:200]}")

        st.subheader(" Conflicting Findings")
        for i, c in enumerate(results.get("conflicting_findings",[])):
            st.warning(f"**Conflict {i1}** - {c.get('source_1','')} vs {c.get('source_2','')}\n\n{c.get('finding_1','')[:100]}...\n\n{c.get('finding_2','')[:100]}...\n\n*Resolution: {c.get('resolution_needed','')}*")

        st.subheader(" Unexplored Hypotheses")
        for i, h in enumerate(results.get("unexplored_hypotheses",[])[:8]):
            conf_pct = int(h.get("confidence",0.5)*100)
            st.info(f"**H{i1}:** {h.get('hypothesis','')[:200]}\n\n*Approach: {h.get('proposed_approach','')[:150]}*")

    with tab3:
        results = st.session_state.get("_gap_analysis_results")
        if not results:
            st.info("Run a gap analysis first.")
            return
        proposal = results.get("proposal_outline", {})
        if not proposal or not proposal.get("sections"):
            st.info("No proposal generated.")
            return

        st.subheader(f" {proposal.get('title', 'Research Proposal')}")
        for section in proposal["sections"]:
            with st.expander(f"**{section['title']}**", expanded=(section==proposal["sections"][0])):
                st.markdown(f"*{section.get('prompt','')}*")
                if section.get("key_gaps"):
                    for g in section["key_gaps"]:
                        st.markdown(f"-  {g}")
                if section.get("questions"):
                    for q in section["questions"]:
                        st.markdown(f"-  {q}")
                if section.get("expected_outcomes"):
                    for o in section["expected_outcomes"]:
                        st.markdown(f"-  {o}")
                if section.get("phases"):
                    for phase in section["phases"]:
                        st.markdown(f"**{phase['phase']}** ({phase['duration']}): {phase['description']}")
                if section.get("approach"):
                    st.info(f" {section['approach']}")

        import base64
        proposal_text = json.dumps(proposal, indent=2)
        b64 = base64.b64encode(proposal_text.encode()).decode()
        st.markdown(f'<a href="data:application/json;base64,{b64}" download="research_proposal.json" style="display:inline-block;padding:10px 20px;background:#1d4ed8;color:white;border-radius:8px;text-decoration:none;font-weight:600;"> Download Proposal</a>', unsafe_allow_html=True)
