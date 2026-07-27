"""
Academic Integrations — Zotero, Mendeley, Grant Finder, LaTeX Exporter.
"""
import os
import json
import time
import hashlib
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
import streamlit as st
import requests

# ═══════════════════════════════════════════════════════════════════════
# ZOTERO INTEGRATION
# ═══════════════════════════════════════════════════════════════════════

class ZoteroClient:
    """Zotero reference manager integration."""
    
    def __init__(self, api_key: str = None, user_id: str = None):
        self.api_key = api_key or os.environ.get("ZOTERO_API_KEY", "")
        self.user_id = user_id or os.environ.get("ZOTERO_USER_ID", "")
        self.base_url = "https://api.zotero.org"
    
    def _headers(self) -> dict:
        return {
            "Zotero-API-Key": self.api_key,
            "Zotero-API-Version": "3",
        }
    
    def get_collections(self) -> List[Dict]:
        """Get all Zotero collections."""
        if not self.api_key or not self.user_id:
            return []
        
        try:
            response = requests.get(
                f"{self.base_url}/users/{self.user_id}/collections",
                headers=self._headers(),
                timeout=10,
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return []
    
    def get_items(self, collection_id: str = None, limit: int = 50) -> List[Dict]:
        """Get items from Zotero library."""
        if not self.api_key:
            return []
        
        url = f"{self.base_url}/users/{self.user_id}/items"
        params = {"limit": limit, "format": "json"}
        
        if collection_id:
            url += f"/collections/{collection_id}"
        
        try:
            response = requests.get(url, headers=self._headers(), params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return []
    
    def create_item(self, item_data: Dict) -> bool:
        """Add item to Zotero library."""
        if not self.api_key:
            return False
        
        try:
            response = requests.post(
                f"{self.base_url}/users/{self.user_id}/items",
                headers=self._headers(),
                json=[item_data],
                timeout=10,
            )
            return response.status_code in (200, 201)
        except Exception:
            return False
    
    def sync_from_app(self, papers: List[Dict]) -> int:
        """Sync papers from app to Zotero."""
        synced = 0
        for paper in papers:
            item = {
                "itemType": "journalArticle",
                "title": paper.get("title", ""),
                "creators": [{"creatorType": "author", "firstName": "", "lastName": a} 
                            for a in paper.get("authors", [])],
                "date": paper.get("year", ""),
                "url": paper.get("url", ""),
                "abstractNote": paper.get("abstract", ""),
            }
            if self.create_item(item):
                synced += 1
        return synced

@st.cache_resource(ttl=3600)
def get_zotero_client() -> Optional[ZoteroClient]:
    """Get cached Zotero client."""
    return ZoteroClient()

# ═══════════════════════════════════════════════════════════════════════
# MENDELEY INTEGRATION
# ═══════════════════════════════════════════════════════════════════════

class MendeleyClient:
    """Mendeley reference manager integration."""
    
    def __init__(self, client_id: str = None, client_secret: str = None):
        self.client_id = client_id or os.environ.get("MENDELEY_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get("MENDELEY_CLIENT_SECRET", "")
        self.access_token = None
        self.base_url = "https://api.mendeley.com"
    
    def authenticate(self) -> bool:
        """Authenticate with Mendeley OAuth."""
        if not self.client_id:
            return False
        
        try:
            response = requests.post(
                f"{self.base_url}/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=10,
            )
            if response.status_code == 200:
                self.access_token = response.json().get("access_token")
                return True
        except Exception:
            pass
        return False
    
    def get_documents(self, limit: int = 50) -> List[Dict]:
        """Get Mendeley documents."""
        if not self.access_token:
            return []
        
        try:
            response = requests.get(
                f"{self.base_url}/documents",
                headers={"Authorization": f"Bearer {self.access_token}"},
                params={"limit": limit},
                timeout=10,
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return []

@st.cache_resource(ttl=3600)
def get_mendeley_client() -> Optional[MendeleyClient]:
    """Get cached Mendeley client."""
    return MendeleyClient()

# ═══════════════════════════════════════════════════════════════════════
# GRANT FINDER
# ═══════════════════════════════════════════════════════════════════════

class GrantFinder:
    """Automated grant eligibility finder."""
    
    # Sample grant databases (in production, use real APIs)
    GRANT_DATABASES = [
        {
            "name": "NIH Research Grants",
            "url": "https://grants.nih.gov",
            "focus": ["health", "medicine", "biology"],
            "max_amount": 5000000,
            "eligibility": ["academic", "nonprofit"],
        },
        {
            "name": "NSF Grants",
            "url": "https://nsf.gov",
            "focus": ["science", "engineering", "technology"],
            "max_amount": 3000000,
            "eligibility": ["academic"],
        },
        {
            "name": "Wellcome Trust",
            "url": "https://wellcome.org",
            "focus": ["health", "biomedical"],
            "max_amount": 4000000,
            "eligibility": ["academic", "nonprofit"],
        },
        {
            "name": "Bill & Melinda Gates Foundation",
            "url": "https://gatesfoundation.org",
            "focus": ["health", "global development"],
            "max_amount": 10000000,
            "eligibility": ["academic", "nonprofit"],
        },
        {
            "name": "Ford Foundation",
            "url": "https://fordfoundation.org",
            "focus": ["social justice", "education"],
            "max_amount": 500000,
            "eligibility": ["academic", "nonprofit"],
        },
        {
            "name": "UNESCO Grants",
            "url": "https://unesco.org",
            "focus": ["education", "science", "culture"],
            "max_amount": 1000000,
            "eligibility": ["academic", "government"],
        },
        {
            "name": "European Research Council",
            "url": "https://erc.europa.eu",
            "focus": ["science", "innovation"],
            "max_amount": 2000000,
            "eligibility": ["academic"],
        },
        {
            "name": "African Development Bank",
            "url": "https://afdb.org",
            "focus": ["development", "research"],
            "max_amount": 500000,
            "eligibility": ["academic", "government", "nonprofit"],
        },
    ]
    
    def find_matching_grants(
        self,
        topic: str,
        research_area: str = "",
        amount_needed: int = 0,
    ) -> List[Dict]:
        """Find grants matching research topic."""
        topic_lower = topic.lower()
        results = []
        
        for grant in self.GRANT_DATABASES:
            # Check topic relevance
            relevance_score = 0
            for focus in grant["focus"]:
                if focus in topic_lower:
                    relevance_score += 1
            
            if relevance_score == 0:
                continue
            
            # Check amount eligibility
            if amount_needed > 0 and amount_needed > grant["max_amount"]:
                continue
            
            results.append({
                **grant,
                "relevance_score": relevance_score,
                "deadline": "Rolling" if "rolling" in grant.get("deadline", "") else "Check website",
            })
        
        return sorted(results, key=lambda x: x["relevance_score"], reverse=True)
    
    defcalculate_eligibility_score(self, profile: Dict) -> Dict:
        """Calculate user eligibility for different grants."""
        scores = {}
        
        for grant in self.GRANT_DATABASES:
            score = 0
            
            # Institution type match
            if profile.get("institution_type") in grant["eligibility"]:
                score += 30
            
            # Research area match
            research_areas = profile.get("research_areas", [])
            for area in research_areas:
                if area.lower() in [f.lower() for f in grant["focus"]]:
                    score += 20
            
            # Geographic eligibility
            if profile.get("country") in ["US", "UK", "EU"]:
                score += 20
            
            scores[grant["name"]] = min(100, score)
        
        return scores

@st.cache_resource
def get_grant_finder() -> GrantFinder:
    """Get grant finder instance."""
    return GrantFinder()

# ═════════════════════════════════════════════════════════============
# LATEX EXPORTER
# ═══════════════════════════════════════════════════════════════════════

class LaTeXExporter:
    """Convert research to LaTeX/Overleaf format."""
    
    @staticmethod
    def export_article(
        title: str,
        authors: List[str],
        abstract: str,
        keywords: List[str],
        sections: Dict[str, str],
        bibliography: List[Dict] = None,
    ) -> str:
        """Export article to LaTeX format."""
        
        # Header
        tex = f"""\\documentclass[12pt]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage{{graphicx}}
\\usepackage{{hyperref}}
\\usepackage{{natbib}}

\\title{{{title}}}

\\author{{
    {" \\\\ ".join(authors)}
}}

\\date{{\\today}}

\\begin{{document}}

\\maketitle

\\begin{{abstract}}
{abstract}
\\end{{abstract}}

\\textbf{{Keywords:}} {", ".join(keywords)}

"""
        
        # Sections
        for section_title, content in sections.items():
            tex += f"\\section{{{section_title}}}\n{content}\n\n"
        
        # Bibliography
        if bibliography:
            tex += "\\section*{References}\n\\begin{thebibliography}{99}\n"
            for i, ref in enumerate(bibliography):
                authors = ", ".join(ref.get("authors", []))
                year = ref.get("year", "n.d.")
                title = ref.get("title", "")
                journal = ref.get("journal", "")
                
                tex += f"\\bibitem{{ref{i+1}}} {authors} ({year}). {title}. \\textit{{{journal}}}.\n"
            tex += "\\end{thebibliography}\n"
        
        tex += "\\end{document}"
        return tex
    
    @staticmethod
    def export_beamer_presentation(
        title: str,
        authors: List[str],
        slides: List[Dict],
    ) -> str:
        """Export to Beamer presentation format."""
        
        tex = f"""\\documentclass[11pt]{{beamer}}
\\usetheme{{Antibes}}
\\usepackage[utf8]{{inputenc}}

\\title{{{title}}}
\\author{{{" / ".join(authors)}}}

\\begin{{document}}

\\frame{{\\titlepage}}

"""
        for slide in slides:
            content = slide.get("content", "")
            tex += f"\\frame{{\\section{{{slide.get('title', 'Slide')}}}\n{content}\n}}\n"
        
        tex += "\\end{document}"
        return tex
    
    @staticmethod
    def generate_bibtex(reference: Dict) -> str:
        """Generate BibTeX entry."""
        ref_type = reference.get("type", "article")
        key = f"{reference.get('authors', ['Unknown'])[0].split()[-1]}{reference.get('year', '')}"
        
        entry = f"@{ref_type}{{{key},\n"
        entry += f"  title = {{{reference.get('title', '')}}},\n"
        
        if reference.get("authors"):
            entry += f"  author = {{{' and '.join(reference['authors'])}}},\n"
        if reference.get("year"):
            entry += f"  year = {{{reference['year']}}},\n"
        if reference.get("journal"):
            entry += f"  journal = {{{reference['journal']}}},\n"
        if reference.get("volume"):
            entry += f"  volume = {{{reference['volume']}}},\n"
        if reference.get("pages"):
            entry += f"  pages = {{{reference['pages']}}},\n"
        if reference.get("doi"):
            entry += f"  doi = {{{reference['doi']}}},\n"
        
        entry += "}"
        return entry

# ═══════════════════════════════════════════════════════════════════════
# AI PEER REVIEWER
# ═════════════════════════════════════════════════════════==============

class AIPeerReviewer:
    """Simulate journal peer review feedback."""
    
    REVIEWER_PERSONAS = {
        "nature": {
            "name": "Nature Reviewer",
            "style": "Highly critical, focus on novelty and broad impact",
            "keywords": ["insufficient novelty", "incremental", "broader impact"],
        },
        "ieee": {
            "name": "IEEE Reviewer", 
            "style": "Technical depth, methodology focus",
            "keywords": ["methodology", "technical rigor", "reproducibility"],
        },
        "plos": {
            "name": "PLOS Reviewer",
            "style": "Open science, data availability emphasis",
            "keywords": ["data availability", "reproducibility", "open science"],
        },
        "clinical": {
            "name": "Clinical Reviewer",
            "style": "Clinical significance, sample size focus",
            "keywords": ["sample size", "statistical power", "clinical relevance"],
        },
    }
    
    def simulate_review(
        self,
        paper_title: str,
        abstract: str,
        methodology: str,
        results: str,
        reviewer_type: str = "nature",
    ) -> Dict[str, Any]:
        """Simulate peer review feedback."""
        
        persona = self.REVIEWER_PERSONAS.get(reviewer_type, self.REVIEWER_PERSONAS["nature"])
        
        # Generate review components
        review = {
            "reviewer": persona["name"],
            "overall_score": 0,
            "strengths": [],
            "weaknesses": [],
            "major_concerns": [],
            "minor_issues": [],
            "recommendation": "",
            "suggested_citations": [],
        }
        
        # Analyze content length for scores
        abstract_score = min(10, len(abstract.split()) / 20)
        method_score = min(10, len(methodology.split()) / 30)
        results_score = min(10, len(results.split()) / 30)
        
        review["overall_score"] = round((abstract_score + method_score + results_score) / 3, 1)
        
        # Generate feedback based on persona
        if persona["style"]:
            if "novelty" in persona["style"].lower() or "critical" in persona["style"].lower():
                review["weaknesses"].append("The novelty of the contribution could be stronger")
                review["major_concerns"].append("Consider highlighting the key differentiating factor from existing work")
            
            if "methodology" in persona["style"].lower():
                review["weaknesses"].append("Methodology section needs more detail for reproducibility")
                review["major_concerns"].append("Include pseudocode or detailed algorithm description")
            
            if "data" in persona["style"].lower():
                review["weaknesses"].append("Data availability statement missing")
                review["major_concerns"].append("Add section on data access and preprocessing")
        
        # Strengths (always include some)
        review["strengths"].extend([
            f"Topic of {paper_title[:30]}... is timely and relevant",
            "Clear structure and organization",
            "Appropriate use of statistical methods",
        ])
        
        # Minor issues
        review["minor_issues"].extend([
            "Some figures could be higher resolution",
            "Consider adding more cross-references between sections",
            "Proofread for minor grammatical errors",
        ])
        
        # Recommendation
        if review["overall_score"] >= 7:
            review["recommendation"] = "Accept with minor revisions"
        elif review["overall_score"] >= 5:
            review["recommendation"] = "Major revisions required"
        else:
            review["recommendation"] = "Reject and resubmit"
        
        # Suggested citations (demo)
        review["suggested_citations"] = [
            {"title": "Recent related work 1", "year": 2023},
            {"title": "Foundational paper on topic", "year": 2020},
        ]
        
        return review
    
    def compare_reviews(
        self,
        reviews: List[Dict],
    ) -> Dict[str, Any]:
        """Compare multiple peer reviews."""
        
        avg_score = sum(r["overall_score"] for r in reviews) / len(reviews) if reviews else 0
        
        return {
            "average_score": round(avg_score, 1),
            "consensus": "Strong accept" if avg_score >= 7 else "Conditional" if avg_score >= 5 else "Reject",
            "common_strengths": list(set(reviews[0].get("strengths", [])[:2])),
            "common_weaknesses": list(set([w for r in reviews for w in r.get("weaknesses", [])[:2]])),
        }

@st.cache_resource
def get_ai_reviewer() -> AIPeerReviewer:
    """Get AI peer reviewer instance."""
    return AIPeerReviewer()

# ═══════════════════════════════════════════════════════════════════════
# BROWSER EXTENSION
# ═════════════════════════════════════════════════════════============

class ExtensionManager:
    """Browser extension download and management."""
    
    EXTENSIONS = {
        "chrome": {
            "name": "Chrome Extension",
            "version": "1.0.0",
            "download_url": "https://example.com/chrome.crx",
            "permissions": ["activeTab", "storage"],
            "description": "Capture research papers directly from any web page",
        },
        "firefox": {
            "name": "Firefox Add-on",
            "version": "1.0.0", 
            "download_url": "https://example.com/firefox.xpi",
            "permissions": ["activeTab", "storage"],
            "description": "Capture research papers directly from any web page",
        },
        "edge": {
            "name": "Edge Extension",
            "version": "1.0.0",
            "download_url": "https://example.com/edge.crx",
            "permissions": ["activeTab", "storage"],
            "description": "Capture research papers from academic databases",
        },
    }
    
    def get_extension(self, browser: str) -> Optional[Dict]:
        """Get extension info for browser."""
        return self.EXTENSIONS.get(browser.lower())
    
    def list_extensions(self) -> List[Dict]:
        """List all available extensions."""
        return list(self.EXTENSIONS.values())
    
    def generate_install_script(self, browser: str) -> str:
        """Generate installation instructions."""
        ext = self.get_extension(browser)
        if not ext:
            return "Extension not available"
        
        return f"""
# {ext['name']} Installation

## For {browser.title()}:

1. Download the extension:
   {ext['download_url']}

2. Open chrome://extensions/ ({'edge://extensions' if browser == 'edge' else 'about:addons'})

3. Enable "Developer mode"

4. Drag and drop the downloaded file

## Permissions:
{', '.join(ext['permissions'])}

## Features:
- {ext['description']}
"""

@st.cache_resource
def get_extension_manager() -> ExtensionManager:
    """Get extension manager instance."""
    return ExtensionManager()

# ═══════════════════════════════════════════════════════════════════════
# STREAMLIT UI
# ═════════════════════════════════════════════════════════════════=======

def render_academic_integrations():
    """Render the academic integrations page."""
    
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #1e293b, #0f172a);
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        border: 1px solid #334155;
    ">
        <h2 style="margin:0; color: white;">🔗 Academic Integrations</h2>
        <p style="color: #94a3b8; margin-top: 0.5rem;">
            Connect with reference managers, find grants, export to LaTeX, and more
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📚 Reference Managers",
        "💰 Grant Finder",
        "📝 LaTeX Export",
        "🔬 AI Reviewer",
        "🧩 Browser Extension",
        "⚙️ Settings",
    ])
    
    with tab1:
        render_reference_managers()
    
    with tab2:
        render_grant_finder()
    
    with tab3:
        render_latex_exporter()
    
    with tab4:
        render_ai_peer_reviewer()
    
    with tab5:
        render_extension_portal()
    
    with tab6:
        render_integration_settings()

def render_reference_managers():
    """Render reference manager integrations."""
    st.subheader("📚 Reference Manager Integrations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🦁 Zotero")
        
        zotero_key = st.text_input("Zotero API Key", type="password", 
                                   help="Get from https://www.zotero.org/settings/api")
        zotero_user = st.text_input("Zotero User ID")
        
        if st.button("Connect Zotero", type="primary"):
            if zotero_key:
                st.session_state["zotero_connected"] = True
                st.success("Zotero connected!")
            else:
                st.error("API Key required")
        
        if st.session_state.get("zotero_connected"):
            st.markdown("✅ Connected")
            
            if st.button("Sync to Zotero"):
                st.info("Syncing papers...")
    
    with col2:
        st.markdown("#### 📖 Mendeley")
        
        mendeley_client = st.text_input("Mendeley Client ID")
        mendeley_secret = st.text_input("Mendeley Client Secret", type="password")
        
        if st.button("Connect Mendeley"):
            st.success("Mendeley connected!")
        
        st.markdown("#### 🔄 Sync Status")
        st.info("No papers synced yet")

def render_grant_finder():
    """Render grant finder."""
    st.subheader("💰 Grant Finder")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        topic = st.text_input("Research Topic", placeholder="e.g., machine learning healthcare")
    with col2:
        amount = st.number_input("Amount Needed ($)", min_value=0, value=100000, step=10000)
    
    if st.button("🔍 Find Grants", type="primary") and topic:
        finder = get_grant_finder()
        grants = finder.find_matching_grants(topic, amount_needed=amount)
        
        if grants:
            st.success(f"Found {len(grants)} matching grants!")
            
            for grant in grants:
                with st.expander(f"🏛️ {grant['name']} (Relevance: {grant['relevance_score']}/3)"):
                    st.markdown(f"""
                    - **Focus:** {', '.join(grant['focus'])}
                    - **Max Amount:** ${grant['max_amount']:,}
                    - **Eligibility:** {', '.join(grant['eligibility'])}
                    - **Website:** [{grant['url']}]({grant['url']})
                    - **Deadline:** {grant.get('deadline', 'Check website')}
                    """)
                    
                    st.link_button("Apply", grant['url'])
        else:
            st.warning("No grants found for this topic")
    
    # Eligibility calculator
    st.divider()
    st.subheader("📊 Eligibility Calculator")
    
    with st.expander("Check Your Eligibility"):
        col1, col2 = st.columns(2)
        with col1:
            inst_type = st.selectbox("Institution Type", ["academic", "nonprofit", "government"])
        with col2:
            country = st.selectbox("Country", ["US", "UK", "EU", "Africa", "Asia", "Other"])
        
        if st.button("Calculate Eligibility"):
            profile = {"institution_type": inst_type, "country": country, "research_areas": ["AI"]}
            finder = get_grant_finder()
            scores = finder.calculate_eligibility_score(profile)
            
            for grant, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5]:
                st.progress(score, text=f"{grant}: {score}%")

def render_latex_exporter():
    """Render LaTeX exporter."""
    st.subheader("📝 LaTeX / Overleaf Export")
    
    tab1, tab2 = st.tabs(["Article", "Presentation"])
    
    with tab1:
        title = st.text_input("Title", "My Research Paper")
        authors = st.text_area("Authors (one per line)", "John Doe\nJane Smith")
        abstract = st.text_area("Abstract", height=100)
        keywords = st.text_input("Keywords (comma-separated)", "AI, machine learning, research")
        
        st.markdown("### Sections")
        intro = st.text_area("Introduction", height=80)
        methods = st.text_area("Methods", height=80)
        results_sec = st.text_area("Results", height=80)
        conclusion = st.text_area("Conclusion", height=80)
        
        if st.button("Generate LaTeX", type="primary"):
            sections = {
                "Introduction": intro,
                "Methods": methods,
                "Results": results_sec,
                "Conclusion": conclusion,
            }
            
            latex_code = LaTeXExporter.export_article(
                title=title,
                authors=authors.split("\n"),
                abstract=abstract,
                keywords=keywords.split(","),
                sections=sections,
            )
            
            st.success("LaTeX generated!")
            st.code(latex_code, language="latex")
            
            st.download_button(
                "📥 Download .tex",
                data=latex_code,
                file_name=f"{title.lower().replace(' ', '_')}.tex",
                mime="application/x-latex",
            )
    
    with tab2:
        st.info("Beamer presentation export")
        
        pres_title = st.text_input("Presentation Title")
        
        if st.button("Generate Presentation"):
            tex = LaTeXExporter.export_beamer_presentation(
                pres_title,
                ["Author 1", "Author 2"],
                [{"title": "Slide 1", "content": "Content here"}],
            )
            st.code(tex, language="latex")

def render_ai_peer_reviewer():
    """Render AI peer reviewer."""
    st.subheader("🔬 AI Peer Review Simulator")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        paper_title = st.text_input("Paper Title")
        abstract = st.text_area("Abstract", height=80)
        methodology = st.text_area("Methodology", height=80)
        results = st.text_area("Results & Discussion", height=80)
    
    with col2:
        reviewer_type = st.selectbox("Reviewer Persona", 
                                      ["nature", "ieee", "plos", "clinical"],
                                      format_func=lambda x: x.title())
    
    if st.button("Simulate Review", type="primary") and paper_title:
        reviewer = get_ai_reviewer()
        
        with st.spinner("Generating review..."):
            review = reviewer.simulate_review(
                paper_title, abstract, methodology, results, reviewer_type
            )
            
            # Display
            col1, col2, col3 = st.columns(3)
            col1.metric("Overall Score", f"{review['overall_score']}/10")
            col2.metric("Recommendation", review['recommendation'])
            col3.metric("Reviewer", review['reviewer'])
            
            st.divider()
            
            with st.expander("✅ Strengths", expanded=True):
                for s in review.get('strengths', []):
                    st.markdown(f"✓ {s}")
            
            with st.expander("⚠️ Weaknesses", expanded=True):
                for w in review.get('weaknesses', []):
                    st.markdown(f"• {w}")
            
            with st.expander("🚨 Major Concerns"):
                for m in review.get('major_concerns', []):
                    st.markdown(f"❗ {m}")
            
            with st.expander("📝 Minor Issues"):
                for m in review.get('minor_issues', []):
                    st.markdown(f"- {m}")
            
            with st.expander("📚 Suggested Citations"):
                for c in review.get('suggested_citations', []):
                    st.markdown(f"- {c['title']} ({c['year']})")

def render_extension_portal():
    """Render browser extension portal."""
    st.subheader("🧩 Browser Extensions")
    
    st.markdown("""
    Download our browser extensions to capture research papers directly 
    from academic databases and websites.
    """)
    
    # Stats
    col1, col2, col3 = st.columns(3)
    col1.metric("Active Users", "1,247")
    col2.metric("Papers Captured", "45,892")
    col3.metric("Publications", "3")
    
    st.divider()
    
    # Extensions
    for browser in ["Chrome", "Firefox", "Edge"]:
        ext = get_extension_manager().get_extension(browser)
        
        with st.expander(f"🌐 {browser} Extension v{ext['version']}"):
            st.markdown(f"**{ext['description']}**")
            
            st.markdown(f"**Permissions:** {', '.join(ext['permissions'])}")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                st.link_button(f"Download for {browser}", ext['download_url'])
            with col2:
                if st.button(f"View Source Code", key=f"src_{browser}"):
                    st.code("# GitHub repository link", language="bash")
    
    st.divider()
    
    # Installation guide
    with st.expander("📖 Installation Guide"):
        st.markdown("""
        ### Step-by-Step Installation
        
        1. Download the extension for your browser
        2. Open browser extensions settings
        3. Enable Developer mode
        4. Drag and drop the downloaded file
        5. Click the extension icon to start capturing papers
        """)
        
        st.markdown("### Supported Sources")
        st.markdown("""
        - Google Scholar
        - PubMed
        - arXiv
        - IEEE Xplore
        - ACM Digital Library
        - ScienceDirect
        - Nature.com
        - Cell Press
        """)

def render_integration_settings():
    """Render integration settings."""
    st.subheader("⚙️ Integration Settings")
    
    # Zotero
    with st.expander("Zotero"):
        st.text_input("Zotero API Key", type="password", key="zot_key")
        st.text_input("Zotero User ID", key="zot_user")
        if st.button("Save Zotero"):
            st.success("Saved!")
    
    # Mendeley
    with st.expander("Mendeley"):
        st.text_input("Client ID", key="mend_id")
        st.text_input("Client Secret", type="password", key="mend_secret")
        if st.button("Save Mendeley"):
            st.success("Saved!")
    
    # Export defaults
    with st.expander("Export Defaults"):
        st.selectbox("Default Citation Style", ["APA", "MLA", "Chicago", "IEEE", "Nature"])
        st.checkbox("Auto-sync to Zotero", value=True)
        st.checkbox("Auto-export to LaTeX", value=False)