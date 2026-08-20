"""
🏠 Home Dashboard — Sovereign Enterprise Platform Landing Hub (Premium)
Consolidated unified enterprise workspace featuring interactive session telemetry, real-time SQLite vault
management, LIVE system health metrics, a cryptographically chained audit ledger, interactive quick-access
navigation hubs, and secure user account management.
"""

import sys
from pathlib import Path

# Ensure the root project directory is in sys.path so 'modules' can always be resolved
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import datetime
import hashlib
import io
import json
import shutil
import sqlite3
import zipfile

import pandas as pd
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.session_manager import dataset_summary, get_active_dataframe
from modules.navigation import hub_quick_access_cards, visible_hubs
from modules.shared_ui import hero_card, section_header, metric_card, render_export_buttons

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

DB_PATH = "sovereign_apex_engine.db"
GENESIS_HASH = "0" * 64


# ──────────────────────────────────────────────────────────────────────────
# Database Layer & Schema Upgrades
# ──────────────────────────────────────────────────────────────────────────

@st.cache_resource
def get_db_connection():
    """Singleton-managed thread-safe SQLite connection for the enterprise engine."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn


def init_db(conn):
    """Ensure core sovereign tables—including subscriptions and telemetry chains—exist with proper schema definitions."""
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
            crypto_hash TEXT,
            prev_hash TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            email TEXT PRIMARY KEY,
            plan TEXT,
            trial_started TEXT,
            renews_at TEXT,
            status TEXT
        )
    """)
    
    # Safe runtime schema migrations for pre-existing databases
    try:
        cursor.execute("ALTER TABLE system_telemetry_logs ADD COLUMN prev_hash TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        cursor.execute("ALTER TABLE subscriptions ADD COLUMN renews_at TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()


def _row_hash(prev_hash: str, timestamp: str, module_name: str, severity: str, details: str) -> str:
    """Deterministic SHA-256 hash chaining this row's content to the previous row's hash."""
    payload = f"{prev_hash}|{timestamp}|{module_name}|{severity}|{details}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def log_telemetry(conn, module_name: str, severity: str, details: str):
    """Append a chained, tamper-evident telemetry record safely."""
    cursor = conn.cursor()
    cursor.execute("SELECT crypto_hash FROM system_telemetry_logs ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    prev_hash = row[0] if row and row[0] else GENESIS_HASH
    ts = datetime.datetime.utcnow().isoformat()
    new_hash = _row_hash(prev_hash, ts, module_name, severity, details)
    cursor.execute(
        "INSERT INTO system_telemetry_logs (timestamp, module_name, severity, details, crypto_hash, prev_hash) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (ts, module_name, severity, details, new_hash, prev_hash),
    )
    conn.commit()


def verify_telemetry_chain(conn):
    """Recompute the hash chain end-to-end and confirm zero records have been altered or removed."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, timestamp, module_name, severity, details, crypto_hash, prev_hash "
        "FROM system_telemetry_logs ORDER BY id ASC"
    )
    rows = cursor.fetchall()
    expected_prev = GENESIS_HASH
    for rid, ts, mod, sev, details, stored_hash, stored_prev in rows:
        if stored_prev != expected_prev:
            return {"valid": False, "reason": f"Row #{rid} broke the chain (prev_hash mismatch).", "records": len(rows)}
        recomputed = _row_hash(stored_prev, ts, mod, sev, details)
        if recomputed != stored_hash:
            return {"valid": False, "reason": f"Row #{rid} content does not match its stored hash — tampering suspected.", "records": len(rows)}
        expected_prev = stored_hash
    return {"valid": True, "records": len(rows)}


# ──────────────────────────────────────────────────────────────────────────
# Live System Health Diagnostics
# ──────────────────────────────────────────────────────────────────────────

@st.cache_resource
def _process_start_time():
    """Persists for the process lifetime to maintain an accurate uptime ticker."""
    return datetime.datetime.utcnow()


def _format_duration(delta: datetime.timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def measure_system_health(conn):
    """Measures actual application health metrics on-demand."""
    uptime = datetime.datetime.utcnow() - _process_start_time()

    t0 = datetime.datetime.now().timestamp()
    conn.execute("SELECT 1").fetchone()
    db_latency_ms = (datetime.datetime.now().timestamp() - t0) * 1000

    try:
        db_size_kb = __import__("os").path.getsize(DB_PATH) / 1024
    except OSError:
        db_size_kb = 0.0

    mem_percent = psutil.virtual_memory().percent if PSUTIL_AVAILABLE else None
    cpu_percent = psutil.cpu_percent(interval=0.0) if PSUTIL_AVAILABLE else None

    disk = shutil.disk_usage(".")
    disk_free_pct = 100 * disk.free / disk.total

    return {
        "uptime": _format_duration(uptime),
        "db_latency_ms": db_latency_ms,
        "db_size_kb": db_size_kb,
        "mem_percent": mem_percent,
        "cpu_percent": cpu_percent,
        "disk_free_pct": disk_free_pct,
    }


# ──────────────────────────────────────────────────────────────────────────
# Vault Rendering & Management Module
# ──────────────────────────────────────────────────────────────────────────

def render_saved_analyses_vault(conn):
    section_header(
        "💾 Saved Analyses & Reports Vault",
        "Review, filter, export, and inspect analytical reports and execution outputs securely stored in the database.",
    )

    cursor = conn.cursor()
    cursor.execute("SELECT id, title, timestamp, category, content FROM saved_analyses ORDER BY id DESC")
    saved_rows = cursor.fetchall()

    if not saved_rows:
        st.info("ℹ️ No saved analyses found yet. Execute analyses across analytical hubs and save them to populate your vault.")
        return

    df_vault = pd.DataFrame(saved_rows, columns=["ID", "Title", "Timestamp", "Category", "Content"])

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        cat_filter = st.selectbox(
            "Filter by Category",
            ["All Categories"] + sorted(df_vault["Category"].dropna().unique().tolist()),
            key="vault_cat_filter_upg",
        )
    with col_f2:
        search_query = st.text_input("Search Vault Reports", placeholder="Filter by title or keyword...", key="vault_search_upg")

    filtered_rows = saved_rows
    if cat_filter != "All Categories":
        filtered_rows = [r for r in filtered_rows if r[3] == cat_filter]
    if search_query:
        q = search_query.lower()
        filtered_rows = [r for r in filtered_rows if q in r[1].lower() or q in r[4].lower()]

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Stored Artifacts", len(saved_rows))
    c2.metric("Filtered View Count", len(filtered_rows))
    c3.metric("Total Vault Word Count", f"{sum(len(str(r[4]).split()) for r in filtered_rows):,}")

    if filtered_rows:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for s_id, s_title, s_ts, s_cat, s_content in filtered_rows:
                safe_name = f"{s_id}_{s_title.lower().replace(' ', '_').replace('/', '_')}.md"
                zf.writestr(safe_name, str(s_content))
            manifest = json.dumps(
                [{"id": r[0], "title": r[1], "timestamp": r[2], "category": r[3]} for r in filtered_rows],
                indent=2,
            )
            zf.writestr("manifest.json", manifest)
        st.download_button(
            "⬇️ Bulk Export Filtered Reports (.zip)",
            data=zip_buffer.getvalue(),
            file_name=f"vault_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip",
            key="vault_bulk_zip",
        )

    st.markdown("---")

    page_size = 10
    total_pages = max(1, (len(filtered_rows) + page_size - 1) // page_size)
    page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1, key="vault_page")
    start = (page - 1) * page_size
    page_rows = filtered_rows[start:start + page_size]
    st.caption(f"Showing records {start + 1}–{min(start + page_size, len(filtered_rows))} of {len(filtered_rows)} (page {page}/{total_pages})")

    for s_id, s_title, s_ts, s_cat, s_content in page_rows:
        display_ts = s_ts[:19] if len(s_ts) >= 19 else s_ts
        with st.expander(f"📄 [{s_cat}] {s_title} — {display_ts}", expanded=False):
            st.markdown(f"**Category:** `{s_cat}` | **Timestamp:** `{s_ts}`")
            st.markdown("---")
            st.markdown(s_content)
            col_dl1, col_dl2, col_dl3 = st.columns(3)
            with col_dl1:
                st.download_button(
                    label="⬇️ Markdown",
                    data=str(s_content),
                    file_name=f"analysis_{s_id}.md",
                    mime="text/markdown",
                    key=f"dl_md_{s_id}",
                )
            with col_dl2:
                st.download_button(
                    label="⬇️ JSON",
                    data=json.dumps({"id": s_id, "title": s_title, "timestamp": s_ts, "category": s_cat, "content": s_content}, indent=2),
                    file_name=f"analysis_{s_id}.json",
                    mime="application/json",
                    key=f"dl_json_{s_id}",
                )
            with col_dl3:
                if st.button("🗑️ Delete", key=f"del_{s_id}"):
                    conn.execute("DELETE FROM saved_analyses WHERE id = ?", (s_id,))
                    conn.commit()
                    log_telemetry(conn, "Home Dashboard", "INFO", f"Deleted saved analysis #{s_id} ({s_title})")
                    st.success(f"Deleted record #{s_id}.")
                    st.rerun()


# ──────────────────────────────────────────────────────────────────────────
# Live Telemetry & Audit Ledger Module
# ──────────────────────────────────────────────────────────────────────────

def render_live_telemetry(conn):
    section_header(
        "📡 Real-Time System Telemetry & Operational Health",
        "Live tracking of system resources, database response times, and the cryptographically secure audit trail.",
    )

    health = measure_system_health(conn)
    hub_count = len(visible_hubs()) if callable(visible_hubs) else "—"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Process Uptime", health["uptime"])
    c2.metric("Database Latency", f"{health['db_latency_ms']:.2f} ms", delta=f"{health['db_size_kb']:.1f} KB on disk")
    if health["mem_percent"] is not None:
        c3.metric("Memory Utilization", f"{health['mem_percent']:.1f}%", delta=f"CPU {health['cpu_percent']:.1f}%")
    else:
        c3.metric("Memory Utilization", "psutil inactive")
    c4.metric("Active Hubs", f"{hub_count} Hubs", delta=f"Disk free: {health['disk_free_pct']:.1f}%")

    st.markdown("#### 🔒 Cryptographically Chained Audit & Telemetry Ledger")
    col_v1, _ = st.columns([1, 3])
    with col_v1:
        if st.button("🔍 Verify Chain Integrity", key="verify_home_chain"):
            result = verify_telemetry_chain(conn)
            if result["valid"]:
                st.success(f"✅ Chain verified — {result['records']} entries intact, zero modifications found.")
            else:
                st.error(f"🚨 TAMPER DETECTED: {result['reason']}")

    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, timestamp, module_name, severity, details, crypto_hash "
        "FROM system_telemetry_logs ORDER BY id DESC LIMIT 20"
    )
    logs_data = cursor.fetchall()

    if logs_data:
        logs_df = pd.DataFrame(logs_data, columns=["ID", "Timestamp", "Module", "Severity", "Details", "Crypto Hash"])
        logs_df["Crypto Hash"] = logs_df["Crypto Hash"].str[:16] + "…"
        st.dataframe(logs_df, use_container_width=True, hide_index=True)
        render_export_buttons(logs_df, base_name="system_telemetry_logs")
    else:
        st.info("ℹ️ No system telemetry logs recorded yet for this session cycle.")


# ──────────────────────────────────────────────────────────────────────────
# Main Application Entrypoint
# ──────────────────────────────────────────────────────────────────────────

def render_automated_intelligence_report():
    section_header(
        "🤖 Automated Intelligence — Scheduled, Unattended Runs",
        "Real output from the scheduled GitHub Actions workflow (.github/workflows/automated_intelligence_run.yml), "
        "not something triggered by clicking a button here. It pulls fresh World Bank data and runs the chaos "
        "detector on a watchlist automatically on a schedule and commits the results back to the repo.",
    )
    from pathlib import Path
    repo_root = Path(__file__).resolve().parent.parent
    report_path = repo_root / "reports" / "latest_report.md"
    alert_path = repo_root / "reports" / "latest_alert_summary.txt"

    if not report_path.exists():
        st.info(
            "No automated run has completed yet. Once `automated_intelligence_run.yml` runs on its schedule "
            "(or you trigger it manually from the repo's Actions tab), the latest results will appear here "
            "automatically — nothing to configure in the app itself."
        )
        return

    if alert_path.exists():
        alert_text = alert_path.read_text().strip()
        if alert_text and alert_text != "No changes since last run.":
            st.warning(f"🚨 **Changes detected in the latest run:**\n\n{alert_text}")
        else:
            st.success("✅ No verdict changes since the previous scheduled run.")

    with st.expander("📄 Full latest report", expanded=False):
        st.markdown(report_path.read_text())


def main():
    setup_page("Home Dashboard", "🏠", initial_sidebar_state="expanded")

    from modules.user_preferences import render_readability_fix, render_accent_color_css
    render_readability_fix()
    render_accent_color_css()

    hero_card(
        "🏠 Chrishem Sovereign Enterprise Platform — Home Command Center",
        "Welcome to your consolidated sovereign workspace. Use the sidebar hubs or quick access cards to navigate advanced analytical pipelines.",
        badge_text="SOVEREIGN ENTERPRISE PLATFORM v11.0",
    )

    conn = get_db_connection()
    init_db(conn)

    identity = st.session_state.get("user_identity", {})
    name = identity.get("name", "Analyst")
    role = identity.get("role", "Data Analyst & Researcher")

    from modules.user_preferences import get_user_timezone, compute_greeting, render_accent_color_css
    import zoneinfo
    render_accent_color_css()

    user_tz_name = get_user_timezone()
    now_dt = datetime.datetime.now(zoneinfo.ZoneInfo(user_tz_name))
    greeting = compute_greeting(now_dt)

    summary = dataset_summary()

    if "home_session_logged" not in st.session_state:
        log_telemetry(conn, "Home Dashboard", "INFO", f"Session initialized for {name} ({role})")
        st.session_state["home_session_logged"] = True

    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center;
             background: linear-gradient(135deg, rgba(56, 189, 248, 0.12), rgba(129, 140, 248, 0.12));
             border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 14px;
             padding: 1.2rem 1.5rem; margin-bottom: 1.5rem;">
            <div>
                <div style="font-size:1.25rem; font-weight:800; color:#F8FAFC;">{greeting}, {name}! 👋</div>
                <div style="font-size:0.9rem; color:#38BDF8; font-weight:600; margin-top:0.2rem;">
                    Active Session Role: {role} | Your Local Time: {now_dt.strftime('%A, %Y-%m-%d %H:%M:%S %Z')}
                </div>
            </div>
            <div>
                <span style="background:rgba(16,185,129,0.2); color:#34d399; padding:0.4rem 0.8rem; border-radius:20px; font-weight:700; font-size:0.85rem; border:1px solid rgba(16,185,129,0.4);">● SYSTEM OPERATIONAL</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if summary:
        st.success(
            f"📊 **Active Ingestion Dataset:** `{summary.get('source', 'Dataset')}` — {summary.get('rows', 0):,} rows × {summary.get('cols', 0)} columns "
            f"| Numeric: `{summary.get('numeric', 0)}` | Categorical: `{summary.get('categorical', 0)}`"
        )
    else:
        st.warning("📭 **No active dataset loaded.** Upload or ingest data via the **📁 Data Studio** hub to jumpstart your analytics.")

    st.markdown('<div class="chris-hr"></div>', unsafe_allow_html=True)

    section_header("🚀 Quick Access — Enterprise Workspace Hubs", "Select an operational hub below to load modular capabilities.")
    hub_quick_access_cards()

    st.markdown('<div class="chris-hr"></div>', unsafe_allow_html=True)

    tab_vault, tab_telemetry, tab_automation, tab_account, tab_about = st.tabs(
        ["💾 Saved Analyses Vault", "📡 Live Telemetry", "🤖 Automated Intelligence", "👤 My Account & Plan", "ℹ️ About Platform"]
    )

    with tab_vault:
        render_saved_analyses_vault(conn)

    with tab_telemetry:
        render_live_telemetry(conn)

    with tab_automation:
        render_automated_intelligence_report()

    with tab_account:
        section_header("👤 Settings & Control Center", "Subscription, timezone, accent color, dependencies, focus engine, and creator profile — all managed in one place.")
        from modules import subscription, verification
        acct_email = identity.get("email", "analyst@sovereign.enterprise")
        if acct_email:
            subscription.ensure_trial_started(acct_email)
            status = subscription.get_status(acct_email)

            c1, c2, c3 = st.columns(3)
            c1.metric("Active Plan Tier", status.get("plan", "Standard"))
            c2.metric("Trial Days Remaining", status.get("days_left") if status.get("days_left") is not None else "Unlimited")
            c3.metric("Account Email", acct_email)

            settings_tabs = st.tabs([
                "🎓 Verification", "🌐 Timezone & Color", "📦 Dependencies", "🧠 Focus Engine", "👑 Creator Profile",
            ])

            with settings_tabs[0]:
                verification.render_student_application_form()

            with settings_tabs[1]:
                from modules.user_preferences import render_timezone_and_accent_settings
                render_timezone_and_accent_settings()

            with settings_tabs[2]:
                from modules.environment_manager import render_environment_manager
                render_environment_manager()

            with settings_tabs[3]:
                from modules.audio_engine import render_generative_synthesizer, render_ambient_library_picker
                st.caption(
                    "The generative synthesizer runs live in your browser — no files, no dead links. "
                    "Streamlit recreates this widget on page navigation, so playback resumes automatically "
                    "from where it left off (via your browser's local storage) rather than continuing "
                    "gaplessly — that's a real platform constraint, not a bug."
                )
                render_generative_synthesizer()
                st.markdown("---")
                st.markdown("#### 🌿 Ambient Library")
                render_ambient_library_picker()

            with settings_tabs[4]:
                from modules.app_settings import get_creator_photo_b64, set_creator_photo_b64
                st.caption(
                    "Replaces the old hardcoded local file path (which only worked on one person's own "
                    "Windows machine) with a real upload stored in the shared database."
                )
                current_photo = get_creator_photo_b64()
                if current_photo:
                    st.image(current_photo, width=150)
                uploaded_photo = st.file_uploader("Upload creator profile photo (JPG/PNG)", type=["jpg", "jpeg", "png"], key="creator_photo_upload")
                if uploaded_photo:
                    import base64 as _b64
                    encoded = _b64.b64encode(uploaded_photo.read()).decode("utf-8")
                    data_uri = f"data:{uploaded_photo.type};base64,{encoded}"
                    set_creator_photo_b64(data_uri)
                    st.success("Photo saved.")
                    st.rerun()
        else:
            st.info("ℹ️ Sign in with a registered user profile to check your subscription status.")

    with tab_about:
        section_header("ℹ️ About the Chrishem Sovereign Intelligence Platform")
        st.markdown(
            """
            **CHRISHEM Sovereign Intelligence Platform v11.0** is an enterprise architecture consolidating core workflows into **15 high-performance hubs**:

            | Operational Hub | Core Capabilities |
            |-----------------|-----------------------------------|
            | 🏠 **Home Dashboard** | Enterprise dashboard, vault, telemetry, automated intelligence |
            | 📁 **Data Studio** | Data ingestion, quality assurance, anomaly testing |
            | 📊 **Statistics Studio** | Hypothesis testing, causal modeling, inference |
            | 🤖 **ML & Predictive Studio**| AutoML pipelines, feature analysis, real-world chaos detection |
            | 📈 **Visualization Studio** | Interactive mapping, presentation dashboards |
            | 💬 **AI & NLP Studio** | Natural language analytics, synthesis engines |
            | 📚 **Literature Hub** | Meta-analysis tools, reference generation |
            | 🔬 **Domain Analytics** | Clinical tracking, geospatial processing |
            | 🔗 **Integrations Hub** | API routing, sync modules, real World Bank data |
            | 🛡️ **Admin & Security** | Access governance, diagnostics, audit forensics, nexus workspace |
            | 🤝 **Collaboration** | Workspace sharing, team pipelines |
            | 🕵️ **Forensics Intelligence** | Investigative and forensic analysis tools |
            | 🔄 **Universal Converter** | Format and encoding conversion utilities |
            | 🛡️ **Threat & Scanner Suite** | PII/secret scanning, threat detection |
            | 🌍 **Global Mission Control** | Live global health & weather telemetry |

            *Engineered by Kula Chris (CHRISHEM).*
            """
        )

    render_standard_footer("HOME DASHBOARD")


if __name__ == "__main__":
    main()