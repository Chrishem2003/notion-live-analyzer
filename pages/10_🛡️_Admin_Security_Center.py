"""
🛡️ Admin & Security Center — Sovereign Enterprise Administration & Security Command Hub (Premium)
The hardened administrative control plane consolidating real-time system diagnostics, enterprise
RBAC user management, Stripe/license billing workflows, academic student verification queues, a
genuinely encrypted credential vault with a real accumulating audit trail, compliance forensic
engines, and the Nexus 2.0 workspace suite.

Changelog vs prior version:
- FIXED (structural): `from modules.admin_guard import require_admin` was imported once *before*
  the module docstring — which meant the docstring was no longer the first statement in the file
  and so was silently discarded as `__doc__` — and then imported again later. Consolidated into
  one import, with the docstring restored as the actual first statement.
- FIXED: System Diagnostics showed hardcoded telemetry ("99.99%" uptime, "14 Threads", "0.1ms
  Latency") that never changed. Replaced with real measurements: process uptime via a
  process-lifetime resource, actual measured DB round-trip latency, real memory (psutil, with
  graceful fallback), and the real live Python thread count via `threading.active_count()`.
- FIXED (real security issue): the "Encrypted Credential & API Token Vault" claimed tokens were
  "encrypted and securely bound" but stored them as plain, unencrypted strings in session state.
  Tokens are now genuinely encrypted with `cryptography.fernet` (AES-128-CBC + HMAC under the
  hood) before being stored, and decrypted only when explicitly retrieved. Note: the encryption
  key is generated per server process for this environment — in a real production deployment,
  source it from a proper secrets manager/environment variable instead, so encrypted values
  survive restarts and work across multiple app instances.
- FIXED: the vault's "Access Audit Trail" wasn't a trail — it regenerated a single row with the
  *current* timestamp on every page render, so nothing ever accumulated. It's now a real,
  persistent, SHA-256 hash-chained log (same tamper-evident pattern used on the Home Dashboard)
  that actually accumulates every vault save/purge/retrieve event.
- ADDED: role changes and billing plan overrides are now written to that same audit ledger.
  Previously, an admin could silently reassign anyone's role or override anyone's subscription
  tier with zero trace anywhere in the system — a real gap for a "security center."
- ADDED: last-admin lockout protection — you can no longer demote the final remaining admin
  account (yourself or anyone else), which previously had no safeguard.
- FIXED (was fake): the camera tab had a "Camera Hardware Device Index" dropdown (0/1/2) that did
  nothing — Streamlit's `st.camera_input` has no device-index parameter, so selecting a value had
  zero effect on which camera was actually used. Removed the non-functional control and added an
  honest note that the browser's own camera picker governs device selection.
- NOTE: the Audit & Compliance forensic engines (statcheck, GRIM/DEGRIM, p-curve, burstiness,
  HIPAA/GDPR auditors, etc.) and the entire Nexus Vault suite call into
  `modules/audit_compliance_engine.py` and `modules/nexus_vault_engine.py`, neither of which was
  provided alongside this file. Their internal correctness could not be verified or rewritten here
  — only the page-level orchestration was audited and fixed.
"""

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))

import datetime
import hashlib
import json
import platform
import shutil
import sqlite3
import threading

import re
import numpy as np
import pandas as pd
import scipy.stats as stats
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.shared_ui import hero_card, section_header, metric_card, render_export_buttons

# ─────────────────────────────────────────────────────────────────────────
# NOTE ON THIS SECTION: the original file imported `modules.admin_guard`,
# `modules.audit_compliance_engine`, and `modules.nexus_vault_engine` — none
# of which exist in this repository (confirmed by the deployment traceback:
# `ModuleNotFoundError: No module named 'modules.admin_guard'`). Rather than
# stub these out, everything they were supposed to provide is implemented
# for real, directly in this file: real admin gating, a real (if lightweight)
# statistical-integrity toolkit, and a real Nexus Vault suite backed by
# actual SQLite tables and actual Fernet encryption. No external module
# dependency for any of it — this page is now fully self-contained.
# ─────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────
# Real admin gate (replaces modules.admin_guard.require_admin)
# ─────────────────────────────────────────────────────────────────────────
def require_admin():
    identity = st.session_state.get("user_identity", {})
    if identity.get("role") != "admin":
        st.error("🚫 Access Denied: this page requires administrator privileges.")
        st.info("If this is your account and it should be an admin, see the account-promotion instructions in `portal.py` (`SOVEREIGN_ADMIN_EMAIL`).")
        st.stop()


# ─────────────────────────────────────────────────────────────────────────
# Real statistical-integrity toolkit (replaces modules.audit_compliance_engine)
# Only the functions this page actually calls are implemented — no dead
# imports for functions that were never invoked anywhere in the original file.
# ─────────────────────────────────────────────────────────────────────────
def statcheck_consistency(test_str: str) -> dict:
    """Parses a reported inferential statistic (t/F/chi-square/r) and checks whether the reported
    p-value is mathematically consistent with the reported statistic and degrees of freedom."""
    s = test_str.strip()
    patterns = [
        (r"t\(\s*(\d+\.?\d*)\s*\)\s*=\s*(-?\d+\.?\d*)\s*,\s*p\s*[=<]\s*(\.?\d+\.?\d*)", "t"),
        (r"F\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*=\s*(\d+\.?\d*)\s*,\s*p\s*[=<]\s*(\.?\d+\.?\d*)", "F"),
        (r"[χx]2?\s*\(\s*(\d+)(?:,\s*N\s*=\s*\d+)?\s*\)\s*=\s*(\d+\.?\d*)\s*,\s*p\s*[=<]\s*(\.?\d+\.?\d*)", "chi2"),
        (r"r\(\s*(\d+)\s*\)\s*=\s*(-?\d?\.?\d*)\s*,\s*p\s*[=<]\s*(\.?\d+\.?\d*)", "r"),
    ]
    for pattern, kind in patterns:
        m = re.search(pattern, s, re.IGNORECASE)
        if not m:
            continue
        try:
            if kind == "t":
                df_val, stat_val, reported_p = float(m.group(1)), float(m.group(2)), float(m.group(3))
                computed_p = 2 * (1 - stats.t.cdf(abs(stat_val), df_val))
            elif kind == "F":
                df1, df2, stat_val, reported_p = float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))
                computed_p = 1 - stats.f.cdf(stat_val, df1, df2)
            elif kind == "chi2":
                df_val, stat_val, reported_p = float(m.group(1)), float(m.group(2)), float(m.group(3))
                computed_p = 1 - stats.chi2.cdf(stat_val, df_val)
            else:
                df_val, stat_val, reported_p = float(m.group(1)), float(m.group(2)), float(m.group(3))
                if abs(stat_val) >= 1:
                    computed_p = 0.0
                else:
                    t_val = stat_val * np.sqrt(df_val / (1 - stat_val ** 2))
                    computed_p = 2 * (1 - stats.t.cdf(abs(t_val), df_val))
            discrepancy = abs(computed_p - reported_p)
            consistent = discrepancy < 0.01 or (reported_p < 0.001 and computed_p < 0.001)
            return {
                "test_type": kind, "reported_p": reported_p, "recomputed_p": round(computed_p, 6),
                "discrepancy": round(discrepancy, 6),
                "verdict": "CONSISTENT" if consistent else "INCONSISTENT — reported p-value does not match the recomputed value for this statistic/df",
            }
        except Exception as e:
            return {"error": f"Matched a pattern but failed to evaluate it: {e}"}
    return {"error": "Could not parse a recognized format. Supported: t(df)=X,p=Y | F(df1,df2)=X,p=Y | chi2(df)=X,p=Y | r(df)=X,p=Y"}


def grim_test(reported_mean: float, n: int, decimals: int = 2) -> dict:
    """GRIM test: for integer-item data (e.g. Likert scales), a valid mean must equal some whole
    number divided by N. Flags means that are mathematically impossible for the given N."""
    if n <= 0:
        return {"error": "N must be positive."}
    target = round(reported_mean, decimals)
    closest, closest_diff, possible = None, None, False
    for total in range(0, n * 20 + 1):
        candidate = round(total / n, decimals)
        diff = abs(candidate - target)
        if closest_diff is None or diff < closest_diff:
            closest_diff, closest = diff, candidate
        if diff < (0.5 * 10 ** (-decimals)):
            possible = True
    return {
        "reported_mean": reported_mean, "n": n, "granularity_consistent": possible,
        "nearest_achievable_mean": closest,
        "verdict": "CONSISTENT — mean is achievable for this N" if possible else f"INCONSISTENT — not achievable for N={n}; nearest valid value is {closest}",
    }


def degrim_test(reported_sd: float, n: int) -> dict:
    """Lightweight plausibility check on a reported SD. Note: the full DEGRIM test additionally
    requires the reported mean's decimal precision, which this simplified check does not use."""
    if n <= 1:
        return {"error": "N must be greater than 1."}
    return {
        "reported_sd": reported_sd, "n": n,
        "verdict": "IMPLAUSIBLE — SD cannot be zero or negative" if reported_sd <= 0 else "No red flags from this simplified check (full DEGRIM needs the mean's decimal precision too).",
    }


def p_curve_analysis(pvals: list) -> dict:
    """Simonsohn/Nelson/Simmons-style p-curve: compares the share of significant p-values below
    .025 vs. between .025-.05. A right-skewed curve suggests real evidential value."""
    sig = [p for p in pvals if 0 < p < 0.05]
    if not sig:
        return {"error": "No significant p-values (< .05) provided."}
    low = sum(1 for p in sig if p < 0.025)
    high = len(sig) - low
    binom = stats.binomtest(low, len(sig), 0.5, alternative="greater")
    right_skewed = low > high
    return {
        "n_significant": len(sig), "below_025": low, "between_025_050": high,
        "binomial_p_value": round(binom.pvalue, 5),
        "verdict": "Evidential value likely present (right-skewed)" if (right_skewed and binom.pvalue < 0.05) else "Flat/left-skewed — evidential value not established; possible p-hacking or underpowered studies.",
    }


def burstiness_detector(text: str) -> dict:
    """Sentence-length variance — a heuristic signal (not proof) sometimes associated with
    AI-generated text when unusually low; human writing typically varies more."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    if len(sentences) < 3:
        return {"error": "Need at least 3 sentences."}
    lengths = [len(s.split()) for s in sentences]
    mean_len, std_len = float(np.mean(lengths)), float(np.std(lengths))
    burstiness = (std_len - mean_len) / (std_len + mean_len) if (std_len + mean_len) > 0 else 0.0
    return {
        "sentence_count": len(sentences), "mean_sentence_length": round(mean_len, 2),
        "sentence_length_std": round(std_len, 2), "burstiness_index": round(burstiness, 4),
        "interpretation": "Low variance — heuristic signal only, not proof of AI generation" if burstiness < -0.3 else "Normal/high variance — typical of human writing patterns",
    }


def perplexity_profiler(text: str) -> dict:
    """Lexical-diversity proxy (type-token ratio). NOT true language-model perplexity, which
    would require scoring against an actual LM — labeled honestly as a proxy."""
    words = re.findall(r"[a-zA-Z']+", text.lower())
    if len(words) < 5:
        return {"error": "Need at least 5 words."}
    ttr = len(set(words)) / len(words)
    return {
        "word_count": len(words), "unique_word_ratio_ttr": round(ttr, 4),
        "avg_word_length": round(float(np.mean([len(w) for w in words])), 2),
        "note": "Lexical-diversity proxy, not true LLM perplexity. Low TTR can indicate repetitive/formulaic text.",
    }


def citation_fabrication_audit(text: str) -> dict:
    """Extracts (Author, YYYY)-style in-text citations and flags basic structural anomalies
    (e.g. future publication years). A heuristic scan — does not check a real bibliography."""
    citations = re.findall(r"\(([A-Z][a-zA-Z'\-]+(?:\s*(?:&|and|et al\.?)\s*[A-Z][a-zA-Z'\-]*)?,\s*(\d{4}))\)", text)
    current_year = datetime.datetime.now().year
    flags = [f"Citation '{full}' has a future publication year ({year})." for full, year in citations if int(year) > current_year]
    return {
        "citations_found": len(citations), "citation_list": [c[0] for c in citations], "flags": flags,
        "verdict": "No structural anomalies detected" if not flags else f"{len(flags)} anomaly(ies) detected",
        "note": "Heuristic structural scan only — does not verify citations exist in a real database.",
    }


def pii_redactor(text: str) -> dict:
    patterns = {
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "phone": r"\+?\d{1,3}[\s.-]?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}",
        "ssn_like": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card_like": r"\b(?:\d[ -]*?){13,16}\b",
        "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    }
    counts, redacted = {}, text
    for label, pattern in patterns.items():
        counts[label] = len(re.findall(pattern, redacted))
        redacted = re.sub(pattern, f"[REDACTED_{label.upper()}]", redacted)
    return {"counts": counts, "redacted_text": redacted}


def hipaa_phi_audit(text: str) -> dict:
    """Heuristic scan for a pattern-matchable subset of HIPAA Safe Harbor PHI identifiers.
    Not a certified compliance tool — a starting point for manual review."""
    findings = []
    if re.search(r"\b\d{3}-\d{2}-\d{4}\b", text):
        findings.append("Possible SSN pattern detected")
    if re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text):
        findings.append("Email address detected")
    if re.search(r"\+?\d{1,3}[\s.-]?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}", text):
        findings.append("Phone number pattern detected")
    if re.search(r"\b(19|20)\d{2}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/(19|20)\d{2}\b", text):
        findings.append("Date pattern detected (birthdate/admission-date risk)")
    if re.search(r"\bMRN[:\s]*\d+\b|\bmedical record\b", text, re.IGNORECASE):
        findings.append("Medical record number reference detected")
    risk = "HIGH" if len(findings) >= 3 else ("MODERATE" if findings else "LOW")
    return {"findings": findings, "risk": risk, "note": "Heuristic Safe Harbor pattern scan — not a certified HIPAA determination."}


def sha256_block(block_id: int, prev_hash: str, payload: str, actor: str) -> dict:
    ts = datetime.datetime.utcnow().isoformat()
    content = f"{block_id}|{prev_hash}|{payload}|{actor}|{ts}"
    return {"block_id": block_id, "prev_hash": prev_hash, "payload": payload, "actor": actor, "timestamp": ts, "block_hash": hashlib.sha256(content.encode("utf-8")).hexdigest()}


def grant_compliance_matrix(required: list, fulfilled: list) -> dict:
    required_set, fulfilled_set = set(required), set(fulfilled)
    missing = sorted(required_set - fulfilled_set)
    pct = round(100 * len(required_set & fulfilled_set) / len(required_set), 1) if required_set else 100.0
    return {
        "required_count": len(required_set), "fulfilled_count": len(fulfilled_set & required_set),
        "completion_pct": pct, "missing_requirements": missing,
        "verdict": "FULLY COMPLIANT" if not missing else f"INCOMPLETE — {len(missing)} requirement(s) missing",
    }


# ─────────────────────────────────────────────────────────────────────────
# Real Nexus Vault suite (replaces modules.nexus_vault_engine) — genuine
# SQLite persistence, genuine Fernet encryption for stored files, genuine
# calendar-overlap detection, genuine (whitelisted, non-eval) formula math.
# ─────────────────────────────────────────────────────────────────────────
def _nexus_conn():
    conn = sqlite3.connect(NEXUS_DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS nexus_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, category TEXT, notes TEXT,
        size_bytes INTEGER, sha256_hash TEXT, encrypted_blob BLOB, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS nexus_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, start_dt TEXT, end_dt TEXT, location TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS nexus_meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, meeting_dt TEXT, duration_min INTEGER,
        attendees TEXT, agenda TEXT, meeting_link TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS nexus_docs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, body TEXT, version INTEGER, updated_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS nexus_sheets (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, rows_json TEXT, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS nexus_contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT, phone TEXT, company TEXT, grp TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS nexus_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, priority TEXT, due_date TEXT, status TEXT)""")
    conn.commit()
    return conn


@st.cache_resource
def _nexus_vault_key():
    """Generated once per server process. In production, source this from a secrets manager /
    environment variable instead so encrypted files survive restarts and multi-instance deploys."""
    return Fernet.generate_key()


def _encrypt_bytes(data: bytes) -> bytes:
    return Fernet(_nexus_vault_key()).encrypt(data) if CRYPTO_AVAILABLE else data


class NexusVault:
    @staticmethod
    def store_file(name, data: bytes, category, notes):
        conn = _nexus_conn()
        file_hash = hashlib.sha256(data).hexdigest()
        ts = datetime.datetime.utcnow().isoformat()
        conn.execute(
            "INSERT INTO nexus_files (name, category, notes, size_bytes, sha256_hash, encrypted_blob, created_at) VALUES (?,?,?,?,?,?,?)",
            (name, category, notes, len(data), file_hash, _encrypt_bytes(data), ts),
        )
        conn.commit()
        return {"name": name, "size_bytes": len(data), "hash": file_hash, "category": category, "created_at": ts, "encrypted": CRYPTO_AVAILABLE}

    @staticmethod
    def list_files():
        conn = _nexus_conn()
        rows = conn.execute("SELECT name, category, size_bytes, created_at FROM nexus_files ORDER BY id DESC").fetchall()
        return [{"name": r[0], "category": r[1], "size_bytes": r[2], "created_at": r[3]} for r in rows]


class NexusCalendar:
    @staticmethod
    def detect_conflicts(title, start, end):
        conn = _nexus_conn()
        rows = conn.execute("SELECT title, start_dt, end_dt FROM nexus_events").fetchall()
        return [t for t, s, e in rows if start < e and end > s]  # real interval-overlap check

    @staticmethod
    def add_event(title, start, end, location):
        conn = _nexus_conn()
        conn.execute("INSERT INTO nexus_events (title, start_dt, end_dt, location) VALUES (?,?,?,?)", (title, start, end, location))
        conn.commit()

    @staticmethod
    def all_events():
        conn = _nexus_conn()
        rows = conn.execute("SELECT title, start_dt, end_dt, location FROM nexus_events ORDER BY start_dt").fetchall()
        return [{"title": r[0], "start_dt": r[1], "end_dt": r[2], "location": r[3]} for r in rows]


class NexusMeet:
    @staticmethod
    def schedule(title, dt_iso, duration_min, attendees, agenda):
        conn = _nexus_conn()
        meeting_id = hashlib.sha256(f"{title}{dt_iso}".encode()).hexdigest()[:10]
        link = f"https://meet.internal/{meeting_id}"
        conn.execute(
            "INSERT INTO nexus_meetings (title, meeting_dt, duration_min, attendees, agenda, meeting_link) VALUES (?,?,?,?,?,?)",
            (title, dt_iso, duration_min, ",".join(attendees), agenda, link),
        )
        conn.commit()
        return {"title": title, "meeting_dt": dt_iso, "duration_min": duration_min, "attendees": attendees, "meeting_link": link}


class NexusDocs:
    @staticmethod
    def create(title, body):
        conn = _nexus_conn()
        existing = conn.execute("SELECT id, version FROM nexus_docs WHERE title = ?", (title,)).fetchone()
        ts = datetime.datetime.utcnow().isoformat()
        if existing:
            conn.execute("UPDATE nexus_docs SET body=?, version=?, updated_at=? WHERE id=?", (body, existing[1] + 1, ts, existing[0]))
        else:
            conn.execute("INSERT INTO nexus_docs (title, body, version, updated_at) VALUES (?,?,?,?)", (title, body, 1, ts))
        conn.commit()

    @staticmethod
    def list_docs():
        conn = _nexus_conn()
        rows = conn.execute("SELECT id, title, version FROM nexus_docs ORDER BY id DESC").fetchall()
        return [{"id": r[0], "title": r[1], "version": r[2]} for r in rows]

    @staticmethod
    def get(doc_id):
        conn = _nexus_conn()
        row = conn.execute("SELECT body, updated_at FROM nexus_docs WHERE id = ?", (doc_id,)).fetchone()
        return {"body": row[0], "updated_at": row[1]} if row else {"body": "", "updated_at": ""}


class NexusSheets:
    @staticmethod
    def evaluate_formula(formula: str):
        """Whitelisted SUM/AVG/MAX/MIN evaluation only — never raw eval() of arbitrary text."""
        m = re.match(r"=\s*(SUM|AVG|AVERAGE|MAX|MIN)\((.*)\)\s*$", formula.strip(), re.IGNORECASE)
        if not m:
            return formula
        func = m.group(1).upper()
        try:
            nums = [float(x.strip()) for x in m.group(2).split(",") if x.strip()]
        except ValueError:
            return "#ERROR"
        if not nums:
            return "#ERROR"
        return {"SUM": sum(nums), "AVG": sum(nums) / len(nums), "AVERAGE": sum(nums) / len(nums), "MAX": max(nums), "MIN": min(nums)}[func]

    @staticmethod
    def create(title, rows):
        conn = _nexus_conn()
        conn.execute("INSERT INTO nexus_sheets (title, rows_json, created_at) VALUES (?,?,?)", (title, json.dumps(rows), datetime.datetime.utcnow().isoformat()))
        conn.commit()


class NexusContacts:
    @staticmethod
    def add(name, email, phone, company, group):
        conn = _nexus_conn()
        conn.execute("INSERT INTO nexus_contacts (name, email, phone, company, grp) VALUES (?,?,?,?,?)", (name, email, phone, company, group))
        conn.commit()

    @staticmethod
    def list_contacts(query=""):
        conn = _nexus_conn()
        rows = conn.execute("SELECT name, email, phone, company, grp FROM nexus_contacts ORDER BY name").fetchall()
        results = [{"Name": r[0], "Email": r[1], "Phone": r[2], "Company": r[3], "Group": r[4]} for r in rows]
        if query:
            q = query.lower()
            results = [c for c in results if q in str(c).lower()]
        return results


class NexusTasks:
    @staticmethod
    def add(title, priority="MEDIUM", due_date=""):
        conn = _nexus_conn()
        conn.execute("INSERT INTO nexus_tasks (title, priority, due_date, status) VALUES (?,?,?,?)", (title, priority, due_date, "OPEN"))
        conn.commit()

    @staticmethod
    def list_tasks(status="OPEN"):
        conn = _nexus_conn()
        rows = conn.execute("SELECT id, title, priority, due_date FROM nexus_tasks WHERE status = ? ORDER BY id DESC", (status,)).fetchall()
        return [{"id": r[0], "title": r[1], "priority": r[2], "due_date": r[3]} for r in rows]

    @staticmethod
    def update_status(task_id, status):
        conn = _nexus_conn()
        conn.execute("UPDATE nexus_tasks SET status = ? WHERE id = ?", (status, task_id))
        conn.commit()


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
    section_header("💳 Enterprise Billing, Licensing & Subscription Management", "Monitor real-time subscription tiers, trial statuses, and license allocations from the shared subscription engine (modules/subscription.py + modules/billing_stripe.py).")

    from modules import subscription, billing_stripe

    conn2 = subscription.get_conn()
    subscription.init_billing_schema(conn2)
    rows = conn2.execute(
        "SELECT email, plan, status, trial_started, trial_ends, current_period_end, stripe_customer_id "
        "FROM subscriptions ORDER BY updated_at DESC"
    ).fetchall()
    conn2.close()

    status_counts, plan_counts = {}, {}
    for _, plan, status, *_ in rows:
        status_counts[status or "active"] = status_counts.get(status or "active", 0) + 1
        plan_counts[plan or "free"] = plan_counts.get(plan or "free", 0) + 1

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Accounts", len(rows))
    c2.metric("Active Trials", status_counts.get("trialing", 0))
    c3.metric("Paid & Active", status_counts.get("active", 0))
    c4.metric("Comp / Admin-Granted", status_counts.get("comp", 0))

    c5, c6, c7 = st.columns(3)
    c5.metric("Free tier", plan_counts.get("free", 0))
    c6.metric("Premium", plan_counts.get("premium", 0))
    c7.metric("Pro", plan_counts.get("pro", 0))

    if not billing_stripe.is_configured():
        st.warning(
            "⚠️ Stripe isn't fully configured. Set `STRIPE_SECRET_KEY`, the four `STRIPE_PRICE_*` "
            "variables (premium/pro × monthly/annual), and `APP_BASE_URL` to enable live checkout, "
            "the billing portal, and Stripe resync."
        )

    st.markdown("#### Registered Subscription Directory")
    if rows:
        bdf = pd.DataFrame(rows, columns=[
            "Email", "Plan", "Status", "Trial Started", "Trial Ends", "Period End", "Stripe Customer",
        ])
        st.dataframe(bdf, width='stretch', hide_index=True)
        render_export_buttons(bdf, base_name="enterprise_subscription_directory")
    else:
        st.info("ℹ️ No subscription records found.")

    st.markdown("---")

    col_override, col_resync = st.columns(2)

    with col_override:
        st.markdown("#### Manual Plan Override")
        st.caption("For comps, refunds handled outside Stripe, or support cases. Always written to the audit ledger and to `billing_events`.")
        target_email = st.text_input("Subscriber email", key="billing_target_email_upg")
        oc1, oc2 = st.columns(2)
        new_plan = oc1.selectbox("Plan", ["free", "premium", "pro"], key="billing_new_plan_upg")
        new_status = oc2.selectbox("Status", ["comp", "active", "trialing", "expired"], key="billing_new_status_upg")

        if st.button("💾 Commit Plan Override", type="primary", key="billing_apply_upg"):
            if target_email.strip():
                actor = st.session_state.get("user_identity", {}).get("email", "unknown")
                subscription.admin_override_plan(actor, target_email.strip().lower(), new_plan, new_status)
                log_admin_action(conn, "Admin Center", "BILLING_OVERRIDE",
                                  f"{target_email.strip().lower()}: plan → {new_plan}/{new_status} (by {actor})")
                st.success(f"✅ `{target_email.strip().lower()}` set to **{new_plan}/{new_status}**.")
                st.rerun()
            else:
                st.warning("⚠️ Please provide a valid subscriber email address.")

    with col_resync:
        st.markdown("#### Resync from Stripe")
        st.caption("Pulls the live subscription state straight from Stripe for one account — use this if a cancellation or renewal doesn't seem to have caught up yet.")
        resync_email = st.text_input("Subscriber email", key="billing_resync_email_upg")
        if st.button("🔄 Resync this account", key="billing_resync_btn_upg"):
            if not billing_stripe.is_configured():
                st.error("Stripe isn't configured on this deployment.")
            elif resync_email.strip():
                result = billing_stripe.reconcile_subscription(resync_email.strip().lower())
                actor = st.session_state.get("user_identity", {}).get("email", "unknown")
                if result:
                    log_admin_action(conn, "Admin Center", "BILLING_RESYNC",
                                      f"{resync_email.strip().lower()}: resynced to {result['plan']}/{result['status']} (by {actor})")
                    st.success(f"Resynced: {result['plan'].title()} ({result['status']}).")
                    st.rerun()
                else:
                    st.info("No Stripe customer/subscription found for that email.")
            else:
                st.warning("⚠️ Please provide a subscriber email address.")

    st.markdown("#### Recent billing events")
    conn4 = subscription.get_conn()
    events = conn4.execute(
        "SELECT timestamp, email, event_type, detail FROM billing_events ORDER BY id DESC LIMIT 30"
    ).fetchall()
    conn4.close()
    if events:
        edf = pd.DataFrame(events, columns=["Timestamp", "Email", "Event", "Detail"])
        st.dataframe(edf, width='stretch', hide_index=True)
    else:
        st.info("No billing events recorded yet.")


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
    st.caption("ℹ️ Implemented natively in this page (no external module dependency) — real GRIM/statcheck math, real p-curve binomial testing, regex-based PII/HIPAA pattern scanning, and SHA-256 chain blocks. Heuristic checks are labeled as such in their own output.")

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
    st.caption("ℹ️ Implemented natively in this page (no external module dependency) — real SQLite-backed persistence, real Fernet file encryption, and real calendar interval-overlap detection.")

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
        st.caption("Manages meeting records and generates a real internal link/ID per meeting. Note: this does not integrate a real video/audio conferencing backend (Zoom, Meet, etc.) — the link is a genuine unique identifier for record-keeping, not a live video call URL. Wire a real provider's API here if live video is needed.")

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
    main()ss