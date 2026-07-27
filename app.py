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
            "📜 Audit Compliance",
            "🔗 Notion Workspace",
            "🔗 Integrations",
            "🎯 Research Hub",
            "⚙️ Settings",
        ]
        
        # Add admin link
        if os.environ.get("ADMIN_KEY"):
            pages.append("🔧 Admin")
        
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
    elif page == "📜 Audit Compliance":
        render_audit_portal()
    elif page == "🔗 Notion Workspace":
        render_notion_module()
    elif page == "⚙️ Settings":
        from modules.advanced_features import render_settings_new
        render_settings_new()
    elif page == "🔗 Integrations":
        from modules.academic_integrations import render_academic_integrations
        render_academic_integrations()
    elif page == "🔧 Admin":
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
    """Audit compliance page."""
    st.markdown("---")
    
    try:
        from modules.ui_stunning import render_hero, render_badge
        render_hero("📜 Audit Compliance", "AI-powered academic integrity analysis", "🛡️")
    except Exception:
        st.title("📜 Audit Compliance")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Document input
    st.subheader("📄 Submit Document for Audit")
    
    input_method = st.radio("Input Method", ["Upload File", "Paste Text"], horizontal=True)
    
    text_content = ""
    
    if input_method == "Upload File":
        uploaded = st.file_uploader("Upload PDF, DOCX, or TXT", type=["pdf", "docx", "txt"])
        if uploaded:
            # Process file
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
    
    # Run audit
    if text_content:
        st.markdown("---")
        st.subheader("📊 Audit Results")
        
        if st.button("🔍 Run Audit Analysis", type="primary"):
            with st.spinner("Analyzing document..."):
                if AuditOrchestrator:
                    try:
                        orch = get_audit_orchestrator()
                        result = orch.audit_text(text_content, student_id="user")
                        
                        # Display scores
                        scores = result.get("composite_scores", {})
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("AI Content", f"{scores.get('ai_content_score', 0)}%")
                        with col2:
                            st.metric("Plagiarism Risk", f"{scores.get('plagiarism_score', 0)}%")
                        with col3:
                            st.metric("Authenticity", f"{scores.get('authenticity_score', 0)}%")
                        
                        # Statistical profile
                        profile = result.get("statistical_profile", {})
                        st.json(profile)
                        
                        # Email delivery
                        st.divider()
                        render_email_options(result)
                        
                    except Exception as e:
                        st.error(f"Audit failed: {e}")
                else:
                    st.error("Audit engine not available")
    
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

# ═══════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()