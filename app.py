"""Main Application — Bio-Research Platform."""
import os
import gc
import time
from datetime import datetime

import streamlit as st
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="Bio-Research Platform",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════════
# MODULE IMPORTS
# ═══════════════════════════════════════════════════════════════════════

# Core modules
try:
    from modules.config import init_session_state
    init_session_state()
except Exception:
    pass

try:
    from modules.ui_stunning import apply_stunning_styles, render_greeting
    apply_stunning_styles()
except ImportError:
    try:
        from modules.ui_styles_enhanced import apply_enhanced_styles, render_location_greeting
        apply_enhanced_styles()
    except ImportError:
        pass

try:
    from modules.auth import get_notion_token, get_database_id, check_authentication
except ImportError:
    def get_notion_token():
        return os.environ.get("NOTION_TOKEN", "")
    def get_database_id():
        return os.environ.get("DATABASE_ID", "")
    def check_authentication():
        return bool(get_notion_token())

try:
    from modules.audit_engine import get_audit_orchestrator, AuditOrchestrator
except ImportError:
    AuditOrchestrator = None

try:
    from modules.notion_client import fetch_notion_data
except ImportError:
    def fetch_notion_data(*a, **k):
        return pd.DataFrame()

try:
    from modules.file_analyzer import render_file_analyzer_page
except ImportError:
    def render_file_analyzer_page():
        st.info("File Analyzer not available.")

# Enhanced modules
try:
    from modules.subscription import (
        init_subscription_state,
        get_current_tier,
        check_feature_access,
        Tier,
        start_trial,
    )
    init_subscription_state()
except ImportError:
    def get_current_tier():
        return Tier.FREE if 'Tier' in dir() else None

try:
    from modules.notion_module import render_notion_module
except ImportError:
    def render_notion_module():
        st.warning("Notion module not available.")

try:
    from modules.email_engine import render_email_options
except ImportError:
    def render_email_options(*a, **k):
        st.warning("Email module not available.")

try:
    from modules.admin_portal import render_admin_router, check_admin_route
except ImportError:
    def render_admin_router():
        st.warning("Admin portal not available.")
    def check_admin_route():
        return st.query_params.get("route") == "admin"

try:
    from modules.advanced_features import render_professor_vault
except ImportError:
    def render_professor_vault():
        st.warning("Professor Vault not available.")

try:
    from modules.collaboration_ui import render_command_center
    from modules.advanced_automations import render_automations_advanced
except ImportError:
    def render_command_center():
        st.warning("Collaboration module not available.")
    def render_automations_advanced():
        st.warning("Automations module not available.")

def render_research_hub():
    """Research hub page - combines collaboration and automations."""
    st.markdown("---")
    
    try:
        from modules.ui_stunning import render_hero
        render_hero("🎯 Research Hub", "Collaborate, automate, and accelerate your research", "🚀")
    except Exception:
        st.title("🎯 Research Hub")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🎯 Command Center", "⚡ Automations"])
    with tab1:
        render_command_center()
    with tab2:
        render_automations_advanced()

# ═══════════════════════════════════════════════════════════════════════
# CACHE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════

@st.cache_resource(ttl=3600)
def get_memory_cleanup():
    """Cached garbage collection helper."""
    return gc.collect()

# Force cleanup on app start
get_memory_cleanup()

# ═══════════════════════════════════════════════════════════════════════
# MAIN NAVIGATION
# ═══════════════════════════════════════════════════════════════════════

def main():
    """Main application entry."""
    
    # Check for admin route first
    if check_admin_route():
        render_admin_router()
        return
    
    # Contextual greeting
    try:
        from modules.ui_stunning import render_greeting
        greeting = render_greeting()
    except Exception:
        greeting = "Welcome to Bio-Research Platform"
    
    # Sidebar
    with st.sidebar:
        st.title("🔬 Bio-Research")
        
        # User tier display
        try:
            current_tier = get_current_tier()
            tier_name = current_tier.name.title() if current_tier else "Free"
            st.markdown(f"**Tier:** {tier_name}")
        except Exception:
            st.markdown("**Tier:** Free")
        
        st.divider()
        
        # Main navigation
        pages = [
            "📊 Dashboard",
            "📁 File Analyzer",
            "📚 Literature Engine",
            "📜 Audit & Compliance",
            "🔐 Professor Vault",
            "🔗 Notion Workspace",
            "🔗 Integrations",
            "🎯 Research Hub",
            "⚙️ Settings",
        ]
        
        # Always show admin link for developer access
        pages.append("🔧 Admin Portal")
        
        page = st.radio("Navigation", pages)
        
        st.divider()
        
        # Keep-alive option
        st.caption("⏰ Auto-refresh")
        refresh = st.selectbox("Refresh", ["Off", "30 sec", "60 sec", "5 min"], index=0)
        
        st.caption("---")
        st.caption("© 2024 Bio-Research Platform")
    
    # ═══════════════════════════════════════════════════════════════════════
    # PAGE ROUTING
    # ═══════════════════════════════════════════════════════════════════════
    
    if page == "📊 Dashboard":
        render_dashboard()
    elif page == "📁 File Analyzer":
        render_file_analyzer()
    elif page == "📚 Literature Engine":
        render_literature_engine()
    elif page == "📜 Audit & Compliance":
        render_audit_portal()
    elif page == "🔐 Professor Vault":
        render_professor_vault()
    elif page == "🔗 Notion Workspace":
        render_notion_module()
    elif page == "⚙️ Settings":
        render_settings()
    elif page == "🔗 Integrations":
        from modules.academic_integrations import render_academic_integrations
        render_academic_integrations()
    elif page == "🔧 Admin Portal":
        render_admin_router()
    elif page == "🎯 Research Hub":
        render_research_hub()
    elif page == "⚡ Automations":
        render_automations_advanced()

# ═══════════════════════════════════════════════════════════════════════
# PAGE RENDERERS
# ═══════════════════════════════════════════════════════════════════════

def render_dashboard():
    """Dashboard page."""
    st.markdown("---")
    
    try:
        from modules.ui_stunning import render_hero, render_stat, render_feature_card, render_tier_badge, render_greeting
        greeting = render_greeting()
        st.markdown(f"### {greeting}")
    except Exception:
        st.title("🔬 Bio-Research Platform")
    
    # Hero section
    try:
        render_hero("Bio-Research Platform", "Your AI-powered academic research companion", "🔬")
    except Exception:
        st.title("🔬 Bio-Research Platform")
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_stat("127", "Papers Analyzed", "📄")
    with col2:
        render_stat("12", "Active Projects", "🚀")
    with col3:
        render_stat("45", "Reports Generated", "📊")
    with col4:
        try:
            tier = get_current_tier()
            render_stat(tier.name if tier else "Free", "Subscription Tier", "👑")
        except Exception:
            render_stat("Free", "Subscription Tier", "🆓")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Feature grid
    st.subheader("🚀 Quick Access")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        render_feature_card("📁", "File Analysis", "Upload CSV, Excel, PDF, or DOCX files for analysis.")
        if st.button("Open File Analyzer", key="dash_file"):
            st.session_state["nav"] = "📁 File Analyzer"
            st.rerun()
    
    with col2:
        render_feature_card("📚", "Literature Engine", "Search and analyze academic literature.")
        if st.button("Open Literature Engine", key="dash_lit"):
            st.session_state["nav"] = "📚 Literature Engine"
            st.rerun()
    
    with col3:
        render_feature_card("📜", "Audit Compliance", "Run academic integrity checks on documents.")
        if st.button("Open Audit Portal", key="dash_audit"):
            st.session_state["nav"] = "📜 Audit Compliance"
            st.rerun()
    
    st.markdown("---")
    
    # Notion sync status
    st.subheader("🔗 Notion Connection")
    
    token = get_notion_token()
    db_id = get_database_id()
    
    if token and db_id:
        st.success("✅ Notion connected")
        
        try:
            df = fetch_notion_data(token, db_id)
            if not df.empty:
                st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not fetch data: {e}")
    else:
        st.info("⚠️ Notion not configured. Go to Settings to connect.")

def render_file_analyzer():
    """File analyzer page."""
    st.markdown("---")
    
    try:
        from modules.ui_stunning import render_hero
        render_hero("📁 File Analyzer", "Upload and analyze CSV, Excel, PDF & DOCX files", "📊")
    except Exception:
        st.title("📁 File Analyzer")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    try:
        render_file_analyzer_page()
    except Exception as e:
        st.error(f"❌ File analyzer error: {e}")
        
        # Fallback simple uploader
        st.subheader("Quick Upload")
        uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"])
        if uploaded:
            try:
                if uploaded.name.endswith(".csv"):
                    df = pd.read_csv(uploaded)
                else:
                    df = pd.read_excel(uploaded)
                st.success(f"Loaded: {len(df)} rows")
                st.dataframe(df)
            except Exception as ex:
                st.error(f"Error: {ex}")
    
    gc.collect()

def render_literature_engine():
    """Literature engine page."""
    st.markdown("---")
    
    try:
        from modules.ui_stunning import render_hero, render_feature_card
        render_hero("📚 Literature Engine", "Search and analyze academic papers", "🔍")
    except Exception:
        st.title("📚 Literature Engine")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Check access
    try:
        if not check_feature_access("literature_search"):
            st.warning("🔒 Literature Engine requires at least Free tier.")
            return
    except Exception:
        pass
    
    st.info("Literature Engine - Search and analyze academic papers")
    
    # Search interface
    st.subheader("🔍 Search")
    query = st.text_input("Search query", placeholder="Enter keywords...")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        max_results = st.slider("Max results", 5, 50, 10)
    with col2:
        st.markdown("#####")
        search_btn = st.button("Search", type="primary")
    
    if search_btn and query:
        st.info(f"Searching for: {query}")
        # Add actual search implementation here
    
    gc.collect()

def render_audit_portal():
    """Audit compliance page with tier-based access."""
    st.markdown("---")
    
    try:
        from modules.ui_stunning import render_hero, render_badge
        render_hero("📜 Audit & Compliance", "AI-powered academic integrity analysis", "🛡️")
    except Exception:
        st.title("📜 Audit & Compliance")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Check tier and limits
    tier = get_current_tier() if 'get_current_tier' in dir() else None
    tier_name = tier.name if tier else "FREE"
    
    # Audit limits per tier
    AUDIT_LIMITS = {"FREE": 3, "STANDARD": 15, "PREMIUM": 999999}
    audit_limit = AUDIT_LIMITS.get(tier_name, 3)
    
    # Track usage
    if "audit_count" not in st.session_state:
        st.session_state["audit_count"] = 0
    
    # Access check
    if tier_name == "FREE" and st.session_state["audit_count"] >= 3:
        st.warning("🔒 **Free Tier Limit Reached** - You've used 3/3 free audits this month.")
        st.info("💡 Upgrade to **Standard** (15 audits/mo) or **Premium** (unlimited) in Settings → Subscription")
        return
    
    # Show tier badge & remaining
    col_info, col_tier = st.columns([2, 1])
    with col_info:
        if audit_limit < 999999:
            st.markdown(f"**Remaining Audits:** {audit_limit - st.session_state['audit_count']}/{audit_limit}")
        else:
            st.markdown("**📊 Unlimited Audits**")
    with col_tier:
        st.markdown(f'<span class="tier-badge tier-{tier_name.lower() if tier_name != "FREE" else "free"}">{tier_name}</span>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Multi-tab interface
    tab1, tab2, tab3, tab4 = st.tabs([
        "📤 Upload & Analyze",
        "🔍 Trace Tracker", 
        "📈 Similarity Heatmap",
        "📋 Audit History"
    ])
    
    with tab1:
        render_audit_upload(tab=True)
    
    with tab2:
        render_trace_tracker()
    
    with tab3:
        render_similarity_heatmap()
    
    with tab4:
        render_audit_history()
    
    gc.collect()

def render_settings():
    """Settings page."""
    st.markdown("---")
    
    try:
        from modules.ui_stunning import render_hero, render_badge, render_tier_badge
        render_hero("⚙️ Settings", "Configure your account and preferences", "🔧")
    except Exception:
        st.title("⚙️ Settings")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🔐 Credentials", "💳 Subscription", "📧 Email", "🔧 Advanced"])
    
    with tab1:
        st.subheader("Notion Credentials")
        
        token = st.text_input("Notion Token", type="password", value=get_notion_token())
        db_id = st.text_input("Database ID", value=get_database_id())
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save Credentials"):
                st.session_state["user_NOTION_TOKEN"] = token
                st.session_state["user_DATABASE_ID"] = db_id
                st.success("Saved!")
        with col2:
            if st.button("Clear"):
                st.session_state["user_NOTION_TOKEN"] = ""
                st.session_state["user_DATABASE_ID"] = ""
                st.success("Cleared!")
    
    with tab2:
        from modules.verification import render_tier_selector
        try:
            render_tier_selector()
        except Exception as e:
            st.error(f"Settings error: {e}")
            st.markdown("### 💳 Subscription")
            st.info("Subscription management requires database configuration.")
    
    with tab3:
        st.subheader("Email Settings")
        
        st.text_input("From Email", value="chrishem242@gmail.com", disabled=True)
        st.text_input("SMTP Host", value="smtp.gmail.com", disabled=True)
        
        smtp_pass = st.text_input("SMTP Password", type="password")
        if st.button("Save Email Settings"):
            st.success("Email settings saved!")
    
    with tab4:
        st.subheader("Advanced")
        
        if st.button("Clear Cache"):
            gc.collect()
            st.success("Cache cleared!")
        
        if st.button("Reset Session"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    gc.collect()

# ─── Audit Portal Helpers ─────────────────────────────────────────────

def render_audit_upload(tab=False):
    """Render audit file upload and analysis."""
    if not tab:
        st.subheader("📄 Submit Document for Audit")
    
    input_method = st.radio("Input Method", ["Upload File", "Paste Text"], horizontal=True)
    
    text_content = ""
    
    if input_method == "Upload File":
        uploaded = st.file_uploader("Upload PDF, DOCX, or TXT", type=["pdf", "docx", "txt"])
        if uploaded:
            if AuditOrchestrator:
                try:
                    from modules.audit_engine import UniversalFileReader
                    text_content, _ = UniversalFileReader.read_file(
                        uploaded.getvalue(), uploaded.name
                    )
                    st.success(f"✅ Extracted {len(text_content)} characters")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
            else:
                st.warning("⚠️ Audit engine not available")
    else:
        text_content = st.text_area("Paste text here", height=200)
    
    # Analysis options
    if text_content:
        st.markdown("---")
        st.subheader("⚙️ Analysis Options")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.checkbox("AI Content Detection", value=True, disabled=True)
        with col2:
            st.checkbox("Plagiarism Check", value=True, disabled=True)
        with col3:
            st.checkbox("Statistical Profile", value=True, disabled=True)
        
        if st.button("🔍 Run Audit Analysis", type="primary"):
            st.session_state["audit_count"] = st.session_state.get("audit_count", 0) + 1
            
            with st.spinner("Analyzing document..."):
                if AuditOrchestrator:
                    try:
                        orch = get_audit_orchestrator()
                        result = orch.audit_text(text_content, student_id="user")
                        
                        scores = result.get("composite_scores", {})
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            ai_score = scores.get('ai_content_score', 0)
                            st.metric("🤖 AI Content", f"{ai_score}%")
                        with col2:
                            plag_score = scores.get('plagiarism_score', 0)
                            st.metric("🚨 Plagiarism Risk", f"{plag_score}%")
                        with col3:
                            auth_score = scores.get('authenticity_score', 0)
                            st.metric("✅ Authenticity", f"{auth_score}%")
                        
                        st.divider()
                        render_email_options(result)
                        
                    except Exception as e:
                        st.error(f"Audit failed: {e}")

def render_trace_tracker():
    """Render Aidify traceability timeline."""
    st.subheader("🔍 Aidify Trace Tracker")
    st.info("Track every modification and AI assistance in your document.")
    
    demo_events = [
        {"time": "2 mins ago", "event": "BULK_PASTE_DETECTED", "detail": "150 words pasted"},
        {"time": "5 mins ago", "event": "AI_ASSISTANCE", "detail": "Text humanization applied"},
        {"time": "10 mins ago", "event": "MANUAL_EDIT", "detail": "Paragraph reworded"},
    ]
    
    for ev in demo_events:
        st.markdown(f"**{ev['time']}** - {ev['event']}: {ev['detail']}")
    
    st.info("💡 Connect to a project for real-time traceability.")

def render_similarity_heatmap():
    """Render plagiarism similarity heatmap."""
    st.subheader("📈 Similarity Heatmap")
    st.info("Visualize potential similarity with source materials.")
    
    # Demo visualization
    st.progress(85, text="High similarity: Section 2 (lines 20-45)")
    st.progress(45, text="Moderate: Section 5 (lines 60-80)")
    st.progress(15, text="Low: Section 8 (lines 100-120)")
    
    st.markdown("""
    **Legend:**
    - 🔴 Red (>50%): Review required
    - 🟡 Yellow (20-50%): Citation needed
    - 🟢 Green (<20%): Acceptable
    """)

def render_audit_history():
    """Render audit history."""
    st.subheader("📋 Audit History")
    
    if "audit_history" not in st.session_state:
        st.session_state["audit_history"] = []
    
    history = st.session_state.get("audit_history", [])
    
    if not history:
        st.info("No audits run yet. Upload a document to begin.")
    else:
        for idx, audit in enumerate(history):
            st.write(f"Audit #{idx+1}: {audit.get('date', 'Unknown')}")
    
    if st.button("🗑️ Clear History"):
        st.session_state["audit_history"] = []

# ═══════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()