"""
Audit & Compliance Hub — Standalone Page
=========================================
Provides forensic text analysis, AI-content detection, plagiarism checking,
text humanization, and blockchain-verified audit trails.

Direct access to the 4 sub-tabs from the Audit UI module:
  1. 🔍 Forensic Audit        — Professor-facing forensic view (password-protected)
  2. 🎯 Plagiarism & AI Check — Multi-vector scoring dashboard
  3. ✍️ Optimization Studio   — Student-facing text improvement tools
  4. 📤 Export Audit Report   — Downloadable audit reports & clean exports
"""
import streamlit as st

st.set_page_config(page_title="Audit & Compliance Hub", page_icon="🛡️", layout="wide")

from modules.config import init_session_state
from modules.ui_components import hero_card, load_css, watermark, section_header
from modules.literature_engine import LiteratureDatabase
from modules.audit_ui import render_audit_tab

# ─── Init ─────────────────────────────────────────────────────────────
init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")
hero_card(
    "🛡️ Audit & Compliance Hub",
    "Multi-vector forensic text analysis, blockchain-verified audit trails, "
    "AI-content detection, and advanced humanization — all in one hub.",
    badge_text="🔒 Professor & Student Tools"
)
watermark("CHRISHEM")

# ─── Initialize Database ─────────────────────────────────────────────
db = LiteratureDatabase()

# ─── Project Selection ───────────────────────────────────────────────
st.sidebar.markdown("## 📚 Select Research Project")
st.sidebar.caption("Choose a project to audit or optimize.")

projects = db.get_projects()
if not projects:
    st.sidebar.info("No projects found. Create one in the Literature Engine first.")

project_options = {p["id"]: f"📖 {p['name']}" for p in projects}
project_options[0] = "➕ Create New Project"

selected_option = st.sidebar.selectbox(
    "Project",
    options=list(project_options.keys()),
    format_func=lambda x: project_options.get(x, f"Project #{x}"),
    key="audit_standalone_project",
)

if selected_option == 0:
    st.info(
        "👈 **Select a project from the sidebar** or create one in "
        "**📚 Literature Engine** page first.\n\n"
        "The Audit & Compliance Hub works with your existing research "
        "projects — their report sections and bibliography are used "
        "for plagiarism cross-referencing and section auditing."
    )
    st.stop()

project_id = selected_option
project = db.get_project(project_id)
if project:
    st.sidebar.success(f"📌 **{project['name']}**")
    st.sidebar.caption(f"Topic: {project.get('topic', 'N/A')}")

    # Show stats
    stats = db.get_statistics(project_id)
    st.sidebar.metric("📊 Total Papers", stats["total_papers"])
    st.sidebar.metric("✅ Checked Papers", stats["checked_papers"])
    st.sidebar.metric("🔖 Cited in Report", stats.get("cited_papers", 0))

# ═══════════════════════════════════════════════════════════════════════
# Main Content — Render the Audit Tab UI
# ═══════════════════════════════════════════════════════════════════════
render_audit_tab(db, project_id)

# ─── Sidebar Footer ──────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **Quick Guide:**\n\n"
    "• **Forensic Audit** — Professor view (password: CHRISHEM)\n"
    "• **Plagiarism & AI Check** — Score any text\n"
    "• **Optimization Studio** — Humanize your writing\n"
    "• **Export** — Download audit reports"
)

