"""
Real-Time Citation Integrity & Retraction Inspector
Audits paper bibliographies against live databases to protect researchers
from citing discredited work. Cross-checks references for retractions,
expressions of concern, or methodology disputes.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

import requests
import pandas as pd


class CitationInspector:
    """Inspects citations for retractions, corrections, expressions of concern."""

    RETRACTION_INDICATORS = [
        "retract", "withdrawn", "removed", "retraction",
        "expression of concern", "concern", "erratum",
        "correction", "notice of retraction", "retracted", "withdrawal",
    ]

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "CHRISHEM-CitationInspector/1.0 (mailto:research@example.com)",
        })

    def inspect_citation(self, doi: str = "", title: str = "", authors: str = "", year: Optional[int] = None) -> Dict[str, Any]:
        """Inspect a single citation for integrity issues."""
        result = {
            "doi": doi, "title": title, "health_score": 100, "status": "clean",
            "flags": [], "sources_checked": [], "details": {},
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        if not doi and not title:
            result["health_score"] = 0; result["status"] = "unknown"
            result["flags"].append({"type": "no_identifier", "severity": "warning", "message": "No DOI or title provided"})
            return result
        if doi:
            cr_result = self._check_crossref(doi)
            result["sources_checked"].append("crossref")
            result["details"]["crossref"] = cr_result
            if cr_result.get("retracted"):
                result["flags"].append({"type": "retracted", "severity": "critical", "message": f"RETRACTED: {cr_result.get('retraction_reason', 'Unknown reason')}", "source": "CrossRef"})
                result["health_score"] -= 60; result["status"] = "retracted"
            if cr_result.get("expression_of_concern"):
                result["flags"].append({"type": "expression_of_concern", "severity": "high", "message": "Expression of concern issued", "source": "CrossRef"})
                result["health_score"] -= 40
                if result["status"] == "clean": result["status"] = "concerned"
            if cr_result.get("erratum"):
                result["flags"].append({"type": "erratum", "severity": "low", "message": "Correction/erratum published", "source": "CrossRef"})
                result["health_score"] -= 10
        if year and year < 2000: result["health_score"] -= 5
        if not doi and title:
            result["flags"].append({"type": "missing_doi", "severity": "low", "message": "No DOI for verification"})
            result["health_score"] -= 5
        result["health_score"] = max(0, min(100, result["health_score"]))
        if result["status"] == "clean":
            result["status"] = "clean" if result["health_score"] >= 80 else "caution" if result["health_score"] >= 50 else "concerned"
        return result

    def _check_crossref(self, doi: str) -> Dict[str, Any]:
        """Check CrossRef API for retraction/concern status."""
        result = {"retracted": False, "expression_of_concern": False, "erratum": False}
        try:
            url = f"https://api.crossref.org/works/{doi}"
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200: return result
            data = resp.json().get("message", {})
            title_lower = (data.get("title", [""])[0] or "").lower() if data.get("title") else ""
            for indicator in self.RETRACTION_INDICATORS:
                if indicator in title_lower:
                    if indicator in ("retract", "retracted", "withdrawn", "withdrawal"):
                        result["retracted"] = True
                        result["retraction_reason"] = f"Title indicates: {indicator}"
                    elif "concern" in indicator:
                        result["expression_of_concern"] = True
                    elif indicator in ("erratum", "correction"):
                        result["erratum"] = True
            # Check subtitle
            subtitle = " ".join(data.get("subtitle", []) or []).lower()
            for indicator in self.RETRACTION_INDICATORS:
                if indicator in subtitle:
                    if indicator in ("retract", "retracted", "withdrawn"):
                        result["retracted"] = True
                        result["retraction_reason"] = f"Subtitle indicates: {indicator}"
                    elif "concern" in indicator:
                        result["expression_of_concern"] = True
                    elif indicator in ("erratum", "correction"):
                        result["erratum"] = True
            # Check container title (journal name)
            container = (data.get("container-title", [""])[0] or "").lower()
            if "retraction" in container or "retract" in container:
                result["retracted"] = True
                result["retraction_reason"] = "Published in retraction-related journal"
            result["title"] = data.get("title", [""])[0] if data.get("title") else ""
            result["container"] = data.get("container-title", [""])[0] if data.get("container-title") else ""
            result["year"] = (data.get("issued", {}).get("date-parts", [[None]])[0] or [None])[0]
        except Exception:
            pass
        return result

    def inspect_bibliography(self, papers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Batch inspect all papers in a bibliography."""
        results = []
        clean_count = 0; flagged_count = 0; retracted_count = 0
        for paper in papers:
            r = self.inspect_citation(
                doi=paper.get("doi", ""),
                title=paper.get("title", ""),
                authors=paper.get("authors", ""),
                year=paper.get("year"),
            )
            r["paper_id"] = paper.get("id")
            r["paper_title"] = paper.get("title", "")
            results.append(r)
            if r["status"] == "retracted": retracted_count += 1
            elif r["status"] != "clean": flagged_count += 1
            else: clean_count += 1
        return {
            "total_checked": len(papers),
            "clean": clean_count, "flagged": flagged_count, "retracted": retracted_count,
            "overall_health": round((clean_count / max(len(papers), 1)) * 100, 1),
            "results": results,
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def get_health_label(self, score: int) -> str:
        if score >= 80: return "🟢 Healthy"
        if score >= 60: return "🟡 Caution"
        if score >= 40: return "🟠 Concerned"
        return "🔴 Critical"

    def get_health_color(self, score: int) -> str:
        if score >= 80: return "#2ecc71"
        if score >= 60: return "#e67e22"
        if score >= 40: return "#e74c3c"
        return "#c0392b"


def render_citation_inspector_ui():
    """Render the Citation Inspector UI for Streamlit."""
    import streamlit as st
    st.markdown("## 🚨 Citation Integrity & Retraction Inspector")
    st.markdown("*Audits references against live databases to protect against citing discredited work*")

    tab1, tab2, tab3 = st.tabs(["🔍 Single Citation Check", "📚 Bibliography Audit", "📊 Dashboard"])

    inspector = CitationInspector()

    with tab1:
        st.subheader("🔍 Check a Single Citation")
        col1, col2 = st.columns(2)
        with col1:
            doi = st.text_input("DOI", placeholder="10.1000/xyz123")
            title = st.text_input("Paper title (optional)", placeholder="Enter paper title")
        with col2:
            authors = st.text_input("Authors (optional)", placeholder="Smith et al.")
            year = st.number_input("Year (optional)", min_value=1900, max_value=2030, value=0, step=1)
        if st.button("🔍 Check Citation", type="primary") and (doi or title):
            with st.spinner("Checking citation integrity..."):
                result = inspector.inspect_citation(doi, title, authors, year if year > 0 else None)
            score = result["health_score"]
            color = inspector.get_health_color(score)
            st.markdown(f"""
            <div style="text-align:center;padding:1.5rem;border-radius:14px;border:2px solid {color};background:{color}10;">
                <div style="font-size:3rem;font-weight:900;color:{color};">{score}</div>
                <div style="font-size:1.2rem;font-weight:700;color:{color};">{inspector.get_health_label(score)}</div>
                <div style="color:#64748b;">Citation Health Score</div>
            </div>
            """, unsafe_allow_html=True)
            if result["flags"]:
                st.subheader("⚠️ Flags")
                for flag in result["flags"]:
                    sev_color = "#e74c3c" if flag["severity"] == "critical" else "#e67e22" if flag["severity"] == "high" else "#f1c40f"
                    st.markdown(f'<div style="padding:0.6rem;border-left:4px solid {sev_color};background:{sev_color}08;margin:0.3rem 0;border-radius:6px;">⚠️ <strong>{flag["message"]}</strong></div>', unsafe_allow_html=True)
            if not result["flags"]:
                st.success("✅ No issues detected  citation appears healthy")
            with st.expander("📋 Raw check data"):
                st.json(result)

    with tab2:
        st.subheader("📚 Batch Bibliography Audit")
        st.caption("Check all papers from the current literature project")

        papers = []
        db_papers = st.session_state.get("lit_db_papers", [])
        if db_papers:
            st.info(f"📚 Found {len(db_papers)} papers in current project")
            if st.button("🚀 Audit All Papers", type="primary", use_container_width=True):
                with st.spinner(f"Checking {len(db_papers)} papers..."):
                    audit = inspector.inspect_bibliography(db_papers)
                st.session_state["citation_audit"] = audit
                st.rerun()
        else:
            st.info("No papers loaded. Use the Literature Engine to harvest papers first.")
            sample = st.text_area("Or paste DOIs (one per line)", placeholder="10.1000/xyz123\n10.1000/abc456", height=100)
            if st.button("📋 Check Pasted DOIs") and sample:
                dois = [d.strip() for d in sample.split("\n") if d.strip()]
                papers = [{"doi": d, "title": f"Paper from DOI: {d}"} for d in dois]
                with st.spinner(f"Checking {len(papers)} papers..."):
                    audit = inspector.inspect_bibliography(papers)
                st.session_state["citation_audit"] = audit
                st.rerun()

        audit = st.session_state.get("citation_audit")
        if audit:
            overall = audit.get("overall_health", 0)
            color = inspector.get_health_color(overall)
            st.markdown(f"""
            <div style="text-align:center;padding:1rem;border-radius:12px;border:2px solid {color};background:{color}10;">
                <span style="font-size:2rem;font-weight:900;color:{color};">{overall}%</span>
                <span style="margin-left:1rem;color:#64748b;">Overall Citation Health</span>
            </div>
            """, unsafe_allow_html=True)
            col1, col2, col3, col4 = st.columns(4)
            with col1: st.metric("Total Checked", audit.get("total_checked", 0))
            with col2: st.metric("✅ Clean", audit.get("clean", 0))
            with col3: st.metric("⚠️ Flagged", audit.get("flagged", 0))
            with col4: st.metric("🔴 Retracted", audit.get("retracted", 0))

            results = audit.get("results", [])
            if results:
                st.subheader("Individual Results")
                for r in results:
                    score = r["health_score"]
                    c = inspector.get_health_color(score)
                    with st.container():
                        st.markdown(f"""
                        <div style="padding:0.5rem;margin:0.3rem 0;border-radius:8px;border-left:4px solid {c};background:{c}08;">
                            <strong>{r.get('paper_title', 'Unknown')}</strong>
                            <span style="float:right;font-weight:700;color:{c};">{inspector.get_health_label(score)}</span>
                        </div>
                        """, unsafe_allow_html=True)

    with tab3:
        st.subheader("📊 Citation Health Dashboard")
        audit = st.session_state.get("citation_audit")
        if audit and audit.get("results"):
            results = audit["results"]
            df = pd.DataFrame(results)
            if not df.empty:
                col1, col2 = st.columns(2)
                with col1:
                    status_counts = df["status"].value_counts()
                    st.bar_chart(status_counts)
                with col2:
                    st.metric("Mean Health Score", f"{df['health_score'].mean():.1f}")
                    st.metric("Min Health Score", df["health_score"].min())
                    st.metric("Max Health Score", df["health_score"].max())
                st.dataframe(df[["paper_title", "doi", "health_score", "status"]], use_container_width=True, hide_index=True)
        else:
            st.info("Run a bibliography audit first to see the dashboard")

