"""
🏠 Home Dashboard — Sovereign Enterprise Platform Landing Hub (Premium)
Consolidated unified enterprise workspace featuring interactive session telemetry, real-time SQLite vault
management, LIVE system health metrics, a cryptographically chained audit ledger, interactive quick-access
navigation hubs, and secure user account management.

Changelog vs prior version:
- FIXED crash: `json` was used (json.dumps) but never imported.
- FIXED: telemetry metrics (uptime / DB latency / memory / disk) were hardcoded strings ("99.99%",
  "0.2ms Latency", "42.8%"). They are now measured live.
- FIXED: the `crypto_hash` column existed in system_telemetry_logs but nothing ever wrote to it, so the
  "secure audit ledger" had no actual integrity guarantee. It now uses a real SHA-256 hash chain
  (each row hashes its own content + the previous row's hash) with a one-click verifier.
- ADDED: bulk ZIP export of the saved-analyses vault, pagination, and per-record delete.
- ADDED: "Active Hubs" now reflects the real navigation registry instead of a hardcoded "15 Hubs".
"""

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
# Database
# ──────────────────────────────────────────────────────────────────────────

def get_db():
    """Open or initialize the sovereign database connection with secure logging tables."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
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
    conn.commit()
    return conn


def _row_hash(prev_hash: str, timestamp: str, module_name: str, severity: str, details: str) -> str:
    """Deterministic SHA-256 hash chaining this row's content to the previous row's hash."""
    payload = f"{prev_hash}|{timestamp}|{module_name}|{severity}|{details}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def log_telemetry(conn, module_name: str, severity: str, details: str):
    """Append a chained, tamper-evident telemetry record."""
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
    """Recompute the hash chain end-to-end and confirm no row has been altered or removed."""
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
# Live system health (real measurements, no hardcoded placeholders)
# ──────────────────────────────────────────────────────────────────────────

@st.cache_resource
def _process_start_time():
    """Persists for the life of the server process (shared across all sessions), giving a real uptime clock."""
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
    """Returns real, measured system health figures instead of static placeholder strings."""
    uptime = datetime.datetime.utcnow() - _process_start_time()

    t0 = datetime.datetime.now().timestamp()
    conn.execute("SELECT 1").fetchone()
    db_latency_ms = (datetime.datetime.now().timestamp() - t0) * 1000

    try:
        db_size_kb = __import__("os").path.getsize(DB_PATH) / 1024
    except OSError:
        db_size_kb = 0.0

    if PSUTIL_AVAILABLE:
        mem_percent = psutil.virtual_memory().percent
        cpu_percent = psutil.cpu_percent(interval=0.1)
    else:
        mem_percent = None
        cpu_percent = None

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
# Vault
# ──────────────────────────────────────────────────────────────────────────

def render_saved_analyses_vault(conn):
    section_header(
        "💾 Saved Analyses & Reports Vault",
        "Review, filter, export, and inspect all analytical reports and generated artifacts stored securely in the local database.",
    )

    cursor = conn.cursor()
    cursor.execute("SELECT id, title, timestamp, category, content FROM saved_analyses ORDER BY id DESC")
    saved_rows = cursor.fetchall()

    if not saved_rows:
        st.info("ℹ️ No saved analyses found yet. Execute analyses across analytical hubs and save them to populate the vault.")
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
                safe_name = f"{s_id}_{s_title.lower().replace(' ', '_')}.md"
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
        with st.expander(f"📄 [{s_cat}] {s_title} — {s_ts[:19]}", expanded=False):
            st.markdown(f"**Category:** `{s_cat}` | **Timestamp:** `{s_ts}`")
            st.markdown("---")
            st.markdown(s_content)
            col_dl1, col_dl2, col_dl3 = st.columns(3)
            with col_dl1:
                st.download_button(
                    label="⬇️ Markdown",
                    data=str(s_content),
                    file_name=f"analysis_{s_id}_{s_title.lower().replace(' ', '_')}.md",
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
# Live telemetry & tamper-evident audit ledger
# ──────────────────────────────────────────────────────────────────────────

def render_live_telemetry(conn):
    section_header(
        "📡 Real-Time System Telemetry & Operational Health",
        "Live enterprise monitoring of uptime, database response latency, memory utilization, and a cryptographically chained audit log.",
    )

    health = measure_system_health(conn)
    hub_count = len(visible_hubs()) if callable(visible_hubs) else "—"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Process Uptime", health["uptime"])
    c2.metric("Database Latency", f"{health['db_latency_ms']:.2f} ms", delta=f"{health['db_size_kb']:.1f} KB on disk")
    if health["mem_percent"] is not None:
        c3.metric("Memory Utilization", f"{health['mem_percent']:.1f}%", delta=f"CPU {health['cpu_percent']:.1f}%")
    else:
        c3.metric("Memory Utilization", "psutil not installed")
    c4.metric("Active Hubs", f"{hub_count} Hubs", delta=f"Disk free: {health['disk_free_pct']:.1f}%")

    st.markdown("#### 🔒 Cryptographically Chained Audit & Telemetry Ledger")
    col_v1, col_v2 = st.columns([1, 3])
    with col_v1:
        if st.button("🔍 Verify Chain Integrity", key="verify_home_chain"):
            result = verify_telemetry_chain(conn)
            if result["valid"]:
                st.success(f"✅ Chain verified — {result['records']} entries intact, no tampering detected.")
            else:
                st.error(f"🚨 CHAIN TAMPER DETECTED: {result['reason']}")

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
        st.info("ℹ️ No system telemetry entries recorded yet this session cycle.")


def main():
    setup_page("Home Dashboard", "🏠", initial_sidebar_state="expanded")

    hero_card(
        "🏠 Chrishem Sovereign Enterprise Platform — Home Command Center",
        "Welcome to the consolidated sovereign analytics workspace. Navigate via the sidebar hubs to access advanced analytical, machine learning, security, and research tools.",
        badge_text="SOVEREIGN ENTERPRISE PLATFORM v11.0",
    )

    conn = get_db()

    # ── Session Greeting Card ──
    identity = st.session_state.get("user_identity", {})
    name = identity.get("name", "Analyst")
    role = identity.get("role", "Data Analyst & Researcher")

    now_dt = datetime.datetime.now()
    hour = now_dt.hour
    greeting = (
        "Good Morning" if 5 <= hour < 12
        else "Good Afternoon" if 12 <= hour < 17
        else "Good Evening" if 17 <= hour < 21
        else "Good Night"
    )

    summary = dataset_summary()

    if "home_session_logged" not in st.session_state:
        log_telemetry(conn, "Home Dashboard", "INFO", f"Session started for {name} ({role})")
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
                    Active Session Role: {role} | System Timestamp: {now_dt.strftime('%A, %Y-%m-%d %H:%M:%S')}
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
        st.warning("📭 **No active dataset loaded.** Upload or ingest data in the **📁 Data Studio** hub to initiate your analytical pipeline.")

    st.markdown('<div class="chris-hr"></div>', unsafe_allow_html=True)

    section_header("🚀 Quick Access — Enterprise Workspace Hubs", "Select an operational hub below to begin. Each hub consolidates advanced multi-tool workflows into intuitive tabs.")
    hub_quick_access_cards()

    st.markdown('<div class="chris-hr"></div>', unsafe_allow_html=True)

    tab_vault, tab_telemetry, tab_account, tab_about = st.tabs(
        ["💾 Saved Analyses Vault", "📡 Live Telemetry", "👤 My Account & Plan", "ℹ️ About Platform"]
    )

    with tab_vault:
        render_saved_analyses_vault(conn)

    with tab_telemetry:
        render_live_telemetry(conn)

    with tab_account:
        section_header("👤 User Account, Subscription & Academic Verification", "Manage your enterprise subscription tier, trial status, and academic credentials.")
        from modules import subscription, verification
        acct_email = identity.get("email")
        if acct_email:
            status = subscription.get_status(acct_email)
            subscription.ensure_trial_started(acct_email)
            status = subscription.get_status(acct_email)

            c1, c2, c3 = st.columns(3)
            c1.metric("Active Plan Tier", status.get("plan", "Standard"))
            c2.metric("Trial Days Remaining", status.get("days_left") if status.get("days_left") is not None else "Unlimited")
            c3.metric("Account Email", acct_email)

            st.markdown('<div class="chris-hr"></div>', unsafe_allow_html=True)
            verification.render_student_application_form()
        else:
            st.info("ℹ️ Sign in with a registered email profile to view your active subscription tier and manage academic verification.")

    with tab_about:
        section_header("ℹ️ About the Chrishem Sovereign Intelligence Platform")
        st.markdown(
            """
            **CHRISHEM Sovereign Intelligence Platform v11.0** is an enterprise-grade analytical ecosystem consolidating dozens of specialized modules into **15 high-performance hubs**:

            | Operational Hub | Core Capabilities & Consolidations |
            |-----------------|-----------------------------------|
            | 🏠 **Home Dashboard** | Enterprise dashboard, saved vault, live telemetry, chained audit ledger |
            | 📁 **Data Studio** | Advanced data ingestion, quality audits, data transformation, anomaly simulator |
            | 📊 **Statistics Studio** | Hypothesis testing, causal inference, Bayesian modeling |
            | 🤖 **ML & Predictive Studio** | AutoML pipelines, feature engineering, predictive AI insights |
            | 📈 **Visualization Studio** | Interactive charting, executive dashboards, presentation tools |
            | 💬 **AI & NLP Studio** | Text mining, natural language querying, automated synthesis |
            | 📚 **Literature & Publishing Hub** | Meta-analysis synthesis, APA reference generators, grant writing |
            | 🔬 **Domain Analytics Hub** | Clinical studies, GIS geospatial mapping, research quality audits |
            | 🔗 **Integrations Hub** | Notion sync, Google Sheets connectors, Git repositories, API gateways |
            | 🛡️ **Admin & Security Center** | System settings, diagnostics, vault security, licensing management |
            | 🤝 **Collaboration & Portfolio** | Team pipelines, autonomous agents, academic portfolio workspace |
            | 🌍 **Global Mission Control** | Live global health surveillance, climate telemetry, impact scorecard |

            *Engineered and architected by Kula Chris (CHRISHEM).*
            """
        )

    render_standard_footer("HOME DASHBOARD")


if __name__ == "__main__":
    main()