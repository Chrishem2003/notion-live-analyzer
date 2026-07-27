import streamlit as st
import os
from notion_helper import auto_detect_database_ids

# Streamlit Page Configuration
st.set_page_config(
    page_title="Notion Live Research Analyzer",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# SIDEBAR BRANDING & DISPLAY PICTURE (DP)
# ---------------------------------------------------------
with st.sidebar:
    logo_path = os.path.join("assets", "app_logo.png")
    
    if os.path.exists(logo_path):
        # Displays the custom logo / avatar DP
        st.image(logo_path, use_container_width=True)
    else:
        st.title("🧬 Research Analyzer")

    st.markdown("### Notion Research Analyzer")
    st.caption("Real-Time Data & Genomic Pipeline Sync")
    st.markdown("---")

    # Notion Workspace Authentication Input
    st.subheader("Workspace Connection")
    notion_token = st.text_input("Notion Access Token:", type="password", help="Paste your integration token here")

    REQUIRED_DATABASES = [
        "Project Master",
        "Genomic Sequence Log",
        "Literature Pipeline",
        "Sample Collections"
    ]

    if notion_token:
        st.session_state["notion_token"] = notion_token
        
        if st.button("🔍 Auto-Detect Databases", use_container_width=True):
            with st.spinner("Scanning connected Notion workspace..."):
                db_map = auto_detect_database_ids(notion_token, REQUIRED_DATABASES)
                st.session_state["db_ids"] = db_map

    # Display Connection Status
    if "db_ids" in st.session_state:
        db_map = st.session_state["db_ids"]
        found_count = len(db_map)
        total_count = len(REQUIRED_DATABASES)

        if found_count == total_count:
            st.success(f" Connected: {found_count}/{total_count} Databases Found")
        else:
            st.warning(f" Found {found_count}/{total_count} Databases")
            
        with st.expander("Detected Database IDs"):
            for name, db_id in db_map.items():
                st.caption(f"**{name}:** `{db_id[:8]}...`")

# ---------------------------------------------------------
# MAIN DASHBOARD AREA
# ---------------------------------------------------------
st.title("Notion Live Research Analytics Dashboard")
st.write("Welcome to your automated research workspace sync tool.")

if "db_ids" not in st.session_state:
    st.info("👈 Enter your Notion Access Token in the sidebar and click **Auto-Detect Databases** to start sync.")
else:
    st.success("Dashboard connected and ready for data extraction!")
    # Your interactive charts, dataframes, and visualizations go here
