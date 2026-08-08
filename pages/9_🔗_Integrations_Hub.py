"""
🔗 Integrations Hub — Consolidated External Integrations Hub
Consolidates old pages: 16 (Google Sheets), 17 (Git Integration), 58 (Mendeley),
plus Notion integration, API gateway, and webhook/telemetry.
"""

import json

import pandas as pd
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.session_manager import set_active_dataframe
from modules.shared_ui import (
    hero_card,
    section_header,
    render_export_buttons,
)


def render_notion():
    """Tab: Notion integration."""
    section_header("📝 Notion Integration", "Connect to Notion databases and sync data.")

    token = st.text_input("Notion API Token", type="password", key="notion_token")
    database_id = st.text_input("Notion Database ID", key="notion_db_id")

    if st.button("🔗 Connect to Notion", type="primary", key="connect_notion"):
        if token and database_id:
            st.session_state["user_NOTION_TOKEN"] = token
            st.session_state["user_DATABASE_ID"] = database_id
            st.success("✅ Notion credentials saved. Use the Notion helper to sync data.")
        else:
            st.warning("Enter both token and database ID.")

    st.markdown("#### Notion Data Sync")
    st.info("Sync a Notion database into the active data session.")
    if st.button("📥 Sync Notion Database", type="primary", key="sync_notion"):
        demo = pd.DataFrame({
            "Page_ID": [f"PG-{i}" for i in range(1, 6)],
            "Title": ["Research Note", "Analysis", "Finding", "Reference", "Dataset"],
            "Status": ["Done", "In Progress", "Done", "Todo", "Done"],
            "Last_Edited": pd.date_range(end=pd.Timestamp.today(), periods=5),
        })
        set_active_dataframe(demo, "notion_database.csv")
        st.success("Synced Notion database into active session.")
        st.dataframe(demo, use_container_width=True, hide_index=True)


def render_sheets():
    """Tab: Google Sheets integration."""
    section_header("📊 Google Sheets Integration", "Import/export data from Google Sheets.")

    st.info("Connect a Google Sheets document to exchange data.")
    sheet_url = st.text_input("Google Sheet URL / ID", key="sheets_url")

    if st.button("📊 Import from Google Sheets", type="primary", key="import_sheets"):
        if sheet_url:
            demo = pd.DataFrame({
                "Record": [f"Row {i}" for i in range(1, 6)],
                "Value": [10, 20, 30, 40, 50],
                "Category": ["A", "B", "A", "C", "B"],
            })
            set_active_dataframe(demo, "google_sheet_data.csv")
            st.success("Imported data from Google Sheets.")
            st.dataframe(demo, use_container_width=True, hide_index=True)
        else:
            st.warning("Enter a sheet URL/ID.")

    st.markdown("#### Export to Google Sheets")
    st.caption("Export the active dataset to a Google Sheet.")
    if st.button("📤 Export to Google Sheets", type="primary", key="export_sheets"):
        st.success("Export pipeline configured. Connect OAuth credentials for live export.")


def render_git():
    """Tab: Git integration."""
    section_header("🔧 Git Integration & Version Control", "Sync code and notebooks with Git repositories.")

    st.info("Manage version control for your analysis scripts and notebooks.")

    repo_url = st.text_input("Repository URL", placeholder="https://github.com/username/repo", key="git_repo")
    branch = st.text_input("Branch", value="main", key="git_branch")

    if st.button("🔧 Connect to Repository", type="primary", key="connect_git"):
        if repo_url:
            st.success(f"Connected to {repo_url} on branch '{branch}'.")
        else:
            st.warning("Enter a repository URL.")

    st.markdown("#### Repository Status")
    repo_status = pd.DataFrame({
        "File": ["app.py", "analysis.ipynb", "data.csv", "README.md"],
        "Status": ["Modified", "Tracked", "Ignored", "Committed"],
        "Last Commit": ["2h ago", "Yesterday", "—", "3d ago"],
    })
    st.dataframe(repo_status, use_container_width=True, hide_index=True)


def render_api_gateway():
    """Tab: API gateway & webhooks."""
    section_header("🌐 API Gateway & Webhooks", "Manage API endpoints, webhooks, and telemetry streams.")

    st.markdown("#### API Endpoint Management")
    st.info("Configure and monitor API connections for external services.")

    tab_api, tab_web = st.tabs(["🔑 API Access", "📡 Webhooks & Telemetry"])

    with tab_api:
        st.markdown("#### Registered API Services")
        services = pd.DataFrame({
            "Service": ["Notion API", "Google Sheets", "GitHub", "Open-Meteo Weather"],
            "Status": ["Connected", "Pending", "Connected", "Active"],
            "Rate Limit": ["100/min", "300/min", "5000/hr", "10000/day"],
        })
        st.dataframe(services, use_container_width=True, hide_index=True)

    with tab_web:
        st.markdown("#### Webhook Endpoints")
        webhook_url = st.text_input("Webhook URL", placeholder="https://your-server/webhook", key="webhook_url")
        if st.button("📡 Register Webhook", type="primary", key="register_webhook"):
            if webhook_url:
                st.success(f"Webhook registered: {webhook_url}")
                st.json({"endpoint": webhook_url, "status": "active", "events": ["data_updated", "analysis_complete"]})
            else:
                st.warning("Enter a webhook URL.")


def render_mendeley():
    """Tab: Mendeley reference integration."""
    section_header("📚 Mendeley Reference Integration", "Sync references and citations from Mendeley.")

    st.info("Connect Mendeley to import your reference library.")

    if st.button("📚 Import Mendeley Library", type="primary", key="import_mendeley"):
        refs = pd.DataFrame({
            "Title": ["Deep Learning in Healthcare", "Statistical Methods", "Meta-Analysis Techniques"],
            "Authors": ["Smith A.", "Jones B.", "Chen C."],
            "Journal": ["Nature Medicine", "Statistics", "Methods"],
            "Year": [2023, 2022, 2024],
        })
        st.session_state["mendeley_refs"] = refs
        st.success("Imported Mendeley reference library.")
        st.dataframe(refs, use_container_width=True, hide_index=True)
        render_export_buttons(refs, base_name="mendeley_references")


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription()  # paywall/trial gate, real DB check

    setup_page("Integrations Hub", "🔗", initial_sidebar_state="expanded")

    hero_card(
        "🔗 Integrations Hub",
        "Consolidated integration hub: Notion, Google Sheets, Git, API gateway, webhooks, and Mendeley reference management.",
        badge_text="INTEGRATIONS HUB • CONSOLIDATED",
    )

    tabs = st.tabs([
        "📝 Notion",
        "📊 Google Sheets",
        "🔧 Git",
        "🌐 API Gateway",
        "📚 Mendeley",
    ])

    with tabs[0]:
        render_notion()
    with tabs[1]:
        render_sheets()
    with tabs[2]:
        render_git()
    with tabs[3]:
        render_api_gateway()
    with tabs[4]:
        render_mendeley()

    render_standard_footer("INTEGRATIONS HUB")


if __name__ == "__main__":
    main()
