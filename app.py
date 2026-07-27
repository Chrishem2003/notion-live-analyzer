"""
Advanced Research Data Analyzer & Visualizer
Entry point — thin orchestrator that sets up the app and delegates to modules.
Replaces SPSS, Tableau, Power BI with a single, intelligent, Notion-connected research platform.
"""
import os
import time
from datetime import datetime
from importlib.metadata import distributions as _distributions
from pathlib import Path

import pandas as pd
import streamlit as st

from modules.logging_utils import get_logger

logger = get_logger("app")

# ─── Startup Performance Timer ────────────────────────────────────────
_startup_start = time.time()

# ─── Lightweight Dependency Check (Non-Blocking) ─────────────────────
AUTO_FIX_DEPS = os.environ.get("AUTO_FIX_DEPS", "true").lower() == "true"
_HEAVY_PACKAGES = {"xgboost", "shap", "pymc", "arviz", "causalml", "prophet"}

# We defer the full dependency scan by reading the installed distribution metadata
# instead of blocking import calls. Cached in session state for fast reruns.
def _scan_installed_packages() -> set:
    try:
        return {
            (dist.metadata["Name"] or "").lower().replace("-", "_")
            for dist in _distributions()
        }
    except Exception:
        logger.exception("Dependency scan failed — skipping the startup dependency check")
        return set()


if "_installed_pkgs" not in st.session_state:
    st.session_state["_installed_pkgs"] = _scan_installed_packages()
_installed_pkgs = st.session_state["_installed_pkgs"]

# Quick check: are core packages present?
_CORE_PACKAGES = {"streamlit", "pandas", "numpy", "plotly", "requests", "scipy", "statsmodels", "openpyxl"}
_missing_core = [] if _installed_pkgs is None else [p for p in _CORE_PACKAGES if p not in _installed_pkgs]

# Heavy package detection (lazy check)
_missing_heavy = (
    [] if _installed_pkgs is None
    else [p for p in _HEAVY_PACKAGES if p.replace("-", "_") not in _installed_pkgs]
)

# Store results for non-blocking display
st.session_state["_startup_missing_core"] = _missing_core
st.session_state["_startup_missing_heavy"] = _missing_heavy
st.session_state["_startup_complete"] = False  # will be set to True after render

if AUTO_FIX_DEPS and _missing_core:
    from modules.dependency_manager import install_missing_packages

    st.info(f"🔧 Installing {len(_missing_core)} required dependencies. This may take a minute...")
    progress_bar = st.progress(0)
    status_text = st.empty()

    def progress_cb(current, total, msg):
        progress_bar.progress(int(current / total * 100))
        status_text.text(f"[{current}/{total}] {msg}")

    results = install_missing_packages(_missing_core, progress_cb)
    success_count = sum(1 for s, _ in results.values() if s)
    if success_count > 0:
        status_text.text(f"✅ {success_count}/{len(_missing_core)} packages installed")
        import importlib as _il
        _il.invalidate_caches()

# ─── Modules ──────────────────────────────────────────────────────────
from modules.config import CACHE_DIR, init_session_state, get_secret, find_background_image
from modules.keepalive import (
    get_health_check_html, inject_client_keepalive, start_server_keepalive
)
from modules.notion_client import (
    auto_find_duplicated_db, discover_database_id, fetch_notion_data,
    fingerprint_database, get_database_options
)
from modules.ui_components import (
    end_sidebar_card, hero_card, load_css, render_onboarding_tour,
    sidebar_card, sync_status_card, watermark
)

# ═══════════════════════════════════════════════════════════════════════
# 1. PAGE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Advanced Research Data Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════════
# 2. INIT SESSION STATE
# ═══════════════════════════════════════════════════════════════════════
init_session_state()

# ═══════════════════════════════════════════════════════════════════════
# 3. LOAD CSS
# ═══════════════════════════════════════════════════════════════════════
is_dark = st.session_state.get("theme", "light") == "dark"
accent_color = st.session_state.get("accent_color", "#1d4ed8")
load_css(is_dark=is_dark, accent_color=accent_color)

# ═══════════════════════════════════════════════════════════════════════
# 4. HERO & WATERMARK
# ═══════════════════════════════════════════════════════════════════════
hero_card(
    "📊 Advanced Research Data Analyzer & Visualizer",
    "Replace SPSS, Tableau & Power BI — CHRISHEM-powered analysis for Notion, CSV, Excel, SPSS & more.",
    badge_text="v2.0 — Research Suite"
)
watermark("CHRISHEM")

# ─── Startup time (non-blocking) ────────────────────────────────────
_startup_elapsed = time.time() - _startup_start
st.caption(f"⚡ App loaded in {_startup_elapsed:.1f}s")

# Non-blocking warning for missing heavy packages
if st.session_state.get("_startup_missing_heavy"):
    st.info(
        f"ℹ️ Advanced AI packages not installed ({', '.join(st.session_state['_startup_missing_heavy'])}). "
        "Some features (AutoML, forecasting) will use fallback. "
        "Install from Settings page for full capabilities.",
        icon="🧠"
    )

# ═══════════════════════════════════════════════════════════════════════
# 5. CREDENTIAL SETUP (if needed)
# ═══════════════════════════════════════════════════════════════════════
NOTION_TOKEN = get_secret("NOTION_TOKEN")
DATABASE_ID = get_secret("DATABASE_ID")

def show_credential_setup():
    """Render the credential setup wizard for Notion connection."""
    import requests
    from modules.ui_components import end_sidebar_card, sidebar_card

    st.markdown(
        """
        <div class="hero-card">
            <h1>🔑 Connect Your Notion Workspace</h1>
            <p>Enter your Notion Integration Token to connect this dashboard to your database.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container():
        st.info(
            "**Need a token?** Go to https://www.notion.so/my-integrations → "
            "Create a new integration → Copy the Internal Integration Secret."
        )

        col1, col2 = st.columns([3, 1])
        with col1:
            token_input = st.text_input(
                "Notion API Token",
                type="password",
                value=st.session_state.get("user_NOTION_TOKEN", ""),
                placeholder="ntn_xxxxxxxxxxxxxxxxxxxx",
                help="Paste your Notion Internal Integration Token here.",
            )
        with col2:
            st.caption("🔒 Encrypted in-session")
            st.caption("Not stored on server")

        db_input = st.text_input(
            "Database ID (optional — auto-discover if blank)",
            value=st.session_state.get("user_DATABASE_ID", ""),
            placeholder="Leave blank to auto-discover",
        )

        test_col, reset_col = st.columns([1, 1])
        with test_col:
            if st.button("✅ Test & Save Connection", type="primary"):
                if not token_input.strip():
                    st.error("Please provide a Notion API Token.")
                else:
                    with st.spinner("Testing connection to Notion API..."):
                        test_headers = {
                            "Authorization": f"Bearer {token_input.strip()}",
                            "Notion-Version": "2022-06-28",
                            "Content-Type": "application/json",
                        }
                        try:
                            test_resp = requests.post(
                                "https://api.notion.com/v1/search",
                                json={"query": "", "filter": {"property": "object", "value": "database"}, "page_size": 1},
                                headers=test_headers,
                                timeout=15,
                            )
                            if test_resp.status_code == 200:
                                st.session_state["user_NOTION_TOKEN"] = token_input.strip()
                                st.session_state["user_DATABASE_ID"] = db_input.strip()
                                st.session_state["creds_validated"] = True
                                st.session_state["creds_failed"] = False
                                st.success("✅ Connection successful! Dashboard loading...")
                                st.rerun()
                            elif test_resp.status_code == 401:
                                st.error("❌ Invalid token (401). Check your Notion Integration Token.")
                            elif test_resp.status_code == 403:
                                st.error("❌ Token lacks access (403). Make sure you've shared the database with your integration.")
                            else:
                                st.error(f"❌ API error {test_resp.status_code}: {test_resp.text[:200]}")
                        except requests.exceptions.Timeout:
                            st.error("❌ Connection timed out. Check your network / proxy settings.")
                        except Exception as e:
                            st.error(f"❌ Connection error: {str(e)}")

        with reset_col:
            if st.button("🔄 Reset Configuration"):
                for k in ("user_NOTION_TOKEN", "user_DATABASE_ID", "creds_validated", "creds_failed"):
                    st.session_state[k] = "" if "TOKEN" in k or "DATABASE" in k else False
                st.rerun()

        st.markdown("---")
        st.markdown(
            "<div style='text-align:center;color:#64748b;font-size:0.85rem;'>"
            "💡 Credentials are stored in your browser session only. "
            "Each user must supply their own token when they duplicate this workspace."
            "</div>",
            unsafe_allow_html=True,
        )
    st.stop()

# Check credentials — if missing, show setup
if (not NOTION_TOKEN) or st.session_state.get("creds_failed"):
    show_credential_setup()

# ───────────────────────────────────────────────────────────────────────
# 6. DATABASE ID RESOLUTION (CACHED)
# ───────────────────────────────────────────────────────────────────────
from modules.config import DEFAULT_CACHE_TTL, NOTION_API_CACHE_TTL, NOTION_DATA_CACHE_TTL

DATABASE_SOURCE = "configured"

# Cache database discovery results (rarely changes)
@st.cache_data(ttl=NOTION_API_CACHE_TTL, show_spinner=False)
def _cached_discover_db_id(token: str):
    return discover_database_id(token)

@st.cache_data(ttl=NOTION_API_CACHE_TTL, show_spinner=False)
def _cached_get_database_options(token: str):
    return get_database_options(token)

if not DATABASE_ID:
    with st.spinner("🔍 Auto-discovering databases..."):
        DATABASE_ID = _cached_discover_db_id(NOTION_TOKEN)
        DATABASE_SOURCE = "auto-discovered"
        if DATABASE_ID:
            st.session_state["user_DATABASE_ID"] = DATABASE_ID

if not DATABASE_ID:
    st.error("DATABASE_ID is missing and auto-discovery failed. Use the setup to provide one.")
    st.session_state["creds_failed"] = True
    show_credential_setup()

# ───────────────────────────────────────────────────────────────────────
# 7. SIDEBAR — Control Panel & Keep-Alive
# ───────────────────────────────────────────────────────────────────────
with st.sidebar:
    # ─── Connection Status ───────────────────────────────────────
    sidebar_card("Control Panel", "Live connection")

    refresh_options = {
        "Off": 0,
        "30 sec": 30,
        "60 sec": 60,
        "5 min": 300,
        "15 min": 900,
    }
    default_refresh_choice = st.session_state.get("refresh_choice", "30 sec")
    refresh_choice = st.selectbox(
        "Refresh cadence",
        list(refresh_options.keys()),
        index=list(refresh_options.keys()).index(default_refresh_choice)
        if default_refresh_choice in refresh_options else 1,
        key="refresh_choice",
    )
    refresh_seconds = refresh_options.get(refresh_choice, 30)
    st.caption(f"Current cadence: {refresh_choice}")

    # Database selector (cached)
    try:
        database_options = _cached_get_database_options(NOTION_TOKEN)
        if database_options:
            option_ids = [db["id"] for db in database_options]
            option_names = {db["id"]: f"{db['title']} ({db['id'][:8]}...)" for db in database_options}

            search_term = st.text_input("Search databases", placeholder="Type a name or ID...")
            filtered_options = [
                db for db in database_options
                if not search_term or search_term.lower() in db["title"].lower() or search_term.lower() in db["id"].lower()
            ]
            filtered_ids = [db["id"] for db in filtered_options]
            filtered_names = {db["id"]: f"{db['title']} ({db['id'][:8]}...)" for db in filtered_options}

            if filtered_ids:
                default_index = filtered_ids.index(DATABASE_ID) if DATABASE_ID in filtered_ids else 0
                selected_db_id = st.selectbox(
                    "Choose database",
                    options=filtered_ids,
                    index=default_index,
                    format_func=lambda db_id: filtered_names.get(db_id, db_id),
                )
                if selected_db_id != DATABASE_ID:
                    # Debounce: only trigger if user hasn't changed selection in last 2s
                    if st.session_state.get("_last_db_change", 0) + 2 < time.time():
                        DATABASE_ID = selected_db_id
                        DATABASE_SOURCE = "selected in sidebar"
                        st.session_state["_last_db_change"] = time.time()
                        st.cache_data.clear()
                        st.rerun()

            st.code(DATABASE_ID, language="text")
            st.caption(f"Source: {DATABASE_SOURCE}")
    except Exception as e:
        logger.exception("Failed to render the Notion database selector")
        st.warning(f"⚠️ Could not load the database list: {e}")

    end_sidebar_card()

    # ─── Keep-Alive ──────────────────────────────────────────────
    sidebar_card("⏰ Keep-Alive Settings", "Prevent the app from sleeping")
    keep_alive_enabled = st.toggle(
        "Enable client-side keep-alive",
        value=st.session_state.get("keep_alive_enabled", False),
        key="keep_alive_enabled",
    )
    if keep_alive_enabled:
        keep_alive_interval = st.selectbox(
            "Ping interval",
            options=["1 min", "5 min", "10 min", "15 min"],
            index=1,
            key="keep_alive_interval",
        )
        interval_map = {"1 min": 60, "5 min": 300, "10 min": 600, "15 min": 900}
        st.session_state["keep_alive_interval_sec"] = interval_map[keep_alive_interval]
        st.caption(f"⏱️ Will ping every {keep_alive_interval}")

        # Also start server-side keep-alive
        app_url = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:8501")
        start_server_keepalive(app_url, interval=interval_map[keep_alive_interval])

        st.info(
            "💡 For 24/7 uptime on free Render/Hosting plans, also set up a free "
            "external monitor like **UptimeRobot** or **cron-job.org**."
        )

    if st.button("🔄 Sync New Changes"):
        st.cache_data.clear()
        st.session_state["last_sync_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.rerun()
    end_sidebar_card()

# ───────────────────────────────────────────────────────────────────────
# 8. SYNC STATUS CARD
# ───────────────────────────────────────────────────────────────────────
if "last_sync_time" not in st.session_state:
    st.session_state["last_sync_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
if "next_auto_refresh_at" not in st.session_state:
    st.session_state["next_auto_refresh_at"] = time.time() + 30

sync_status_card(DATABASE_ID, DATABASE_SOURCE, st.session_state["last_sync_time"])

# ───────────────────────────────────────────────────────────────────────
# 9. AUTO-REFRESH LOGIC
# ───────────────────────────────────────────────────────────────────────
if refresh_seconds > 0:
    current_ts = time.time()
    if current_ts >= st.session_state.get("next_auto_refresh_at", current_ts + refresh_seconds):
        st.session_state["next_auto_refresh_at"] = current_ts + refresh_seconds
        st.session_state["last_sync_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.cache_data.clear()
        st.rerun()

# ───────────────────────────────────────────────────────────────────────
# 10. CLIENT-SIDE KEEP-ALIVE JS INJECTION
# ───────────────────────────────────────────────────────────────────────
keep_alive_interval_sec = st.session_state.get("keep_alive_interval_sec", 0)
if st.session_state.get("keep_alive_enabled") and keep_alive_interval_sec > 0:
    js = inject_client_keepalive(keep_alive_interval_sec)
    if js:
        st.markdown(js, unsafe_allow_html=True)

# ───────────────────────────────────────────────────────────────────────
# 11. ONBOARDING TOUR
# ───────────────────────────────────────────────────────────────────────
render_onboarding_tour()

# ───────────────────────────────────────────────────────────────────────
# 12. DATA FETCHING (CACHED — 5 min TTL)
# ───────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=NOTION_DATA_CACHE_TTL, show_spinner="🔄 Syncing with Notion...")
def get_notion_data(token, db_id):
    return fetch_notion_data(token, db_id)

df = get_notion_data(NOTION_TOKEN, DATABASE_ID)
st.session_state["last_sync_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Store in session state for page access
if df is not None and not df.empty:
    st.session_state["notion_df"] = df
    st.session_state["active_df"] = df
    st.session_state["data_source"] = "notion"

    # ─── Auto-trigger Executive Storyteller ────────────────────────
    if not st.session_state.get("executive_report_generated", False) and not df.empty:
        try:
            from modules.executive_storyteller import ExecutiveStoryteller
            storyteller = ExecutiveStoryteller()
            report = storyteller.generate_executive_report(df)
            if "error" not in report:
                st.session_state["executive_report"] = report
                st.session_state["executive_report_generated"] = True
            else:
                logger.warning("Executive report generation returned an error: %s", report["error"])
        except Exception:
            # Non-blocking; the report can still be generated on demand.
            logger.exception("Auto-generation of the executive report failed")

# ───────────────────────────────────────────────────────────────────────
# 13. DASHBOARD OVERVIEW
# ───────────────────────────────────────────────────────────────────────
if df.empty:
    st.warning("⚠️ No data parsed from Notion yet. Try uploading a file in **📁 File Analyzer** page, or check your Notion credentials.")
else:
    from modules.chart_builder import build_chart
    from modules.data_processor import get_column_summary, infer_column_types, profile_dataset
    from modules.export import render_export_buttons
    from modules.ui_components import insight_card, section_header
    from modules.viz_engine import auto_recommend_chart

    # Profile
    profile = profile_dataset(df)

    # KPI Row
    section_header("📊 Snapshot Overview")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric("Total Records", profile["rows"])
    with kpi2:
        st.metric("Variables", profile["columns"])
    with kpi3:
        numeric_cols = profile.get("numeric_columns", [])
        st.metric("Numeric Variables", len(numeric_cols))
    with kpi4:
        missing_pct = profile.get("missing_pct", 0)
        st.metric("Missing %", f"{missing_pct}%")

    # Auto-recommended charts
    section_header("🎯 CHRISHEM-Recommended Visualizations")
    recommendations = auto_recommend_chart(df)[:6]

    rec_cols = st.columns(3)
    for idx, rec in enumerate(recommendations[:3]):
        with rec_cols[idx]:
            chart_name = rec.get("chart", "").replace("_", " ").title()
            reason = rec.get("reason", "")
            st.markdown(f"**📈 {chart_name}** — {reason}")
            chart = build_chart(rec["chart"], df, **{k: v for k, v in rec.items() if k in ("x", "y", "color", "size", "z", "dimensions", "path", "values")})
            if chart:
                st.plotly_chart(chart, use_container_width=True)

    # Data preview
    section_header("📋 Data Preview")
    st.dataframe(df.head(100), use_container_width=True, hide_index=True)

    # Export
    section_header("📥 Export Data")
    render_export_buttons(df)

# ───────────────────────────────────────────────────────────────────────
# 14. NAVIGATION HINT (for multipage apps)
# ───────────────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    ### 📍 Explore More
    Use the **sidebar pages** above for:
    - **📁 File Analyzer** — Upload CSV/Excel/SPSS files
    - **🔬 Statistical Tests** — T-tests, ANOVA, Regression
    - **📈 Advanced Visuals** — 18+ chart types
    - **🤖 CHRISHEM Insights** — Automated analysis
    - **⚙️ Settings** — Theme, credentials, keep-alive
    """
)