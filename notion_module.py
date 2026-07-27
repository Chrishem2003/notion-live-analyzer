import streamlit as st
import time

RAW_NOTION_TEMPLATE_URL = "https://app.notion.com/p/Bio-Research-Enterprise-Research-Planner-35f9142806c6805286a5c6767a7c9cfd"
EMBED_NOTION_URL = "https://site.notion.site/Bio-Research-Enterprise-Research-Planner-35f9142806c6805286a5c6767a7c9cfd"

def render_notion_portal():
    st.title("🧬 Bio-Research Enterprise Planner")
    st.caption("Custom high-throughput workspace for managing research logs, citations, and laboratory data.")

    tier = st.session_state.get("user_tier", "Free")
    notion_claimed = st.session_state.get("notion_claimed", False)

    tab1, tab2 = st.tabs(["🚀 One-Time Template Export", "📱 In-App Interactive Workspace"])

    with tab1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Duplicate Planner to Your Notion Workspace")
        
        if tier != "Premium":
            st.warning("🔒 Direct Notion Workspace duplication is an exclusive **Premium** feature.")
            st.info("Upgrade your subscription or use the In-App Interactive Workspace tab.")
        else:
            if notion_claimed:
                st.error("⛔ **Duplication Limit Reached**: You have already claimed your 1-time Notion Template export.")
                st.info("Check your primary Notion workspace for 'Bio-Research Enterprise Research Planner'.")
            else:
                st.success("✨ As a Premium member, you hold **1-time duplication authorization**.")
                st.write("Clicking below will record your single-use transfer and launch Notion.")
                
                if st.button("Claim & Duplicate to Notion Space", type="primary"):
                    st.session_state["notion_claimed"] = True
                    st.toast("Authorization recorded! Opening Notion...", icon="🚀")
                    time.sleep(1)
                    
                    js_redirect = f"<script>window.open('{RAW_NOTION_TEMPLATE_URL}', '_blank');</script>"
                    st.components.v1.html(js_redirect, height=0)
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Live Interactive Bio-Planner")
        st.caption("Work directly inside the research planner without leaving Streamlit.")
        
        st.components.v1.iframe(src=EMBED_NOTION_URL, height=800, scrolling=True)
        st.markdown('</div>', unsafe_allow_html=True)