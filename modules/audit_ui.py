"""
Audit & Compliance Hub — UI Rendering Module
==============================================
Renders the 5th tab "Audit & Compliance Hub" with 4 sub-tabs:
  1. 🔍 Forensic Audit        — Professor-facing forensic view (password-protected)
  2. 🎯 Plagiarism & AI Check — Multi-vector scoring dashboard
  3. ✍️ Optimization Studio   — Student-facing text improvement tools
  4. 📤 Export Audit Report   — Downloadable audit reports & clean exports
"""
from __future__ import annotations

import base64
import hmac
import io
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.audit_engine import (
    AuditOrchestrator,
    EnterpriseDataEngine,
    ProductionLinguisticProcessor,
    TextHumanizer,
    UniversalFileReader,
    get_audit_orchestrator,
)
from modules import similarity as similarity_engine
from modules.accounts import AccountError
from modules.billing import AUDIT_CHECK, EMAIL_REPORT, UNLIMITED
from modules.email_reports import (
    Attachment,
    AuditSummary,
    active_transport,
    configuration_hint,
    send_audit_report,
)
from modules.session_auth import consume as consume_feature
from modules.session_auth import entitlement
from modules.ui_components import section_header

# ─── Constants ────────────────────────────────────────────────────────
SUPPORTED_FORMATS = ", ".join(sorted(UniversalFileReader.SUPPORTED_EXTENSIONS))


def forensic_password() -> str:
    """Password guarding the professor-facing forensic view.

    Read from the environment: the previous literal in this file was public in
    the repository, so anyone who read the source could unlock a professor's
    audit trail. An unset variable keeps the view locked rather than falling
    back to a shared default.
    """
    return os.environ.get("FORENSIC_MASTER_PASSWORD", "")


def render_audit_tab(db, project_id: int):
    """
    Main entry point — renders the entire Audit & Compliance Hub tab.
    Called from the Literature Engine page as the 5th tab.
    """
    section_header("🛡️ Audit & Compliance Hub")
    st.caption(
        "Multi-vector forensic text analysis, blockchain-verified audit trails, "
        "AI-content detection, and advanced humanization — all in one hub."
    )

    # Initialize orchestrator for this project
    orchestrator = get_audit_orchestrator(project_id)

    # ─── Retrieve project data for auditing ─────────────────────────
    report_sections = db.get_report_sections(project_id)
    bibliography = db.get_bibliography(project_id)

    # ─── Sub-tabs ───────────────────────────────────────────────────
    subtab1, subtab2, subtab3, subtab4 = st.tabs([
        "🔍 Forensic Audit",
        "🎯 Plagiarism & AI Check",
        "✍️ Optimization Studio",
        "📤 Export Audit Report",
    ])

    # ═════════════════════════════════════════════════════════════════
    # SUB-TAB 1: FORENSIC AUDIT (Password-Protected)
    # ═════════════════════════════════════════════════════════════════
    with subtab1:
        render_forensic_audit(orchestrator, db, project_id, report_sections)

    # ═════════════════════════════════════════════════════════════════
    # SUB-TAB 2: PLAGIARISM & AI CHECK
    # ═════════════════════════════════════════════════════════════════
    with subtab2:
        render_plagiarism_ai_check(orchestrator, report_sections, bibliography)

    # ═════════════════════════════════════════════════════════════════
    # SUB-TAB 3: OPTIMIZATION STUDIO
    # ═════════════════════════════════════════════════════════════════
    with subtab3:
        render_optimization_studio(orchestrator)

    # ═════════════════════════════════════════════════════════════════
    # SUB-TAB 4: EXPORT AUDIT REPORT
    # ═════════════════════════════════════════════════════════════════
    with subtab4:
        render_export_audit(orchestrator, report_sections, bibliography)


# ═══════════════════════════════════════════════════════════════════════
# SUB-TAB 1: FORENSIC AUDIT
# ═══════════════════════════════════════════════════════════════════════
def render_forensic_audit(
    orchestrator: AuditOrchestrator,
    db,
    project_id: int,
    report_sections: List[Dict],
):
    """Professor-facing forensic dashboard with password protection."""
    st.subheader("🔍 Forensic Audit Dashboard")
    st.caption(
        "Professor-facing view with full cryptographic audit trail, "
        "timeline playback, and writing pattern analysis."
    )

    # ─── Password Gate ──────────────────────────────────────────────
    if "forensic_unlocked" not in st.session_state:
        st.session_state["forensic_unlocked"] = False

    if not st.session_state["forensic_unlocked"]:
        col1, col2 = st.columns([2, 1])
        with col1:
            pwd = st.text_input(
                "Master Password",
                type="password",
                placeholder="Enter master password to unlock forensic view",
                key="forensic_pwd",
            )
        with col2:
            st.markdown("")
            st.markdown("")
            if st.button("🔓 Unlock", type="primary", use_container_width=True):
                secret = forensic_password()
                if not secret:
                    st.error(
                        "❌ `FORENSIC_MASTER_PASSWORD` is not configured on this "
                        "deployment, so the forensic view stays locked."
                    )
                elif hmac.compare_digest(pwd or "", secret):
                    st.session_state["forensic_unlocked"] = True
                    st.success("✅ Forensic view unlocked!")
                    st.rerun()
                else:
                    st.error("❌ Incorrect password. Access denied.")

        st.warning(
            "🔒 **Forensic Audit is locked.** This section contains sensitive "
            "cryptographic audit trails, keystroke-level diff analysis, and "
            "writing pattern forensics. Only authorized professors/instructors "
            "should access this view."
        )
        return

    # ─── Unlocked: Full forensic view ───────────────────────────────
    st.success("✅ **Forensic Mode Active** — All audit trails are visible.")

    ledger = orchestrator.ledger

    # ─── Ledger Overview ────────────────────────────────────────────
    st.markdown("### 📊 Audit Ledger Overview")
    counts, records = ledger.get_admin_metrics(project_id)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📁 Sessions", counts[0])
    with col2:
        st.metric("📝 Total Records", counts[1])
    with col3:
        st.metric("👤 Students", counts[2])

    # ─── Blockchain Verification ────────────────────────────────────
    st.markdown("### 🔗 Blockchain Chain Verification")
    st.caption("Cryptographically verify the integrity of the entire audit trail.")

    session_id_input = st.text_input(
        "Session ID to verify",
        placeholder="Paste a session ID or leave blank for latest",
        key="forensic_session",
    )

    if st.button("🔗 Verify Chain Integrity", type="primary", use_container_width=True):
        session_to_check = session_id_input.strip() or orchestrator.session_id
        if session_to_check:
            with st.spinner("🔍 Verifying blockchain integrity..."):
                is_valid, result = ledger.fetch_and_verify_chain(session_to_check)

            if is_valid:
                st.success("✅ **Blockchain VERIFIED** — No tampering detected.")
                st.info(f"📊 Timeline contains {len(result)} events.")

                # Show timeline
                with st.expander("📜 View Full Timeline", expanded=True):
                    timeline_df = pd.DataFrame([
                        {
                            "Time": datetime.fromtimestamp(e["timestamp"]).strftime("%H:%M:%S"),
                            "Event": e["event_type"],
                            "Student": e["student_id"],
                            "Text Preview": e["text"][:100] + "..." if len(e.get("text", "")) > 100 else e.get("text", ""),
                        }
                        for e in result
                    ])
                    st.dataframe(timeline_df, use_container_width=True, hide_index=True)

                    # Timeline visualization
                    if len(result) > 1:
                        fig = px.scatter(
                            timeline_df,
                            x=range(len(timeline_df)),
                            y="Event",
                            color="Student",
                            title="Audit Event Timeline",
                            labels={"x": "Event Sequence", "y": "Event Type"},
                            size=[20] * len(timeline_df),
                        )
                        fig.update_layout(showlegend=True, height=300)
                        st.plotly_chart(fig, use_container_width=True)
            else:
                st.error(f"❌ **Chain Verification FAILED:** {result}")
        else:
            st.warning("No session ID provided.")

    # ─── WPM Speed Analysis ─────────────────────────────────────────
    st.markdown("### ⏱️ Writing Speed Analysis (WPM)")
    st.caption("Words-per-minute analysis based on audit trail timestamps.")

    if st.button("📊 Calculate WPM Metrics", use_container_width=True):
        session_wpm = session_id_input.strip() or orchestrator.session_id
        timeline = ledger.get_session_timeline(session_wpm)

        if timeline and len(timeline) > 1:
            # Calculate time between events and word counts
            wpm_data = []
            for i in range(1, len(timeline)):
                prev = timeline[i - 1]
                curr = timeline[i]
                time_diff = curr["timestamp"] - prev["timestamp"]
                if time_diff > 0 and time_diff < 300:  # Max 5 min gap
                    prev_words = len(prev.get("text", "").split())
                    curr_words = len(curr.get("text", "").split())
                    words_added = max(0, curr_words - prev_words)
                    if words_added > 0:
                        wpm = (words_added / time_diff) * 60
                        wpm_data.append({
                            "Time": datetime.fromtimestamp(curr["timestamp"]).strftime("%H:%M:%S"),
                            "Words Added": words_added,
                            "WPM": round(wpm, 1),
                            "Event": curr["event_type"],
                        })

            if wpm_data:
                wpm_df = pd.DataFrame(wpm_data)
                avg_wpm = wpm_df["WPM"].mean()
                max_wpm = wpm_df["WPM"].max()

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📊 Avg WPM", f"{avg_wpm:.1f}")
                with col2:
                    st.metric("🚀 Max WPM", f"{max_wpm:.1f}")
                with col3:
                    st.metric("📝 Data Points", len(wpm_data))

                fig = px.line(
                    wpm_df, x="Time", y="WPM",
                    title="Writing Speed Over Time (WPM)",
                    markers=True,
                )
                fig.add_hline(y=avg_wpm, line_dash="dash", line_color="red",
                              annotation_text=f"Avg: {avg_wpm:.1f} WPM")
                st.plotly_chart(fig, use_container_width=True)

                st.dataframe(wpm_df, use_container_width=True, hide_index=True)

                # Flag anomalies
                anomalies = wpm_df[wpm_df["WPM"] > 120]
                if not anomalies.empty:
                    st.warning(
                        f"⚠️ **{len(anomalies)} high-speed writing events detected "
                        f"(>120 WPM).** Possible copy-paste activity."
                    )
            else:
                st.info("Insufficient data for WPM analysis.")
        else:
            st.info("Not enough timeline data for WPM analysis.")

    # ─── Diff Analysis ──────────────────────────────────────────────
    st.markdown("### 📝 Keystroke-Level Diff Analysis")
    st.caption("Compare two text versions at the word level.")

    col1, col2 = st.columns(2)
    with col1:
        text_a = st.text_area(
            "Original Text (Version A)",
            height=150,
            placeholder="Paste the original text here...",
            key="forensic_diff_a",
        )
    with col2:
        text_b = st.text_area(
            "Modified Text (Version B)",
            height=150,
            placeholder="Paste the modified text here...",
            key="forensic_diff_b",
        )

    if st.button("🔍 Generate Diff", use_container_width=True) and text_a and text_b:
        timeline = orchestrator.create_forensic_timeline(text_a, text_b)
        if timeline:
            st.info(f"**{len(timeline)} word-level changes detected.**")

            diff_df = pd.DataFrame(timeline)
            st.dataframe(diff_df, use_container_width=True, hide_index=True)

            # Summary
            added = sum(1 for e in timeline if e["event_type"] == "WORD_ADDED")
            removed = sum(1 for e in timeline if e["event_type"] == "WORD_REMOVED")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("➕ Words Added", added)
            with col2:
                st.metric("➖ Words Removed", removed)
        else:
            st.info("No changes detected between the two texts.")

    # ─── Lock button ────────────────────────────────────────────────
    st.markdown("---")
    if st.button("🔒 Lock Forensic View", type="secondary", use_container_width=True):
        st.session_state["forensic_unlocked"] = False
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════
# SUB-TAB 2: PLAGIARISM & AI CHECK
# ═══════════════════════════════════════════════════════════════════════
def render_plagiarism_ai_check(
    orchestrator: AuditOrchestrator,
    report_sections: List[Dict],
    bibliography: List[Dict],
):
    """Multi-vector plagiarism and AI-content scoring dashboard."""
    st.subheader("🎯 Plagiarism & AI Content Detection")
    st.caption(
        "Multi-vector forensic analysis using statistical profiling, "
        "AI pattern recognition, and n-gram cross-referencing."
    )

    # ─── Source Selection ───────────────────────────────────────────
    source_option = st.radio(
        "Select text source to audit",
        options=[
            "📄 Report Sections (from Report Builder)",
            "✏️ Paste Custom Text (Unlimited)",
            "📁 Upload File (All Formats Supported)",
        ],
        horizontal=True,
        key="ai_source_option",
    )

    text_to_audit = ""
    source_label = ""

    if source_option == "📄 Report Sections (from Report Builder)":
        source_label = "Report Sections"

        if not report_sections:
            st.info("No report sections found. Write content in the Report Builder tab first.")
            return

        section_options = {
            s["id"]: f"{s['section_title']} ({len(s.get('content', ''))} chars)"
            for s in report_sections if s.get("content", "").strip()
        }
        if not section_options:
            st.info("Report sections are empty. Add content in the Report Builder first.")
            return

        selected_section_id = st.selectbox(
            "Choose a section to audit",
            options=list(section_options.keys()),
            format_func=lambda x: section_options.get(x, "Unknown"),
            key="ai_section_select",
        )
        selected_section = next((s for s in report_sections if s["id"] == selected_section_id), None)
        if selected_section:
            text_to_audit = selected_section.get("content", "")
            source_label = f"Section: {selected_section['section_title']}"

    elif source_option == "✏️ Paste Custom Text (Unlimited)":
        source_label = "Custom Text"
        text_to_audit = st.text_area(
            "Paste your text below (no limit)",
            height=300,
            placeholder="Paste any text for plagiarism and AI-content analysis...",
            key="ai_custom_text",
        )

    else:  # Upload file
        source_label = "Uploaded File"
        uploaded_file = st.file_uploader(
            "Upload a file for auditing",
            type=list(UniversalFileReader.SUPPORTED_EXTENSIONS),
            key="ai_file_upload",
            help=f"Supported formats: {SUPPORTED_FORMATS}",
        )

        if uploaded_file is not None:
            with st.spinner("📖 Reading file..."):
                file_bytes = uploaded_file.read()
                extracted_text, error = UniversalFileReader.read_file(file_bytes, uploaded_file.name)

            if error:
                st.error(f"❌ {error}")
            else:
                text_to_audit = extracted_text
                st.success(f"✅ Successfully read '{uploaded_file.name}' ({len(text_to_audit):,} chars)")

                with st.expander("📖 Preview extracted text", expanded=False):
                    st.text(text_to_audit[:2000] + ("..." if len(text_to_audit) > 2000 else ""))

    # ─── Run Audit ──────────────────────────────────────────────────
    if text_to_audit and text_to_audit.strip():
        # Build reference texts from bibliography
        reference_texts = []
        if bibliography:
            for paper in bibliography:
                combined = " ".join(filter(None, [
                    paper.get("title", ""),
                    paper.get("abstract", ""),
                    paper.get("user_notes", ""),
                    paper.get("user_findings", ""),
                ])).strip()
                if len(combined) > 50:
                    reference_texts.append(combined)

        st.markdown("---")
        col1, col2 = st.columns([1, 3])
        with col1:
            run_audit = st.button(
                "🚀 Run Full Audit",
                type="primary",
                use_container_width=True,
            )
        with col2:
            if reference_texts:
                st.info(f"📚 {len(reference_texts)} reference texts available for plagiarism check.")
            else:
                st.info("📚 No bibliography references available. AI-check only (no plagiarism cross-ref).")

        allowance = entitlement(AUDIT_CHECK)
        if not allowance.allowed:
            st.warning(allowance.reason)
            st.page_link("pages/48_💳_Pricing.py", label="See plans", icon="💳")
        elif allowance.limit != UNLIMITED:
            st.caption(
                f"🎟️ {allowance.remaining} of {allowance.limit} audit checks left this month."
            )

        if run_audit:
            try:
                consume_feature(AUDIT_CHECK)
            except AccountError as exc:
                st.warning(str(exc))
                st.stop()

            with st.spinner("🔍 Running multi-vector audit..."):
                results = orchestrator.audit_text(
                    text=text_to_audit,
                    student_id="researcher",
                    reference_texts=reference_texts,
                )

            if "error" in results:
                st.error(f"❌ {results['error']}")
            else:
                st.success("✅ Audit complete!")

                # ─── Display Results ────────────────────────────────
                display_audit_results(results, source_label)

                corpus = build_corpus(bibliography, report_sections, source_label)
                render_similarity_panel(text_to_audit, corpus)

                # Store in session state for export
                st.session_state["_last_audit_results"] = results
                st.session_state["_last_audit_text"] = text_to_audit
                st.session_state["_last_audit_source"] = source_label

    else:
        if source_option != "📄 Report Sections (from Report Builder)":
            st.info("👆 Paste text or upload a file above, then click 'Run Full Audit'.")


def build_corpus(
    bibliography: List[Dict],
    report_sections: List[Dict],
    exclude_label: str = "",
) -> List[similarity_engine.Source]:
    """Everything in this project the audited text can legitimately be compared to."""
    sources: List[similarity_engine.Source] = []
    for paper in bibliography or []:
        text = " ".join(
            filter(
                None,
                [
                    paper.get("abstract", ""),
                    paper.get("user_notes", ""),
                    paper.get("user_findings", ""),
                ],
            )
        ).strip()
        if len(text) > 50:
            sources.append(
                similarity_engine.Source(
                    id=f"ref-{paper.get('id', len(sources))}",
                    title=(paper.get("title") or "Untitled reference")[:60],
                    text=text,
                )
            )
    for section in report_sections or []:
        title = section.get("section_title", "Section")
        content = (section.get("content") or "").strip()
        # Comparing a section with itself would report 100% and mean nothing.
        if len(content) > 50 and title not in exclude_label:
            sources.append(
                similarity_engine.Source(
                    id=f"sec-{section.get('id', len(sources))}",
                    title=f"§ {title}"[:60],
                    text=content,
                )
            )
    return sources


def render_similarity_panel(
    text: str,
    sources: List[similarity_engine.Source],
) -> Dict[str, Any]:
    """Corpus similarity and citation coverage, with the scope stated up front."""
    st.markdown("---")
    st.markdown("### 🧬 Source Similarity & Citation Coverage")
    st.caption(similarity_engine.SCOPE_NOTE)

    report = similarity_engine.compare(text, sources)
    citations = similarity_engine.citation_coverage(text)

    col1, col2, col3 = st.columns(3)
    col1.metric("Corpus similarity", f"{report.overall_similarity:.1f}%")
    col2.metric("Citation coverage", f"{citations.coverage:.1f}%", citations.verdict)
    col3.metric("Uncited claims", len(citations.uncited))

    if not sources:
        st.info(
            "No comparable sources in this project yet — add references with "
            "abstracts or notes in the Literature Engine to enable matching."
        )
    else:
        labels, source_labels, matrix = similarity_engine.heatmap(text, sources)
        if matrix:
            figure = px.imshow(
                matrix,
                x=labels,
                y=source_labels,
                color_continuous_scale="Reds",
                labels={"x": "Document position (words)", "y": "Source", "color": "% overlap"},
                aspect="auto",
            )
            figure.update_layout(height=90 + 34 * len(source_labels), margin=dict(l=8, r=8, t=28, b=8))
            st.plotly_chart(figure, use_container_width=True)

        passages = report.passages(limit=10)
        if passages:
            with st.expander(f"🔎 {len(passages)} matching passages", expanded=False):
                for passage in passages:
                    st.markdown(
                        f"**{passage.source_title}** · words "
                        f"{passage.start_word + 1}–{passage.end_word}"
                    )
                    st.caption(f"“{passage.text[:300]}”")

    if citations.uncited:
        with st.expander(f"📚 {len(citations.uncited)} claims without a citation", expanded=False):
            for sentence in citations.uncited[:20]:
                st.markdown(f"- {sentence.text[:240]}")

    summary = {
        "similarity": report.overall_similarity,
        "citation_coverage": citations.coverage,
        "uncited_claims": len(citations.uncited),
        "top_source": report.top_source.source_title if report.top_source else None,
    }
    st.session_state["_last_similarity"] = summary
    return summary


def display_audit_results(results: Dict[str, Any], source_label: str = "Text"):
    """Display audit results in a structured dashboard."""

    # ─── Overview Scores ────────────────────────────────────────────
    scores = results.get("composite_scores", {})
    stats = results.get("statistical_profile", {})
    ai_det = results.get("ai_detection", {})

    st.markdown(f"### 📊 Audit Results for: {source_label}")

    # Risk level gauge
    risk = scores.get("overall_risk", 0)
    if risk < 30:
        risk_label = "🟢 Low Risk"
        risk_color = "#2ecc71"
    elif risk < 60:
        risk_label = "🟡 Medium Risk"
        risk_color = "#f39c12"
    else:
        risk_label = "🔴 High Risk"
        risk_color = "#e74c3c"

    st.markdown(
        f"<div style='text-align:center;padding:1rem;border-radius:12px;"
        f"background:{risk_color}22;border:2px solid {risk_color};'>"
        f"<h2 style='margin:0;color:{risk_color};'>{risk_label}</h2>"
        f"<p style='margin:0;font-size:2rem;font-weight:800;color:{risk_color};'>{risk}%</p>"
        f"<p style='margin:0;color:#64748b;'>Overall Risk Score</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ─── Score Cards ────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        ai_score = scores.get("ai_content_score", 0)
        st.metric(
            "🤖 AI Content Score",
            f"{ai_score}%",
            delta="High AI" if ai_score > 60 else "Low AI" if ai_score < 30 else "Moderate",
            delta_color="inverse" if ai_score > 60 else "normal",
        )
    with col2:
        auth_score = scores.get("authenticity_score", 0)
        st.metric(
            "✍️ Authenticity Score",
            f"{auth_score}%",
            delta="Human-like" if auth_score > 60 else "Synthetic",
        )
    with col3:
        plag_score = scores.get("plagiarism_score", 0)
        st.metric(
            "📋 Plagiarism Score",
            f"{plag_score}%",
            delta="High" if plag_score > 50 else "Low",
            delta_color="inverse",
        )
    with col4:
        pattern_count = ai_det.get("pattern_count", 0)
        st.metric("🔍 AI Pattern Matches", pattern_count)

    # ─── Statistical Profile ────────────────────────────────────────
    st.markdown("### 📈 Statistical Profile")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Words", stats.get("total_words", 0))
    with col2:
        st.metric("Sentences", stats.get("sentences", 0))
    with col3:
        st.metric("Avg Sentence Length", f'{stats.get("avg_sentence_length", 0)} words')

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Burstiness",
            stats.get("burstiness", 0),
            help="Std dev of sentence lengths. Higher = more natural variation.",
        )
    with col2:
        st.metric(
            "Perplexity",
            f'{stats.get("perplexity", 0)}%',
            help="Unique word ratio. 40-70% = typical human range.",
        )
    with col3:
        st.metric(
            "Vocabulary Richness",
            f'{stats.get("vocabulary_richness", 0):.3f}',
            help="Type-token ratio. Higher = richer vocabulary.",
        )

    # ─── Visualizations ─────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        # Score radar chart
        categories = ["AI Content", "Authenticity", "Plagiarism", "Pattern Match"]
        values = [
            scores.get("ai_content_score", 0),
            scores.get("authenticity_score", 0),
            scores.get("plagiarism_score", 0),
            min(100, ai_det.get("pattern_count", 0) * 20),
        ]
        fig = go.Figure(data=go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name="Scores",
            line_color="#1d4ed8",
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=False,
            height=350,
            title="Multi-Vector Score Profile",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Burstiness gauge style
        burst = stats.get("burstiness", 0)
        perplex = stats.get("perplexity", 50)

        fig = go.Figure()
        fig.add_trace(go.Indicator(
            mode="gauge+number+delta",
            value=burst,
            title={"text": "Burstiness (Sentence Length Variation)"},
            delta={"reference": 3.5, "increasing": {"color": "green"}, "decreasing": {"color": "red"}},
            gauge={
                "axis": {"range": [0, max(10, burst * 1.5)]},
                "bar": {"color": "#1d4ed8"},
                # plotly rejects #RRGGBBAA, so translucent bands use rgba().
                "steps": [
                    {"range": [0, 2], "color": "rgba(231, 76, 60, 0.13)"},
                    {"range": [2, 5], "color": "rgba(46, 204, 113, 0.13)"},
                    {"range": [5, max(10, burst * 1.5)], "color": "rgba(243, 156, 18, 0.13)"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 3.5,
                },
            },
        ))
        fig.update_layout(height=350, title="Burstiness Gauge (Target: 3.5+)")
        st.plotly_chart(fig, use_container_width=True)

    # ─── AI Pattern Details ─────────────────────────────────────────
    if ai_det.get("matches"):
        with st.expander("🔍 AI Pattern Matches Found", expanded=ai_det["pattern_count"] > 5):
            st.warning(f"**{ai_det['pattern_count']} AI-typical phrases detected.**")
            matches_df = pd.DataFrame({"Matched Phrase": ai_det["matches"][:50]})
            st.dataframe(matches_df, use_container_width=True, hide_index=True)

    # ─── Plagiarism Details ─────────────────────────────────────────
    plag = results.get("plagiarism_check")
    if plag and plag.get("total_ngrams", 0) > 0:
        with st.expander(
            "📋 N-Gram Plagiarism Cross-Reference",
            expanded=plag.get("overall_similarity", 0) > 30,
        ):
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Overall Similarity", f'{plag["overall_similarity"]}%')
            with col2:
                st.metric("Matching N-Grams", plag["matched_count"])

            if plag.get("ngram_matches"):
                ngram_df = pd.DataFrame({"Matching N-Grams": plag["ngram_matches"][:50]})
                st.dataframe(ngram_df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════
# SUB-TAB 3: OPTIMIZATION STUDIO
# ═══════════════════════════════════════════════════════════════════════
def render_optimization_studio(orchestrator: AuditOrchestrator):
    """Student-facing text optimization and humanization tools."""
    st.subheader("✍️ Optimization Studio")
    st.caption(
        "Improve your text with structural cadence adjustments, "
        "burstiness optimization, and advanced humanization."
    )

    # ─── Text Input ─────────────────────────────────────────────────
    source_option = st.radio(
        "Select text source",
        options=[
            "✏️ Paste Text (Unlimited)",
            "📁 Upload File",
        ],
        horizontal=True,
        key="opt_source_option",
    )

    text_to_optimize = ""

    if source_option == "✏️ Paste Text (Unlimited)":
        text_to_optimize = st.text_area(
            "Paste your text below",
            height=250,
            placeholder="Paste the text you want to optimize and humanize...",
            key="opt_custom_text",
        )
    else:
        uploaded_file = st.file_uploader(
            "Upload a file for optimization",
            type=list(UniversalFileReader.SUPPORTED_EXTENSIONS),
            key="opt_file_upload",
            help=f"Supported: {SUPPORTED_FORMATS}",
        )
        if uploaded_file is not None:
            with st.spinner("📖 Reading file..."):
                file_bytes = uploaded_file.read()
                extracted_text, error = UniversalFileReader.read_file(file_bytes, uploaded_file.name)
            if error:
                st.error(f"❌ {error}")
            else:
                text_to_optimize = extracted_text
                st.success(f"✅ Loaded ({len(text_to_optimize):,} chars)")

    if not text_to_optimize or not text_to_optimize.strip():
        st.info("👆 Paste text or upload a file to begin optimization.")
        return

    # ─── Original Stats ─────────────────────────────────────────────
    original_stats = orchestrator.processor.run_statistical_profile(text_to_optimize)

    with st.expander("📊 Original Text Profile", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Words", original_stats.get("total_words", 0))
        with col2:
            st.metric("Sentences", original_stats.get("sentences", 0))
        with col3:
            st.metric("Burstiness", original_stats.get("burstiness", 0))
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Perplexity", f'{original_stats.get("perplexity", 0)}%')
        with col2:
            st.metric("Avg Sent. Length", original_stats.get("avg_sentence_length", 0))
        with col3:
            st.metric("Vocab Richness", f'{original_stats.get("vocabulary_richness", 0):.3f}')

    # ─── Optimization Mode ──────────────────────────────────────────
    st.markdown("### ⚙️ Optimization Settings")

    col1, col2 = st.columns(2)
    with col1:
        optimization_mode = st.selectbox(
            "Optimization Mode",
            options=[
                "💡 Light — Fluid Cadence Only",
                "⚖️ Balanced — Cadence + Burstiness",
                "🔧 Deep — Full Humanization Pipeline",
            ],
            index=0,
            key="opt_mode",
            help="Deep mode applies all transformations for maximum human-likeness.",
        )
    with col2:
        # Only show advanced settings for Deep mode
        show_advanced = "Deep" in optimization_mode
        target_burstiness = st.slider(
            "Target Burstiness",
            min_value=1.0, max_value=10.0, value=3.5, step=0.1,
            help="Higher = more varied sentence lengths (more natural).",
            key="opt_burstiness",
        )
        target_perplexity = st.slider(
            "Target Perplexity (%)",
            min_value=30, max_value=90, value=65, step=1,
            help="Unique word ratio target. 40-70% is typical for human writing.",
            key="opt_perplexity",
        )

    mode_map = {
        "💡 Light — Fluid Cadence Only": "light",
        "⚖️ Balanced — Cadence + Burstiness": "balanced",
        "🔧 Deep — Full Humanization Pipeline": "deep",
    }

    # ─── Run Optimization ───────────────────────────────────────────
    if st.button("🚀 Run Optimization", type="primary", use_container_width=True):
        with st.spinner("✍️ Optimizing text..."):
            result = orchestrator.optimize_text(
                text=text_to_optimize,
                mode=mode_map[optimization_mode],
                target_burstiness=target_burstiness,
                target_perplexity=target_perplexity,
            )

        if "error" in result:
            st.error(f"❌ {result['error']}")
        else:
            st.success("✅ Optimization complete!")

            optimized_text = result["optimized_text"]
            orig_stats = result["original_stats"]
            opt_stats = result["optimized_stats"]
            changes = result["changes"]

            # ─── Comparison Metrics ─────────────────────────────────
            st.markdown("### 📊 Before vs After")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "Burstiness",
                    f"{opt_stats['burstiness']}",
                    delta=f"{changes['burstiness_delta']:+.2f}",
                    delta_color="off",
                )
            with col2:
                st.metric(
                    "Perplexity",
                    f"{opt_stats['perplexity']}%",
                    delta=f"{changes['perplexity_delta']:+.2f}%",
                    delta_color="off",
                )
            with col3:
                st.metric(
                    "Sentences",
                    opt_stats["sentences"],
                    delta=f"{changes['sentence_delta']:+d}",
                    delta_color="off",
                )

            # ─── Side-by-Side ───────────────────────────────────────
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Original Text**")
                st.text_area(
                    "",
                    value=text_to_optimize[:2000] + ("..." if len(text_to_optimize) > 2000 else ""),
                    height=300,
                    key="opt_original_display",
                    label_visibility="collapsed",
                )
            with col2:
                st.markdown("**Optimized Text**")
                st.text_area(
                    "",
                    value=optimized_text[:2000] + ("..." if len(optimized_text) > 2000 else ""),
                    height=300,
                    key="opt_optimized_display",
                    label_visibility="collapsed",
                )

            # ─── Full Text with Clean Export ────────────────────────
            st.markdown("### 📥 Clean Export")
            st.caption(
                "The export below is **completely clean** — all steganographic "
                "markers, processing codes, and layout markers have been stripped."
            )

            # Clean for export
            clean_text = orchestrator.processor.clean_for_export(optimized_text)

            with st.expander("📖 View Full Optimized Text", expanded=True):
                st.text_area("", value=clean_text, height=250, label_visibility="collapsed", key="opt_clean_output")

            # Download buttons
            col1, col2 = st.columns(2)
            with col1:
                txt_bytes = clean_text.encode("utf-8")
                b64 = base64.b64encode(txt_bytes).decode()
                st.markdown(
                    f'<a href="data:text/plain;base64,{b64}" '
                    f'download="optimized_text_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt" '
                    f'style="display:inline-block;padding:10px 20px;background:#1d4ed8;color:white;'
                    f'border-radius:8px;text-decoration:none;font-weight:600;">📥 Download TXT</a>',
                    unsafe_allow_html=True,
                )
            with col2:
                # Copy to clipboard button
                # Pre-escape backticks and ${} for safe JavaScript template literal use
                escaped_js = clean_text[:50000].replace("`", "\\`").replace("${", "\\${")
                clipboard_html = (
                    '<button onclick="navigator.clipboard.writeText(`' + escaped_js + '`).then(() => {'
                    "this.innerHTML='✅ Copied!';"
                    "setTimeout(()=>this.innerHTML='📋 Copy to Clipboard', 2000);"
                    '})"'
                    ' style="display:inline-block;padding:10px 20px;background:#059669;color:white;'
                    'border:none;border-radius:8px;cursor:pointer;font-weight:600;">'
                    '📋 Copy to Clipboard</button>'
                )
                st.markdown(clipboard_html, unsafe_allow_html=True)

            # ─── Store for export ───────────────────────────────────
            st.session_state["_last_optimized_text"] = clean_text
            st.session_state["_last_optimized_stats"] = {
                "original": orig_stats,
                "optimized": opt_stats,
                "mode": optimization_mode,
            }


# ═══════════════════════════════════════════════════════════════════════
# SUB-TAB 4: EXPORT AUDIT REPORT
# ═══════════════════════════════════════════════════════════════════════
def render_email_delivery(export_content: str) -> None:
    """Offer emailing the report, or say plainly why it is unavailable."""
    with st.expander("✉️ Email this report", expanded=False):
        transport = active_transport()
        if transport == "none":
            st.info(
                "Email delivery is not configured on this deployment. "
                f"{configuration_hint()} You can still download the report above."
            )
            return

        allowance = entitlement(EMAIL_REPORT)
        if not allowance.allowed:
            st.warning(allowance.reason)
            st.page_link("pages/48_💳_Pricing.py", label="See plans", icon="💳")
            return
        if allowance.limit != UNLIMITED:
            st.caption(f"🎟️ {allowance.remaining} of {allowance.limit} emailed reports left this month.")

        recipient = st.text_input("Send to", key="audit_email_to", placeholder="supervisor@university.edu")
        attach = st.checkbox("Attach the report as a .txt file", value=True, key="audit_email_attach")
        if not st.button("Send report", type="primary", key="audit_email_send"):
            return

        similarity_summary = st.session_state.get("_last_similarity", {})
        scores = (st.session_state.get("_last_audit_results") or {}).get("composite_scores", {})
        summary = AuditSummary(
            document=st.session_state.get("_last_audit_source", "Audit report"),
            authenticity=scores.get("authenticity_score"),
            ai_content=scores.get("ai_content_score"),
            similarity=similarity_summary.get("similarity"),
            citation_coverage=similarity_summary.get("citation_coverage"),
            findings=(
                [f"{similarity_summary['uncited_claims']} claims carry no citation."]
                if similarity_summary.get("uncited_claims")
                else []
            ),
        )
        attachments = (
            [Attachment("audit_report.txt", export_content.encode("utf-8"), "text/plain")]
            if attach
            else []
        )
        try:
            consume_feature(EMAIL_REPORT)
        except AccountError as exc:
            st.warning(str(exc))
            return

        with st.spinner("Sending…"):
            result = send_audit_report([recipient], summary, attachments)
        if result.sent:
            st.success(f"✅ Sent to {recipient} via {result.transport}.")
        else:
            st.error(f"❌ Not sent: {result.detail}")


def render_export_audit(
    orchestrator: AuditOrchestrator,
    report_sections: List[Dict],
    bibliography: List[Dict],
):
    """Export audit reports, clean text, and comprehensive compliance docs."""
    st.subheader("📤 Export Audit & Compliance Report")
    st.caption(
        "Download comprehensive audit reports, clean optimized text, "
        "and blockchain verification certificates."
    )

    export_type = st.radio(
        "Select export type",
        options=[
            "📋 Full Audit Report (all sections)",
            "🔗 Blockchain Verification Certificate",
            "📥 Latest Optimized Text (Clean)",
            "📊 Audit Results Summary",
        ],
        horizontal=True,
        key="export_type",
    )

    if st.button("📄 Generate Export", type="primary", use_container_width=True):
        if export_type == "📋 Full Audit Report (all sections)":
            with st.spinner("🔍 Auditing all report sections..."):
                audit_results = orchestrator.audit_report_sections(
                    sections=report_sections,
                    bibliography=bibliography,
                )

            if audit_results:
                report_text = orchestrator.generate_export_report(audit_results)
                st.session_state["_export_report"] = report_text
                st.success(f"✅ Generated report for {len(audit_results)} sections.")
            else:
                st.info("No auditable content found in report sections.")

        elif export_type == "🔗 Blockchain Verification Certificate":
            with st.spinner("🔗 Verifying blockchain integrity..."):
                is_valid, result = orchestrator.ledger.fetch_and_verify_chain(orchestrator.session_id)

            cert_lines = [
                "=" * 70,
                "BLOCKCHAIN VERIFICATION CERTIFICATE",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Session ID: {orchestrator.session_id}",
                f"Project ID: {orchestrator.project_id}",
                "=" * 70,
                "",
                f"Verification Status: {'✅ PASSED - No tampering detected' if is_valid else '❌ FAILED - Tampering detected!'}",
                "",
            ]
            if is_valid:
                cert_lines.append(f"Total Blocks Verified: {len(result)}")
                cert_lines.append("Integrity: 100% intact")
                cert_lines.append("")
                cert_lines.append("Timeline Summary:")
                for e in result:
                    cert_lines.append(
                        f"  [{datetime.fromtimestamp(e['timestamp']).strftime('%H:%M:%S')}] "
                        f"{e['event_type']} — {e.get('text', '')[:80]}"
                    )
            else:
                cert_lines.append(f"Error: {result}")

            cert_lines.extend(["", "=" * 70, "END OF CERTIFICATE", "=" * 70])
            st.session_state["_export_report"] = "\n".join(cert_lines)
            st.success("✅ Blockchain certificate generated.")

        elif export_type == "📥 Latest Optimized Text (Clean)":
            clean_text = st.session_state.get("_last_optimized_text", "")
            if clean_text:
                st.session_state["_export_report"] = clean_text
                st.success("✅ Clean optimized text ready for download.")
            else:
                st.info("No optimized text found. Run optimization in the Optimization Studio first.")

        elif export_type == "📊 Audit Results Summary":
            last_results = st.session_state.get("_last_audit_results")
            last_text = st.session_state.get("_last_audit_text", "")
            last_source = st.session_state.get("_last_audit_source", "Unknown")

            if last_results:
                scores = last_results.get("composite_scores", {})
                stats = last_results.get("statistical_profile", {})
                ai_det = last_results.get("ai_detection", {})

                summary = [
                    "=" * 70,
                    "AUDIT RESULTS SUMMARY",
                    f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    f"Source: {last_source}",
                    "=" * 70,
                    "",
                    "COMPOSITE SCORES:",
                    f"  AI Content Score:     {scores.get('ai_content_score', 'N/A')}%",
                    f"  Authenticity Score:   {scores.get('authenticity_score', 'N/A')}%",
                    f"  Plagiarism Score:     {scores.get('plagiarism_score', 'N/A')}%",
                    f"  Overall Risk:         {scores.get('overall_risk', 'N/A')}%",
                    "",
                    "STATISTICAL PROFILE:",
                    f"  Total Words:          {stats.get('total_words', 'N/A')}",
                    f"  Sentences:            {stats.get('sentences', 'N/A')}",
                    f"  Burstiness:           {stats.get('burstiness', 'N/A')}",
                    f"  Perplexity:           {stats.get('perplexity', 'N/A')}%",
                    f"  Avg Sentence Length:  {stats.get('avg_sentence_length', 'N/A')}",
                    f"  Vocabulary Richness:  {stats.get('vocabulary_richness', 'N/A')}",
                    "",
                    f"AI Pattern Matches:     {ai_det.get('pattern_count', 'N/A')}",
                    "",
                    "=" * 70,
                    "END OF SUMMARY",
                    "=" * 70,
                ]
                st.session_state["_export_report"] = "\n".join(summary)
                st.success("✅ Audit summary generated.")
            else:
                st.info("No audit results found. Run an audit in the Plagiarism & AI Check tab first.")

    # ─── Display & Download ─────────────────────────────────────────
    export_content = st.session_state.get("_export_report", "")
    if export_content:
        st.markdown("---")
        st.markdown("### 📄 Preview & Download")

        with st.expander("📖 Preview", expanded=True):
            st.text_area("", value=export_content[:5000], height=250, label_visibility="collapsed")

        render_email_delivery(export_content)

        col1, col2 = st.columns(2)
        with col1:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            txt_bytes = export_content.encode("utf-8")
            b64 = base64.b64encode(txt_bytes).decode()
            st.markdown(
                f'<a href="data:text/plain;base64,{b64}" '
                f'download="audit_report_{timestamp}.txt" '
                f'style="display:inline-block;padding:10px 20px;background:#1d4ed8;color:white;'
                f'border-radius:8px;text-decoration:none;font-weight:600;text-align:center;">'
                f'📥 Download TXT Report</a>',
                unsafe_allow_html=True,
            )
        with col2:
            # Pre-escape backticks and ${} for safe JavaScript template literal use
            escaped_export = export_content[:50000].replace("`", "\\`").replace("${", "\\${")
            st.markdown(
                f"""<button onclick="navigator.clipboard.writeText(
                    `{escaped_export}`
                ).then(() => {{this.innerHTML='✅ Copied!';setTimeout(()=>this.innerHTML='📋 Copy to Clipboard',2000)}})"
                style="display:inline-block;padding:10px 20px;background:#059669;color:white;"
                "border:none;border-radius:8px;cursor:pointer;font-weight:600;text-align:center;">
                📋 Copy to Clipboard</button>""",
                unsafe_allow_html=True,
            )

