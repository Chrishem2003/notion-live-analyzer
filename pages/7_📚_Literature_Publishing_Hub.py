"""
📚 Literature & Publishing Hub — Consolidated Research & Publication Hub (Premium)
Real CrossRef-backed literature search, a genuine reference manager with accurate BibTeX
generation, real regex-based APA compliance checking, a real meta-analysis engine driven by
actual study-level data (not simulated numbers), APA formatting templates, grant proposal
scaffolding, and research quality self-assessment.

Changelog vs prior version — this hub previously fabricated academic data, which is a serious
integrity issue for a research tool:
- FIXED (was fabricating fake papers): "Literature Search" slept for 1 second and invented fake
  paper titles with hardcoded fake author names ("Kula, C.", "Awor, P.") and random citation
  counts, presented as "validated scholarly results." It now queries the real, free CrossRef API
  (no key required) and returns actual publications, authors, journals, and citation counts. If
  the network is unavailable, it says so plainly and shows nothing rather than inventing sources.
  Also fixed a `np.randint()` bug (doesn't exist — only worked by accident via a dead fallback).
- FIXED (ignored your input): BibTeX generation always returned the identical fabricated citation
  regardless of which reference you selected. There's now a real reference manager — add your own
  references with real fields, and BibTeX is generated from what you actually entered.
- FIXED (did nothing): "Citation Compliance Inspector" always returned "✅ complies with APA 7th
  edition" for any input, including garbage text. It now runs real regex-based structural checks
  (author format, parenthetical year, punctuation density, volume/page pattern) and reports which
  specific checks passed or failed — honestly labeled as heuristic checks, not a guarantee.
- FIXED (the big one): "Meta-Analysis Studio" never took real study data as input — the sliders
  for "number of studies" and "mean effect" just parameterized a random number generator, and the
  tool pooled *fabricated* numbers while presenting real-looking I², Q-statistics, and a forest
  plot. It now uses an editable data table for actual per-study effect sizes and standard errors,
  and every downstream statistic is computed from what you actually entered. A clearly-labeled
  "load example data" button exists for exploring the tool, but it can't be mistaken for real
  analysis output.
- FIXED: "Citation Network Mapper" plotted random `np.random.normal` coordinates as if they meant
  something. It now plots real Year vs. Citation-Count data from your last literature search (or
  prompts you to run a search first) — no fabricated coordinates.
- UPGRADED: Grant Proposal Formatter's Abstract/Background/Methodology sections were fixed
  boilerplate regardless of what you entered. They're now user-editable text areas that flow
  through to the generated document.
"""

import re
import datetime

import numpy as np
import pandas as pd
import scipy.stats as stats
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.shared_ui import (
    hero_card,
    section_header,
    render_export_buttons,
    metric_card,
)

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


# ══════════════════════════════════════════════════════════════════════
# Real literature search via CrossRef (free, no API key)
# ══════════════════════════════════════════════════════════════════════
def search_crossref(query: str, n_results: int, sort_by: str):
    if not REQUESTS_AVAILABLE:
        return None, "`requests` package not installed in this environment."
    try:
        params = {"query": query, "rows": min(max(n_results, 1), 50)}
        if sort_by == "Citation Count":
            params["sort"], params["order"] = "is-referenced-by-count", "desc"
        elif sort_by == "Publication Date":
            params["sort"], params["order"] = "published", "desc"

        resp = requests.get(
            "https://api.crossref.org/works",
            params=params,
            timeout=8,
            headers={"User-Agent": "ChrishemPlatform-LiteratureHub/1.0 (mailto:research@example.com)"},
        )
        resp.raise_for_status()
        items = resp.json().get("message", {}).get("items", [])

        records = []
        for it in items:
            title = (it.get("title") or ["Untitled"])[0]
            authors = it.get("author", [])
            first_author = f"{authors[0].get('family','?')}, {authors[0].get('given','')[:1]}." if authors else "Unknown"
            year = None
            for key in ("published-print", "published-online", "issued"):
                dp = it.get(key, {}).get("date-parts")
                if dp and dp[0]:
                    year = dp[0][0]
                    break
            records.append({
                "Title": title,
                "First Author": first_author,
                "Year": year or "n/a",
                "Citations": it.get("is-referenced-by-count", 0),
                "Journal": (it.get("container-title") or ["—"])[0],
                "DOI": it.get("DOI", ""),
            })
        return pd.DataFrame(records), None
    except Exception as e:
        return None, str(e)


def render_literature_search():
    section_header("📚 Literature Search & Reference Management", "Real bibliographic search (CrossRef), a genuine reference manager, and a bibliometric map built from actual retrieved data.")

    tab_search, tab_manage, tab_cluster = st.tabs(["🔎 Live Literature Search", "📚 Reference Manager", "🌐 Bibliometric Map"])

    with tab_search:
        st.markdown("#### Live Academic Search (CrossRef — real publication data, no API key required)")
        query = st.text_input("Enter Research Query / Topic", placeholder="e.g., multi-omics biomarker discovery", key="lit_search_upg")
        col1, col2 = st.columns(2)
        with col1:
            n_results = st.slider("Result Count", 5, 50, 15, key="lit_results_upg")
        with col2:
            sort_by = st.selectbox("Sort Priority", ["Relevance", "Citation Count", "Publication Date"], key="lit_sort_upg")

        if st.button("🔎 Search CrossRef", type="primary", key="run_lit_search_upg"):
            if not query.strip():
                st.warning("Enter a search query.")
            else:
                with st.spinner(f"Querying CrossRef for '{query}'..."):
                    results_df, error = search_crossref(query, n_results, sort_by)
                if error:
                    st.error(f"🚫 Live search unavailable: {error}. No fabricated results are shown — try again, or check your network/outbound access settings.")
                elif results_df is None or results_df.empty:
                    st.info("No results found for this query.")
                else:
                    st.success(f"✅ Retrieved {len(results_df)} real publications from CrossRef for '{query}'.")
                    st.dataframe(results_df, use_container_width=True, hide_index=True)
                    render_export_buttons(results_df, base_name="literature_search_results")
                    st.session_state["lit_search_results"] = results_df

    with tab_manage:
        st.markdown("#### Reference Library — Add your own references for accurate BibTeX export")
        if "lit_references" not in st.session_state:
            st.session_state["lit_references"] = []

        with st.form("add_reference_form"):
            c1, c2 = st.columns(2)
            with c1:
                citation_key = st.text_input("Citation Key", placeholder="Smith2026")
                authors = st.text_input("Authors", placeholder="Smith, J., & Doe, A.")
                title = st.text_input("Title")
            with c2:
                journal = st.text_input("Journal / Source")
                volume = st.text_input("Volume")
                pages = st.text_input("Pages", placeholder="112-125")
                year = st.text_input("Year", placeholder="2026")
            submitted = st.form_submit_button("➕ Add Reference")
            if submitted:
                if citation_key.strip() and authors.strip() and title.strip():
                    st.session_state["lit_references"].append({
                        "citation_key": citation_key.strip(), "authors": authors.strip(), "title": title.strip(),
                        "journal": journal.strip(), "volume": volume.strip(), "pages": pages.strip(), "year": year.strip(),
                    })
                    st.success(f"✅ Added reference `{citation_key}`.")
                else:
                    st.warning("Citation key, authors, and title are required.")

        refs = st.session_state["lit_references"]
        if not refs:
            st.info("No references added yet. Use the form above, or search CrossRef and add results here.")
        else:
            refs_df = pd.DataFrame(refs)
            st.dataframe(refs_df, use_container_width=True, hide_index=True)

            selected_key = st.selectbox("Select Reference for BibTeX Export", [r["citation_key"] for r in refs], key="bibtex_sel")
            if st.button("📋 Generate BibTeX", key="gen_bibtex"):
                ref = next(r for r in refs if r["citation_key"] == selected_key)
                bibtex_str = f"""@article{{{ref['citation_key']},
  author = {{{ref['authors']}}},
  title = {{{ref['title']}}},
  journal = {{{ref['journal'] or 'Unknown Journal'}}},
  volume = {{{ref['volume'] or 'n/a'}}},
  pages = {{{ref['pages'] or 'n/a'}}},
  year = {{{ref['year'] or 'n/a'}}}
}}"""
                st.code(bibtex_str, language="bibtex")
                st.download_button("⬇️ Download .bib", data=bibtex_str, file_name=f"{ref['citation_key']}.bib", mime="text/plain", key="dl_bibtex")

    with tab_cluster:
        st.markdown("#### Bibliometric Map — Year vs. Citation Count")
        st.caption("Built from your last live search results — not synthetic coordinates.")
        results_df = st.session_state.get("lit_search_results")
        if results_df is None or results_df.empty:
            st.info("ℹ️ Run a search in the **Live Literature Search** tab first — this map plots real data from those results.")
        elif not PLOTLY_AVAILABLE:
            st.info("Plotly required for map rendering.")
        else:
            plot_df = results_df[results_df["Year"] != "n/a"].copy()
            if plot_df.empty:
                st.info("No results with resolvable publication years to plot.")
            else:
                plot_df["Year"] = plot_df["Year"].astype(int)
                fig = px.scatter(plot_df, x="Year", y="Citations", size="Citations", color="Journal", hover_name="Title", template="plotly_dark", height=420)
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=20, b=0))
                st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════
# Real meta-analysis: takes actual study data, computes real statistics
# ══════════════════════════════════════════════════════════════════════
def render_meta_analysis():
    section_header("📊 Meta-Analysis & Effect Size Studio", "Pool effect sizes from studies you actually enter, compute real heterogeneity (I², Q-statistic), and generate a forest plot from that real data.")

    if "meta_study_table" not in st.session_state:
        st.session_state["meta_study_table"] = pd.DataFrame({
            "Study": ["Study 1", "Study 2", "Study 3"],
            "Effect_Size": [0.45, 0.62, 0.38],
            "Standard_Error": [0.12, 0.15, 0.10],
        })

    st.markdown("#### Enter Study-Level Data")
    st.caption("Effect Size (Cohen's d / Hedges' g) and Standard Error for each study you're pooling. Edit, add, or remove rows directly.")

    col_load, col_clear = st.columns(2)
    with col_load:
        if st.button("📥 Load Labeled Example Data (for demonstration only)", key="meta_load_example"):
            rng = np.random.default_rng(42)
            n_demo = 8
            effects = rng.normal(0.5, 0.15, n_demo).round(3)
            ses = rng.uniform(0.06, 0.20, n_demo).round(3)
            st.session_state["meta_study_table"] = pd.DataFrame({
                "Study": [f"[DEMO] Study {i+1}" for i in range(n_demo)],
                "Effect_Size": effects,
                "Standard_Error": ses,
            })
            st.rerun()
    with col_clear:
        if st.button("🗑️ Clear Table", key="meta_clear"):
            st.session_state["meta_study_table"] = pd.DataFrame({"Study": [], "Effect_Size": [], "Standard_Error": []})
            st.rerun()

    edited = st.data_editor(
        st.session_state["meta_study_table"],
        num_rows="dynamic",
        use_container_width=True,
        key="meta_data_editor",
        column_config={
            "Effect_Size": st.column_config.NumberColumn("Effect Size (g)", format="%.4f"),
            "Standard_Error": st.column_config.NumberColumn("Standard Error", format="%.4f", min_value=0.0001),
        },
    )
    st.session_state["meta_study_table"] = edited

    valid = edited.dropna(subset=["Effect_Size", "Standard_Error"])
    valid = valid[valid["Standard_Error"] > 0]

    if st.button("🚀 Run Meta-Analysis on This Data", type="primary", key="run_meta_upg"):
        if len(valid) < 2:
            st.error("🚫 Need at least 2 studies with valid Effect Size and Standard Error (> 0) to pool.")
        else:
            effects = valid["Effect_Size"].values.astype(float)
            ses = valid["Standard_Error"].values.astype(float)
            weights = 1 / (ses ** 2)
            pooled_effect = np.sum(effects * weights) / np.sum(weights)
            pooled_se = np.sqrt(1 / np.sum(weights))

            q_stat = np.sum(weights * (effects - pooled_effect) ** 2)
            df_val = len(effects) - 1
            i_squared = max(0.0, 100 * (q_stat - df_val) / q_stat) if q_stat > 0 else 0.0
            q_p_value = 1 - stats.chi2.cdf(q_stat, df_val) if df_val > 0 else np.nan

            z = pooled_effect / pooled_se
            p_val = 2 * (1 - stats.norm.cdf(abs(z)))
            ci_low, ci_high = pooled_effect - 1.96 * pooled_se, pooled_effect + 1.96 * pooled_se

            display_df = valid.copy()
            display_df["Weight (%)"] = (weights / weights.sum() * 100).round(2)
            st.markdown("#### 📋 Study Weights (Inverse-Variance)")
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Pooled Effect Size", f"{pooled_effect:.3f}", delta=f"95% CI [{ci_low:.3f}, {ci_high:.3f}]")
            c2.metric("Pooled p-value", f"{p_val:.5f}")
            c3.metric("Heterogeneity (I²)", f"{i_squared:.1f}%", delta="High" if i_squared >= 75 else ("Moderate" if i_squared >= 50 else "Low"))
            c4.metric("Cochran's Q", f"{q_stat:.2f}", delta=f"df={df_val}, p={q_p_value:.4f}" if not np.isnan(q_p_value) else None)

            if i_squared >= 75:
                st.warning("⚠️ High heterogeneity (I² ≥ 75%) — a random-effects interpretation is more appropriate than fixed-effect, and pooling may mask meaningfully different underlying effects across studies.")

            if PLOTLY_AVAILABLE:
                st.markdown("#### 🌲 Forest Plot")
                fig = go.Figure()
                for i, (_, row) in enumerate(display_df.iterrows()):
                    fig.add_trace(go.Scatter(
                        x=[row["Effect_Size"] - 1.96 * row["Standard_Error"], row["Effect_Size"] + 1.96 * row["Standard_Error"]],
                        y=[i, i], mode="lines", line=dict(color="#38BDF8", width=2), showlegend=False,
                    ))
                    fig.add_trace(go.Scatter(
                        x=[row["Effect_Size"]], y=[i], mode="markers",
                        marker=dict(size=10 + row["Weight (%)"] / 2, color="#00F2FE"),
                        name=row["Study"], showlegend=False,
                    ))
                fig.add_shape(type="line", x0=pooled_effect, y0=-1, x1=pooled_effect, y1=len(display_df), line=dict(color="red", width=2, dash="dash"))
                fig.update_layout(
                    title_text="Meta-Analysis Forest Plot", xaxis_title="Effect Size", yaxis_title="Study",
                    yaxis=dict(tickmode="array", tickvals=list(range(len(display_df))), ticktext=display_df["Study"].tolist()),
                    template="plotly_dark", height=max(320, 60 * len(display_df)), margin=dict(l=20, r=20, t=40, b=20),
                )
                st.plotly_chart(fig, use_container_width=True)

            render_export_buttons(display_df, base_name="meta_analysis_results")


# ══════════════════════════════════════════════════════════════════════
# Real APA compliance checking (regex-based, honestly labeled as heuristic)
# ══════════════════════════════════════════════════════════════════════
def inspect_apa_citation(citation: str):
    c = citation.strip()
    checks = []
    checks.append(("Author format (Surname, Initial.)", bool(re.match(r"^[A-Z][A-Za-z'\-]+,\s*[A-Z]\.(\s*[A-Z]\.)?", c))))
    checks.append(("Year in parentheses, e.g. (2026)", bool(re.search(r"\((1[5-9]\d{2}|20\d{2})[a-z]?\)", c))))
    checks.append(("Sentence-level punctuation present (periods separating author/year/title/source)", c.count(".") >= 2))
    checks.append(("Volume/issue or page-range pattern present", bool(re.search(r"\b\d+\s*\(\d+\)|\b\d+[-–]\d+\b", c))))
    checks.append(("DOI or URL present", bool(re.search(r"https?://\S+", c))))
    passed = sum(1 for _, ok in checks if ok)
    return checks, passed, len(checks)


def render_apa_outputs():
    section_header("📑 APA 7th Edition Formatting & Citation Compliance", "Publication-grade write-up templates, a real structural citation checker, and formatted tables.")

    tab_apa, tab_cite, tab_tables = st.tabs(["📝 APA Statistical Templates", "🔍 Citation Inspector", "📋 Publication Tables"])

    with tab_apa:
        st.markdown("#### APA 7th Edition Standardized Write-Up Templates")
        test_type = st.selectbox("Select Statistical Procedure", [
            "Independent Samples t-Test", "One-Way Analysis of Variance (ANOVA)", "Pearson Product-Moment Correlation", "Chi-Square Test of Independence", "Multiple Linear Regression"
        ], key="apa_test_upg")

        templates = {
            "Independent Samples t-Test": "An independent-samples t-test was conducted to compare [Dependent Variable] between [Group A] and [Group B]. There was a statistically significant difference between the groups, t(df) = [X.XX], p = [.XXX], Cohen's d = [X.XX].",
            "One-Way Analysis of Variance (ANOVA)": "A one-way ANOVA was conducted to evaluate the effect of [Independent Variable] on [Dependent Variable]. The overall effect was statistically significant, F(df_between, df_within) = [X.XX], p = [.XXX], partial η² = [X.XX].",
            "Pearson Product-Moment Correlation": "A Pearson correlation coefficient was computed to assess the linear relationship between [Variable A] and [Variable B]. There was a strong, positive correlation between the two variables, r(df) = [X.XX], p = [.XXX].",
            "Chi-Square Test of Independence": "A chi-square test of independence was performed to examine the association between [Categorical Var A] and [Categorical Var B]. The relation between these variables was significant, χ²(df, N = XXX) = [X.XX], p = [.XXX], Cramer's V = [X.XX].",
            "Multiple Linear Regression": "A multiple linear regression was calculated to predict [Dependent Variable] from [Predictor 1] and [Predictor 2]. Significant regression equation was found, F(df_reg, df_res) = [X.XX], p = [.XXX], with an R² of [X.XX].",
        }
        st.code(templates[test_type], language="markdown")
        st.download_button("⬇️ Download APA Template Code", data=templates[test_type], file_name=f"apa_{test_type.lower().replace(' ', '_')}.md", mime="text/markdown")

    with tab_cite:
        st.markdown("#### Citation Structure Checker (heuristic — flags common formatting issues, not a guarantee of full APA compliance)")
        citation_input = st.text_area("Paste Reference Citation to Validate", placeholder="Author, A. A. (2026). Title of article. Journal Name, 42(3), 112-125. https://doi.org/...", key="cite_input_upg")
        if st.button("🔍 Inspect Citation", type="primary", key="run_cite_upg"):
            if citation_input.strip():
                checks, passed, total = inspect_apa_citation(citation_input)
                for label, ok in checks:
                    st.markdown(f"{'✅' if ok else '❌'} {label}")
                if passed == total:
                    st.success(f"✅ All {total} structural checks passed.")
                elif passed >= total - 1:
                    st.warning(f"⚠️ {passed}/{total} checks passed — minor formatting issues likely.")
                else:
                    st.error(f"🚨 Only {passed}/{total} checks passed — this citation likely needs reformatting.")
            else:
                st.warning("⚠️ Please provide a citation string to inspect.")

    with tab_tables:
        st.markdown("#### Publication-Ready APA Statistical Table Generator")
        st.caption("Fill in your own values — this replaces the placeholder table with your actual numbers before export.")
        default_stub = pd.DataFrame({
            "Variable": ["Age (Years)", "Baseline Score", "Post-Intervention Score", "Mean Gain", "Cohen's d"],
            "Experimental Group": ["", "", "", "", ""],
            "Control Group": ["", "", "", "", ""],
            "t-statistic": ["", "", "", "", ""],
            "p-value": ["", "", "", "", ""],
        })
        edited_table = st.data_editor(default_stub, num_rows="dynamic", use_container_width=True, key="apa_table_editor")
        render_export_buttons(edited_table, base_name="apa_publication_table")


def render_grants_and_quality():
    section_header("📜 Grant Application Formatter & Research Quality Assessor", "Format grant proposals using your own content, and self-assess research rigor.")

    tab_grant, tab_quality = st.tabs(["📜 Grant Proposal Formatter", "✅ Research Quality Assessor"])

    with tab_grant:
        st.markdown("#### Institutional Grant Proposal Builder")
        col1, col2 = st.columns(2)
        with col1:
            grant_title = st.text_input("Grant Project Title", value="Multi-Omics Integration for Precision Diagnostics", key="grant_title_upg")
            pi_name = st.text_input("Principal Investigator (PI)", value="Dr. Chris Kula, Ph.D.", key="grant_pi_upg")
        with col2:
            amount = st.number_input("Requested Funding Budget ($ USD)", value=150000.0, step=5000.0, key="grant_amount_upg")
            agency = st.selectbox("Funding Agency", ["National Science Foundation (NSF)", "National Institutes of Health (NIH)", "Wellcome Trust", "Gates Foundation"], key="grant_agency")

        st.markdown("#### Your Content (flows directly into the generated document)")
        abstract_text = st.text_area("Abstract & Specific Aims", value="This research project establishes an integrated analytical framework to address critical gaps in biomedical data science.", height=100, key="grant_abstract")
        background_text = st.text_area("Background & Significance", value="Prior studies highlight significant bottlenecks in this domain. This proposal directly addresses these limitations.", height=100, key="grant_background")
        methodology_text = st.text_area("Research Design & Methodology", value="We utilize advanced analytical pipelines, cross-validation architectures, and automated statistical validation.", height=100, key="grant_methodology")

        if st.button("📜 Generate Grant Proposal Package", type="primary", key="run_grant_upg"):
            proposal_text = f"""# GRANT PROPOSAL: {agency.upper()}
**Project Title:** {grant_title}
**Principal Investigator:** {pi_name}
**Requested Budget:** ${amount:,.2f}
**Date:** {datetime.date.today().isoformat()}

## 1. Abstract & Specific Aims
{abstract_text}

## 2. Background & Significance
{background_text}

## 3. Research Design & Methodology
{methodology_text}

## 4. Budget Justification
Personnel (60%): ${amount * 0.6:,.2f} | Equipment & Infrastructure (30%): ${amount * 0.3:,.2f} | Publication & Overhead (10%): ${amount * 0.1:,.2f}
"""
            st.code(proposal_text, language="markdown")
            st.download_button("⬇️ Download Grant Proposal Package", data=proposal_text, file_name="grant_proposal_package.md", mime="text/markdown")

    with tab_quality:
        st.markdown("#### Multidimensional Research Rigor Self-Assessment")
        st.caption("A self-report checklist — score your own study design honestly across these dimensions.")
        dims = ["Design Rigor & Control", "Sample Size Adequacy", "Measurement Validity", "Statistical Power", "Reporting Transparency"]
        scores = {}
        cols = st.columns(2)
        for i, dim in enumerate(dims):
            scores[dim] = cols[i % 2].slider(dim, 0, 100, 50, key=f"quality_score_{i}")

        if st.button("✅ Evaluate Research Rigor Score", type="primary", key="run_quality_upg"):
            avg_score = np.mean(list(scores.values()))
            st.metric("Overall Research Quality Index", f"{avg_score:.1f} / 100")
            st.progress(int(avg_score))
            verdict = "Strong — likely publication ready" if avg_score >= 85 else ("Moderate — revision recommended" if avg_score >= 65 else "Weak — methodological overhaul needed")
            st.success(f"**Self-Assessment Verdict:** {verdict}")
            weakest = min(scores, key=scores.get)
            st.info(f"💡 Lowest-scored dimension: **{weakest}** ({scores[weakest]}/100) — consider prioritizing improvements here.")


def render_publication_pipeline():
    section_header("🚀 Publication Lifecycle Reference", "A reference roadmap for navigating from literature discovery to journal submission.")

    steps = [
        ("📚 Phase 1: Literature Discovery & Context", "Use the Live Literature Search tab to find and manage real sources via CrossRef."),
        ("📊 Phase 2: Rigorous Statistical Analysis", "Run meta-analyses on your real study data, or use Statistics Studio for primary analyses."),
        ("📑 Phase 3: APA Formatting & Tables", "Compile write-ups using the APA templates and publication table editor."),
        ("🔍 Phase 4: Citation Compliance & Review", "Run each reference through the Citation Inspector before submission."),
        ("🚀 Phase 5: Final Submission & Export", "Export publication-ready markdown, BibTeX, and structured datasets for journal upload."),
    ]

    for i, (title, desc) in enumerate(steps, 1):
        st.markdown(
            f"""<div style="display:flex; gap:1rem; align-items:center; background:#0b1321; border:1px solid #1e293b; border-radius:10px; padding:1.0rem 1.2rem; margin-bottom:0.75rem;">
                <div style="background:#00f2fe22; color:#00f2fe; border-radius:50%; width:36px; height:36px; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:1.1rem;">{i}</div>
                <div><div style="font-weight:700; color:#f8fafc; font-size:1.05rem;">{title}</div><div style="color:#94a3b8; font-size:0.9rem;">{desc}</div></div>
            </div>""",
            unsafe_allow_html=True,
        )


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription()

    setup_page("Literature & Publishing Hub", "📚", initial_sidebar_state="expanded")

    hero_card(
        "📚 Literature & Publishing Hub — Premium Research Suite",
        "Consolidated research platform featuring real CrossRef literature search, a genuine reference manager, meta-analysis driven by your actual study data, real APA compliance checking, grant proposal drafting, and publication pipeline guidance.",
        badge_text="LITERATURE & PUBLISHING HUB • PREMIUM TIER",
    )

    tabs = st.tabs([
        "📚 Literature & References",
        "📊 Meta-Analysis Studio",
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