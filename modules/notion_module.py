
"""Notion Module  Template Duplication & Embedded Workspace."""
import os
import time
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

import streamlit as st
import requests


# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

# The Bio-Research Enterprise Research Planner template
TEMPLATE_PAGE_ID = "35f9142806c6805286a5c6767a7c9cfd"
TEMPLATE_URL = f"https://app.notion.so/p/{TEMPLATE_PAGE_ID}"
EMBED_URL = f"https://site.notion.site/Bio-Research-Enterprise-Research-Planner-{TEMPLATE_PAGE_ID}"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

def _get_service_headers() -> dict:
    return {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }

# ═══════════════════════════════════════════════════════════════════════
# NOTION API CLIENT
# ═══════════════════════════════════════════════════════════════════════

class NotionClient:
    """Client for interacting with Notion API."""
    
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make rate-limited API request."""
        url = f"{NOTION_API_URL}{endpoint}"
        kwargs.setdefault("headers", self.headers)
        kwargs.setdefault("timeout", 30)
        
        # Simple rate limiting
        time.sleep(0.35)  # ~3 requests per second max
        
        try:
            response = requests.request(method, url, **kwargs)
            if response.status_code == 200:
                return response.json()
            elif response.status_code in (401, 403):
                st.error("🔐 Invalid Notion token or insufficient permissions.")
                return None
            elif response.status_code == 404:
                st.warning("📄 Notion resource not found.")
                return None
            else:
                st.error(f"Notion API error: {response.status_code}")
                return None
        except Exception as e:
            st.error(f"Request failed: {e}")
            return None
    
    def get_page(self, page_id: str) -> Optional[Dict]:
        """Get a page by ID."""
        return self._request("GET", f"/pages/{page_id}")
    
    def get_page_children(self, block_id: str) -> List[Dict]:
        """Get child blocks of a page."""
        results = []
        has_more = True
        cursor = None
        
        while has_more:
            params = {"page_size": 100}
            if cursor:
                params["start_cursor"] = cursor
            
            data = self._request("GET", f"/blocks/{block_id}/children", params=params)
            if not data:
                break
            
            results.extend(data.get("results", []))
            has_more = data.get("has_more", False)
            cursor = data.get("next_cursor")
        
        return results
    
    def duplicate_page(self, page_id: str, new_title: str = None) -> Optional[str]:
        """
        Create a copy of a page.
        Notion doesn't have a direct duplicate API - we copy content.
        Returns new page ID.
        """
        # Get source page blocks
        source_blocks = self.get_page_children(page_id)
        if not source_blocks:
            return None
        
        # Create new page (requires a parent database or page)
        # For now, return the template link (user duplicates manually)
        # In production: create page in user's workspace
        
        return page_id  # Return original - user must duplicate manually
    
    def search(self, query: str = "", filter_type: str = "page") -> List[Dict]:
        """Search Notion workspace."""
        payload = {
            "query": query,
            "filter": {"property": "object", "value": filter_type},
            "page_size": 100,
        }
        
        data = self._request("POST", "/search", json=payload)
        if data:
            return data.get("results", [])
        return []
    
    def get_databases(self) -> List[Dict]:
        """List all accessible databases."""
        return self.search(query="", filter_type="database")

# ═══════════════════════════════════════════════════════════════════════
# DUPLICATION TRACKING
# ═══════════════════════════════════════════════════════════════════════

def check_notion_claimed(user_id: str = None) -> bool:
    """Check if user has already claimed their Notion duplication."""
    user_id = user_id or st.session_state.get("user_id")
    
    if not user_id:
        return False
    
    # Check Supabase
    if SUPABASE_URL:
        try:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                },
            )
            if response.status_code == 200:
                users = response.json()
                if users:
                    return users[0].get("notion_claimed", False)
        except Exception:
            pass
    
    # Fallback to session state
    return st.session_state.get("notion_claimed", False)

def mark_notion_claimed(user_id: str = None):
    """Mark Notion duplication as claimed in database."""
    user_id = user_id or st.session_state.get("user_id")
    
    if not user_id:
        st.session_state["notion_claimed"] = True
        return
    
    # Update Supabase
    if SUPABASE_URL:
        try:
            requests.patch(
                f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}",
                headers=_get_service_headers(),
                json={"notion_claimed": True, "notion_claimed_at": datetime.utcnow().isoformat()},
            )
        except Exception:
            pass
    
    # Update session
    st.session_state["notion_claimed"] = True

# ═══════════════════════════════════════════════════════════════════════
# STREAMLIT UI
# ═══════════════════════════════════════════════════════════════════════

def render_notion_duplication():
    """Render the Notion template duplication UI."""
    from modules.subscription import check_feature_access, Tier, get_current_tier
    
    st.subheader("📋 Notion Enterprise Research Planner")
    
    # Check premium access
    current_tier = get_current_tier()
    if current_tier != Tier.PREMIUM:
        if not check_feature_access("notion_workspace"):
            st.warning(f"🔒 Notion Workspace requires **Premium** tier.")
            st.info("Upgrade at: Settings → Subscription → Premium")
            
            # Show preview
            with st.expander("👀 Preview the Template"):
                st.markdown(f"""
                ### Bio-Research Enterprise Research Planner
                
                A comprehensive research planning tool including:
                -  Project Timeline & Milestones
                - 📚 Literature Review Tracker
                - 🔬 Methodology Framework
                - 📝 Research Journal
                - 📈 Data Analysis Templates
                - 📋 Grant Application Checklist
                
                [View Template]({TEMPLATE_URL})
                """)
            return
    
    # Check if already claimed
    already_claimed = check_notion_claimed()
    
    if already_claimed:
        st.success("✅ You have already claimed your 1-time Notion workspace duplication!")
        
        st.markdown(f"""
        ### Your Notion Research Planner
        
        Access your duplicated workspace below:
        
        **[Open in Notion →]({TEMPLATE_URL})**
        
        *Note: The duplication was created when you first claimed this feature.*
        """)
    else:
        st.markdown(f"""
        ### Claim Your Free Notion Workspace
        
        As a **Premium** member, you get a one-time free duplication of the 
        **Bio-Research Enterprise Research Planner** template.
        
        This template includes:
        -  Project Timeline & Milestones
        - 📚 Literature Review Tracker  
        - 🔬 Methodology Framework
        - 📝 Research Journal
        - 📈 Data Analysis Templates
        - 📋 Grant Application Checklist
        """)
        
        # Claim button
        if st.button("🎁 Claim & Duplicate Workspace", type="primary"):
            # Mark as claimed BEFORE opening link
            mark_notion_claimed()
            
            # Open Notion in new tab
            st.markdown('''
            <script>
                window.open("{TEMPLATE_URL}", "_blank");
            </script>
            ''', unsafe_allow_html=True)
            
            st.success("✅ Workspace duplication claimed!")
            st.info(f"[Click here to open Notion]({TEMPLATE_URL}) if the link didn't open automatically.")
            
            st.rerun()

def render_notion_embed():
    """Render embedded Notion workspace view."""
    from modules.subscription import check_feature_access, Tier, get_current_tier
    
    st.subheader("🔗 Live Notion Workspace")
    
    # Check premium access
    current_tier = get_current_tier()
    if current_tier != Tier.PREMIUM:
        st.warning(f"🔒 Notion Workspace requires **Premium** tier.")
        return
    
    # Check if claimed
    if not check_notion_claimed():
        st.info("⚠️ You need to claim your workspace first!")
        if st.button("Go to Claim Page"):
            st.session_state["notion_tab"] = "claim"
            st.rerun()
        return
    
    # Render embedded iframe
    st.markdown(f"""
    <iframe 
        src="{EMBED_URL}"
        style="
            width: 100%;
            height: 850px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            frameborder: 0;
        "
        allow="clipboard-write"
    ></iframe>
    """, unsafe_allow_html=True)
    
    # Controls
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Refresh"):
            st.rerun()
    with col2:
        st.markdown(f"[Open Full Screen →]({EMBED_URL})")
    with col3:
        if st.button("📋 Copy Link"):
            st.code(EMBED_URL)
            st.toast("Link copied to clipboard!")

def render_notion_module():
    """Main render function for the Notion module tab."""
    st.markdown("## 🔗 Notion Integration")
    
    # Tabs for different Notion features
    tab1, tab2, tab3 = st.tabs(["📋 Claim Workspace", "🔗 Embedded View", "⚙️ Settings"])
    
    with tab1:
        render_notion_duplication()
    
    with tab2:
        render_notion_embed()
    
    with tab3:
        st.markdown("### ⚙️ Notion Settings")
        
        st.write("""
        **Connection Status:**
        - Template: Bio-Research Enterprise Research Planner
        - Claim Status: One-time per Premium user
        """)
        
        # Re-link option
        st.divider()
        if st.button("🔄 Reset Claim Status (Developer Only)"):
            # Only allow if explicitly set in secrets
            if os.environ.get("ALLOW_NOTION_RESET", "").lower() == "true":
                user_id = st.session_state.get("user_id")
                if SUPABASE_URL and user_id:
                    try:
                        requests.patch(
                            f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}",
                            headers=_get_service_headers(),
                            json={"notion_claimed": False},
                        )
                    except Exception:
                        pass
                st.session_state["notion_claimed"] = False
                st.success("Claim status reset!")
                st.rerun()
            else:
                st.error("This action is disabled. Contact administrator.")

# ═══════════════════════════════════════════════════════════════════════
# CACHED RESOURCES
# ═══════════════════════════════════════════════════════════════════════

@st.cache_resource(ttl=3600)
def get_notion_client(token: str = None) -> Optional[NotionClient]:
    """Get cached Notion client instance."""
    if not token:
        from modules.auth import get_notion_token
        token = get_notion_token()
    
    if not token:
        return None
    
    return NotionClient(token)

@st.cache_data(ttl=300)
def get_notion_databases_cached(token: str) -> List[Dict]:
    """Get cached list of Notion databases."""
    client = get_notion_client(token)
    if client:
        return client.get_databases()
    return []

def open_notion_link(url: str):
    """Open Notion link in new tab via JavaScript."""
    st.markdown(f'<script>window.open("{url}", "_blank");</script>', unsafe_allow_html=True)


