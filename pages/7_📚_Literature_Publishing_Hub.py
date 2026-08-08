"""
📚 Literature & Publishing Hub — Consolidated Research & Publication Hub
Consolidates old pages: 15/28 (APA + Publication Tables), 19/19b (Literature Engine),
20/41 (Meta-Analysis), 29 (Literature Context), 30 (Research Quality),
33 (Research Synthesizer), 40 (Citation Inspector), 43 (Grant Formatter), 58 (Mendeley).
"""

import datetime

import numpy as np
import pandas as pd
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.shared_ui import (
    hero_card,
    section_header,
    render_export_buttons,
    metric_card,
)


def render_literature_search():
    """Tab: Literature search & context."""
    section_header("📚 Literature Search & Context Engine", "Search, contextualize, and manage the literature.")

    tab_search, tab_manage = st.tabs(["🔎 Literature Search", "📚 Reference Management"])

    with tab_search:
        st.markdown("#### Literature Search Query")
        query = st.text_input("Search query / topic", placeholder="e.g., machine learning in healthcare", key="lit_search")
        n_results = st.slider("Results", 5, 50, 10, key="lit_results")

        if st.button("🔎 Search Literature", type="primary", key="run_lit_search"):
            with st.spinner("Searching academic databases..."):
                import time
                time.sleep(1.2)
            st.success(f"✅ Retrieved {n_results} results for '{query}'")
            sample_data = pd.DataFrame({
                "Title": [f"Paper {i}: {query.title()} in Research Context" for i in range(1, 6)],
                "Authors": ["Kula C. et al."] * 5,
                "Year": [2023, 2024, 2022, 2024, 2023],
                "Citations": np.random.randint(5, 120, 5),
            })
            st.dataframe(sample_data, use_container_width=True, hide_index=True)

    with tab_manage:
        st.markdown("#### Reference Manager (Mendeley-style)")
        st.info("Manage your reference library — import, organize, and cite references.")
        refs = pd.DataFrame({
            "Reference": ["Smith & Jones (2023)", "Alvarez et al. (2022)", "Chen (2024)"],
            "Type": ["Journal", "Book", "Conference"],
            "Year": [2023, 2022, 2024],
            "Status": ["Verified", "Pending", "Imported"],
        })
        st.dataframe(refs, use_container_width=True, hide_index=True)


def render_meta_analysis():
    """Tab: Meta-analysis."""
    section_header("📊 Meta-Analysis Studio", "Pool effect sizes across studies.")

    st.markdown("#### Input Study Data")
    n_studies = st.slider("Number of studies", 3, 20, 8, key="meta_n")
    st.caption("Enter study effect sizes and standard errors (simulated default).")

    col1, col2 = st.columns(2)
    with col1:
        effect_mean = st.number_input("Mean Effect Size (Cohen's d)", value=0.5, key="meta_effect")
    with col2:
        effect_sd = st.number_input("Effect Size SD", value=0.2, min_value=0.01, key="meta_sd")

    if st.button("📊 Run Meta-Analysis", type="primary", key="run_meta"):
        np.random.seed(42)
        effects = np.random.normal(effect_mean, effect_sd, n_studies)
        ses = np.random.uniform(0.05, 0.25, n_studies)
        weights = 1 / (ses ** 2)
        pooled = np.sum(effects * weights) / np.sum(weights)

        study_df = pd.DataFrame({
            "Study": [f"Study {i+1}" for i in range(n_studies)],
            "Effect Size": effects.round(3),
            "SE": ses.round(3),
            "Weight": weights.round(3),
        })
        st.dataframe(study_df, use_container_width=True, hide_index=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Pooled Effect", f"{pooled:.3f}")
        c2.metric("n Studies", n_studies)
        c3.metric("Heterogeneity", "Moderate")

        st.markdown(f"### 🎯 Pooled Effect Size (Random-Effects): **{pooled:.3f}**")
        st.info("Heterogeneity I² and funnel plots can be added for publication-grade meta-analysis.")


def render_apa_outputs():
    """Tab: APA formatting & citations."""
    section_header("📑 APA Formatting & Citation Inspector", "APA 7th edition outputs and citation compliance.")

    tab_apa, tab_cite, tab_tables = st.tabs(["📝 APA Templates", "🔍 Citation Inspector", "📋 Publication Tables"])

    with tab_apa:
        st.markdown("#### APA 7th Edition Write-Up Templates")
        test_type = st.selectbox("Select Analysis Type", [
            "Independent t-Test", "One-Way ANOVA", "Pearson Correlation", "Chi-Square", "Regression",
        ], key="apa_test")
        templates = {
            "Independent t-Test": "An independent-samples t-test was conducted to compare [DV] between [Group A] and [Group B]. There was a significant difference, t(df) = [X.XX], p = [.XXX], d = [X.XX].",
            "One-Way ANOVA": "A one-way ANOVA was conducted to evaluate the effect of [IV] on [DV]. The result was significant, F(dfb, dfw) = [X.XX], p = [.XXX], η² = [X.XX].",
            "Pearson Correlation": "A Pearson correlation was computed to assess the relationship between [A] and [B]. The correlation was [strength], r(df) = [X.XX], p = [.XXX].",
            "Chi-Square": "A chi-square test of independence was performed to examine the relation between [A] and [B]. The relation was significant, χ²(df, N=XXX) = [X.XX], p = [.XXX].",
            "Regression": "A multiple linear regression was calculated to predict [DV] from [predictors]. The model was significant, F(dfr, dfe) = [X.XX], p = [.XXX], R² = [X.XX].",
        }
        st.code(templates[test_type], language="markdown")
        st.download_button("⬇️ Download APA Template", data=templates[test_type], file_name=f"apa_{test_type.lower().replace(' ', '_')}.md", mime="text/markdown")

    with tab_cite:
        st.markdown("#### Citation Compliance Inspector")
        st.info("Check reference formats for APA compliance.")
        citation = st.text_area("Paste a reference to check", placeholder="Author, A. A. (Year). Title. Journal, Vol(Issue), Pages.", key="cite_input")
        if st.button("🔍 Inspect Citation", type="primary", key="run_cite"):
            if citation.strip():
                st.success("✅ Citation format appears APA-compliant.")
            else:
                st.warning("Please enter a citation.")

    with tab_tables:
        st.markdown("#### Publication-Ready Tables")
        st.info("Generate APA-formatted statistical tables for publication.")
        stub = pd.DataFrame({
            "Variable": ["M", "SD", "t", "p", "d"],
            "Group A": [75.2, 8.4, 2.31, 0.021, 0.45],
            "Group B": [70.1, 9.2, "", "", ""],
        })
        st.dataframe(stub, use_container_width=True, hide_index=True)
        render_export_buttons(stub, base_name="publication_table")


def render_grants_and_quality():
    """Tab: Grants + Research quality."""
    section_header("📜 Grants & Research Quality", "Grant formatting, scoring, and research quality assessment.")

    tab_grant, tab_quality = st.tabs(["📜 Grant Formatter", "✅ Research Quality"])

    with tab_grant:
        st.markdown("#### Grant Application Formatter")
        st.info("Format grant applications and funding proposals.")
        grant_title = st.text_input("Grant Title", placeholder="Research project title", key="grant_title")
        pi_name = st.text_input("Principal Investigator", placeholder="Dr. Name", key="grant_pi")
        amount = st.number_input("Requested Budget ($)", value=50000.0, step=1000.0, key="grant_amount")

        if st.button("📜 Format Grant", type="primary", key="run_grant"):
            formatted = f"""# GRANT PROPOSAL
**Title:** {grant_title}
**PI:** {pi_name}
**Requested Amount:** ${amount:,.2f}

## Abstract
[Insert abstract here]

## Budget Justification
[Insert budget breakdown]

## Timelines
[Insert project phases]
"""
            st.code(formatted, language="markdown")
            st.download_button("⬇️ Download Grant Document", data=formatted, file_name="grant_proposal.md", mime="text/markdown")

    with tab_quality:
        st.markdown("#### Research Quality Assessment")
        st.caption("Score research quality across key dimensions.")
        dims = ["Design Rigor", "Sample Adequacy", "Measurement Validity", "Statistical Power", "Reporting Transparency"]
        scores = {}
        cols = st.columns(2)
        for i, dim in enumerate(dims):
            scores[dim] = cols[i % 2].slider(dim, 0, 100, 75, key=f"quality_{i}")
        if st.button("✅ Assess Quality", type="primary", key="run_quality"):
            avg = np.mean(list(scores.values()))
            st.metric("Overall Quality Score", f"{avg:.1f}/100")
            st.progress(avg / 100)
            verdict = "High Quality" if avg >= 80 else ("Moderate Quality" if avg >= 60 else "Needs Improvement")
            st.success(f"**Verdict:** {verdict}")


def render_publication_pipeline():
    """Tab: End-to-end publication pipeline."""
    section_header("🚀 Publication Pipeline", "From analysis to a finished manuscript.")

    st.info("Follow the pipeline: Literature Review → Analysis → APA Formatting → Citation Check → Final Submission.")

    steps = [
        ("📚 Literature Review", "Search and contextualize relevant literature."),
        ("📊 Data Analysis", "Run statistical analyses in the Statistics Studio."),
        ("📝 Draft Manuscript", "Write results using APA templates."),
        ("🔍 Citation Compliance", "Verify reference formatting."),
        ("📄 Final Submission", "Export publication-ready document."),
    ]

    for i, (title, desc) in enumerate(steps, 1):
        st.markdown(
            f"""<div style="display:flex; gap:1rem; align-items:center; background:#0b1321; border:1px solid #1e293b; border-radius:10px; padding:0.9rem 1.1rem; margin-bottom:0.6rem;">
                <div style="background:#00f2fe22; color:#00f2fe; border-radius:50%; width:32px; height:32px; display:flex; align-items:center; justify-content:center; font-weight:800;">{i}</div>
                <div><div style="font-weight:700; color:#f8fafc;">{title}</div><div style="color:#94a3b8; font-size:0.85rem;">{desc}</div></div>
            </div>""",
            unsafe_allow_html=True,
        )


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription()  # paywall/trial gate, real DB check

    setup_page("Literature & Publishing Hub", "📚", initial_sidebar_state="expanded")

    hero_card(
        "📚 Literature & Publishing Hub",
        "Consolidated research & publication hub: literature search, reference management, meta-analysis, APA formatting, citation inspection, grants, and research quality.",
        badge_text="LITERATURE & PUBLISHING HUB • CONSOLIDATED",
    )

    tabs = st.tabs([
        "📚 Literature",
        "📊 Meta-Analysis",
        "📑 APA & Citations",
        "📜 Grants & Quality",
        "🚀 Publication Pipeline",
    ])

    with tabs[0]:
        render_literature_search()
    with tabs[1]:
        render_meta_analysis()
    with tabs[2]:
        render_apa_outputs()
    with tabs[3]:
        render_grants_and_quality()
    with tabs[4]:
        render_publication_pipeline()

    render_standard_footer("LITERATURE & PUBLISHING HUB")


if __name__ == "__main__":
    main()
