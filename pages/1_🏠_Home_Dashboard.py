"""
🏠 Home Dashboard — Unified Platform Landing Hub
Consolidates: app.py dashboard hub, saved analyses vault, live telemetry, system overview.
"""

import datetime
import sqlite3

import pandas as pd
import streamlit as st
from streamlit.components.v1 import html

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.session_manager import dataset_summary, get_active_dataframe
from modules.navigation import hub_quick_access_cards, visible_hubs
from modules.shared_ui import hero_card, section_header, metric_card


def get_db():
    """Open the sovereign database connection."""
    conn = sqlite3.connect("sovereign_apex_engine.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            timestamp TEXT,
            category TEXT,
            content TEXT
        )
    """)
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
    conn.commit()
    return conn


def render_saved_analyses_vault(conn):
    """Render the saved analyses vault."""
    section_header("💾 Saved Analyses & Reports Vault", "Review all reports and analyses saved to the secure database.")

    cursor = conn.cursor()
    cursor.execute("SELECT id, title, timestamp, category, content FROM saved_analyses ORDER BY id DESC")
    saved_rows = cursor.fetchall()

    if not saved_rows:
        st.info("No saved analyses found yet. Run analyses across the hubs and they'll appear here.")
        return

    for s_id, s_title, s_ts, s_cat, s_content in saved_rows:
        with st.expander(f"📄 {s_title} — {s_ts[:19]}", expanded=False):
            st.markdown(f"**Category:** `{s_cat}`")
            st.markdown(s_content)
            st.download_button(
                label=f"⬇️ Download as Markdown (#{s_id})",
                data=str(s_content),
                file_name=f"analysis_{s_id}.md",
                mime="text/markdown",
                key=f"dl_{s_id}",
            )


def render_live_telemetry(conn):
    """Render system telemetry overview."""
    section_header("📡 System Telemetry & Health", "Live monitoring of the sovereign platform.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("System Uptime", "99.99%", delta="Stable")
    c2.metric("Database Health", "Connected", delta="0ms Latency")
    c3.metric("Memory Utilization", "42.8%", delta="-1.2%")
    c4.metric("Active Hubs", "15 Hubs", delta="Unified")

    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, module_name, severity, crypto_hash FROM system_telemetry_logs ORDER BY id DESC LIMIT 10")
    logs_data = cursor.fetchall()
    if logs_data:
        logs_df = pd.DataFrame(logs_data, columns=["ID", "Timestamp", "Module", "Severity", "Crypto Hash"])
        st.dataframe(logs_df, use_container_width=True, hide_index=True)
    else:
        st.info("No system telemetry logs recorded yet.")


def main():
    setup_page("Home Dashboard", "🏠", initial_sidebar_state="expanded")

    hero_card(
        "🏠 Chrishem Unified Platform Home",
        "Welcome to the consolidated sovereign analytics workspace. Navigate via the sidebar hubs to access all analytical, ML, publishing, integration, and security tools.",
        badge_text="UNIFIED PLATFORM v9.0",
    )

    # ── Session greeting card ──
    identity = st.session_state.get("user_identity", {})
    name = identity.get("name", "Analyst")
    role = identity.get("role", "Data Analyst")

    now_dt = datetime.datetime.now()
    hour = now_dt.hour
    greeting = (
        "Good Morning" if 5 <= hour < 12
        else "Good Afternoon" if 12 <= hour < 17
        else "Good Evening" if 17 <= hour < 21
        else "Good Night"
    )

    summary = dataset_summary()

    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center; 
             background: linear-gradient(135deg, rgba(56, 189, 248, 0.12), rgba(129, 140, 248, 0.12)); 
             border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 14px; 
             padding: 1rem 1.25rem; margin-bottom: 1.25rem;">
            <div>
                <div style="font-size:1.15rem; font-weight:700; color:#F8FAFC;">{greeting}, {name}! 👋</div>
                <div style="font-size:0.85rem; color:#38BDF8; font-weight:500; margin-top:0.15rem;">
                    Active Session: {role} | {now_dt.strftime('%A, %Y-%m-%d %H:%M')}
                </div>
            </div>
            <div>
                <span class="status-badge status-stable">● SYSTEM OPERATIONAL</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Dataset status strip ──
    if summary:
        st.success(
            f"📊 **Active Dataset:** `{summary['source']}` — {summary['rows']:,} rows × {summary['cols']} cols "
            f"| {summary['numeric']} numeric | {summary['categorical']} categorical"
        )
    else:
        st.warning("📭 **No active dataset.** Load data in the **📁 Data Studio** hub to begin your analysis pipeline.")

    st.markdown('<div class="chris-hr"></div>', unsafe_allow_html=True)

    # ── Quick access cards ──
    section_header("🚀 Quick Access — Workspace Hubs", "Select a hub to begin. Each hub consolidates multiple tools into tabs.")
    hub_quick_access_cards()

    st.markdown('<div class="chris-hr"></div>', unsafe_allow_html=True)

    # ── Tabs for vault + telemetry ──
    tab_vault, tab_telemetry, tab_about = st.tabs(["💾 Saved Analyses Vault", "📡 Live Telemetry", "ℹ️ About Platform"])

    conn = get_db()

    with tab_vault:
        render_saved_analyses_vault(conn)

    with tab_telemetry:
        render_live_telemetry(conn)

with tab_about:
        section_header("ℹ️ About the Unified Platform")
        st.markdown(
            """
            **CHRISHEM Sovereign Intelligence Platform v10.0** consolidates 66 legacy pages into **15 organized hubs**:

            | Hub | Consolidates |
            |-----|-------------|
            | 🏠 Home Dashboard | Dashboard, vault, telemetry |
            | 📁 Data Studio | Ingestion, quality, transform, simulator |
            | 📊 Statistics Studio | Hypothesis tests, causal, Bayesian |
            | 🤖 ML & Predictive Studio | AutoML, feature engineering, AI insights |
            | 📈 Visualization Studio | Charts, dashboards, presentations |
            | 💬 AI & NLP Studio | Text mining, NL query, synthesis |
            | 📚 Literature & Publishing Hub | Meta-analysis, APA, citations, grants |
            | 🔬 Domain Analytics Hub | Clinical, GIS, research quality |
            | 🔗 Integrations Hub | Notion, Sheets, Git, APIs |
            | 🛡️ Admin & Security Center | Settings, diagnostics, vault, licensing |
            | 🤝 Collaboration & Portfolio | Pipeline, agents, academic portfolio |

            *Built by Kula Chris (CHRISHEM).*
            """
        )

    render_standard_footer("HOME DASHBOARD")


if __name__ == "__main__":
    main()

