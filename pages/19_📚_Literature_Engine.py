"""
📚 Global Literature Aggregator & Auto-Drafting Engine
=====================================================
Fetch REAL papers from Semantic Scholar, build your working bibliography,
write your own findings, and generate publication-ready references.

Core Principles:
- ✅ ZERO AI-generated citations — every paper is REAL, from live APIs
- ✅ ZERO AI-written text — every word is authored by YOU
- ✅ 100% factual — Semantic Scholar + CrossRef, no hallucination
- ✅ Instant persistence — SQLite saves every click instantly
- ✅ Unlimited paper fetching — paginate through thousands of real papers
- ✅ Papers used in your report are marked 🔖 CITED
- ✅ Multi-format exports: MD, HTML, TXT, .BIB, Notion, Google Drive
"""
import base64
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Literature Engine", layout="wide", page_icon="📚")

from modules.config import init_session_state
from modules.ui_components import hero_card, load_css, watermark, section_header
from modules.literature_engine import (
    LiteratureDatabase,
    PaperHarvester,
    ReferenceFormatter,
    DraftingEngine,
    ExportEngine,
    render_paper_table_row,
    render_report_builder,
)

# ─── Init ─────────────────────────────────────────────────────────────
init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")
hero_card(
    "📚 Global Literature Aggregator & Auto-Drafting Engine",
    "Fetch unlimited real academic papers, build your bibliography, write your own findings, and export in multiple formats — zero AI hallucination, zero plagiarism.",
    badge_text="v2.0 — Unlimited Fetch + Multi-Export"
)
watermark("CHRISHEM")

# ─── Initialize Engine ───────────────────────────────────────────────
db = LiteratureDatabase()
harvester = PaperHarvester()
formatter = ReferenceFormatter()
exporter = ExportEngine()

# ─── Session State for this page ─────────────────────────────────────
if "lit_engine_project_id" not in st.session_state:
    st.session_state["lit_engine_project_id"] = None
if "lit_engine_last_topic" not in st.session_state:
    st.session_state["lit_engine_last_topic"] = ""
if "lit_engine_last_country" not in st.session_state:
    st.session_state["lit_engine_last_country"] = ""
if "lit_engine_fetch_count" not in st.session_state:
    st.session_state["lit_engine_fetch_count"] = 0
if "lit_engine_last_save" not in st.session_state:
    st.session_state["lit_engine_last_save"] = None
if "lit_engine_generated_report" not in st.session_state:
    st.session_state["lit_engine_generated_report"] = None

# ═══════════════════════════════════════════════════════════════════════
# 1. PROJECT SELECTION / CREATION
# ═══════════════════════════════════════════════════════════════════════
st.sidebar.markdown("## 📚 Research Projects")
st.sidebar.caption("Auto-saved to SQLite — safe from crashes.")

projects = db.get_projects()

# Auto-save indicator
if st.session_state.get("lit_engine_last_save"):
    st.sidebar.caption(f"💾 Last auto-save: {st.session_state['lit_engine_last_save']}")

project_options = {p["id"]: f"📖 {p['name']}" for p in projects}
project_options[0] = "➕ Create New Project"

selected_option = st.sidebar.selectbox(
    "Select or create project",
    options=list(project_options.keys()),
    format_func=lambda x: project_options.get(x, f"Project #{x}"),
    index=0 if st.session_state["lit_engine_project_id"] is None
           else (list(project_options.keys()).index(st.session_state["lit_engine_project_id"])
                 if st.session_state["lit_engine_project_id"] in project_options else 0),
    key="lit_project_selector",
)

if selected_option == 0:
    with st.sidebar.expander("🆕 Create New Project", expanded=True):
        new_name = st.text_input("Project name", placeholder="e.g., Climate Change in East Africa")
        new_topic = st.text_input("Research Topic / Keywords", placeholder="e.g., climate adaptation, agriculture")
        new_country = st.text_input("Country of Study (optional)", placeholder="e.g., Kenya")
        if st.button("🚀 Create Project", type="primary", use_container_width=True) and new_name:
            pid = db.create_project(name=new_name, topic=new_topic, country=new_country)
            if pid:
                st.session_state["lit_engine_project_id"] = pid
                st.session_state["lit_engine_last_save"] = datetime.now().strftime("%H:%M:%S")
                st.success(f"✅ Project '{new_name}' created!")
                st.rerun()
else:
    st.session_state["lit_engine_project_id"] = selected_option

# Get current project
project_id = st.session_state.get("lit_engine_project_id")
if project_id:
    project = db.get_project(project_id)
    if project:
        st.sidebar.success(f"📌 **{project['name']}**")
        st.sidebar.caption(f"Topic: {project.get('topic', 'N/A')} | Country: {project.get('country', 'N/A')}")

        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("✏️ Edit", use_container_width=True):
                st.session_state["_edit_project"] = True
        with col2:
            if st.button("🗑️ Delete", use_container_width=True):
                db.delete_project(project_id)
                st.session_state["lit_engine_project_id"] = None
                st.success("Project deleted.")
                st.rerun()

        if st.session_state.get("_edit_project"):
            with st.sidebar.expander("Edit Project", expanded=True):
                edit_name = st.text_input("Name", value=project["name"])
                edit_topic = st.text_input("Topic", value=project.get("topic", ""))
                edit_country = st.text_input("Country", value=project.get("country", ""))
                if st.button("💾 Save Changes"):
                    db.update_project(project_id, name=edit_name, topic=edit_topic, country=edit_country)
                    st.session_state["_edit_project"] = False
                    st.session_state["lit_engine_last_save"] = datetime.now().strftime("%H:%M:%S")
                    st.success("✅ Updated!")
                    st.rerun()
                if st.button("❌ Cancel"):
                    st.session_state["_edit_project"] = False
                    st.rerun()

        # Enhanced stats
        stats = db.get_statistics(project_id)
        st.sidebar.markdown("---")
        st.sidebar.metric("📊 Total Papers", stats["total_papers"])
        st.sidebar.metric("✅ Checked Papers", stats["checked_papers"])
        st.sidebar.metric("🔖 Cited in Report", stats.get("cited_papers", 0))
        st.sidebar.metric("🏆 Max Citations", stats["max_citations"])
        st.sidebar.caption(f"📅 Year range: {stats['year_range']}")

if not project_id:
    st.info("👈 **Start by creating or selecting a project** from the sidebar.")
    st.markdown("""
    ### 📖 How it works

    1. **Create a project** → Give it a name, topic, and country
    2. **Harvest papers** → Fetch unlimited real papers from Semantic Scholar
    3. **Check papers** → Select papers for your working bibliography
    4. **Add findings** → Write your own notes and findings for each paper
    5. **Build report** → Write your paper sections and insert citations
    6. **Export** → Download as MD/HTML/TXT/.BIB, push to Notion, or save to Google Drive
    """)
    st.stop()

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 Paper Harvester",
    "📋 Working Bibliography",
    "✍️ Report Builder",
    "📑 Reference Engine",
])

# ══════════════════════════════════════════════════════════════════════════
# TAB 1: PAPER HARVESTER — Unlimited fetching
# ══════════════════════════════════════════════════════════════════════════
with tab1:
    section_header("🔍 Harvest Real Academic Papers")
    st.caption("Fetch unlimited real papers from Semantic Scholar + CrossRef. Every paper is REAL. Use the pagination to browse through thousands.")

    default_topic = project.get("topic", "") or ""
    default_country = project.get("country", "") or ""

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        topic = st.text_input(
            "Research Topic / Keywords",
            value=st.session_state.get("lit_engine_last_topic", default_topic),
            placeholder="e.g., machine learning for climate change adaptation",
            key="harvester_topic",
        )
    with col2:
        country = st.text_input(
            "Country of Study (optional)",
            value=st.session_state.get("lit_engine_last_country", default_country),
            placeholder="e.g., Kenya",
            key="harvester_country",
        )
    with col3:
        # Unlimited — user can choose any number
        fetch_limit = st.number_input(
            "Papers to fetch",
            min_value=10, max_value=5000, value=100, step=10,
            key="harvester_limit",
            help="Unlimited — fetch up to 5000 papers in one go. The API will paginate automatically.",
        )

    if topic and topic != project.get("topic", ""):
        db.update_project(project_id, topic=topic)
    if country and country != project.get("country", ""):
        db.update_project(project_id, country=country)

    col1, col2 = st.columns([1, 3])
    with col1:
        fetch_clicked = st.button(
            f"🚀 Fetch {fetch_limit} Papers",
            type="primary",
            use_container_width=True,
            disabled=not topic.strip(),
        )
    with col2:
        if st.session_state.get("lit_engine_fetch_count", 0) > 0:
            st.info(f"📊 Total papers in project: {stats['total_papers']}")

    if fetch_clicked and topic.strip():
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(current, total):
            progress_bar.progress(min(current / total, 1.0))
            status_text.text(f"🔍 Fetched {current}/{total} papers...")

        with st.spinner(f"🔍 Searching Semantic Scholar for '{topic}'..."):
            st.session_state["lit_engine_last_topic"] = topic
            st.session_state["lit_engine_last_country"] = country

            papers = harvester.search_combined(
                query=topic.strip(),
                country=country.strip(),
                limit=fetch_limit,
            )

            if papers:
                saved = db.save_papers(project_id, papers)
                st.session_state["lit_engine_fetch_count"] = saved
                st.session_state["lit_engine_last_save"] = datetime.now().strftime("%H:%M:%S")
                progress_bar.progress(1.0)
                status_text.text(f"✅ Found {len(papers)} papers, saved {saved} new ones!")
                st.success(f"✅ Found {len(papers)} papers, saved {saved} new ones to your project!")
            else:
                st.warning("⚠️ No papers found. Try different keywords.")

    # Display fetched papers with pagination
    st.markdown("---")
    section_header("📄 Fetched Papers")

    per_page = 20
    page = st.number_input("Page", min_value=0, value=0, step=1, key="harvester_page")

    papers, total = db.get_papers(project_id, checked_only=False, page=page, per_page=per_page)
    total_pages = max(0, (total - 1) // per_page)

    if papers:
        st.caption(f"Showing {page * per_page + 1}–{min((page + 1) * per_page, total)} of {total} papers")

        for paper in papers:
            render_paper_table_row(paper, db)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if page > 0 and st.button("⬅️ Previous", use_container_width=True):
                st.session_state["harvester_page"] = page - 1
                st.rerun()
        with col2:
            st.markdown(f"<div style='text-align:center;'>Page {page + 1} of {total_pages + 1}</div>", unsafe_allow_html=True)
        with col3:
            if page < total_pages and st.button("Next ➡️", use_container_width=True):
                st.session_state["harvester_page"] = page + 1
                st.rerun()
    else:
        if st.session_state.get("lit_engine_fetch_count", 0) > 0:
            st.info("📭 All papers filtered out. Try modifying your search.")
        else:
            st.info("🔍 No papers yet. Use the search above to fetch papers from Semantic Scholar.")

# ══════════════════════════════════════════════════════════════════════════
# TAB 2: WORKING BIBLIOGRAPHY
# ══════════════════════════════════════════════════════════════════════════
with tab2:
    section_header("📋 Working Bibliography")
    st.caption("Papers you've checked will appear here. Papers marked 🔖 CITED have been used in your report.")

    bibliography = db.get_bibliography(project_id)

    if not bibliography:
        st.info("📭 No papers checked yet. Go to **Paper Harvester** tab, find papers, and check the boxes to add them here.")
    else:
        # Count cited papers
        cited_count = sum(1 for p in bibliography if p.get("is_cited"))
        st.success(f"✅ {len(bibliography)} papers in your working bibliography ({cited_count} cited in report)")

        # Summary table
        bib_data = []
        for p in bibliography:
            status = "🔖 CITED" if p.get("is_cited") else "📋 Selected"
            bib_data.append({
                "Status": status,
                "Title": p["title"][:80] + "..." if len(p["title"]) > 80 else p["title"],
                "Authors": p["authors"][:50] + "..." if len(p["authors"]) > 50 else p["authors"],
                "Year": p.get("year", ""),
                "Citations": p.get("citations", 0),
                "Journal": p.get("journal", "")[:40] if p.get("journal") else "",
                "DOI": p.get("doi", ""),
            })

        if bib_data:
            st.dataframe(pd.DataFrame(bib_data), use_container_width=True, hide_index=True)

        st.markdown("---")
        section_header("📝 Your Findings & Notes")

        for paper in bibliography:
            cited_tag = " 🔖 CITED" if paper.get("is_cited") else ""
            with st.expander(f"📖 {paper['title'][:80]}...{cited_tag}"):
                citation = formatter.format_citation(paper, "apa", inline=False)
                st.code(citation, language="text")

                col1, col2 = st.columns(2)
                with col1:
                    current_notes = paper.get("user_notes", "") or ""
                    new_notes = st.text_area("📝 Your Notes", value=current_notes,
                        key=f"bib_notes_{paper['id']}", height=100,
                        placeholder="Your observations, critiques, or connections...")
                    if new_notes != current_notes:
                        db.update_paper_notes(paper["id"], new_notes)
                        st.session_state["lit_engine_last_save"] = datetime.now().strftime("%H:%M:%S")
                        st.success("✅ Saved!", icon="💾")

                with col2:
                    current_finding = paper.get("user_findings", "") or ""
                    new_finding = st.text_area("🔬 Your Finding / Contribution", value=current_finding,
                        key=f"bib_finding_{paper['id']}", height=100,
                        placeholder="What does this paper contribute to YOUR research?")
                    if new_finding != current_finding:
                        db.update_paper_findings(paper["id"], new_finding)
                        st.session_state["lit_engine_last_save"] = datetime.now().strftime("%H:%M:%S")
                        st.success("✅ Saved!", icon="💾")

        # Export bibliography
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            bib_style = st.selectbox("Reference style for export",
                options=["apa", "harvard", "chicago", "mla", "vancouver"],
                format_func=lambda s: s.upper(), key="bib_export_style")
        with col2:
            st.markdown("")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📄 Generate Reference List", type="primary", use_container_width=True):
                ref_text = formatter.format_references(bibliography, bib_style)
                st.session_state["_generated_references"] = ref_text
                st.success("✅ Reference list generated! Check below.")

        with col2:
            bib_content = formatter.generate_bibtex(bibliography)
            st.markdown(exporter.get_bib_download_link(bib_content,
                f"references_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bib"), unsafe_allow_html=True)

        if st.session_state.get("_generated_references"):
            ref_text = st.session_state["_generated_references"]
            with st.expander("📖 Preview References", expanded=True):
                st.markdown(ref_text)

            timestamp = datetime.now().strftime('%Y%m%d')
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.markdown(exporter.get_markdown_download_link(ref_text, f"references_{bib_style}_{timestamp}.md", "Download MD"), unsafe_allow_html=True)
            with col_b:
                st.markdown(exporter.get_txt_download_link(ref_text, f"references_{bib_style}_{timestamp}.txt", "Download TXT"), unsafe_allow_html=True)
            with col_c:
                st.markdown(exporter.get_copy_js(ref_text, "📋 Copy References"), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# TAB 3: REPORT BUILDER
# ══════════════════════════════════════════════════════════════════════════
with tab3:
    section_header("✍️ Proposal & Report Builder")
    st.caption("Write your own content. Every word is YOURS — zero AI generation. Insert authentic citations from your bibliography.")

    sections = db.get_report_sections(project_id)
    bibliography = db.get_bibliography(project_id)

    if not sections:
        st.info("No report sections found. Create sections from the builder below.")
    else:
        render_report_builder(sections, bibliography, db, project_id)

# ══════════════════════════════════════════════════════════════════════════
# TAB 4: REFERENCE ENGINE
# ══════════════════════════════════════════════════════════════════════════
with tab4:
    section_header("📑 Reference Engine")
    st.caption("Mechanical, zero-AI reference formatting. Export in multiple formats.")

    all_papers, _ = db.get_papers(project_id, checked_only=False, page=0, per_page=10000)
    checked_papers = [p for p in all_papers if p["is_checked"]]

    col1, col2 = st.columns(2)
    with col1:
        ref_style = st.selectbox("Citation Style",
            options=["apa", "harvard", "chicago", "mla", "vancouver"],
            format_func=lambda s: s.upper(), key="ref_engine_style")
    with col2:
        ref_source = st.radio("Papers to include",
            options=["All harvested papers", "Only checked (bibliography)"],
            index=1, key="ref_source")

    papers_for_ref = checked_papers if "checked" in ref_source else all_papers

    if not papers_for_ref:
        st.info("📭 No papers available. Harvest papers in the Paper Harvester tab first.")
    else:
        st.success(f"📚 Formatting {len(papers_for_ref)} papers in {ref_style.upper()} style")

        if st.button("📄 Generate Reference List", type="primary", use_container_width=True):
            ref_text = formatter.format_references(papers_for_ref, ref_style)
            st.session_state["_ref_engine_refs"] = ref_text

        if st.session_state.get("_ref_engine_refs"):
            ref_text = st.session_state["_ref_engine_refs"]
            timestamp = datetime.now().strftime('%Y%m%d')

            with st.expander("📖 Reference List Preview", expanded=True):
                st.markdown(ref_text)

            col_a, col_b, col_c, col_d = st.columns(4)
            with col_a:
                st.markdown(exporter.get_markdown_download_link(ref_text, f"references_{ref_style}_{timestamp}.md", "Download MD"), unsafe_allow_html=True)
            with col_b:
                st.markdown(exporter.get_txt_download_link(ref_text, f"references_{ref_style}_{timestamp}.txt", "Download TXT"), unsafe_allow_html=True)
            with col_c:
                st.markdown(exporter.get_copy_js(ref_text, "📋 Copy"), unsafe_allow_html=True)
            with col_d:
                bib_content = formatter.generate_bibtex(papers_for_ref)
                st.markdown(exporter.get_bib_download_link(bib_content,
                    f"references_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bib"), unsafe_allow_html=True)

            # Notion push for references
            st.markdown("---")
            st.markdown("#### 🔗 Push References to Notion")
            st.markdown(exporter.get_notion_push_html(ref_text, ref_style), unsafe_allow_html=True)

    # .bib file
    st.markdown("---")
    section_header("📦 BibTeX Export (Mendeley / Zotero Compatible)")
    st.caption("Download a .bib file to import directly into your reference manager.")

    if st.button("📦 Generate .BIB File", use_container_width=True):
        bib_content = formatter.generate_bibtex(papers_for_ref)
        st.session_state["_bibtex_content"] = bib_content
        st.success("✅ .BIB file generated!")

    if st.session_state.get("_bibtex_content"):
        bib_content = st.session_state["_bibtex_content"]
        st.markdown(exporter.get_bib_download_link(bib_content,
            f"references_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bib"), unsafe_allow_html=True)
