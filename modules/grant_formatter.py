"""
One-Click Grant & Journal Transpiler
======================================
Instantly reformats summaries, bibliographies, and proposal drafts into
specific institutional or journal formats. Supports APA 7, IEEE, Nature,
Science, NIH Grant, European Research Council, and institutional templates.
"""
from __future__ import annotations

import json, re
from datetime import datetime
from typing import Dict, List, Any, Optional
from modules.literature_engine import ReferenceFormatter


class GrantFormatter:
    """
    Reformats research content into various journal and grant formats.
    """

    FORMATS = {
        "APA 7": {
            "name": "APA 7th Edition",
            "citation_style": "apa",
            "header": "References",
            "font": "Times New Roman, 12pt",
            "spacing": "double",
            "margins": "1 inch",
        },
        "IEEE": {
            "name": "IEEE",
            "citation_style": "ieee",
            "header": "References",
            "format": "[N] Author, 'Title,' Journal, vol., no., pp., year.",
        },
        "Nature": {
            "name": "Nature",
            "citation_style": "nature",
            "header": "References",
            "format": "Author, A. B. Title. Journal Vol, Pages (Year).",
            "max_refs": 50,
        },
        "Science": {
            "name": "Science",
            "citation_style": "science",
            "header": "References and Notes",
            "format": "1. A. B. Author, Journal Vol, pages (year).",
        },
        "NIH Grant": {
            "name": "NIH Grant Application",
            "citation_style": "nih",
            "header": "References",
            "max_pages": 12,
            "sections": ["Specific Aims", "Background & Significance", "Preliminary Data", "Research Design", "Timeline"],
        },
        "ERC Grant": {
            "name": "European Research Council",
            "citation_style": "erc",
            "header": "Bibliography",
            "sections": ["State of the Art", "Objectives", "Methodology", "Resources", "Impact"],
        },
        "MLA": {
            "name": "MLA Handbook",
            "citation_style": "mla",
            "header": "Works Cited",
            "font": "Times New Roman, 12pt",
            "spacing": "double",
        },
        "Chicago": {
            "name": "Chicago Manual of Style",
            "citation_style": "chicago",
            "header": "Bibliography",
            "spacing": "single",
        },
        "Vancouver": {
            "name": "Vancouver Style",
            "citation_style": "vancouver",
            "header": "References",
            "format": "1. Author AB. Title. Journal. Year;Vol:Pages.",
        },
    }

    def __init__(self):
        self.ref_formatter = ReferenceFormatter()

    def get_format_options(self) -> List[str]:
        return list(self.FORMATS.keys())

    def format_content(self, content: str, target_format: str, title: str = "",
                       authors: str = "", abstract: str = "") -> Dict[str, Any]:
        """Reformat content to a target journal/grant format."""
        fmt_info = self.FORMATS.get(target_format, self.FORMATS["APA 7"])
        lines = []

        if target_format in ("NIH Grant", "ERC Grant"):
            return self._format_grant_proposal(content, target_format, title, authors, abstract)
        elif target_format == "Nature":
            lines.append(self._nature_format(content, title, authors))
        elif target_format == "Science":
            lines.append(self._science_format(content, title, authors))
        elif target_format == "IEEE":
            lines.append(self._ieee_format(content, title, authors))
        else:
            lines.append(content)

        result = "\n\n".join(lines) if lines else content
        return {
            "format": target_format,
            "content": result,
            "word_count": len(result.split()),
            "formatting_notes": fmt_info,
        }

    def _nature_format(self, content: str, title: str, authors: str) -> str:
        para = re.sub(r'\n\s*\n', '\n\n', content.strip())
        max_chars = 2000
        return f"# {title}\n" + (f"**{authors}**\n\n" if authors else "") + para[:max_chars] + "\n\n*Nature format: ~2000-character limit for main text*"

    def _science_format(self, content: str, title: str, authors: str) -> str:
        para = re.sub(r'\n\s*\n', '\n\n', content.strip())
        max_chars = 3000
        return f"# {title}\n" + (f"*{authors}*\n\n" if authors else "") + para[:max_chars] + "\n\n*Science format: ~3000-character limit*"

    def _ieee_format(self, content: str, title: str, authors: str) -> str:
        return f"# {title}\n{content.strip()[:4000]}\n\n*IEEE format: ~4000-word limit*"

    def _format_grant_proposal(self, content: str, grant_type: str, title: str,
                                authors: str, abstract: str) -> Dict[str, Any]:
        fmt_info = self.FORMATS.get(grant_type, self.FORMATS["NIH Grant"])
        sections = fmt_info.get("sections", ["Abstract", "Background", "Methodology", "Impact"])
        max_pages = fmt_info.get("max_pages", 12)

        proposal = f"# {grant_type}: {title}\n"
        if authors: proposal += f"**PI(s):** {authors}\n"
        proposal += f"**Date:** {datetime.now().strftime('%B %d, %Y')}\n\n"

        abstract_text = abstract or "**Abstract:** [Write a compelling summary of your proposal]"
        proposal += f"## Abstract\n{abstract_text}\n\n"

        words = content.split()
        para_size = max(50, len(words) // max(1, len(sections) - 1))
        for i, section in enumerate(sections):
            start = i * para_size
            end = min(len(words), (i + 1) * para_size) if i < len(sections) - 1 else len(words)
            section_text = " ".join(words[start:end]) if words else "[Add content here]"
            proposal += f"## {section}\n{section_text}\n\n"

        proposal += f"\n*{grant_type} format: max {max_pages} pages*"
        return {"format": grant_type, "content": proposal, "word_count": len(words), "formatting_notes": fmt_info}

    def format_references(self, papers: List[Dict], format_name: str = "APA 7") -> str:
        style_map = {
            "APA 7": "apa", "IEEE": "ieee", "Nature": "apa",
            "Science": "apa", "NIH Grant": "apa", "ERC Grant": "apa",
            "MLA": "mla", "Chicago": "chicago", "Vancouver": "vancouver",
        }
        style = style_map.get(format_name, "apa")
        return self.ref_formatter.format_references(papers, style)

    def format_structured_abstract(self, background: str = "", methods: str = "",
                                    results: str = "", conclusion: str = "",
                                    format_name: str = "APA 7") -> str:
        templates = {
            "APA 7": f"**Objective:** {background}\n**Method:** {methods}\n**Results:** {results}\n**Conclusions:** {conclusion}",
            "NIH Grant": f"**Specific Aims:** {background}\n**Approach:** {methods}\n**Expected Outcomes:** {results}\n**Impact:** {conclusion}",
            "Nature": f"**Background:** {background}\n**Methods:** {methods}\n**Findings:** {results}\n**Conclusions:** {conclusion}",
        }
        return templates.get(format_name, templates["APA 7"])

    def add_formatting_guide(self, format_name: str) -> str:
        info = self.FORMATS.get(format_name, {})
        guide = f"## 📋 {info.get('name', format_name)} Formatting Guide\n\n"
        for key, val in info.items():
            if key not in ("name", "citation_style", "sections"):
                guide += f"- **{key.replace('_', ' ').title()}**: {val}\n"
        if "sections" in info:
            guide += "- **Required Sections**:\n" + "\n".join(f"  - {s}" for s in info["sections"])
        return guide


def render_grant_formatter_ui():
    """Render the Grant & Journal Transpiler UI."""
    import streamlit as st
    import base64

    st.markdown("## 📜 One-Click Grant & Journal Transpiler")
    st.markdown("*Instantly reformat for journals, grants, and institutions*")

    formatter = GrantFormatter()

    tab1, tab2, tab3 = st.tabs(["📝 Content Formatter", "📚 Reference Formatter", "📋 Format Guides"])

    with tab1:
        st.subheader("📝 Reformat Your Content")
        col1, col2 = st.columns([3, 1])
        with col1:
            content = st.text_area("Paste your content", height=200,
                placeholder="Paste your abstract, summary, or proposal text here...",
                key="gf_content")
        with col2:
            target = st.selectbox("Target format", options=formatter.get_format_options(), key="gf_target")
            title = st.text_input("Title (optional)", key="gf_title")
            authors = st.text_input("Authors/PI (optional)", key="gf_authors")
            abstract = st.text_area("Abstract (optional, for grants)", height=80, key="gf_abstract")

        if st.button("🔄 Reformat", type="primary", use_container_width=True) and content:
            result = formatter.format_content(content, target, title, authors, abstract)
            st.subheader(f"📄 {target} Format")
            st.markdown(result["content"])
            st.caption(f"Word count: {result.get('word_count', 0)}")
            st.download_button("📥 Download", result["content"], file_name=f"{target.lower().replace(' ', '_')}.md", mime="text/markdown", use_container_width=True)

    with tab2:
        st.subheader("📚 Format References")
        papers = []
        lit_papers = st.session_state.get("lit_db_papers", [])
        if lit_papers:
            st.info(f"📚 {len(lit_papers)} papers available")
            target_ref = st.selectbox("Reference format", options=formatter.get_format_options(), key="gf_ref_format", index=0)
            if st.button("📚 Format References", type="primary", use_container_width=True):
                refs = formatter.format_references(lit_papers, target_ref)
                st.markdown(refs)
                st.download_button("📥 Download References", refs, file_name=f"references_{target_ref.lower().replace(' ', '_')}.md", mime="text/markdown", use_container_width=True)
        else:
            st.info("Load papers in the Literature Engine first.")

    with tab3:
        st.subheader("📋 Formatting Guides")
        fmt_choice = st.selectbox("Select format for guide", options=formatter.get_format_options(), key="gf_guide")
        guide = formatter.add_formatting_guide(fmt_choice)
        st.markdown(guide)

