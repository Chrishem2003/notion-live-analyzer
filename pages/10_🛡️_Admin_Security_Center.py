"""
🛡️ Admin & Security Center — Sovereign Enterprise Administration & Security Command Hub (Premium v2.0)
The hardened administrative control plane consolidating real-time system diagnostics, enterprise
RBAC user management, Stripe/license billing workflows, academic student verification queues, a
genuinely encrypted credential vault with a real accumulating audit trail, compliance forensic
engines, and the Nexus 2.0 workspace suite.
"""

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from modules.page_bootstrap import setup_page, render_standard_footer
from modules.shared_ui import hero_card, section_header, metric_card, render_export_buttons
from modules.admin_guard import require_admin

import datetime
import hashlib
import json
import platform
import shutil
import sqlite3
import threading

import numpy as np
import pandas as pd
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.shared_ui import hero_card, section_header, metric_card, render_export_buttons
from modules.admin_guard import require_admin
from modules.audit_compliance_engine import (
    statcheck_consistency,
    p_curve_analysis,
    grim_test,
    degrim_test,
    p_hacking_detector,
    harking_flag,
    power_audit,
    outlier_truncation_audit,
    burstiness_detector,
    perplexity_profiler,
    citation_fabrication_audit,
    paraphrase_spin_detector,
    stylometric_fingerprint,
    self_citation_inflation,
    paper_mill_classifier,
    pii_redactor,
    hipaa_phi_audit,
    gdpr_purge_validator,
    differential_privacy_audit,
    sha256_block,
    merkle_root,
    raw_data_hash,
    data_lineage_provenance,
    grant_compliance_matrix,
    fair_data_rating,
    peer_review_redflags,
    license_verification,
    reproducibility_validator,
    system_security_health,
)
from modules.nexus_vault_engine import (
    NexusVault,
    NexusCalendar,
    NexusMeet,
    NexusDocs,
    NexusSheets,
    NexusContacts,
    NexusTasks,
)

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

GENESIS_HASH = "0" * 64


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
            crypto_hash TEXT,
            prev_hash TEXT
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


def log_admin_action(conn, module_name: str, severity: str, details: str):
    """Same SHA-256 hash-chain pattern as the Home Dashboard ledger — shared table, shared integrity guarantee."""
    cursor = conn.cursor()
    cursor.execute("SELECT crypto_hash FROM system_telemetry_logs ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    prev_hash = row[0] if row and row[0] else GENESIS_HASH
    ts = datetime.datetime.utcnow().isoformat()
    payload = f"{prev_hash}|{ts}|{module_name}|{severity}|{details}".encode("utf-8")
    new_hash = hashlib.sha256(payload).hexdigest()
    cursor.execute(
        "INSERT INTO system_telemetry_logs (timestamp, module_name, severity, details, crypto_hash, prev_hash) VALUES (?,?,?,?,?,?)",
        (ts, module_name, severity, details, new_hash, prev_hash),
    )
    conn.commit()


@st.cache_resource
def _process_start_time():
    return datetime.datetime.utcnow()


@st.cache_resource
def _get_vault_key():
    """Generated once per server process. In production, replace with a key sourced from a
    secrets manager or environment variable so encrypted values survive restarts/scale-out."""
    return Fernet.generate_key()


def encrypt_secret(plaintext: str) -> str:
    if not CRYPTO_AVAILABLE or not plaintext:
        return plaintext
    f = Fernet(_get_vault_key())
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    if not CRYPTO_AVAILABLE or not ciphertext:
        return ciphertext
    try:
        f = Fernet(_get_vault_key())
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except Exception:
        return "[decryption failed]"


def render_system_diagnostics(conn):
    section_header("🔍 System Diagnostics & Real-Time Runtime Telemetry", "Live server runtime health, memory footprint, active thread count, and the cryptographically chained system audit log.")

    uptime = datetime.datetime.utcnow() - _process_start_time()
    t0 = datetime.datetime.now().timestamp()
    conn.execute("SELECT 1").fetchone()
    db_latency_ms = (datetime.datetime.now().timestamp() - t0) * 1000
    mem_percent = psutil.virtual_memory().percent if PSUTIL_AVAILABLE else None
    thread_count = threading.active_count()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Process Uptime", f"{int(uptime.total_seconds() // 3600)}h {int((uptime.total_seconds() % 3600) // 60)}m")
    c2.metric("Database Health", "Connected", delta=f"{db_latency_ms:.2f}ms Latency")
    c3.metric("Memory Utilization", f"{mem_percent:.1f}%" if mem_percent is not None else "psutil not installed")
    c4.metric("Active Threads", f"{thread_count}", delta="Live count")

    st.markdown("#### Server Runtime Environment Specifications")
    disk = shutil.disk_usage(".")
    env_data = pd.DataFrame({
        "System Property": ["Python Core Version", "Host Operating System", "System Platform", "Disk Free", "UTC Timestamp"],
        "Value": [
            platform.python_version(), platform.system(), platform.platform(),
            f"{disk.free / (1024**3):.1f} GB ({100*disk.free/disk.total:.1f}%)",
            datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        ],
    })
    st.dataframe(env_data, width='stretch', hide_index=True)
    render_export_buttons(env_data, base_name="system_runtime_environment")

    st.markdown("#### Cryptographic Telemetry Log Stream")
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, module_name, severity, details, crypto_hash FROM system_telemetry_logs ORDER BY id DESC LIMIT 20")
    logs = cursor.fetchall()
    if logs:
        logs_df = pd.DataFrame(logs, columns=["ID", "Timestamp", "Module", "Severity", "Details", "SHA-256 Hash"])
        st.dataframe(logs_df, width='stretch', hide_index=True)
        render_export_buttons(logs_df, base_name="system_telemetry_audit_logs")
    else:
        st.info("ℹ️ No system telemetry entries recorded during the active operational window.")

    col_gc1, col_gc2 = st.columns(2)
    with col_gc1:
        if st.button("🧹 Force Garbage Collection & Purge Buffers", type="primary", key="gc_btn_upg"):
            import gc
            collected = gc.collect()
            st.success(f"✅ Garbage collection successfully executed (`{collected}` unreferenced objects purged from heap memory).")
    with col_gc2:
        if st.button("🔄 Flush In-Memory Stream Caches", key="flush_cache_btn"):
            st.cache_data.clear()
            st.success("✅ Application cache layers successfully flushed.")


def render_user_management(conn):
    section_header("👤 RBAC User Management & Administrative Privilege Control", "Enforce strict security boundaries by managing user accounts, permission tiers, and role assignments from the persistent auth store.")

    from modules import auth_store

    auth_conn = auth_store.get_conn()
    users = auth_conn.execute(
        "SELECT email, name, role, created_at, last_login FROM auth_users ORDER BY created_at DESC"
    ).fetchall()
    auth_conn.close()

    if not users:
        st.info("ℹ️ No registered accounts detected in authentication database.")
        return

    users_df = pd.DataFrame(users, columns=["Email Address", "Full Name", "Assigned Role", "Registration Date", "Last Active"])
    st.dataframe(users_df, width='stretch', hide_index=True)
    render_export_buttons(users_df, base_name="rbac_user_directory")

    st.markdown("#### Privilege Elevation & Role Modification Console")
    st.caption("🛡️ Administrative Security Boundary: Only authorized super-administrators can modify security access roles.")

    emails = [u[0] for u in users]
    admin_count = sum(1 for u in users if u[2] == "admin")

    col1, col2 = st.columns(2)
    with col1:
        sel_email = st.selectbox("Target Account Email", emails, key="rbac_target_email_upg")
    with col2:
        sel_role = st.selectbox("Assign New Security Role", auth_store.ROLES, key="rbac_new_role_upg")

    current_admin = st.session_state.get("user_identity", {}).get("email")
    target_current_role = next((u[2] for u in users if u[0] == sel_email), None)

    if st.button("🔐 Apply Role Permission Update", type="primary", key="rbac_apply_upg"):
        if sel_role == "user" and sel_email == current_admin:
            st.error("🚨 Security Violation: You cannot demote your own active super-admin session. Authenticate via a secondary admin account.")
        elif target_current_role == "admin" and sel_role != "admin" and admin_count <= 1:
            st.error(f"🚨 Lockout Prevention: `{sel_email}` is the last remaining admin account. Promote another account to admin before demoting this one.")
        else:
            auth_store.set_role(sel_email, sel_role)
            log_admin_action(conn, "Admin Center", "ROLE_CHANGE", f"{sel_email}: role → {sel_role} (by {current_admin or 'unknown'})")
            st.success(f"✅ Privilege level for `{sel_email}` successfully updated to `{sel_role}`.")
            st.rerun()


def render_billing(conn):
    section_header("💳 Enterprise Billing, Licensing & Subscription Management", "Monitor real-time subscription tiers, trial statuses, and license allocations from the primary database repository.")

    from modules import subscription, billing_stripe

    conn2 = subscription.get_conn()
    rows = conn2.execute("SELECT email, plan, trial_started FROM subscriptions").fetchall()
    conn2.close()

    plan_counts = {}
    for _, plan, _ in rows:
        plan_counts[plan] = plan_counts.get(plan, 0) + 1

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Accounts", len(rows))
    c2.metric("Active Trials", plan_counts.get("trial", 0))
    c3.metric("Paid Active Tiers", plan_counts.get("active", 0))
    c4.metric("Student Free Access", plan_counts.get("student_free", 0))

    if not billing_stripe.is_configured():
        st.warning(
            "⚠️ Stripe API credentials not fully detected. Configure STRIPE_SECRET_KEY, STRIPE_PRICE_ID, and "
            "STRIPE_WEBHOOK_SECRET environment variables to enable automated payment gateway settlement."
        )

    st.markdown("#### Registered Subscription Directory")
    if rows:
        bdf = pd.DataFrame(rows, columns=["Subscriber Email", "Subscription Plan", "Trial Commencement"])
        st.dataframe(bdf, width='stretch', hide_index=True)
        render_export_buttons(bdf, base_name="enterprise_subscription_directory")
    else:
        st.info("ℹ️ No subscription records found.")

    st.markdown("#### Manual Plan Override Console")
    st.caption("Execute administrative account comps, refunds, or manual tier adjustments. All overrides are written to the audit ledger.")

    col1, col2 = st.columns(2)
    with col1:
        target_email = st.text_input("Subscriber Email Address", key="billing_target_email_upg")
    with col2:
        new_plan = st.selectbox("Target Subscription Tier", ["trial", "active", "expired", "student_free"], key="billing_new_plan_upg")

    if st.button("💾 Commit Plan Override", type="primary", key="billing_apply_upg"):
        if target_email.strip():
            actor = st.session_state.get("user_identity", {}).get("email", "unknown")
            conn3 = subscription.get_conn()
            conn3.execute(
                "INSERT INTO subscriptions (email, trial_started, plan) VALUES (?,?,?) "
                "ON CONFLICT(email) DO UPDATE SET plan=excluded.plan",
                (target_email.strip().lower(), datetime.datetime.utcnow().isoformat(), new_plan),
            )
            conn3.commit()
            conn3.close()
            log_admin_action(conn, "Admin Center", "BILLING_OVERRIDE", f"{target_email.strip().lower()}: plan → {new_plan} (by {actor})")
            st.success(f"✅ Subscription tier for `{target_email}` successfully overridden to `{new_plan}`.")
            st.rerun()
        else:
            st.warning("⚠️ Please provide a valid subscriber email address.")


def render_security_vault(conn):
    section_header("🔒 Encrypted Credential & API Token Vault", "Genuinely encrypted (Fernet/AES) local storage for third-party service tokens, with a real, persistent, hash-chained access audit trail.")

    if not CRYPTO_AVAILABLE:
        st.error("⚠️ `cryptography` package not installed — tokens cannot be encrypted in this environment. Install with `pip install cryptography`.")

    st.markdown("#### Secure Credential Storage Interface")
    col1, col2 = st.columns(2)
    with col1:
        token = st.text_input("Notion / External Integration Token", type="password", key="vault_token_upg")
    with col2:
        db_id = st.text_input("Target Database / Resource ID", key="vault_db_upg")

    actor = st.session_state.get("user_identity", {}).get("name", "System Administrator")

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        if st.button("🔒 Encrypt & Save to Session Vault", type="primary", key="save_vault_upg"):
            st.session_state["user_NOTION_TOKEN_enc"] = encrypt_secret(token)
            st.session_state["user_DATABASE_ID_enc"] = encrypt_secret(db_id)
            log_admin_action(conn, "Security Vault", "VAULT_WRITE", f"Credential saved by {actor}" + (" (encrypted)" if CRYPTO_AVAILABLE else " (PLAINTEXT — cryptography package missing)"))
            st.success("✅ Credentials " + ("encrypted and " if CRYPTO_AVAILABLE else "") + "bound to current session context.")
    with col_s2:
        if st.button("👁️ Reveal Stored Token", key="reveal_vault_upg"):
            stored = st.session_state.get("user_NOTION_TOKEN_enc", "")
            if stored:
                st.code(decrypt_secret(stored))
                log_admin_action(conn, "Security Vault", "VAULT_READ", f"Credential decrypted/viewed by {actor}")
            else:
                st.info("No credential currently stored.")
    with col_s3:
        if st.button("🗑️ Purge Vault Secrets", key="clear_vault_upg"):
            st.session_state["user_NOTION_TOKEN_enc"] = ""
            st.session_state["user_DATABASE_ID_enc"] = ""
            log_admin_action(conn, "Security Vault", "VAULT_PURGE", f"Vault purged by {actor}")
            st.success("✅ Vault memory buffers successfully wiped.")

    st.markdown("#### Vault Access Audit Trail (real, accumulating log — not regenerated per render)")
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, details FROM system_telemetry_logs WHERE module_name = 'Security Vault' ORDER BY id DESC LIMIT 15")
    vault_events = cursor.fetchall()
    if vault_events:
        st.dataframe(pd.DataFrame(vault_events, columns=["Timestamp (UTC)", "Event"]), width='stretch', hide_index=True)
    else:
        st.info("No vault access events recorded yet this session — save, reveal, or purge a credential above to populate this log.")


def render_audit_forensics():
    section_header("🛡️ Audit & Compliance Forensic Engines", "Computational scanners verifying statistical integrity, AI-content signals, privacy compliance, and cryptographic proofs.")
    st.caption("ℹ️ These call into `modules/audit_compliance_engine.py`, which was not provided alongside this page — their internal correctness could not be independently verified here.")

    tab_int = st.tabs([
        "📊 Statistical Integrity",
        "🤖 AI & Plagiarism Forensics",
        "🔒 Privacy & HIPAA/GDPR",
        "🔗 Cryptographic Proofs",
        "📋 Compliance Reports",
    ])

    with tab_int[0]:
        st.markdown("#### Statcheck Consistency & P-Curve Analysis")
        c1, c2 = st.columns(2)
        with c1:
            test_str = st.text_input("Reported Statistical Test", value="t(248) = 4.12, p = .0001", key="audit_statcheck_upg")
            if st.button("Run Statcheck Validation", key="btn_statcheck_upg"):
                try:
                    st.json(statcheck_consistency(test_str))
                except Exception as e:
                    st.error(f"Engine error: {e}")
        with c2:
            pvals = st.text_input("P-Values (comma-separated)", value="0.01, 0.02, 0.03, 0.04, 0.012, 0.045", key="audit_pcurve_upg")
            if st.button("Execute P-Curve Audit", key="btn_pcurve_upg"):
                try:
                    vals = [float(x) for x in pvals.split(",")]
                    st.json(p_curve_analysis(vals))
                except ValueError:
                    st.error("⚠️ Invalid numeric format for p-value list.")
                except Exception as e:
                    st.error(f"Engine error: {e}")

        st.markdown("#### GRIM & DEGRIM Mathematical Validation")
        c3, c4, c5 = st.columns(3)
        mean = c3.number_input("Reported Mean", value=4.25, key="audit_mean_upg")
        sd = c4.number_input("Reported Standard Deviation", value=1.20, key="audit_sd_upg")
        n = int(c5.number_input("Sample Size (N)", value=20, key="audit_n_upg"))

        col_g, col_d = st.columns(2)
        with col_g:
            if st.button("Run GRIM Test", key="btn_grim_upg"):
                st.json(grim_test(mean, n))
        with col_d:
            if st.button("Run DEGRIM Test", key="btn_degrim_upg"):
                st.json(degrim_test(sd, n))

    with tab_int[1]:
        st.markdown("#### Linguistic Burstiness & Perplexity Profiler")
        sample_text = st.text_area(
            "Corpus Text for AI Signature Analysis",
            value="The quick brown fox jumps over the lazy dog. This is a very short sentence. "
                  "Here is another sentence that is significantly longer and more complex in its grammatical structure.",
            height=120, key="audit_text_upg",
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Compute Burstiness Index", key="btn_burst_upg"):
                st.json(burstiness_detector(sample_text))
        with c2:
            if st.button("Profile Token Perplexity", key="btn_perp_upg"):
                st.json(perplexity_profiler(sample_text))

        st.markdown("#### Citation Fabrication & Spin Detection")
        if st.button("Audit Citation Integrity", key="btn_cite_upg"):
            st.json(citation_fabrication_audit(sample_text))

    with tab_int[2]:
        st.markdown("#### Automated PII Redaction & HIPAA PHI Auditor")
        pii_text = st.text_area("Text Corpus for PII Scanning", value="Contact john@example.com or call +256 700 123 456. ID: 123-45-6789", key="audit_pii_upg", height=80)
        if st.button("Execute PII Redaction Scan", key="btn_redact_upg"):
            res = pii_redactor(pii_text)
            st.json(res["counts"])
            st.code(res["redacted_text"])

        if st.button("Audit Clinical Text for HIPAA PHI", key="btn_hipaa_upg"):
            st.json(hipaa_phi_audit(pii_text))

    with tab_int[3]:
        st.markdown("#### SHA-256 Cryptographic Chain Block Generator")
        c1, c2 = st.columns(2)
        block_id = int(c1.number_input("Block Index", value=1, key="audit_block_id_upg"))
        prev_hash = c2.text_input("Parent Cryptographic Hash", value="0000000000000000", key="audit_prev_hash_upg")
        payload = st.text_input("Payload Data String", value="audited_transaction_record_v1", key="audit_payload_upg")

        if st.button("Generate Cryptographic Proof Block", type="primary", key="btn_block_upg"):
            st.json(sha256_block(block_id, prev_hash, payload, "Sovereign Administrator"))

    with tab_int[4]:
        st.markdown("#### Grant Compliance Matrix & FAIR Data Rating")
        reqs = st.text_input("Mandatory Grant Requirements (comma-separated)", value="abstract, methodology, results, financial_audit", key="audit_reqs_upg")
        done = st.text_input("Fulfilled Deliverables", value="abstract, methodology, results", key="audit_done_upg")

        if st.button("Compile Compliance Matrix", type="primary", key="btn_matrix_upg"):
            st.json(grant_compliance_matrix([r.strip() for r in reqs.split(",")], [d.strip() for d in done.split(",")]))


def render_nexus_vault():
    section_header("🔐 Nexus Vault 2.0 — Secure Workspace Suite", "Integrated encrypted drive, calendar conflict manager, virtual meeting scheduler, markdown documentation suite, spreadsheet engine, and contacts directory.")
    st.caption("ℹ️ Backed by `modules/nexus_vault_engine.py`, which was not provided alongside this page — internals not independently verified here.")

    tab_v = st.tabs([
        "📁 Encrypted Drive",
        "📅 Calendar",
        "🎥 Virtual Meet",
        "📝 Docs",
        "📊 Sheets",
        "👥 Contacts",
        "✅ Tasks",
    ])

    with tab_v[0]:
        st.markdown("#### Encrypted File Repository")
        uploaded = st.file_uploader("Upload confidential document or dataset", type=None, key="nexus_upload_upg")
        if uploaded:
            data = uploaded.getvalue()
            cat = st.selectbox("Data Classification Category", ["DOCUMENTS", "CLINICAL", "GENOMIC", "FINANCIAL", "CODE"], key="nexus_cat_upg")
            notes = st.text_input("Metadata Notes", key="nexus_file_notes_upg")
            if st.button("🔐 Encrypt & Store Securely", type="primary", key="nexus_store_upg"):
                res = NexusVault.store_file(uploaded.name, data, cat, notes)
                st.success(f"✅ Successfully stored **{res['name']}** ({res['size_bytes']} bytes) — SHA-256: `{res['hash'][:16]}…`")
                st.json(res)

        st.markdown("#### Stored Secure Artifacts")
        files = NexusVault.list_files()
        if files:
            df = pd.DataFrame([{k: f[k] for k in ("name", "category", "size_bytes", "created_at")} for f in files])
            df["Size Display"] = df["size_bytes"].apply(lambda b: f"{b/1024:.2f} KB" if b > 1024 else f"{b} B")
            st.dataframe(df.drop(columns=["size_bytes"]), width='stretch', hide_index=True)
            render_export_buttons(df, base_name="nexus_vault_file_directory")
        else:
            st.info("ℹ️ Vault is currently empty. Upload files above to initiate encryption.")

    with tab_v[1]:
        st.markdown("#### Secure Calendar & Conflict Detection")
        with st.form("nexus_event_form_upg"):
            title = st.text_input("Event Title", key="nexus_ev_title_upg")
            d = st.date_input("Event Date", value=datetime.date.today(), key="nexus_ev_date_upg")
            t1 = st.time_input("Start Time", key="nexus_ev_t1_upg")
            t2 = st.time_input("End Time", key="nexus_ev_t2_upg")
            loc = st.text_input("Location / Secure Room", key="nexus_ev_loc_upg")
            submitted = st.form_submit_button("➕ Schedule Event")
            if submitted and title.strip():
                start = datetime.datetime.combine(d, t1).isoformat()
                end = datetime.datetime.combine(d, t2).isoformat()
                conflicts = NexusCalendar.detect_conflicts(title, start, end)
                NexusCalendar.add_event(title, start, end, loc)
                if conflicts:
                    st.warning(f"⚠️ Scheduling conflict detected with {len(conflicts)} overlapping event(s).")
                st.success(f"✅ Event `{title}` successfully scheduled.")

        st.markdown("#### Scheduled Calendar Events")
        events = NexusCalendar.all_events()
        if events:
            ev_df = pd.DataFrame([{"Title": e["title"], "Start": e["start_dt"][:16].replace("T", " "), "End": e["end_dt"][:16].replace("T", " "), "Location": e.get("location", "")} for e in events])
            st.dataframe(ev_df, width='stretch', hide_index=True)
            render_export_buttons(ev_df, base_name="nexus_calendar_events")
        else:
            st.info("ℹ️ No calendar events scheduled.")

    with tab_v[2]:
        st.markdown("#### Virtual Meeting Scheduler")
        st.caption("Manage meeting records and generate links. Video/audio is handled by whatever conferencing backend `NexusMeet.schedule` integrates with — verify that integration in `modules/nexus_vault_engine.py`.")

        with st.form("nexus_meet_form_upg"):
            m_title = st.text_input("Meeting Subject", key="nexus_meet_title_upg")
            m_date = st.date_input("Meeting Date", key="nexus_meet_date_upg")
            m_time = st.time_input("Meeting Time", key="nexus_meet_time_upg")
            m_dur = st.number_input("Duration (Minutes)", value=30, key="nexus_meet_dur_upg")
            m_attendees = st.text_input("Invitees (comma-separated emails)", key="nexus_meet_att_upg")
            m_agenda = st.text_area("Meeting Agenda", key="nexus_meet_agenda_upg")
            m_submitted = st.form_submit_button("🔗 Generate Meeting Link")
            if m_submitted and m_title.strip():
                dat = datetime.datetime.combine(m_date, m_time).isoformat()
                res = NexusMeet.schedule(m_title, dat, int(m_dur), [a.strip() for a in m_attendees.split(",") if a.strip()], m_agenda)
                st.success(f"✅ Meeting created: `{res['meeting_link']}`")
                st.json(res)

        st.markdown("---")
        st.markdown("#### 🎥 Camera Snapshot")
        st.caption("Uses your browser's camera picker directly — Streamlit has no API to select a hardware device index from Python, so that control has been removed rather than left non-functional.")
        camera_capture = st.camera_input("Capture Meeting Snapshot")
        if camera_capture is not None:
            st.success("✅ Frame captured.")
            st.image(camera_capture, caption="Captured Snapshot", width='stretch')

    with tab_v[3]:
        st.markdown("#### Secure Document Editor")
        with st.form("nexus_doc_form_upg"):
            doc_title = st.text_input("Document Title", key="nexus_doc_title_upg")
            doc_body = st.text_area("Markdown Document Body", height=180, key="nexus_doc_body_upg")
            doc_submitted = st.form_submit_button("💾 Save Document")
            if doc_submitted and doc_title.strip():
                NexusDocs.create(doc_title, doc_body)
                st.success(f"✅ Document `{doc_title}` successfully saved to vault.")

        st.markdown("#### Document Archive")
        docs = NexusDocs.list_docs()
        if docs:
            for doc in docs:
                with st.expander(f"📄 {doc['title']} (v{doc['version']})"):
                    content = NexusDocs.get(doc["id"])
                    st.write(content["body"])
                    st.caption(f"Last Modified: {content['updated_at']}")
        else:
            st.info("ℹ️ No documents recorded in vault.")

    with tab_v[4]:
        st.markdown("#### Spreadsheet Engine with Live Formula Evaluation")
        st.caption("Supports live execution formulas such as `=SUM(1,2,3)`, `=AVG(10,20,30)`, `=MAX(...)`.")
        with st.form("nexus_sheet_form_upg"):
            sheet_title = st.text_input("Spreadsheet Title", value="Analytics Sheet", key="nexus_sheet_title_upg")
            sheet_rows = st.text_area("Row Data (pipe-separated cells, one row per line)", value="=SUM(10,20,30)\n=AVG(50,60,70)\n=MAX(100,250,175)", key="nexus_sheet_data_upg")
            sheet_submitted = st.form_submit_button("💾 Save Spreadsheet")
            if sheet_submitted:
                rows = []
                for line in sheet_rows.splitlines():
                    if line.strip():
                        cells = [c.strip() for c in line.split("|")]
                        cells = [NexusSheets.evaluate_formula(c) if c.startswith("=") else c for c in cells]
                        rows.append([str(c) for c in cells])
                NexusSheets.create(sheet_title, rows)
                st.success("✅ Spreadsheet successfully computed and saved.")

    with tab_v[5]:
        st.markdown("#### Contacts Directory")
        with st.form("nexus_contact_form_upg"):
            name = st.text_input("Full Name", key="nexus_contact_name_upg")
            email = st.text_input("Email Address", key="nexus_contact_email_upg")
            phone = st.text_input("Telephone", key="nexus_contact_phone_upg")
            company = st.text_input("Institution / Organization", key="nexus_contact_company_upg")
            group = st.text_input("Group / Tag", value="Collaborators", key="nexus_contact_group_upg")
            contact_submitted = st.form_submit_button("➕ Add Contact")
            if contact_submitted and name.strip():
                NexusContacts.add(name, email, phone, company, group)
                st.success(f"✅ Contact `{name}` added to directory.")

        query = st.text_input("🔍 Search Contacts Directory", key="nexus_contact_search_upg")
        contacts = NexusContacts.list_contacts(query=query)
        if contacts:
            df_contacts = pd.DataFrame(contacts)
            st.dataframe(df_contacts, width='stretch', hide_index=True)
            render_export_buttons(df_contacts, base_name="nexus_contacts_directory")
        else:
            st.info("ℹ️ No matching contacts found.")

    with tab_v[6]:
        st.markdown("#### Task & Milestone Tracker")
        with st.form("nexus_task_form_upg"):
            task_title = st.text_input("Task Description", key="nexus_task_title_upg")
            task_priority = st.selectbox("Priority Level", ["HIGH", "MEDIUM", "LOW"], key="nexus_task_pri_upg")
            task_due = st.date_input("Target Due Date", key="nexus_task_due_upg")
            task_submitted = st.form_submit_button("➕ Add Task Item")
            if task_submitted and task_title.strip():
                NexusTasks.add(task_title, priority=task_priority, due_date=str(task_due))
                st.success("✅ Task successfully recorded.")

        st.markdown("#### Open Task Backlog")
        tasks = NexusTasks.list_tasks(status="OPEN")
        if tasks:
            for t in tasks:
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"- **{t['title']}** · `{t['priority']}` · Due: {t['due_date']}")
                if c2.button("✔️ Complete", key=f"nexus_done_{t['id']}_upg"):
                    NexusTasks.update_status(t["id"], "DONE")
                    st.rerun()
        else:
            st.info("ℹ️ No pending tasks in backlog.")


def render_settings():
    section_header("⚙️ Platform Settings & Configuration", "Manage interface themes, accent coloration, application cache purging, and session data snapshots.")

    st.markdown("#### Appearance & Theme Preferences")
    c1, c2 = st.columns(2)
    with c1:
        theme = st.selectbox("UI Color Scheme", ["dark", "light"], index=0, key="settings_theme_upg")
    with c2:
        accent = st.color_picker("Accent Brand Color", value="#00f2fe", key="settings_accent_upg")

    if theme != st.session_state.get("theme", "dark") or accent != st.session_state.get("accent_color", "#00f2fe"):
        st.session_state["theme"] = theme
        st.session_state["accent_color"] = accent
        st.success("✅ Theme preferences updated successfully.")

    st.markdown("#### Data Management & Cache Operations")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧹 Purge System Cache & Working Datasets", type="primary", key="purge_cache_upg"):
            st.cache_data.clear()
            for key in ["active_df", "working_df", "uploaded_df", "notion_df"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.success("✅ System cache flushed and active datasets cleared.")
    with col2:
        if st.button("📦 Export Session Snapshot", key="export_snapshot_upg"):
            snapshot = {
                "theme": st.session_state.get("theme", "dark"),
                "accent": st.session_state.get("accent_color", "#00f2fe"),
                "user": st.session_state.get("user_identity", {}),
                "active_source_name": st.session_state.get("source_name"),
                "dataset_fingerprint": st.session_state.get("dataset_schema_meta", {}).get("fingerprint"),
                "timestamp": datetime.datetime.utcnow().isoformat(),
            }
            st.download_button("⬇️ Download JSON Snapshot", data=json.dumps(snapshot, indent=2), file_name="sovereign_session_snapshot.json", mime="application/json")


def main():
    require_admin()

    setup_page("Admin & Security Center", "🛡️", initial_sidebar_state="expanded")

    hero_card(
        "🛡️ Admin & Security Center — Sovereign Enterprise Control Plane",
        "Hardened administrative hub consolidating runtime diagnostics, RBAC privilege management, subscription billing, student verification queues, a genuinely encrypted credential vault, compliance forensics, and the Nexus 2.0 workspace suite.",
        badge_text="ADMIN & SECURITY CENTER • ENTERPRISE CONTROL PLANE",
    )

    conn = get_db()

    tabs = st.tabs([
        "🔍 Diagnostics",
        "👤 Users & RBAC",
        "💳 Billing & Licensing",
        "🎓 Student Verification",
        "🔒 Secure Vault",
        "🛡️ Audit & Compliance",
        "🔐 Nexus Vault 2.0",
        "⚙️ Settings",
    ])

    with tabs[0]:
        render_system_diagnostics(conn)
    with tabs[1]:
        render_user_management(conn)
    with tabs[2]:
        render_billing(conn)
    with tabs[3]:
        from modules.verification import render_admin_review_queue
        render_admin_review_queue()
    with tabs[4]:
        render_security_vault(conn)
    with tabs[5]:
        render_audit_forensics()
    with tabs[6]:
        render_nexus_vault()
    with tabs[7]:
        render_settings()

    render_standard_footer("ADMIN & SECURITY CENTER")


if __name__ == "__main__":
    main()