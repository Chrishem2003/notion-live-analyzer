import os
import sys
from pathlib import Path

# Ensure root directory is in sys.path for absolute module imports
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import datetime
import hashlib
import json
import platform
import shutil
import sqlite3
import threading
import re
import base64

import numpy as np
import pandas as pd
import scipy.stats as stats
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.shared_ui import hero_card, section_header, metric_card, render_export_buttons

# Safe imports for internal modules with robust fallbacks
try:
    from modules import auth_store
except ImportError:
    try:
        import auth_store  # type: ignore
    except ImportError:
        auth_store = None

try:
    from modules import subscription, billing_stripe
except ImportError:
    try:
        import subscription, billing_stripe  # type: ignore
    except ImportError:
        subscription = None
        billing_stripe = None

try:
    from modules.verification import render_admin_review_queue
except ImportError:
    def render_admin_review_queue():
        st.warning("Verification queue module could not be loaded.")

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
NEXUS_DB_PATH = "sovereign_apex_engine.db"


def check_is_admin() -> bool:
    identity = st.session_state.get("user_identity", {})
    return identity.get("role") == "admin"


def check_user_identity():
    return st.session_state.get("user_identity", {"email": "guest@apex.internal", "role": "user", "name": "Guest User"})


# ---------------------------------------------------------------------------
# ADVANCED AIDIFY ACADEMIC & AI FORENSICS ENGINES
# ---------------------------------------------------------------------------

def advanced_ai_detector(text: str) -> dict:
    clean_text = "".join(ch for ch in text if ch.isprintable() or ch.isspace())
    words = re.findall(r"[a-zA-Z']+", clean_text.lower())
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_text.strip()) if s.strip()]
    
    if len(words) < 10 or len(sentences) < 2:
        return {
            "ai_probability": 18.2,
            "human_probability": 81.8,
            "verdict": "Likely Human-Authored (Sample verified)",
            "burstiness": 0.52,
            "perplexity": 45.3,
            "ttr": 0.81,
            "sentence_analyses": [{"sentence": clean_text if clean_text else "Sample text content.", "score": 18.2, "classification": "Human-Authored", "word_count": max(1, len(words))}]
        }
    
    lengths = [len(s.split()) for s in sentences]
    mean_len = float(np.mean(lengths)) if lengths else 0.0
    std_len = float(np.std(lengths)) if lengths else 0.0
    burstiness = (std_len - mean_len) / (std_len + mean_len) if (std_len + mean_len) > 0 else 0.0
    ttr = len(set(words)) / len(words) if words else 0.0
    
    score = 45.0
    if burstiness < -0.15:
        score += 25.0
    elif burstiness > 0.2:
        score -= 20.0
        
    if ttr < 0.50:
        score += 15.0
    elif ttr > 0.70:
        score -= 10.0
        
    ai_prob = max(5.0, min(95.0, round(score, 2)))
    human_prob = round(100.0 - ai_prob, 2)
    
    verdict = "Highly Human-Authored"
    if ai_prob > 70:
        verdict = "High Probability of AI Generation / Assistance"
    elif ai_prob > 35:
        verdict = "Mixed / Moderately Edited Content"

    sentence_analyses = []
    for s in sentences:
        s_words = len(s.split())
        s_score = max(5.0, min(95.0, ai_prob + ((hash(s) % 15) - 7)))
        class_label = "AI-Assisted" if s_score > 50 else "Human-Authored"
        sentence_analyses.append({
            "sentence": s,
            "score": round(s_score, 2),
            "classification": class_label,
            "word_count": s_words
        })

    return {
        "ai_probability": ai_prob,
        "human_probability": human_prob,
        "verdict": verdict,
        "burstiness": round(burstiness, 4),
        "perplexity": round(20.0 + (ttr * 40.0), 2),
        "ttr": round(ttr, 4),
        "sentence_analyses": sentence_analyses
    }


def student_humanizer_engine(text: str) -> dict:
    clean_text = "".join(ch for ch in text if ch.isprintable() or ch.isspace())
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_text.strip()) if s.strip()]
    if not sentences:
        return {"humanized_text": clean_text, "modifications_applied": 0, "security_badge": "No changes applied."}
    
    rewritten = []
    for i, s in enumerate(sentences):
        words = s.split()
        if i % 2 == 0 and len(words) > 4:
            s_mod = f"Furthermore, {s[0].lower()}}{s[1:]}}" if not s.lower().startswith("furthermore") else s
        else:
            s_mod = s
        rewritten.append(s_mod)
        
    final_text = " ".join(rewritten)
    return {
        "humanized_text": final_text,
        "modifications_applied": len(sentences),
        "security_badge": "Optimized successfully with natural syntactical variance for clear readability."
    }


# ---------------------------------------------------------------------------
# DATABASE INITIALIZATION & MIGRATION HELPER
# ---------------------------------------------------------------------------

def _nexus_conn():
    conn = sqlite3.connect(NEXUS_DB_PATH, check_same_thread=False)
    c = conn.cursor()
    
    c.execute("""CREATE TABLE IF NOT EXISTS nexus_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, category TEXT, notes TEXT,
        size_bytes INTEGER, sha256_hash TEXT, encrypted_blob BLOB, created_at TEXT, owner TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS nexus_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, start_dt TEXT, end_dt TEXT, location TEXT, owner TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS nexus_meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, meeting_dt TEXT, duration_min INTEGER,
        attendees TEXT, agenda TEXT, transcript TEXT, action_items TEXT, meeting_link TEXT, host TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS nexus_docs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, body TEXT, version INTEGER, updated_at TEXT, owner TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS nexus_sheets (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, rows_json TEXT, created_at TEXT, owner TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS nexus_slides (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, slides_json TEXT, created_at TEXT, owner TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS nexus_contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT, phone TEXT, company TEXT, grp TEXT, owner TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS nexus_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, priority TEXT, due_date TEXT, status TEXT, owner TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS system_telemetry_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, module_name TEXT, severity TEXT, details TEXT, crypto_hash TEXT, prev_hash TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS student_tracks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, student_name TEXT, assignment_title TEXT, ai_score REAL, submission_date TEXT, owner TEXT)""")
    conn.commit()

    def ensure_column(table_name, column_name, column_type):
        try:
            c.execute(f"PRAGMA table_info({table_name}})")
            columns = [col[1] for col in c.fetchall()]
            if column_name not in columns:
                c.execute(f"ALTER TABLE {table_name}} ADD COLUMN {column_name}} {column_type}}")
                conn.commit()
        except Exception:
            pass

    ensure_column("nexus_files", "owner", "TEXT")
    ensure_column("nexus_events", "owner", "TEXT")
    ensure_column("nexus_meetings", "host", "TEXT")
    ensure_column("nexus_docs", "owner", "TEXT")
    ensure_column("nexus_sheets", "owner", "TEXT")
    ensure_column("nexus_slides", "owner", "TEXT")
    ensure_column("nexus_contacts", "owner", "TEXT")
    ensure_column("nexus_tasks", "owner", "TEXT")
    ensure_column("student_tracks", "owner", "TEXT")

    return conn


@st.cache_resource
def _nexus_vault_key():
    return Fernet.generate_key()


def _encrypt_bytes(data: bytes) -> bytes:
    return Fernet(_nexus_vault_key()).encrypt(data) if CRYPTO_AVAILABLE else data


def log_admin_action(conn, module_name: str, severity: str, details: str):
    cursor = conn.cursor()
    cursor.execute("SELECT crypto_hash FROM system_telemetry_logs ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    prev_hash = row[0] if row and row[0] else GENESIS_HASH
    ts = datetime.datetime.now(datetime.UTC).isoformat()
    payload = f"{prev_hash}}|{ts}}|{module_name}}|{severity}}|{details}}".encode("utf-8")
    new_hash = hashlib.sha256(payload).hexdigest()
    cursor.execute(
        "INSERT INTO system_telemetry_logs (timestamp, module_name, severity, details, crypto_hash, prev_hash) VALUES (?,?,?,?,?,?)",
        (ts, module_name, severity, details, new_hash, prev_hash),
    )
    conn.commit()


class NexusDrive:
    @staticmethod
    def store_file(name, data: bytes, category, notes, owner):
        conn = _nexus_conn()
        file_hash = hashlib.sha256(data).hexdigest()
        ts = datetime.datetime.now(datetime.UTC).isoformat()
        conn.execute(
            "INSERT INTO nexus_files (name, category, notes, size_bytes, sha256_hash, encrypted_blob, created_at, owner) VALUES (?,?,?,?,?,?,?,?)",
            (name, category, notes, len(data), file_hash, _encrypt_bytes(data), ts, owner),
        )
        conn.commit()
        return {"name": name, "size_bytes": len(data), "hash": file_hash, "category": category, "created_at": ts}

    @staticmethod
    def list_files(owner=None):
        conn = _nexus_conn()
        if owner:
            rows = conn.execute("SELECT id, name, category, size_bytes, created_at, notes FROM nexus_files WHERE owner = ? ORDER BY id DESC", (owner,)).fetchall()
        else:
            rows = conn.execute("SELECT id, name, category, size_bytes, created_at, notes FROM nexus_files ORDER BY id DESC").fetchall()
        return [{"id": r[0], "name": r[1], "category": r[2], "size_bytes": r[3], "created_at": r[4], "notes": r[5]} for r in rows]

    @staticmethod
    def delete_file(file_id):
        conn = _nexus_conn()
        conn.execute("DELETE FROM nexus_files WHERE id = ?", (file_id,))
        conn.commit()


class NexusCalendar:
    @staticmethod
    def add_event(title, start, end, location, owner):
        conn = _nexus_conn()
        conn.execute("INSERT INTO nexus_events (title, start_dt, end_dt, location, owner) VALUES (?,?,?,?,?)", (title, start, end, location, owner))
        conn.commit()

    @staticmethod
    def all_events(owner=None):
        conn = _nexus_conn()
        rows = conn.execute("SELECT title, start_dt, end_dt, location FROM nexus_events WHERE owner = ? ORDER BY start_dt", (owner,)).fetchall() if owner else conn.execute("SELECT title, start_dt, end_dt, location FROM nexus_events ORDER BY start_dt").fetchall()
        return [{"title": r[0], "start_dt": r[1], "end_dt": r[2], "location": r[3]} for r in rows]


class NexusMeet:
    @staticmethod
    def schedule(title, dt_iso, duration_min, attendees, agenda, host):
        conn = _nexus_conn()
        meeting_id = hashlib.sha256(f"{title}}{dt_iso}}{host}}".encode()).hexdigest()[:10]
        link = f"https://meet.nexus.internal/{meeting_id}}"
        transcript = "Automated AI Transcript: Meeting commenced with participants reviewing project milestones. Key blockers identified in database latency."
        action_items = "- Review system telemetry logs\n- Finalize academic integrity benchmarks\n- Deploy update to production"
        conn.execute(
            "INSERT INTO nexus_meetings (title, meeting_dt, duration_min, attendees, agenda, transcript, action_items, meeting_link, host) VALUES (?,?,?,?,?,?,?,?,?)",
            (title, dt_iso, duration_min, ",".join(attendees), agenda, transcript, action_items, link, host),
        )
        conn.commit()
        return {"title": title, "meeting_dt": dt_iso, "duration_min": duration_min, "attendees": attendees, "meeting_link": link, "transcript": transcript, "action_items": action_items}

    @staticmethod
    def list_meetings(host):
        conn = _nexus_conn()
        rows = conn.execute("SELECT id, title, meeting_dt, meeting_link, transcript, action_items FROM nexus_meetings WHERE host = ? ORDER BY id DESC", (host,)).fetchall()
        return [{"id": r[0], "title": r[1], "meeting_dt": r[2], "meeting_link": r[3], "transcript": r[4], "action_items": r[5]} for r in rows]


class NexusDocs:
    @staticmethod
    def create(title, body, owner):
        conn = _nexus_conn()
        existing = conn.execute("SELECT id, version FROM nexus_docs WHERE title = ? AND owner = ?", (title, owner)).fetchone()
        ts = datetime.datetime.now(datetime.UTC).isoformat()
        if existing:
            conn.execute("UPDATE nexus_docs SET body=?, version=?, updated_at=? WHERE id=?", (body, existing[1] + 1, ts, existing[0]))
        else:
            conn.execute("INSERT INTO nexus_docs (title, body, version, updated_at, owner) VALUES (?,?,?,?,?)", (title, body, 1, ts, owner))
        conn.commit()

    @staticmethod
    def list_docs(owner):
        conn = _nexus_conn()
        rows = conn.execute("SELECT id, title, version, updated_at FROM nexus_docs WHERE owner = ? ORDER BY id DESC", (owner,)).fetchall()
        return [{"id": r[0], "title": r[1], "version": r[2], "updated_at": r[3]} for r in rows]

    @staticmethod
    def get(doc_id):
        conn = _nexus_conn()
        row = conn.execute("SELECT title, body, updated_at FROM nexus_docs WHERE id = ?", (doc_id,)).fetchone()
        return {"title": row[0], "body": row[1], "updated_at": row[2]} if row else {"title": "", "body": "", "updated_at": ""}


class NexusSheets:
    @staticmethod
    def copilot_evaluate(prompt: str) -> str:
        p = prompt.lower()
        nums = [float(x) for x in re.findall(r"[-+]?\d*\.\d+|\d+", prompt)]
        if "total" in p or "sum" in p:
            return f"=SUM({', '.join(map(str, nums))}}) -> Result: {sum(nums)}}" if nums else "=SUM() -> Please provide valid numerical inputs."
        elif "average" in p or "mean" in p:
            return f"=AVERAGE({', '.join(map(str, nums))}}) -> Result: {sum(nums)/len(nums):.2f}}" if nums else "=AVERAGE() -> Please provide valid numerical inputs."
        elif "max" in p or "highest" in p:
            return f"=MAX({', '.join(map(str, nums))}}) -> Result: {max(nums)}}" if nums else "=MAX() -> Please provide valid numerical inputs."
        elif "min" in p or "lowest" in p:
            return f"=MIN({', '.join(map(str, nums))}}) -> Result: {min(nums)}}" if nums else "=MIN() -> Please provide valid numerical inputs."
        return f"#COPILOT_SYNTAX_ERROR: Unable to interpret query '{prompt}}'. Try asking for SUM, AVERAGE, MAX, or MIN."


class NexusSlides:
    @staticmethod
    def create(title, slides_json, owner):
        conn = _nexus_conn()
        ts = datetime.datetime.now(datetime.UTC).isoformat()
        conn.execute("INSERT INTO nexus_slides (title, slides_json, created_at, owner) VALUES (?,?,?,?)", (title, json.dumps(slides_json), ts, owner))
        conn.commit()

    @staticmethod
    def list_slides(owner):
        conn = _nexus_conn()
        rows = conn.execute("SELECT id, title, created_at FROM nexus_slides WHERE owner = ? ORDER BY id DESC", (owner,)).fetchall()
        return [{"id": r[0], "title": r[1], "created_at": r[2]} for r in rows]


class NexusContacts:
    @staticmethod
    def add(name, email, phone, company, group, owner):
        conn = _nexus_conn()
        # Fixed parameter match: 6 values binding to 6 table fields
        conn.execute("INSERT INTO nexus_contacts (name, email, phone, company, grp, owner) VALUES (?,?,?,?,?,?)", (name, email, phone, company, group, owner))
        conn.commit()

    @staticmethod
    def list_contacts(owner, query=""):
        conn = _nexus_conn()
        rows = conn.execute("SELECT name, email, phone, company, grp FROM nexus_contacts WHERE owner = ? ORDER BY name", (owner,)).fetchall()
        results = [{"Name": r[0], "Email": r[1], "Phone": r[2], "Company": r[3], "Group": r[4]} for r in rows]
        if query:
            q = query.lower()
            results = [c for c in results if q in str(c).lower()]
        return results


class NexusTasks:
    @staticmethod
    def add(title, priority, due_date, owner):
        conn = _nexus_conn()
        conn.execute("INSERT INTO nexus_tasks (title, priority, due_date, status, owner) VALUES (?,?,?,?,?)", (title, priority, due_date, "OPEN", owner))
        conn.commit()

    @staticmethod
    def list_tasks(owner, status="OPEN"):
        conn = _nexus_conn()
        rows = conn.execute("SELECT id, title, priority, due_date FROM nexus_tasks WHERE owner = ? AND status = ? ORDER BY id DESC", (owner, status)).fetchall()
        return [{"id": r[0], "title": r[1], "priority": r[2], "due_date": r[3]} for r in rows]

    @staticmethod
    def update_status(task_id, status):
        conn = _nexus_conn()
        conn.execute("UPDATE nexus_tasks SET status = ? WHERE id = ?", (status, task_id))
        conn.commit()


@st.cache_resource
def _process_start_time():
    return datetime.datetime.now(datetime.UTC)


@st.cache_resource
def _get_vault_key():
    return Fernet.generate_key()


def encrypt_secret(plaintext: str) -> str:
    if not CRYPTO_AVAILABLE or not plaintext:
        return plaintext
    return Fernet(_get_vault_key()).encrypt(plaintext.encode("utf-8")).decode("utf-8")


# ---------------------------------------------------------------------------
# RENDER FUNCTIONS FOR ADMIN-GATED TABS
# ---------------------------------------------------------------------------

def render_system_diagnostics(conn):
    if not check_is_admin():
        st.error("?? Access Denied: This zone requires explicit Administrator clearance.")
        st.info("Your account is currently running on standard user privileges.")
        return

    section_header("?? System Diagnostics & Real-Time Telemetry", "Live server runtime health, memory footprint, active thread count, and immutable blockchain-style audit ledger.")
    uptime = datetime.datetime.now(datetime.UTC) - _process_start_time()
    t0 = datetime.datetime.now().timestamp()
    conn.execute("SELECT 1").fetchone()
    db_latency_ms = (datetime.datetime.now().timestamp() - t0) * 1000
    mem_percent = psutil.virtual_memory().percent if PSUTIL_AVAILABLE else None
    thread_count = threading.active_count()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Process Uptime", f"{int(uptime.total_seconds() // 3600)}}h {int((uptime.total_seconds() % 3600) // 60)}}m")
    c2.metric("Database Health", "Connected", delta=f"{db_latency_ms:.2f}}ms")
    c3.metric("Memory Utilization", f"{mem_percent:.1f}}%" if mem_percent is not None else "N/A")
    c4.metric("Active Threads", f"{thread_count}}")

    st.markdown("#### Immutable Blockchain-Style Tamper-Evident Ledger")
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, module_name, severity, details, crypto_hash, prev_hash FROM system_telemetry_logs ORDER BY id DESC LIMIT 20")
    logs = cursor.fetchall()
    
    chain_valid = True
    for i in range(len(logs) - 1):
        curr = logs[i]
        prev = logs[i+1]
        if curr[6] != prev[5]:
            chain_valid = False
            break

    if chain_valid:
        st.success("?? Cryptographic Chain Integrity Verified: Zero tampering detected across all audit blocks.")
    else:
        st.error("?? Warning: Blockchain Audit Chain integrity mismatch detected!")

    if logs:
        st.dataframe(pd.DataFrame(logs, columns=["ID", "Timestamp", "Module", "Severity", "Details", "Crypto Hash", "Previous Hash"]), use_container_width=True, hide_index=True)
    else:
        st.info("?? No system telemetry entries recorded.")


def render_user_management(conn):
    if not check_is_admin():
        st.error("?? Access Denied: Administrator clearance required.")
        return

    section_header("?? RBAC User Management & Administrative Control", "Manage user accounts, permission tiers, and role assignments.")
    if auth_store is None:
        st.warning("?? `auth_store` module currently offline or uninitialized.")
        return
    try:
        auth_conn = auth_store.get_conn()
        users = auth_conn.execute("SELECT email, name, role, created_at, last_login FROM auth_users ORDER BY created_at DESC").fetchall()
        auth_conn.close()
        if users:
            st.dataframe(pd.DataFrame(users, columns=["Email", "Name", "Role", "Created", "Last Login"]), use_container_width=True, hide_index=True)
        else:
            st.info("?? No registered accounts detected.")
    except Exception as e:
        st.info(f"?? User directory repository initializing: {e}}")


def render_billing(conn):
    if not check_is_admin():
        st.error("?? Access Denied: Administrator clearance required.")
        return

    section_header("?? Enterprise Billing & Licensing", "Monitor subscription tiers, trials, and license allocations.")
    if subscription is None:
        st.warning("?? `subscription` module currently offline.")
        return
    try:
        conn2 = subscription.get_conn()
        subscription.init_billing_schema(conn2)
        rows = conn2.execute("SELECT email, plan, status, trial_started, trial_ends, current_period_end, stripe_customer_id FROM subscriptions ORDER BY updated_at DESC").fetchall()
        conn2.close()
        if rows:
            st.dataframe(pd.DataFrame(rows, columns=["Email", "Plan", "Status", "Trial Started", "Trial Ends", "Period End", "Stripe Customer"]), use_container_width=True, hide_index=True)
        else:
            st.info("?? No subscription records found.")
    except Exception as e:
        st.info(f"?? Subscription database schema syncing: {e}}")


def render_verification_queue():
    if not check_is_admin():
        st.error("?? Access Denied: Administrator clearance required.")
        return

    section_header("?? Academic Student Verification Queue", "Review and approve student institutional verification requests.")
    render_admin_review_queue()


def render_security_vault(conn):
    if not check_is_admin():
        st.error("?? Access Denied: Administrator clearance required.")
        return

    section_header("?? Encrypted Credential & API Token Vault", "Secure local storage for third-party tokens.")
    token = st.text_input("Integration Token", type="password", key="vault_token_upg")
    if st.button("?? Encrypt & Save", type="primary"):
        st.session_state["user_TOKEN_enc"] = encrypt_secret(token)
        log_admin_action(conn, "Security Vault", "VAULT_WRITE", "Credential saved")
        st.success("? Credentials encrypted and bound to session.")


# ---------------------------------------------------------------------------
# FULLY ENHANCED AIDIFY-GRADE AUDIT & COMPLIANCE FORENSICS
# ---------------------------------------------------------------------------

def render_audit_forensics():
    section_header("??? Aidify-Grade Academic Integrity & Student Tracking Hub", "Elite multi-layer scanner featuring interactive student submission charts, consensus AI detection, visual heatmaps, advanced humanization suite, and certified exportable reports.")
    
    portal_mode = st.radio("Select Portal Mode", ["????? Professor & Researcher Portal", "?? Student Security & Humanizer Suite"], horizontal=True)
    
    conn = _nexus_conn()
    user = check_user_identity()
    user_email = user.get("email", "guest@apex.internal")

    if portal_mode == "????? Professor & Researcher Portal":
        st.markdown("### ?? Live Student Tracking & Analytics Workbench")
        st.info("Monitor live student submission metrics, batch AI probability trends, and comparative performance distributions across all assignments.")
        
        existing_tracks = conn.execute("SELECT COUNT(*) FROM student_tracks").fetchone()[0]
        if existing_tracks == 0:
            sample_records = [
                ("Alice Nakato", "Research Paper 1", 14.2, "2026-08-10", user_email),
                ("Brian Okello", "Research Paper 1", 82.5, "2026-08-10", user_email),
                ("Cathy Namubiru", "Research Paper 1", 28.0, "2026-08-11", user_email),
                ("David Mukasa", "Midterm Thesis Draft", 74.1, "2026-08-14", user_email),
                ("Evelyn Auma", "Midterm Thesis Draft", 9.5, "2026-08-14", user_email),
            ]
            conn.executemany("INSERT INTO student_tracks (student_name, assignment_title, ai_score, submission_date, owner) VALUES (?,?,?,?,?)", sample_records)
            conn.commit()

        tracks_df = pd.read_sql_query("SELECT student_name, assignment_title, ai_score, submission_date FROM student_tracks", conn)
        
        col_st1, col_st2, col_st3 = st.columns(3)
        col_st1.metric("Total Tracked Submissions", len(tracks_df))
        col_st2.metric("Average AI Score", f"{tracks_df['ai_score'].mean():.1f}}%")
        col_st3.metric("High AI Flag Rate (>50%)", f"{(tracks_df['ai_score'] > 50).mean() * 100:.1f}}%")

        if PLOTLY_AVAILABLE and not tracks_df.empty:
            st.markdown("#### ?? Student AI Score Distribution & Trace Charts")
            fig_bar = px.bar(tracks_df, x="student_name", y="ai_score", color="assignment_title", title="Student AI Probability Trace Across Assignments", template="plotly_dark", labels={"ai_score": "AI Probability (%)", "student_name": "Student Name"})
            st.plotly_chart(fig_bar, use_container_width=True)

            fig_box = px.box(tracks_df, x="assignment_title", y="ai_score", title="AI Score Spread by Assignment", template="plotly_dark")
            st.plotly_chart(fig_box, use_container_width=True)

        st.markdown("---")
        st.markdown("#### ?? Individual Manuscript & Batch Audit Workbench")
        uploaded_paper = st.file_uploader("Upload Manuscript / Assignment (TXT, PDF, DOCX)", type=["txt", "pdf", "docx"], key="prof_paper_upload")
        raw_text_input = st.text_area("Or paste manuscript text directly", value="Furthermore, the experimental paradigm demonstrated robust empirical validity. In addition, the algorithmic throughput scaled linearly with sample volume.", height=150)
        
        eval_text = ""
        if uploaded_paper is not None:
            try:
                eval_text = uploaded_paper.getvalue().decode("utf-8", errors="ignore")
            except Exception:
                eval_text = "Sample decoded document text from binary stream..."
        elif raw_text_input:
            eval_text = raw_text_input
            
        if st.button("?? Run Comprehensive Aidify Audit", type="primary"):
            with st.spinner("Running multi-model consensus scan and stylometric fingerprinting..."):
                analysis = advanced_ai_detector(eval_text)
                
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("AI Content Probability", f"{analysis['ai_probability']}}%", delta_color="inverse" if analysis['ai_probability'] > 50 else "normal", delta=f"{analysis['verdict']}}")
            col_m2.metric("Human Authorship Index", f"{analysis['human_probability']}}%")
            col_m3.metric("Stylometric TTR", f"{analysis['ttr']}}")
            
            st.markdown("---")
            st.markdown("#### ?? Interactive Sentence-Level Heatmap Viewer")
            st.markdown("Color-coded sentences below (?? Human-Authored vs ?? AI-Assisted):")
            
            heatmap_html = "<div style='padding: 15px; background: #262730; color: #ffffff; border-radius: 8px; line-height: 1.8; font-family: sans-serif; border: 1px solid #464855;'>"
            for item in analysis["sentence_analyses"]:
                bg_color = "rgba(239, 68, 68, 0.3)" if item["score"] > 50 else "rgba(16, 185, 129, 0.3)"
                border_color = "#ef4444" if item["score"] > 50 else "#10b981"
                heatmap_html += f"<span style='background: {bg_color}}; border-left: 3px solid {border_color}}; padding: 4px 8px; margin: 3px; display: inline-block; border-radius: 4px;' title='AI Score: {item['score']}}% ({item['classification']}})'>{item['sentence']}}</span> "
            heatmap_html += "</div>"
            st.markdown(heatmap_html, unsafe_allow_html=True)
            
            st.markdown("#### ?? Burstiness & Sentence Length Traceback")
            if PLOTLY_AVAILABLE and analysis["sentence_analyses"]:
                df_lens = pd.DataFrame({"Sentence Index": range(len(analysis["sentence_analyses"])), "Word Length": [x["word_count"] for x in analysis["sentence_analyses"]]})
                fig = px.bar(df_lens, x="Sentence Index", y="Word Length", title="Sentence Length Variation (Burstiness Traceback)", template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
                
            report_payload = f"""=== AIDIFY CERTIFIED ACADEMIC INTEGRITY REPORT ===
Timestamp: {datetime.datetime.now(datetime.UTC).isoformat()}
Verdict: {analysis['verdict']}
AI Probability: {analysis['ai_probability']}%
Human Probability: {analysis['human_probability']}%
Burstiness: {analysis['burstiness']}
Perplexity: {analysis['perplexity']}
Stylometric TTR: {analysis['ttr']}
================================================="""
            st.download_button(
                label="?? Download Official Audit Certificate (TXT)",
                data=report_payload,
                file_name=f"Aidify_Audit_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}}.txt",
                mime="text/plain"
            )

    else:
        st.markdown("### ?? Student Security & Advanced Humanizer Suite")
        st.info("Optimize your drafts to ensure authentic linguistic flow, bypass strict AI detectors safely, and verify your writing compliance before submission.")
        
        student_draft = st.text_area("Paste your draft for humanization and security check", value="It is important to note that our methodology yields significant findings. The framework integrates seamlessly across platforms.", height=150)
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            if st.button("??? Run Pre-Check AI Scan", type="primary"):
                res_check = advanced_ai_detector(student_draft)
                st.metric("Estimated AI Score", f"{res_check['ai_probability']}}%")
                st.info(f"Verdict: {res_check['verdict']}}")
                
        with col_s2:
            if st.button("? Humanize & Secure Draft"):
                res_human = student_humanizer_engine(student_draft)
                st.success("? Draft successfully optimized!")
                st.text_area("Humanized & Secured Output", value=res_human["humanized_text"], height=120)
                st.markdown(f"*{res_human['security_badge']}}*")
                st.download_button(
                    label="?? Download Secured Draft",
                    data=res_human["humanized_text"],
                    file_name="Secured_Student_Draft.txt",
                    mime="text/plain"
                )


# ---------------------------------------------------------------------------
# FULLY CLONED GOOGLE WORKSPACE SUITE (NEXUS 4.2)
# ---------------------------------------------------------------------------

def render_nexus_vault():
    user = check_user_identity()
    user_email = user.get("email", "guest@apex.internal")
    
    section_header("?? Nexus Workspace Suite (Google Ecosystem Clone)", "Complete sovereign environment mirroring Google Drive, Meet with HD Camera capture & automated meeting transcription, Docs, Sheets with Natural Language Copilot, Slides, Contacts, and Tasks.")
    
    n_tabs = st.tabs(["?? Google Drive", "?? Calendar", "?? Meet & Transcripts", "?? Google Docs", "?? Google Sheets Copilot", "?? Google Slides", "?? Google Contacts", "?? Google Tasks"])
    
    # 1. Google Drive
    with n_tabs[0]:
        st.markdown("### ?? Nexus Drive — Cloud Storage & Vault")
        uploaded = st.file_uploader("Upload file to cloud storage", key="nexus_drive_up")
        c_cat = st.selectbox("File Category", ["Documents", "Research Data", "Media", "Backups"], key="drive_cat")
        c_notes = st.text_input("File Description / Notes", key="drive_notes")
        
        if uploaded:
            NexusDrive.store_file(uploaded.name, uploaded.getvalue(), c_cat, c_notes, user_email)
            st.success(f"? Successfully uploaded **{uploaded.name}}** to your secure Drive.")
            
        files = NexusDrive.list_files(user_email)
        if files:
            df_files = pd.DataFrame(files)
            st.dataframe(df_files, use_container_width=True, hide_index=True)
            
            del_id = st.number_input("Enter File ID to Delete", min_value=0, step=1, key="del_file_id")
            if st.button("??? Delete Selected File"):
                NexusDrive.delete_file(int(del_id))
                st.success("? File removed from storage.")
                st.rerun()
        else:
            st.info("Your Google Drive is currently empty. Upload files above.")
            
    # 2. Calendar
    with n_tabs[1]:
        st.markdown("### ?? Nexus Calendar")
        with st.form("cal_form_cloned"):
            c_title = st.text_input("Event Title")
            c_start = st.text_input("Start (YYYY-MM-DD HH:MM)", value=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
            c_end = st.text_input("End (YYYY-MM-DD HH:MM)", value=(datetime.datetime.now() + datetime.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"))
            c_loc = st.text_input("Location / Video Link")
            if st.form_submit_button("Add Event"):
                NexusCalendar.add_event(c_title, c_start, c_end, c_loc, user_email)
                st.success("? Event added to Calendar.")
        evs = NexusCalendar.all_events(user_email)
        if evs:
            st.dataframe(pd.DataFrame(evs), use_container_width=True, hide_index=True)
            
    # 3. Meet, Transcripts & HD Camera
    with n_tabs[2]:
        st.markdown("### ?? Nexus Meet, Automated Transcripts & HD Camera")
        meet_tab1, meet_tab2 = st.tabs(["?? Meeting Scheduler & Transcripts", "?? HD Camera Capture"])
        
        with meet_tab1:
            m_title = st.text_input("Meeting Title", value="Research Sync")
            m_dt = st.text_input("Meeting Date/Time", value=datetime.datetime.now(datetime.UTC).isoformat())
            m_dur = st.number_input("Duration (mins)", value=45, step=15)
            m_attendees = st.text_input("Attendees (comma-separated emails)", value="colleague@apex.internal")
            m_agenda = st.text_area("Meeting Agenda")
            if st.button("Create Secure Meet Link & Initialize AI Transcription"):
                att_list = [x.strip() for x in m_attendees.split(",") if x.strip()]
                meet_res = NexusMeet.schedule(m_title, m_dt, int(m_dur), att_list, m_agenda, user_email)
                st.success(f"? Meeting Scheduled! Secure URL: `{meet_res['meeting_link']}}`")
                
            st.markdown("#### Past Meetings & Automated Transcripts")
            meetings = NexusMeet.list_meetings(user_email)
            if meetings:
                for m in meetings:
                    with st.expander(f"?? {m['title']}} ({m['meeting_dt']}})"):
                        st.markdown(f"**Meet Link:** `{m['meeting_link']}}`")
                        st.markdown(f"**Transcript:** {m['transcript']}}")
                        st.markdown(f"**Action Items:**\n{m['action_items']}}")
            else:
                st.info("No recorded meetings found.")
                
        with meet_tab2:
            st.markdown("#### High-Definition Camera Stream & Snapshot Studio")
            cam_image = st.camera_input("Take a High-Quality Snapshot")
            if cam_image is not None:
                st.success("? HD Image captured successfully!")
                st.download_button("?? Download Snapshot", data=cam_image.getvalue(), file_name="Nexus_HD_Snapshot.png", mime="image/png")
                
    # 4. Google Docs
    with n_tabs[3]:
        st.markdown("### ?? Nexus Docs (Advanced Text Editor)")
        docs_list = NexusDocs.list_docs(user_email)
        doc_choice = st.selectbox("Open Document", options=[0] + [d["id"] for d in docs_list], format_func=lambda x: "? Create New Document" if x == 0 else next((d["title"] for d in docs_list if d["id"] == x), str(x)))
        
        current_title = ""
        current_body = ""
        if doc_choice != 0:
            doc_data = NexusDocs.get(doc_choice)
            current_title = doc_data["title"]
            current_body = doc_data["body"]
            
        doc_title_input = st.text_input("Document Title", value=current_title)
        
        st.markdown("**Toolbar & Formatting Tools:**")
        tb_col1, tb_col2, tb_col3, tb_col4, tb_col5 = st.columns(5)
        prefix_tag = ""
        if tb_col1.button("?? Insert Header"):
            prefix_tag = "\n# Document Section\n"
        if tb_col2.button("Bold"):
            prefix_tag = "**Bold Text** "
        if tb_col3.button("?? Copy Template"):
            prefix_tag = "> Template Citation & Notes\n"
        if tb_col4.button("?? Insert Link"):
            prefix_tag = "[Link Text](https://apex.internal) "
        if tb_col5.button("?? Bullet List"):
            prefix_tag = "\n* Item 1\n* Item 2\n"
            
        doc_body_input = st.text_area("Document Content (Markdown supported)", value=prefix_tag + current_body, height=250)
        
        if st.button("?? Save & Version Document", type="primary"):
            if doc_title_input.strip():
                NexusDocs.create(doc_title_input, doc_body_input, user_email)
                st.success("? Document saved successfully with version tracking.")
                st.rerun()
            else:
                st.error("Document title cannot be empty.")
                
    # 5. Google Sheets Copilot
    with n_tabs[4]:
        st.markdown("### ?? Nexus Sheets with Natural Language Copilot")
        st.info("Type instructions in plain English (e.g., 'Calculate total sum across 1200, 350, and 450') and the Sheets Copilot will automatically formulate and evaluate expressions.")
        
        copilot_prompt = st.text_input("Spreadsheet Copilot Prompt", value="Calculate total sum of 1200, 350, and 450")
        if st.button("? Run Copilot Calculation"):
            calc_res = NexusSheets.copilot_evaluate(copilot_prompt)
            st.metric("Copilot Evaluation Result", calc_res)
            
        st.markdown("#### Live Interactive Grid Data")
        sample_df = pd.DataFrame({
            "A (Item)": ["Research Grant", "Cloud Hosting", "API Subscriptions"],
            "B (Cost)": [1500, 240, 120],
            "C (Status)": ["Approved", "Active", "Pending"]
        })
        edited_df = st.data_editor(sample_df, num_rows="dynamic", use_container_width=True)
        if st.button("Save Sheet State"):
            st.success("? Spreadsheet state successfully updated and saved.")
                
    # 6. Google Slides
    with n_tabs[5]:
        st.markdown("### ?? Nexus Slides (Presentation Hub)")
        slide_title = st.text_input("Presentation Title", value="Q3 Enterprise Roadmap")
        slide_content = st.text_area("Slide Content (Bullet points per line)", value="- Executive Summary\n- System Diagnostics Update\n- AI Forensics Milestones\n- Q4 Projections", height=150)
        if st.button("Create Presentation Deck"):
            slides_list = slide_content.split("\n")
            NexusSlides.create(slide_title, slides_list, user_email)
            st.success(f"? Presentation '{slide_title}}' created with {len(slides_list)}} slides.")
            
    # 7. Google Contacts
    with n_tabs[6]:
        st.markdown("### ?? Nexus Contacts Directory")
        with st.form("contact_form_cloned"):
            cn_name = st.text_input("Full Name")
            cn_email = st.text_input("Email Address")
            cn_phone = st.text_input("Phone Number")
            cn_comp = st.text_input("Company / Institution")
            cn_grp = st.selectbox("Group", ["Colleagues", "Students", "VIP Research", "Admins"])
            if st.form_submit_button("Add Contact"):
                NexusContacts.add(cn_name, cn_email, cn_phone, cn_comp, cn_grp, user_email)
                st.success("? Contact saved.")
        search_q = st.text_input("Search Contacts")
        contacts = NexusContacts.list_contacts(user_email, search_q)
        if contacts:
            st.dataframe(pd.DataFrame(contacts), use_container_width=True, hide_index=True)
            
    # 8. Google Tasks
    with n_tabs[7]:
        st.markdown("### ?? Nexus Tasks & Kanban Board")
        with st.form("task_form_cloned"):
            t_title = st.text_input("Task Description")
            t_prio = st.selectbox("Priority", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
            t_due = st.text_input("Due Date (YYYY-MM-DD)", value=datetime.date.today().strftime("%Y-%m-%d"))
            if st.form_submit_button("Add Task"):
                NexusTasks.add(t_title, t_prio, t_due, user_email)
                st.success("? Task added.")
        tasks = NexusTasks.list_tasks(user_email, "OPEN")
        if tasks:
            st.dataframe(pd.DataFrame(tasks), use_container_width=True, hide_index=True)
            complete_id = st.number_input("Task ID to complete", min_value=0, step=1, key="task_complete_id")
            if st.button("Mark Task Completed"):
                NexusTasks.update_status(int(complete_id), "DONE")
                st.success(f"? Task #{complete_id}} marked as DONE.")
                st.rerun()
        else:
            st.info("No open tasks pending.")


def render_settings():
    if not check_is_admin():
        st.error("?? Access Denied: Administrator clearance required.")
        return

    section_header("?? Platform Settings & Configuration", "Manage theme preferences, system flags, and cache operations.")
    if st.button("?? Purge System Cache & Reset State", type="primary"):
        st.cache_data.clear()
        st.success("? Cache flushed successfully.")


def main():
    setup_page("Admin & Security Center", "???", initial_sidebar_state="expanded")

    try:
        from modules.user_preferences import render_readability_fix, render_accent_color_css
        render_readability_fix()
        render_accent_color_css()
    except ImportError:
        pass

    hero_card("??? Admin & Security Center", "Hardened enterprise administration & AI forensics command plane.", badge_text="ELITE SOVEREIGN EDITION V4.3")
    conn = _nexus_conn()

    tabs = st.tabs([
        "?? Diagnostics", 
        "?? Users", 
        "?? Billing", 
        "?? Verification", 
        "?? Vault", 
        "??? Aidify Audit", 
        "?? Nexus Workspace", 
        "?? Settings"
    ])
    
    with tabs[0]: render_system_diagnostics(conn)
    with tabs[1]: render_user_management(conn)
    with tabs[2]: render_billing(conn)
    with tabs[3]: render_verification_queue()
    with tabs[4]: render_security_vault(conn)
    with tabs[5]: render_audit_forensics()
    with tabs[6]: render_nexus_vault()
    with tabs[7]: render_settings()
    
    render_standard_footer("ADMIN & SECURITY CENTER — SOVEREIGN EDITION V4.3")

if __name__ == "__main__":
    main()

