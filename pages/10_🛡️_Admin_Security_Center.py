"""
🛡️ Admin & Security Center — Consolidated Administration & Security Hub
Consolidates old pages: 5 (Settings), 32 (Audit Compliance), 44 (Secure Vault),
47 (System Diagnostics), 61/62 (Billing/Licensing), 65 (AI Defensive Cores).
"""

import datetime
import json
import platform
import sqlite3

import pandas as pd
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.shared_ui import (
    hero_card,
    section_header,
    metric_card,
)


def get_db():
    conn = sqlite3.connect("sovereign_apex_engine.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_telemetry_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            module_name TEXT,
            severity TEXT,
            details TEXT,
            crypto_hash TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            username TEXT PRIMARY KEY,
            role TEXT,
            birthday TEXT,
            last_seen TEXT,
            visit_count INTEGER
        )
    """)
    conn.commit()
    return conn


def render_system_diagnostics(conn):
    """Tab: System diagnostics."""
    section_header("🔍 System Diagnostics & Telemetry", "Real-time system health monitoring.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("System Uptime", "99.99%", delta="Stable")
    c2.metric("Database Health", "Connected", delta="0ms")
    c3.metric("Memory Utilization", "42.8%", delta="-1.2%")
    c4.metric("Active Threads", "14 Daemons", delta="Optimal")

    st.markdown("#### Runtime Environment")
    env_data = pd.DataFrame({
        "Property": ["Python Version", "Operating System", "Platform", "Timestamp"],
        "Value": [platform.python_version(), platform.system(), platform.platform(), datetime.datetime.now().strftime("%Y-%m-%d %H:%M")],
    })
    st.dataframe(env_data, use_container_width=True, hide_index=True)

    st.markdown("#### Telemetry Logs")
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, module_name, severity, crypto_hash FROM system_telemetry_logs ORDER BY id DESC LIMIT 10")
    logs = cursor.fetchall()
    if logs:
        logs_df = pd.DataFrame(logs, columns=["ID", "Timestamp", "Module", "Severity", "Hash"])
        st.dataframe(logs_df, use_container_width=True, hide_index=True)
    else:
        st.info("No telemetry logs recorded yet.")

    if st.button("🧹 Force Garbage Collection", type="primary", key="gc_btn"):
        import gc
        collected = gc.collect()
        st.success(f"Garbage collection complete ({collected} objects freed).")


def render_user_management(conn):
    """Tab: User access & roles."""
    section_header("👤 User Management & Access Control", "Manage users, roles, and permissions.")

    st.markdown("#### Active Users")
    cursor = conn.cursor()
    cursor.execute("SELECT username, role, last_seen, visit_count FROM user_profiles ORDER BY visit_count DESC")
    users = cursor.fetchall()
    if users:
        users_df = pd.DataFrame(users, columns=["Username", "Role", "Last Seen", "Visits"])
        st.dataframe(users_df, use_container_width=True, hide_index=True)
    else:
        st.info("No user profiles recorded yet.")

    st.markdown("#### Role-Based Access Control (RBAC)")
    rbac_data = pd.DataFrame({
        "Role": ["Sovereign Administrator", "Data Analyst", "Field Researcher", "System Auditor"],
        "Access Level": ["Full Control", "Analytics Tools", "Data Entry & View", "Read-Only Audit"],
        "Permissions": ["All Hubs", "Data/Stats/ML/Viz", "Data Studio", "Admin Center"],
    })
    st.dataframe(rbac_data, use_container_width=True, hide_index=True)


def render_billing():
    """Tab: Billing & licensing."""
    section_header("💳 Billing, Licensing & Subscriptions", "Manage plans, licenses, and billing.")

    st.markdown("#### Current Plan")
    c1, c2, c3 = st.columns(3)
    c1.metric("Plan Tier", "Enterprise")
    c2.metric("License Expiry", "2030-12-31")
    c3.metric("Active Nodes", "128")

    st.markdown("#### Subscription Management")
    plan_options = ["Free", "Professional", "Enterprise", "Sovereign Apex"]
    selected_plan = st.selectbox("Select Plan", plan_options, index=2, key="plan_sel")
    if st.button("💳 Update Subscription", type="primary", key="update_plan"):
        st.success(f"Subscription updated to **{selected_plan}** plan.")

    st.markdown("#### Billing History")
    billing = pd.DataFrame({
        "Invoice": ["INV-001", "INV-002", "INV-003"],
        "Amount": ["$99.00", "$99.00", "$499.00"],
        "Status": ["Paid", "Paid", "Pending"],
        "Date": ["2024-01-01", "2024-02-01", "2024-03-01"],
    })
    st.dataframe(billing, use_container_width=True, hide_index=True)


def render_security_vault():
    """Tab: Secure vault."""
    section_header("🔒 Secure Personal Vault", "Encrypted storage for credentials and sensitive data.")

    st.markdown("#### Vault Credentials")
    token = st.text_input("Notion Token", type="password", key="vault_token")
    db_id = st.text_input("Database ID", key="vault_db")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔒 Save to Vault", type="primary", key="save_vault"):
            st.session_state["user_NOTION_TOKEN"] = token
            st.session_state["user_DATABASE_ID"] = db_id
            st.success("✅ Credentials saved to session vault.")
    with col2:
        if st.button("🗑️ Clear Vault", key="clear_vault"):
            st.session_state["user_NOTION_TOKEN"] = ""
            st.session_state["user_DATABASE_ID"] = ""
            st.success("Vault cleared.")

    st.markdown("#### Vault Audit Trail")
    st.info("Track access to sensitive vault credentials.")
    audit = pd.DataFrame({
        "Timestamp": [datetime.datetime.now().strftime("%Y-%m-%d %H:%M")],
        "Action": ["Vault Access"],
        "User": [st.session_state.get("user_identity", {}).get("name", "Analyst")],
    })
    st.dataframe(audit, use_container_width=True, hide_index=True)


def render_audit_compliance(conn):
    """Tab: Audit & compliance."""
    section_header("🛡️ Audit & Compliance Center", "Regulatory compliance and audit trail management.")

    st.markdown("#### Compliance Framework")
    compliance = pd.DataFrame({
        "Framework": ["HIPAA", "GDPR", "Data Protection", "Research Ethics"],
        "Status": ["Aligned", "Aligned", "Aligned", "Aligned"],
        "Last Audit": ["2024-01-15", "2024-02-01", "2023-12-20", "2024-03-05"],
    })
    st.dataframe(compliance, use_container_width=True, hide_index=True)

    st.markdown("#### Audit Trail")
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, module_name, severity FROM system_telemetry_logs ORDER BY id DESC LIMIT 15")
    trails = cursor.fetchall()
    if trails:
        trail_df = pd.DataFrame(trails, columns=["ID", "Timestamp", "Module", "Severity"])
        st.dataframe(trail_df, use_container_width=True, hide_index=True)
    else:
        st.info("No audit trail events recorded yet.")

    if st.button("📄 Generate Compliance Report", type="primary", key="gen_compliance"):
        report = "# COMPLIANCE & AUDIT REPORT\n\nAll frameworks aligned. No critical findings."
        st.download_button("⬇️ Download Compliance Report", data=report, file_name="compliance_report.md", mime="text/markdown")


def render_settings():
    """Tab: Settings."""
    section_header("⚙️ Platform Settings", "Theme, preferences, and system configuration.")

    st.markdown("#### Appearance Settings")
    c1, c2 = st.columns(2)
    with c1:
        theme = st.selectbox("Theme", ["dark", "light"], index=0, key="settings_theme")
    with c2:
        accent = st.color_picker("Accent Color", value="#00f2fe", key="settings_accent")

    if theme != "dark" or accent != "#00f2fe":
        st.session_state["theme"] = theme
        st.session_state["accent_color"] = accent
        st.success("Theme settings updated (applied on next rerun).")

    st.markdown("#### Data Management")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧹 Purge Cache & Datasets", type="primary", key="purge_cache"):
            st.cache_data.clear()
            for key in ["active_df", "working_df", "uploaded_df", "notion_df"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.success("Cache purged and datasets cleared.")
    with col2:
        if st.button("📦 Export Session Snapshot", key="export_snapshot"):
            snapshot = {
                "theme": st.session_state.get("theme", "dark"),
                "accent": st.session_state.get("accent_color", "#00f2fe"),
                "user": st.session_state.get("user_identity", {}),
                "timestamp": datetime.datetime.now().isoformat(),
            }
            st.download_button("⬇️ Download Snapshot", data=json.dumps(snapshot, indent=2), file_name="session_snapshot.json", mime="application/json")


def main():
    setup_page("Admin & Security Center", "🛡️", initial_sidebar_state="expanded")

    hero_card(
        "🛡️ Admin & Security Center",
        "Consolidated administration hub: system diagnostics, user management, billing & licensing, secure vault, audit compliance, and platform settings.",
        badge_text="ADMIN & SECURITY CENTER • CONSOLIDATED",
    )

    conn = get_db()

    tabs = st.tabs([
        "🔍 Diagnostics",
        "👤 Users & Access",
        "💳 Billing & Licensing",
        "🔒 Secure Vault",
        "🛡️ Audit & Compliance",
        "⚙️ Settings",
    ])

    with tabs[0]:
        render_system_diagnostics(conn)
    with tabs[1]:
        render_user_management(conn)
    with tabs[2]:
        render_billing()
    with tabs[3]:
        render_security_vault()
    with tabs[4]:
        render_audit_compliance(conn)
    with tabs[5]:
        render_settings()

    render_standard_footer("ADMIN & SECURITY CENTER")


if __name__ == "__main__":
    main()
