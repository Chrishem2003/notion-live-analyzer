import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

"""
📚 Literature & Publishing Hub — Advanced Production Suite
CrossRef & PubMed integration, persistent reference manager with JSON/BibTeX import/export, 
RIS exporter, PRISMA 2020 flow diagram generator, APA compliance checker, meta-analysis engine 
(Fixed & Random Effects, Funnel Plots, Egger's Test), and grant/rigor tracking workflows.
"""

import re
import json
import datetime
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
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


# ==============================================================================
# CrossRef & PubMed Search Engine & Metadata Utilities
# ==============================================================================
def search_crossref(query: str, n_results: int, sort_by: str, contact_email: str):
    if not REQUESTS_AVAILABLE:
        return None, "`requests` package not installed in this environment."
    try:
        params = {"query": query, "rows": min(max(n_results, 1), 100)}
        if sort_by == "Citation Count":
            params["sort"], params["order"] = "is-referenced-by-count", "desc"
        elif sort_by == "Publication Date":
            params["sort"], params["order"] = "published", "desc"
        elif sort_by == "Relevance":
            params["sort"], params["order"] = "score", "desc"

        email = contact_email.strip() if contact_email else "researcher@university.edu"
        headers = {"User-Agent": f"ChrishemProductionHub/2.0 (mailto:{email})"}
        resp = requests.get(
            "https://api.crossref.org/works",
            params=params,
            timeout=12,
            headers=headers,
        )
        resp.raise_for_status()
        items = resp.json().get("message", {}).get("items", [])

        records = []
        for it in items:
            title_list = it.get("title")
            title = title_list[0] if title_list else "Untitled"
            
            authors = it.get("author", [])
            if authors:
                first_fam = authors[0].get('family', 'Unknown')
                first_giv = authors[0].get('given', '')
                initial = f"{first_giv[0]}." if first_giv else ""
                first_author = f"{first_fam}, {initial}".strip()
                if len(authors) > 1:
                    first_author += " et al."
            else:
                first_author = "Unknown"

            year = None
            for key in ("published-print", "published-online", "issued"):
                dp = it.get(key, {}).get("date-parts")
                if dp and dp[0] and dp[0][0]:
                    year = dp[0][0]
                    break

            container = it.get("container-title")
            journal = container[0] if container else "—"
            
            records.append({
                "Source": "CrossRef",
                "Title": title,
                "First Author": first_author,
                "Year": year if year else "n/a",
                "Citations": it.get("is-referenced-by-count", 0),
                "Journal": journal,
                "DOI": it.get("DOI", "n/a"),
                "Type": it.get("type", "journal-article"),
            })
        return pd.DataFrame(records), None
    except Exception as e:
        return None, str(e)


def search_pubmed(query: str, n_results: int):
    if not REQUESTS_AVAILABLE:
        return None, "`requests` package not installed."
    try:
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        s_params = {"db": "pubmed", "term": query, "retmode": "json", "retmax": n_results}
        s_resp = requests.get(search_url, params=s_params, timeout=10)
        s_resp.raise_for_status()
        id_list = s_resp.json().get("esearchresult", {}).get("idlist", [])

        if not id_list:
            return pd.DataFrame(), None

        summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        sum_params = {"db": "pubmed", "id": ",".join(id_list), "retmode": "json"}
        sum_resp = requests.get(summary_url, params=sum_params, timeout=10)
        sum_resp.raise_for_status()
        result_set = sum_resp.json().get("result", {})

        records = []
        for pmid in id_list:
            item = result_set.get(pmid, {})
            authors = item.get("authors", [])
            first_author = authors[0].get("name", "Unknown") if authors else "Unknown"
            if len(authors) > 1:
                first_author += " et al."

            pubdate = item.get("pubdate", "")
            year_match = re.search(r"\b(19|20)\d{2}\b", pubdate)
            year = year_match.group(0) if year_match else "n/a"

            article_ids = item.get("articleids", [])
            doi = "n/a"
            for aid in article_ids:
                if aid.get("idtype") == "doi":
                    doi = aid.get("value")
                    break

            records.append({
                "Source": "PubMed",
                "Title": item.get("title", "Untitled"),
                "First Author": first_author,
                "Year": year,
                "Citations": 0,
                "Journal": item.get("source", "—"),
                "DOI": doi,
                "Type": "journal-article",
            })
        return pd.DataFrame(records), None
    except Exception as e:
        return None, str(e)


def escape_bibtex(text: str) -> str:
    if not text:
        return ""
    return (str(text).replace("&", "\\&")
                     .replace("%", "\\%")
                     .replace("$", "\\$")
                     .replace("#", "\\#")
                     .replace("_", "\\_"))


def parse_bibtex_string(bibtext: str):
    entries = []
    blocks = re.findall(r'@(\w+)\s*\{\s*([^,]+),([^@]+)\}', bibtext, re.DOTALL)
    for entry_type, citation_key, body in blocks:
        ref = {"entry_type": entry_type.lower(), "citation_key": citation_key.strip()}
        fields = re.findall(r'(\w+)\s*=\s*[\{"]([^"\}]+)[\}"]', body)
        for k, v in fields:
            ref[k.lower()] = v.strip()
        ref["authors"] = ref.get("author", ref.get("authors", "Unknown"))
        ref["title"] = ref.get("title", "Untitled")
        entries.append(ref)
    return entries


def convert_to_ris(refs: list) -> str:
    ris_lines = []
    for r in refs:
        ris_lines.append("TY  - JOUR" if r.get("entry_type") == "article" else "TY  - GEN")
        ris_lines.append(f"TI  - {r.get('title', '')}")
        ris_lines.append(f"AU  - {r.get('authors', '')}")
        ris_lines.append(f"JO  - {r.get('journal', '')}")
        ris_lines.append(f"VL  - {r.get('volume', '')}")
        ris_lines.append(f"SP  - {r.get('pages', '')}")
        ris_lines.append(f"PY  - {r.get('year', '')}")
        ris_lines.append(f"DO  - {r.get('doi', '')}")
        ris_lines.append("ER  - \n")
    return "\n".join(ris_lines)


def render_literature_search():
    section_header("📚 Literature Search & Reference Management", "Multi-database academic discovery (CrossRef & PubMed), persistent reference storage, BibTeX/RIS tools, and bibliometrics.")

    tab_search, tab_manage, tab_prisma, tab_cluster = st.tabs([
        "🔍 Multi-Engine Search", 
        "📚 Reference Manager", 
        "📐 PRISMA Flow Diagram",
        "🌐 Bibliometric Map"
    ])

    with tab_search:
        st.markdown("#### Live Academic Search Engine")
        col_q1, col_q2 = st.columns([3, 1])
        with col_q1:
            query = st.text_input("Research Query / Topic", placeholder="e.g., plasmid-mediated mobile colistin resistance mcr", key="lit_search_prod")
        with col_q2:
            db_engine = st.selectbox("Database Provider", ["CrossRef API", "PubMed (NCBI)"], key="lit_db_engine")

        col1, col2, col3 = st.columns(3)
        with col1:
            n_results = st.slider("Result Count", 5, 100, 20, key="lit_results_prod")
        with col2:
            sort_by = st.selectbox("Sort Priority", ["Relevance", "Citation Count", "Publication Date"], key="lit_sort_prod")
        with col3:
            contact_email = st.text_input("Contact Email (Politeness)", value="researcher@university.edu", key="crossref_email")

        if st.button("🔍 Execute Academic Search", type="primary", key="run_lit_search_prod", use_container_width=True):
            if not query.strip():
                st.warning("Please enter a valid search query.")
            else:
                with st.spinner(f"Querying {db_engine} for '{query}'..."):
                    if "CrossRef" in db_engine:
                        results_df, error = search_crossref(query, n_results, sort_by, contact_email)
                    else:
                        results_df, error = search_pubmed(query, n_results)

                if error:
                    st.error(f"🚫 Search failed: {error}")
                elif results_df is None or results_df.empty:
                    st.info("No publications found matching this query string.")
                else:
                    st.success(f"✅ Retrieved {len(results_df)} verified publications.")
                    st.dataframe(results_df, use_container_width=True, hide_index=True)
                    render_export_buttons(results_df, base_name="literature_results")
                    st.session_state["lit_search_results"] = results_df

    with tab_manage:
        st.markdown("#### Reference Library, BibTeX & RIS Exporter")
        if "lit_references" not in st.session_state:
            st.session_state["lit_references"] = []

        with st.form("add_reference_form_prod"):
            c1, c2 = st.columns(2)
            with c1:
                citation_key = st.text_input("Citation Key", placeholder="Kula2026")
                authors = st.text_input("Authors", placeholder="Kula, C., & Smith, J.")
                title = st.text_input("Publication Title")
                entry_type = st.selectbox("Entry Type", ["article", "inproceedings", "book", "phdthesis"])
            with c2:
                journal = st.text_input("Journal / Conference Source")
                volume = st.text_input("Volume / Issue")
                pages = st.text_input("Pages", placeholder="112-125")
                year = st.text_input("Year", placeholder="2026")
                doi = st.text_input("DOI", placeholder="10.1038/s41587-026-00000-x")
            
            submitted = st.form_submit_button("➕ Add Reference to Library")
            if submitted:
                if citation_key.strip() and authors.strip() and title.strip():
                    new_ref = {
                        "citation_key": citation_key.strip(),
                        "entry_type": entry_type,
                        "authors": authors.strip(),
                        "title": title.strip(),
                        "journal": journal.strip(),
                        "volume": volume.strip(),
                        "pages": pages.strip(),
                        "year": year.strip(),
                        "doi": doi.strip(),
                    }
                    st.session_state["lit_references"].append(new_ref)
                    st.success(f"✅ Added reference `{citation_key}`.")
                else:
                    st.warning("Citation key, authors, and title are required.")

        refs = st.session_state["lit_references"]
        if refs:
            refs_df = pd.DataFrame(refs)
            st.markdown("#### Stored Reference Library")
            st.dataframe(refs_df, use_container_width=True, hide_index=True)

            col_exp1, col_exp2, col_exp3 = st.columns(3)
            with col_exp1:
                library_json = json.dumps(refs, indent=2)
                st.download_button("⬇️ Download Library (JSON)", data=library_json, file_name="reference_library.json", mime="application/json")
            with col_exp2:
                ris_data = convert_to_ris(refs)
                st.download_button("⬇️ Download Library (RIS)", data=ris_data, file_name="reference_library.ris", mime="text/plain")
            with col_exp3:
                uploaded_bib = st.file_uploader("📥 Upload .bib File", type=["bib"], key="import_bib_file")
                if uploaded_bib is not None:
                    bib_content = uploaded_bib.read().decode("utf-8")
                    parsed_refs = parse_bibtex_string(bib_content)
                    if parsed_refs:
                        st.session_state["lit_references"].extend(parsed_refs)
                        st.success(f"✅ Imported {len(parsed_refs)} entries from BibTeX.")
                        st.rerun()

            st.markdown("---")
            keys = [r["citation_key"] for r in refs if "citation_key" in r]
            if keys:
                selected_key = st.selectbox("Select Reference for BibTeX Preview", keys, key="bibtex_sel_prod")
                ref = next((r for r in refs if r.get("citation_key") == selected_key), None)
                if ref:
                    bibtex_str = f"""@{ref['entry_type']}{{{escape_bibtex(ref['citation_key'])},
  author = {{{escape_bibtex(ref['authors'])},
  title = {{{escape_bibtex(ref['title'])},
  journal = {{{escape_bibtex(ref.get('journal') or 'Unknown')},
  volume = {{{escape_bibtex(ref.get('volume') or 'n/a')},
  pages = {{{escape_bibtex(ref.get('pages') or 'n/a')},
  year = {{{escape_bibtex(ref.get('year') or 'n/a')},
  doi = {{{escape_bibtex(ref.get('doi') or 'n/a')}
}}"""
                    st.code(bibtex_str, language="bibtex")

    with tab_prisma:
        st.markdown("#### PRISMA 2020 Flow Diagram Generator")
        st.caption("Document identification, screening, eligibility, and inclusion metrics for systematic reviews.")

        c_id, c_scr, c_eli, c_inc = st.columns(4)
        with c_id:
            n_identified = st.number_input("Records Identified", value=1250, step=10)
            n_duplicates = st.number_input("Duplicates Removed", value=320, step=5)
        with c_scr:
            n_screened = n_identified - n_duplicates
            st.metric("Records Screened", n_screened)
            n_excluded_screen = st.number_input("Records Excluded", value=810, step=10)
        with c_eli:
            n_reports_sought = n_screened - n_excluded_screen
            st.metric("Full-Text Sought", n_reports_sought)
            n_excluded_elig = st.number_input("Full-Text Excluded", value=85, step=5)
        with c_inc:
            n_included = n_reports_sought - n_excluded_elig
            st.metric("Studies Included", n_included)

        if PLOTLY_AVAILABLE:
            fig_prisma = go.Figure(go.Sankey(
                node=dict(
                    pad=15, thickness=20, line=dict(color="black", width=0.5),
                    label=["Identified", "Duplicates Removed", "Screened", "Excluded at Screening", "Full-Text Assessed", "Excluded at Full-Text", "Included Studies"],
                    color=["#E8A33D", "#E5484D", "#4FB8A6", "#E8A33D", "#8B93A8", "#E5484D", "#34C787"]
                ),
                link=dict(
                    source=[0, 0, 2, 2, 4, 4],
                    target=[1, 2, 3, 4, 5, 6],
                    value=[n_duplicates, n_screened, n_excluded_screen, n_reports_sought, n_excluded_elig, max(0, n_included)]
                )
            ))
            fig_prisma.update_layout(title_text="PRISMA Systematic Review Flow Structure", template="plotly_dark", height=400)
            st.plotly_chart(fig_prisma, use_container_width=True)

    with tab_cluster:
        st.markdown("#### Bibliometric Visualizer")
        results_df = st.session_state.get("lit_search_results")
        if results_df is None or results_df.empty:
            st.info("ℹ️ Execute a search in the **Multi-Engine Search** tab to populate visualizations.")
        elif not PLOTLY_AVAILABLE:
            st.info("Plotly library required for map rendering.")
        else:
            plot_df = results_df.copy()
            plot_df["Year_Num"] = pd.to_numeric(plot_df["Year"], errors="coerce")
            plot_df = plot_df.dropna(subset=["Year_Num"])
            
            if not plot_df.empty:
                plot_df["Year_Num"] = plot_df["Year_Num"].astype(int)
                fig = px.scatter(
                    plot_df, x="Year_Num", y="Citations", size="Citations", color="Journal",
                    hover_name="Title", hover_data=["DOI", "First Author"], template="plotly_dark", height=450
                )
                fig.update_layout(
                    xaxis_title="Publication Year",
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=20, b=0)
                )
                st.plotly_chart(fig, use_container_width=True)


# ==============================================================================
# Meta-Analysis Engine (Fixed/Random Effects, Egger's Test & Funnel Plot)
# ==============================================================================
def render_meta_analysis():
    section_header("📊 Meta-Analysis & Statistical Pooling Engine", "Inverse-variance weighting, Cochran's Q, I² heterogeneity, Egger's test for publication bias, and forest/funnel plots.")

    st.markdown("##### Dynamic Formula Reference")
    st.latex(r"w_i = \frac{1}{SE_i^2 + \tau^2}, \quad Q = \sum w_i (y_i - \hat{\theta})^2, \quad I^2 = \max\left(0, \frac{Q - df}{Q}\right)")

    if "meta_study_table" not in st.session_state:
        st.session_state["meta_study_table"] = pd.DataFrame({
            "Study": ["Primary Trial A", "Primary Trial B", "Primary Trial C"],
            "Effect_Size": [0.45, 0.62, 0.38],
            "Standard_Error": [0.12, 0.15, 0.10],
            "Sample_Size": [120, 95, 150],
        })

    col_load, col_model, col_clear = st.columns([2, 2, 1])
    with col_load:
        if st.button("📥 Load Benchmark Dataset", key="meta_load_benchmark"):
            st.session_state["meta_study_table"] = pd.DataFrame({
                "Study": ["Smith et al. (2024)", "Johnson & Lee (2025)", "Garcia et al. (2025)", "Kula et al. (2026)", "Ochieng et al. (2026)"],
                "Effect_Size": [0.52, 0.68, 0.31, 0.45, 0.59],
                "Standard_Error": [0.11, 0.14, 0.09, 0.12, 0.15],
                "Sample_Size": [210, 180, 310, 140, 195],
            })
            st.rerun()
    with col_model:
        model_type = st.selectbox("Pooling Model", ["Fixed-Effect (Inverse Variance)", "Random-Effects (DerSimonian-Laird)"], key="meta_model_type")
    with col_clear:
        if st.button("🗑️ Clear Rows", key="meta_clear_prod"):
            st.session_state["meta_study_table"] = pd.DataFrame({"Study": [], "Effect_Size": [], "Standard_Error": [], "Sample_Size": []})
            st.rerun()

    edited = st.data_editor(
        st.session_state["meta_study_table"],
        num_rows="dynamic",
        use_container_width=True,
        key="meta_data_editor_prod",
        column_config={
            "Effect_Size": st.column_config.NumberColumn("Effect Size (g / d)", format="%.4f"),
            "Standard_Error": st.column_config.NumberColumn("Standard Error (SE)", format="%.4f", min_value=0.0001),
            "Sample_Size": st.column_config.NumberColumn("Sample Size (N)", format="%d", min_value=1),
        },
    )
    st.session_state["meta_study_table"] = edited

    valid = edited.dropna(subset=["Effect_Size", "Standard_Error"])
    valid = valid[valid["Standard_Error"] > 0]

    if st.button("🚀 Execute Meta-Analysis Engine", type="primary", key="run_meta_prod"):
        if len(valid) < 2:
            st.error("🚫 At least 2 valid study entries with non-zero standard errors are required.")
        else:
            effects = valid["Effect_Size"].values.astype(float)
            ses = valid["Standard_Error"].values.astype(float)
            weights_fe = 1.0 / (ses ** 2)
            
            pooled_fe = np.sum(effects * weights_fe) / np.sum(weights_fe)
            q_stat = np.sum(weights_fe * (effects - pooled_fe) ** 2)
            df_val = len(effects) - 1
            q_p_value = 1.0 - stats.chi2.cdf(q_stat, df_val) if df_val > 0 else np.nan
            i_squared = max(0.0, 100.0 * (q_stat - df_val) / q_stat) if q_stat > 0 else 0.0
            
            c_val = np.sum(weights_fe) - (np.sum(weights_fe ** 2) / np.sum(weights_fe))
            tau_sq = max(0.0, (q_stat - df_val) / c_val) if c_val > 0 else 0.0

            if "Random-Effects" in model_type:
                weights = 1.0 / ((ses ** 2) + tau_sq)
                pooled_effect = np.sum(effects * weights) / np.sum(weights)
                pooled_se = np.sqrt(1.0 / np.sum(weights))
            else:
                weights = weights_fe
                pooled_effect = pooled_fe
                pooled_se = np.sqrt(1.0 / np.sum(weights_fe))

            z_score = pooled_effect / pooled_se
            p_val = 2.0 * (1.0 - stats.norm.cdf(abs(z_score)))
            ci_low, ci_high = pooled_effect - 1.96 * pooled_se, pooled_effect + 1.96 * pooled_se

            precision = 1.0 / ses
            snd = effects / ses
            slope, intercept, r_val, p_egger, std_err = stats.linregress(precision, snd)

            display_df = valid.copy()
            display_df["Weight (%)"] = (weights / weights.sum() * 100.0).round(2)
            display_df["CI_Lower"] = (display_df["Effect_Size"] - 1.96 * display_df["Standard_Error"]).round(3)
            display_df["CI_Upper"] = (display_df["Effect_Size"] + 1.96 * display_df["Standard_Error"]).round(3)

            st.markdown("#### 📋 Weighting & Sensitivity Breakdown")
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric(f"Pooled Effect ({'RE' if 'Random' in model_type else 'FE'})", f"{pooled_effect:.3f}", delta=f"95% CI [{ci_low:.3f}, {ci_high:.3f}]")
            c2.metric("Pooled p-value", f"{p_val:.5f}" if p_val >= 0.0001 else "< 0.0001")
            c3.metric("Heterogeneity (I²)", f"{i_squared:.1f}%", delta=f"τ² = {tau_sq:.4f}")
            c4.metric("Egger's Test Bias p", f"{p_egger:.4f}", delta="Asymmetry Detected" if p_egger < 0.05 else "Symmetrical")

            if PLOTLY_AVAILABLE:
                t_forest, t_funnel = st.tabs(["🌲 Forest Plot", "🎯 Funnel Plot (Publication Bias)"])
                
                with t_forest:
                    fig = go.Figure()
                    for i, (_, row) in enumerate(display_df.iterrows()):
                        fig.add_trace(go.Scatter(
                            x=[row["CI_Lower"], row["CI_Upper"]], y=[i, i],
                            mode="lines", line=dict(color="#4FB8A6", width=2.5), showlegend=False,
                        ))
                        fig.add_trace(go.Scatter(
                            x=[row["Effect_Size"]], y=[i], mode="markers",
                            marker=dict(size=8 + row["Weight (%)"] / 2.5, color="#E8A33D"),
                            name=row["Study"], showlegend=False,
                        ))
                    fig.add_shape(type="line", x0=pooled_effect, y0=-0.8, x1=pooled_effect, y1=len(display_df) - 0.2, line=dict(color="#E5484D", width=2.5, dash="dash"))
                    fig.update_layout(
                        title_text=f"Forest Plot (Pooled Effect = {pooled_effect:.3f}, 95% CI [{ci_low:.3f}, {ci_high:.3f}])",
                        xaxis_title="Effect Size & 95% CI", yaxis_title="Study",
                        yaxis=dict(tickmode="array", tickvals=list(range(len(display_df))), ticktext=display_df["Study"].tolist()),
                        template="plotly_dark", height=max(360, 60 * len(display_df))
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with t_funnel:
                    fig_f = go.Figure()
                    fig_f.add_trace(go.Scatter(
                        x=display_df["Effect_Size"], y=display_df["Standard_Error"],
                        mode="markers", marker=dict(size=10, color="#E8A33D"), text=display_df["Study"]
                    ))
                    max_se = max(display_df["Standard_Error"]) * 1.1
                    se_seq = np.linspace(0.001, max_se, 50)
                    fig_f.add_trace(go.Scatter(x=pooled_effect - 1.96 * se_seq, y=se_seq, mode="lines", line=dict(color="gray", dash="dash"), showlegend=False))
                    fig_f.add_trace(go.Scatter(x=pooled_effect + 1.96 * se_seq, y=se_seq, mode="lines", line=dict(color="gray", dash="dash"), showlegend=False))
                    fig_f.add_shape(type="line", x0=pooled_effect, y0=0, x1=pooled_effect, y1=max_se, line=dict(color="#E5484D", dash="solid"))
                    
                    fig_f.update_layout(
                        title_text="Funnel Plot for Publication Bias Inspection",
                        xaxis_title="Effect Size", yaxis_title="Standard Error (SE)",
                        yaxis=dict(autorange="reversed"), template="plotly_dark", height=400
                    )
                    st.plotly_chart(fig_f, use_container_width=True)

            render_export_buttons(display_df, base_name="meta_analysis_pooled_results")


# ==============================================================================
# APA Compliance Inspector & Standardized Templates
# ==============================================================================
def inspect_apa_citation(citation: str):
    c = citation.strip()
    checks = [
        ("Author format (Surname, Initial.)", bool(re.match(r"^[A-Z][A-Za-z'\-]+\,\s*[A-Z]\.", c))),
        ("Parenthetical publication year e.g. (2026)", bool(re.search(r"\((1[5-9]\d{2}|20\d{2})[a-z]?\)", c))),
        ("Punctuation structure density", c.count(".") >= 2),
        ("Volume/issue or page range pattern", bool(re.search(r"\b\d+\s*\(\d+\)|\b\d+[\-–—]\d+\b", c))),
        ("DOI / URL pattern presence", bool(re.search(r"https?://\S+|10\.\d{4,9}/\S+", c))),
    ]
    passed = sum(1 for _, ok in checks if ok)
    return checks, passed, len(checks)


def render_apa_outputs():
    section_header("📏 APA 7th Edition Formatting & Citation Compliance", "Standardized reporting templates, heuristic structural citation inspector, and publication data tables.")

    tab_apa, tab_cite, tab_tables = st.tabs(["📑 APA Templates", "🔍 Citation Inspector", "📋 Publication Tables"])

    with tab_apa:
        st.markdown("#### APA 7th Edition Standardized Write-Up Templates")
        test_type = st.selectbox("Select Statistical Procedure", [
            "Independent Samples t-Test", "One-Way Analysis of Variance (ANOVA)", 
            "Pearson Product-Moment Correlation", "Chi-Square Test of Independence", "Multiple Linear Regression"
        ], key="apa_test_prod")

        templates = {
            "Independent Samples t-Test": "An independent-samples t-test was conducted to compare [Dependent Variable] between [Group A] and [Group B]. There was a statistically significant difference between the groups, t(df) = [X.XX], p = [.XXX], Cohen's d = [X.XX].",
            "One-Way Analysis of Variance (ANOVA)": "A one-way ANOVA was conducted to evaluate the effect of [Independent Variable] on [Dependent Variable]. The overall effect was statistically significant, F(df_between, df_within) = [X.XX], p = [.XXX], partial η² = [X.XX].",
            "Pearson Product-Moment Correlation": "A Pearson correlation coefficient was computed to assess the linear relationship between [Variable A] and [Variable B]. There was a strong, positive correlation between the two variables, r(df) = [X.XX], p = [.XXX].",
            "Chi-Square Test of Independence": "A chi-square test of independence was performed to examine the association between [Categorical Var A] and [Categorical Var B]. The relation between these variables was significant, χ²(df, N = XXX) = [X.XX], p = [.XXX], Cramer's V = [X.XX].",
            "Multiple Linear Regression": "A multiple linear regression was calculated to predict [Dependent Variable] from [Predictor 1] and [Predictor 2]. A significant regression equation was found, F(df_reg, df_res) = [X.XX], p = [.XXX], with an R² of [X.XX].",
        }
        st.code(templates[test_type], language="markdown")
        st.download_button("⬇️ Download Template (.md)", data=templates[test_type], file_name=f"apa_{test_type.lower().replace(' ', '_')}.md", mime="text/markdown")

    with tab_cite:
        st.markdown("#### Structural Citation Inspector (Heuristic APA Validator)")
        citation_input = st.text_area("Paste Citation String to Audit", placeholder="Kula, C. (2026). Multi-omics biomarkers in clinical diagnostics. Journal of Biomedical Informatics, 42(3), 112-125. https://doi.org/10.1016/j.jbi.2026.100000", key="cite_input_prod")
        if st.button("🔍 Run Structural Inspection", type="primary", key="run_cite_prod"):
            if citation_input.strip():
                checks, passed, total = inspect_apa_citation(citation_input)
                for label, ok in checks:
                    st.markdown(f"{'✅' if ok else '❌'} {label}")
                if passed == total:
                    st.success(f"✅ All {total} structural checks passed.")
                else:
                    st.warning(f"⚠️ Passed {passed}/{total} structural checks.")
            else:
                st.warning("Please enter a citation string.")

    with tab_tables:
        st.markdown("#### Publication-Ready APA Statistical Table Generator")
        default_stub = pd.DataFrame({
            "Variable": ["Age (Years)", "Baseline Biomarker (ng/mL)", "Post-Intervention Biomarker", "Mean Difference", "Cohen's d"],
            "Experimental Group": ["45.2 (7.1)", "2.41 (0.35)", "1.12 (0.18)", "-1.29", "2.84"],
            "Control Group": ["44.8 (6.9)", "2.39 (0.32)", "2.35 (0.31)", "-0.04", "0.11"],
            "t-statistic / F": ["0.42", "0.38", "14.21", "11.50", "—"],
            "p-value": [".675", ".704", "< .001", "< .001", "—"],
        })
        edited_table = st.data_editor(default_stub, num_rows="dynamic", use_container_width=True, key="apa_table_editor_prod")
        render_export_buttons(edited_table, base_name="apa_publication_table")


def render_grants_and_quality():
    section_header("📜 Grant Proposal Formatter & Quality Assessor", "Customizable institutional grant builder and multidimensional research rigor evaluation suite.")

    tab_grant, tab_quality = st.tabs(["📜 Grant Proposal Formatter", "✅ Research Quality Assessor"])

    with tab_grant:
        st.markdown("#### Institutional Grant Proposal Builder")
        col1, col2 = st.columns(2)
        with col1:
            grant_title = st.text_input("Grant Project Title", value="Integrated Multi-Omics Platform for Early Diagnostic Precision", key="grant_title_prod")
            pi_name = st.text_input("Principal Investigator (PI)", value="Dr. Chris Kula, Ph.D.", key="grant_pi_prod")
        with col2:
            amount = st.number_input("Requested Funding Budget ($ USD)", value=250000.0, step=10000.0, key="grant_amount_prod")
            agency = st.selectbox("Funding Agency", ["National Science Foundation (NSF)", "National Institutes of Health (NIH)", "Wellcome Trust", "Gates Foundation"], key="grant_agency_prod")

        abstract_text = st.text_area("Abstract & Specific Aims", value="This project establishes an automated computational framework to overcome bottlenecks in multi-omics integration and biomarker validation.", height=100, key="grant_abstract_prod")
        background_text = st.text_area("Background & Significance", value="Current literature demonstrates critical gaps in reproducible bioinformatics pipelines. This proposal addresses this limitation.", height=100, key="grant_background_prod")
        methodology_text = st.text_area("Research Design & Methodology", value="We utilize robust statistical validation, modular Python architectures, and cross-validated algorithms.", height=100, key="grant_methodology_prod")

        if st.button("📜 Generate Grant Package", type="primary", key="run_grant_prod"):
            proposal_text = f"""# INSTITUTIONAL GRANT PROPOSAL: {agency.upper()}
**Project Title:** {grant_title}
**Principal Investigator:** {pi_name}
**Requested Budget:** ${amount:,.2f}
**Submission Date:** {datetime.date.today().isoformat()}

## 1. Abstract & Specific Aims
{abstract_text}

## 2. Background & Significance
{background_text}

## 3. Research Design & Methodology
{methodology_text}

## 4. Budget Justification
* **Personnel & Research Fellows (60%):** ${amount * 0.6:,.2f}
* **Computational Infrastructure & Cloud Hosting (30%):** ${amount * 0.3:,.2f}
* **Open-Access Dissemination (10%):** ${amount * 0.1:,.2f}
"""
            st.code(proposal_text, language="markdown")
            st.download_button("⬇️ Download Grant Package (.md)", data=proposal_text, file_name="grant_proposal_package.md", mime="text/markdown")

    with tab_quality:
        st.markdown("#### Multidimensional Research Rigor Assessment")
        dims = ["Design Rigor & Control", "Sample Size Adequacy", "Measurement Validity", "Statistical Power", "Reporting Transparency"]
        scores = {}
        cols = st.columns(2)
        for i, dim in enumerate(dims):
            scores[dim] = cols[i % 2].slider(dim, 0, 100, 75, key=f"quality_score_prod_{i}")

        if st.button("✅ Calculate Rigor Index", type="primary", key="run_quality_prod"):
            avg_score = float(np.mean(list(scores.values())))
            st.metric("Overall Research Quality Index", f"{avg_score:.1f} / 100")
            st.progress(int(avg_score))
            verdict = "Strong — publication ready" if avg_score >= 85 else ("Moderate — minor revisions recommended" if avg_score >= 65 else "Weak — methodological overhaul required")
            st.success(f"**Evaluation Verdict:** {verdict}")


def render_publication_pipeline():
    section_header("🚀 Publication Lifecycle Reference", "Standard operating roadmap from literature discovery to publication.")

    steps = [
        ("📚 Phase 1: Multi-Engine Literature Search", "Execute CrossRef and PubMed queries; store references and generate PRISMA flow charts."),
        ("📊 Phase 2: Meta-Analysis & Publication Bias Audit", "Pool effect sizes, evaluate Cochran's Q and I², and check funnel plots/Egger's test."),
        ("📏 Phase 3: APA Formatting & Tables", "Draft manuscript sections using standardized statistical write-ups and data editors."),
        ("🔍 Phase 4: Citation Compliance & RIS/BibTeX Export", "Audit reference strings with the heuristic inspector and export `.ris` / `.bib` files."),
        ("🚀 Phase 5: Grant Packaging & Final Compilation", "Generate formatted markdown grant applications and compile complete study documentation."),
    ]

    for i, (title, desc) in enumerate(steps, 1):
        st.markdown(
            f"""<div style="display:flex; gap:1rem; align-items:center; background:#171B23; border:1px solid #262B33; border-radius:10px; padding:1.0rem 1.2rem; margin-bottom:0.75rem;">
                <div style="background:#e8a33d22; color:#e8a33d; border-radius:50%; width:36px; height:36px; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:1.1rem;">{i}</div>
                <div><div style="font-weight:700; color:#EDEFF2; font-size:1.05rem;">{title}</div><div style="color:#6B7280; font-size:0.9rem;">{desc}</div></div>
            </div>""",
            unsafe_allow_html=True,
        )


def render_academic_vault():
    section_header("📁 Academic Report Vault", "Academic publications & fieldwork repository.")

    try:
        from modules.legacy_research_data import get_academic_vault_df, add_academic_report
        reports_df = get_academic_vault_df()
        for _, row in reports_df.iterrows():
            with st.expander(f"📖 [{row['course_code']}] {row['title']}"):
                st.write(f"**Department:** {row['department']} | **Status:** `{row['status']}`")
                st.write(row["abstract_text"])

        with st.expander("➕ Add a report to the vault"):
            with st.form("academic_vault_add"):
                title = st.text_input("Title")
                c1, c2, c3 = st.columns(3)
                course_code = c1.text_input("Course Code")
                department = c2.text_input("Department")
                status = c3.selectbox("Status", ["Planning", "In Progress", "Submitted", "Completed"])
                abstract = st.text_area("Abstract")
                if st.form_submit_button("Add to Vault"):
                    if title.strip():
                        add_academic_report(title, course_code, department, status, abstract)
                        st.success("Report added.")
                        st.rerun()
                    else:
                        st.warning("Title is required.")
    except ImportError:
        st.info("Academic vault storage module (`modules.legacy_research_data`) is not currently accessible.")


def render_reference_manager():
    """Real, persistent AI-assisted reference manager — the EndNote-style
    core of this hub. See modules/reference_manager.py for what's real
    vs. what's an honest, labeled fallback."""
    from modules.reference_manager import (
        add_reference, list_references, get_reference_pdf, delete_reference,
        update_reference, extract_pdf_text, guess_metadata_from_pdf_text,
        find_duplicates, semantic_search, CITATION_STYLES, suggest_tags,
        llm_available, validate_citation_key, export_bibtex, export_ris,
        list_collections, add_to_collection, remove_from_collection,
        get_reference_collections, list_references_in_collection, ask_library,
    )

    owner = st.session_state.get("user_identity", {}).get("email", "anonymous")

    st.caption(
        "A persistent reference library that survives across sessions — PDF metadata "
        "extraction, duplicate detection, TF-IDF semantic search, multi-style "
        "citation formatting, groups/collections, and grounded AI Q&A over your own "
        "library, all genuinely working end to end."
    )
    if not llm_available():
        st.caption("🔌 AI features are running on honest, labeled fallbacks (keyword tags, search-only Q&A) — set `ANTHROPIC_API_KEY` in secrets to enable full LLM-assisted features.")

    tab_add, tab_library, tab_search, tab_ask, tab_cite, tab_export = st.tabs([
        "➕ Add Reference", "📚 My Library", "🔍 Smart Search", "🤖 Ask Your Library",
        "📝 Generate Citations", "📤 Export"
    ])

    with tab_add:
        st.markdown("#### Add from PDF (auto-extracts metadata)")
        uploaded_pdf = st.file_uploader("Upload a PDF", type=["pdf"], key="ref_pdf_upload")
        guessed = {}
        pdf_text = ""
        if uploaded_pdf is not None:
            pdf_bytes = uploaded_pdf.getvalue()
            pdf_text = extract_pdf_text(pdf_bytes)
            if pdf_text:
                guessed = guess_metadata_from_pdf_text(pdf_text)
                st.success(f"Extracted from PDF — Title: *{guessed.get('title') or '(not found)'}*, Year: {guessed.get('year') or '(not found)'}, DOI: {guessed.get('doi') or '(not found)'}")
            else:
                st.warning("Couldn't extract text from this PDF (may be scanned/image-only). You can still fill in the fields manually below.")

        with st.form("ref_add_form"):
            c1, c2 = st.columns(2)
            with c1:
                citation_key = st.text_input("Citation Key", placeholder="smith2024", help="Letters, numbers, hyphens, underscores only — no spaces.")
                authors = st.text_input("Authors", placeholder="Smith, J., & Doe, A.")
                title = st.text_input("Title", value=guessed.get("title", ""))
                entry_type = st.selectbox("Entry Type", ["article", "inproceedings", "book", "phdthesis"])
            with c2:
                journal = st.text_input("Journal / Conference")
                volume = st.text_input("Volume")
                issue = st.text_input("Issue")
                pages = st.text_input("Pages", placeholder="112-125")
                year = st.text_input("Year", value=guessed.get("year", ""))
                doi = st.text_input("DOI", value=guessed.get("doi", ""))
            abstract = st.text_area("Abstract (optional, improves search + AI Q&A + tag suggestions)")
            tags = st.text_input("Tags (comma-separated, optional)")
            collection = st.text_input("Add to collection/group (optional)", placeholder="e.g. Thesis Chapter 2")
            submitted = st.form_submit_button("➕ Add to Library", type="primary")

        if submitted:
            key_ok, key_msg = validate_citation_key(citation_key)
            if not key_ok:
                st.error(key_msg)
            elif not (authors.strip() and title.strip()):
                st.error("Authors and title are required.")
            else:
                dupes = find_duplicates(owner, title, doi)
                if dupes:
                    st.warning(f"⚠️ Possible duplicate: '{dupes[0]['title']}' ({dupes[0]['match_reason']}, similarity {dupes[0]['similarity']:.0%}). Submit again to add anyway.")
                entry = {
                    "citation_key": citation_key.strip(), "entry_type": entry_type,
                    "authors": authors.strip(), "title": title.strip(),
                    "journal": journal.strip(), "volume": volume.strip(), "issue": issue.strip(),
                    "pages": pages.strip(), "year": year.strip(), "doi": doi.strip(),
                    "abstract": abstract.strip(), "tags": tags.strip(),
                }
                pdf_bytes = uploaded_pdf.getvalue() if uploaded_pdf is not None else None
                pdf_filename = uploaded_pdf.name if uploaded_pdf is not None else None
                ok, msg = add_reference(owner, entry, pdf_bytes, pdf_filename, pdf_text)
                (st.success if ok else st.error)(msg)
                if ok:
                    if collection.strip():
                        new_refs = list_references(owner)
                        matching = [r for r in new_refs if r["citation_key"] == citation_key.strip()]
                        if matching:
                            add_to_collection(owner, matching[0]["id"], collection.strip())
                    if not tags.strip():
                        suggested, source = suggest_tags(entry)
                        if suggested:
                            st.info(f"💡 Suggested tags ({source}): {', '.join(suggested)}")
                    st.rerun()

    with tab_library:
        collections = list_collections(owner)
        filter_collection = st.selectbox("Filter by collection", ["All References"] + collections, key="lib_filter_collection")
        refs = list_references_in_collection(owner, filter_collection) if filter_collection != "All References" else list_references(owner)

        if not refs:
            st.info("Your library is empty — add your first reference in the **Add Reference** tab.")
        else:
            st.markdown(f"#### {len(refs)} reference(s)")
            for ref in refs:
                with st.expander(f"📄 {ref['citation_key']} — {ref['title'][:80]}"):
                    edit_mode = st.session_state.get(f"editing_{ref['id']}", False)

                    if edit_mode:
                        with st.form(f"edit_form_{ref['id']}"):
                            e_authors = st.text_input("Authors", value=ref["authors"], key=f"e_auth_{ref['id']}")
                            e_title = st.text_input("Title", value=ref["title"], key=f"e_title_{ref['id']}")
                            e_journal = st.text_input("Journal", value=ref["journal"] or "", key=f"e_journal_{ref['id']}")
                            e_year = st.text_input("Year", value=ref["year"] or "", key=f"e_year_{ref['id']}")
                            e_doi = st.text_input("DOI", value=ref["doi"] or "", key=f"e_doi_{ref['id']}")
                            e_tags = st.text_input("Tags", value=ref["tags"] or "", key=f"e_tags_{ref['id']}")
                            save_col, cancel_col = st.columns(2)
                            with save_col:
                                save_clicked = st.form_submit_button("💾 Save", type="primary")
                            with cancel_col:
                                cancel_clicked = st.form_submit_button("Cancel")
                        if save_clicked:
                            ok, msg = update_reference(ref["id"], owner, {
                                **ref, "authors": e_authors, "title": e_title,
                                "journal": e_journal, "year": e_year, "doi": e_doi, "tags": e_tags,
                            })
                            (st.success if ok else st.error)(msg)
                            st.session_state[f"editing_{ref['id']}"] = False
                            st.rerun()
                        if cancel_clicked:
                            st.session_state[f"editing_{ref['id']}"] = False
                            st.rerun()
                    else:
                        c1, c2 = st.columns([4, 1])
                        with c1:
                            st.write(f"**Authors:** {ref['authors']}")
                            st.write(f"**Year:** {ref['year'] or '—'} | **Journal:** {ref['journal'] or '—'}")
                            if ref["doi"]:
                                st.write(f"**DOI:** {ref['doi']}")
                            if ref["tags"]:
                                st.caption(f"Tags: {ref['tags']}")
                            ref_collections = get_reference_collections(owner, ref["id"])
                            if ref_collections:
                                st.caption(f"📁 In: {', '.join(ref_collections)}")
                            if ref["pdf_filename"]:
                                pdf_bytes, pdf_name = get_reference_pdf(ref["id"])
                                if pdf_bytes:
                                    st.download_button("📥 Download attached PDF", data=pdf_bytes, file_name=pdf_name, key=f"dl_{ref['id']}")
                        with c2:
                            if st.button("✏️ Edit", key=f"edit_btn_{ref['id']}"):
                                st.session_state[f"editing_{ref['id']}"] = True
                                st.rerun()
                            if st.button("🗑️ Delete", key=f"del_ref_{ref['id']}"):
                                delete_reference(ref["id"], owner)
                                st.rerun()

                        with st.form(f"collection_form_{ref['id']}", clear_on_submit=True):
                            new_collection = st.text_input("Add to collection", key=f"new_coll_{ref['id']}", placeholder="e.g. Thesis Chapter 2")
                            if st.form_submit_button("📁 Add"):
                                if new_collection.strip():
                                    add_to_collection(owner, ref["id"], new_collection.strip())
                                    st.rerun()

    with tab_search:
        st.markdown("#### Semantic Search")
        st.caption("Ranks by real term relevance (TF-IDF + cosine similarity) across title, abstract, tags, and extracted PDF text — not just keyword matching.")
        query = st.text_input("Search your library", placeholder="e.g. climate prediction using neural networks")
        if query:
            results = semantic_search(owner, query)
            if not results:
                st.info("No relevant matches found.")
            for r in results:
                st.markdown(f"**{r['citation_key']}** — {r['title']}  \n*Relevance: {r['relevance']:.0%} · {r['authors']} ({r['year'] or 'n.d.'})*")
                st.markdown("---")

    with tab_ask:
        st.markdown("#### 🤖 Ask Your Library")
        st.caption(
            "Grounded Q&A: retrieves your most relevant references via real semantic search, "
            "then (if AI is configured) answers strictly from those references, citing them "
            "by number — it won't make things up beyond what's in your library."
        )
        question = st.text_input("Ask a question about your references", placeholder="What methods do my papers use for X?")
        if question:
            result = ask_library(owner, question)
            if result["mode"] == "no_results":
                st.info("No relevant references found in your library for this question.")
            elif result["mode"] == "ai_answered":
                st.markdown(result["answer"])
                with st.expander("📚 Sources used"):
                    for i, s in enumerate(result["sources"], 1):
                        st.write(f"[{i}] {s['citation_key']} — {s['title']} ({s['year'] or 'n.d.'})")
            elif result["mode"] == "ai_error":
                st.warning(f"AI call failed ({result.get('error', 'unknown error')}) — showing matched references instead:")
                for s in result["sources"]:
                    st.write(f"**{s['citation_key']}** — {s['title']} (relevance {s['relevance']:.0%})")
            else:  # search_only
                st.info("AI answering isn't configured (`ANTHROPIC_API_KEY` not set) — showing the most relevant references instead:")
                for s in result["sources"]:
                    st.write(f"**{s['citation_key']}** — {s['title']} (relevance {s['relevance']:.0%})")

    with tab_cite:
        refs = list_references(owner)
        if not refs:
            st.info("Add references first to generate citations.")
        else:
            style_name = st.selectbox("Citation Style", list(CITATION_STYLES.keys()))
            selected_keys = st.multiselect("References to cite", [r["citation_key"] for r in refs], default=[r["citation_key"] for r in refs])
            if selected_keys:
                fmt_fn = CITATION_STYLES[style_name]
                selected_refs = [r for r in refs if r["citation_key"] in selected_keys]
                lines = []
                for i, ref in enumerate(selected_refs, 1):
                    line = fmt_fn(ref, i) if style_name in ("IEEE", "Vancouver") else fmt_fn(ref)
                    lines.append(line)
                bibliography = "\n\n".join(lines)
                st.text_area("Generated Bibliography", value=bibliography, height=250)
                st.download_button("⬇️ Download Bibliography (.txt)", data=bibliography, file_name=f"bibliography_{style_name.split()[0].lower()}.txt")

    with tab_export:
        refs = list_references(owner)
        if not refs:
            st.info("Add references first to export.")
        else:
            st.markdown("#### Export Your Library")
            export_keys = st.multiselect("References to export", [r["citation_key"] for r in refs], default=[r["citation_key"] for r in refs], key="export_select")
            selected = [r for r in refs if r["citation_key"] in export_keys]
            if selected:
                c1, c2 = st.columns(2)
                with c1:
                    bibtex_str = export_bibtex(selected)
                    st.download_button("⬇️ Export BibTeX (.bib)", data=bibtex_str, file_name="library.bib", mime="text/plain")
                with c2:
                    ris_str = export_ris(selected)
                    st.download_button("⬇️ Export RIS (.ris)", data=ris_str, file_name="library.ris", mime="text/plain", help="Compatible with EndNote, Zotero, and Mendeley import.")


def main():
    try:
        from modules.subscription import require_active_subscription
        require_active_subscription(hub_id="literature")
    except ImportError:
        pass

    setup_page("Literature & Publishing Hub", "📚", initial_sidebar_state="expanded")

    try:
        from modules.user_preferences import render_readability_fix, render_accent_color_css
        render_readability_fix()
        render_accent_color_css()
    except ImportError:
        pass

    hero_card(
        "📚 Literature & Publishing Hub — Advanced Suite",
        "Comprehensive academic platform featuring CrossRef & PubMed search, RIS/BibTeX management, PRISMA 2020 flow charts, meta-analysis (forest/funnel plots & Egger's test), APA compliance tools, and grant proposal formatting.",
        badge_text="LITERATURE & PUBLISHING HUB • ADVANCED TIER",
    )

    tabs = st.tabs([
        "🧠 AI Reference Manager",
        "📚 Literature & References",
        "📊 Meta-Analysis Studio",
        "📏 APA & Citations",
        "📜 Grants & Quality",
        "🚀 Publication Pipeline",
        "📁 Academic Report Vault",
    ])

    with tabs[0]:
        render_reference_manager()
    with tabs[1]:
        render_literature_search()
    with tabs[2]:
        render_meta_analysis()
    with tabs[3]:
        render_apa_outputs()
    with tabs[4]:
        render_grants_and_quality()
    with tabs[5]:
        render_publication_pipeline()
    with tabs[6]:
        render_academic_vault()

    render_standard_footer("LITERATURE & PUBLISHING HUB")


if __name__ == "__main__":
    main()