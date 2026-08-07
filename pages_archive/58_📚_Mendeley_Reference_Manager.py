"""
Page 58 — Mendeley Reference Manager & Library
"""
import sys
from pathlib import Path

import streamlit as st

current_file = Path(__file__).resolve()
root_dir = current_file.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

st.set_page_config(page_title="Mendeley Reference Manager", page_icon="📚", layout="wide")


def _hero(title, subtitle, badge):
    st.markdown(
        f"""
        <div style="padding:1.6rem;background:linear-gradient(135deg,rgba(59,130,246,.12),rgba(11,19,33,.96));border-radius:14px;border:1px solid rgba(59,130,246,.35);margin-bottom:1.2rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem;">
                <h1 style="color:#3b82f6 !important;font-size:1.9rem;margin:0;font-weight:800;">{title}</h1>
                <span style="background:rgba(59,130,246,.15);color:#3b82f6;padding:.3rem .8rem;border-radius:999px;font-size:.75rem;font-weight:700;border:1px solid #3b82f6;">{badge}</span>
            </div>
            <p style="color:#cbd5e1 !important;margin:.4rem 0 0;font-size:.95rem;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


_hero(
    "📚 Mendeley Reference Manager & Citation Library",
    "Connect your Mendeley account (OAuth), sync documents into a persistent local library, manage references, search/dedupe by DOI, and export to BibTeX (.bib) or RIS (.ris).",
    "Real Mendeley OAuth Integration",
)

try:
    from modules.mendeley_integration import (
        MendeleyClient,
        add_reference,
        delete_reference,
        export_bibtex,
        export_ris,
        init_library,
        library_stats,
        list_references,
        sync_from_mendeley,
    )
except Exception as e:
    st.error(f"Failed to load Mendeley integration: {e}")
    st.stop()

init_library()

tab1, tab2, tab3, tab4 = st.tabs([
    "🔗 Connect & Sync",
    "➕ Add Reference",
    "📑 Library",
    "📤 Export",
])

with tab1:
    st.markdown("### Connect Mendeley Account")
    st.info("Set `MENDELEY_CLIENT_ID` and `MENDELEY_CLIENT_SECRET` in your `.env` for real OAuth sync.")
    client = MendeleyClient()
    if st.button("🔗 Authenticate & Sync from Mendeley", type="primary", use_container_width=True):
        if not client.configured:
            st.warning("Mendeley credentials not configured. Add MENDELEY_CLIENT_ID / MENDELEY_CLIENT_SECRET to .env")
        else:
            with st.spinner("Authenticating and syncing documents..."):
                count = sync_from_mendeley(client)
            if count:
                st.success(f"Synced {count} documents into local library.")
            else:
                st.error("Authentication or sync failed. Check credentials and internet.")

    stats = library_stats()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total References", stats["total"])
    c2.metric("Latest Publication Year", stats["latest_year"])
    c3.metric("Reference Types", len(stats.get("by_type", {})))

with tab2:
    st.markdown("### Add Reference Manually")
    with st.form("add_ref"):
        title = st.text_input("Title *")
        authors = st.text_input("Authors (Last, First; separated by commas)")
        year = st.number_input("Year", min_value=1800, max_value=2100, value=2024, step=1)
        journal = st.text_input("Journal / Source")
        doi = st.text_input("DOI")
        url = st.text_input("URL")
        abstract = st.text_area("Abstract")
        ref_type = st.selectbox("Type", ["journalArticle", "book", "bookSection", "conferencePaper", "thesis"])
        submitted = st.form_submit_button("💾 Save Reference", type="primary")
        if submitted:
            if not title.strip():
                st.error("Title is required.")
            else:
                add_reference(
                    title=title, authors=authors, year=int(year), journal=journal,
                    doi=doi, url=url, abstract=abstract, ref_type=ref_type,
                )
                st.success("Reference saved to library.")
                st.rerun()

with tab3:
    st.markdown("### Reference Library")
    q = st.text_input("Search library (title / author / DOI / journal)")
    refs = list_references(query=q)
    if not refs:
        st.info("No references found. Add one or sync from Mendeley.")
    else:
        st.caption(f"{len(refs)} reference(s)")
        for r in refs:
            with st.expander(f"{r['title']} ({r.get('year', 'n.d.')})"):
                st.markdown(f"**Authors:** {r.get('authors', '—')}")
                st.markdown(f"**Journal:** {r.get('journal', '—')}")
                if r.get("doi"):
                    st.markdown(f"**DOI:** {r['doi']}")
                if r.get("abstract"):
                    st.markdown(f"**Abstract:** {r['abstract'][:300]}...")
                if st.button("🗑️ Delete", key=f"del_{r['id']}"):
                    delete_reference(r["id"])
                    st.rerun()

with tab4:
    st.markdown("### Export Options")
    refs = list_references()
    if not refs:
        st.info("Library is empty — nothing to export yet.")
    else:
        bib = export_bibtex(refs)
        ris = export_ris(refs)
        st.download_button("⬇️ Download BibTeX (.bib)", data=bib.encode("utf-8"), file_name="mendeley_library.bib", mime="application/x-bibtex", use_container_width=True)
        st.download_button("⬇️ Download RIS (.ris)", data=ris.encode("utf-8"), file_name="mendeley_library.ris", mime="application/x-research-info-systems", use_container_width=True)
        with st.expander("Preview BibTeX"):
            st.code(bib, language="text")

st.markdown("---")
st.caption("CHRISHEM Multi-Problem Solver • Mendeley Reference Module")
