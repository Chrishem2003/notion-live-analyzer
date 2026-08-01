"""

import base64
import datetime
import hashlib
import io
import json
import secrets
import sqlite3
import uuid

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ============================================================================
# CHANGE_ME_FIRST — basic settings you should personalize
# ============================================================================
APP_TITLE = "Nexus Vault"
DB_PATH = "nexus_vault.db"
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"   # <-- change this, then delete nexus_vault.db once to reseed
STORAGE_PLANS_GB = {"Free (15 GB)": 15, "Plus (100 GB)": 100, "Pro (1 TB)": 1024, "Unlimited*": 10_000_000}

# ============================================================================
# OPTIONAL DEPENDENCIES — each one degrades gracefully if not installed
# ============================================================================
try:
    from fpdf import FPDF
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    from pptx import Presentation
    HAS_PPTX = True
except ImportError:
    HAS_PPTX = False

try:
    from cryptography.fernet import Fernet
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


# ============================================================================
# PAGE CONFIG + THEME  ("Vault Ledger": ink + brass, clean paper canvas)
# ============================================================================
st.set_page_config(page_title=APP_TITLE, page_icon="🔒", layout="wide", initial_sidebar_state="expanded")

BRASS = "#C99A3A"
BRASS_DARK = "#A87F2A"
INK = "#14161F"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700;800&family=Source+Serif+4:wght@400;600&family=JetBrains+Mono:wght@500&display=swap');
html, body, [class*="css"]  {{ font-family: 'Space Grotesk', sans-serif; }}
code, pre {{ font-family: 'JetBrains Mono', monospace !important; }}

.nv-header {{
    # [Fixed by launcher]     background: linear-gradient(120deg, #1e1e2f 0%, #2b2f45 60%, #3a3050 100%);
    border-radius: 18px; padding: 26px 30px; color: white; margin-bottom: 18px;
    border: 1px solid rgba(201,154,58,0.28); box-shadow: 0 10px 30px rgba(0,0,0,0.25);
}}
.nv-header h1 {{ margin: 0; font-size: 1.7rem; font-weight: 800; }}
.nv-header p {{ margin: 6px 0 0 0; opacity: 0.78; font-size: 0.92rem; }}

.nv-card {{
    background: rgba(255,255,255,0.035); backdrop-filter: blur(10px);
    border: 1px solid rgba(201,154,58,0.20); border-radius: 14px; padding: 16px 18px;
}}
.nv-card-title {{ font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.6px; color: {BRASS}; }}
.nv-card-value {{ font-size: 1.5rem; font-weight: 800; margin-top: 4px; }}

.stButton>button {{
    # [Fixed by launcher]     background: linear-gradient(120deg, #1e1e2f 0%, #2b2f45 60%, #3a3050 100%);
    border-radius: 9px; font-weight: 700; transition: all .15s ease; box-shadow: 0 3px 10px rgba(201,154,58,0.25);
}}
.stButton>button:hover {{ transform: translateY(-1px); box-shadow: 0 8px 20px rgba(201,154,58,0.35); }}

.nv-badge {{ display:inline-block; padding: 3px 10px; border-radius: 20px; font-size: 0.72rem; font-weight:700; }}
.nv-badge-live {{ background:#D1FAE5; color:#065F46; }}
.nv-badge-demo {{ background:#F1F5F9; color:#475569; }}
.nv-badge-role {{ background: rgba(201,154,58,0.15); color: {BRASS}; border: 1px solid rgba(201,154,58,0.35); }}
.nv-empty {{ text-align:center; padding: 40px 10px; color:#94A3B8; }}
</style>
""", unsafe_allow_html=True)


# ============================================================================
# DATABASE — plain sqlite3 (stdlib), parameterized queries only
# ============================================================================
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT,
        role TEXT DEFAULT 'Editor', created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT, owner TEXT,
        modified_at TEXT, deleted INTEGER DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS sheets (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, data_json TEXT, owner TEXT,
        modified_at TEXT, deleted INTEGER DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS slide_decks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, slides_json TEXT, owner TEXT,
        modified_at TEXT, deleted INTEGER DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS mail (
        id INTEGER PRIMARY KEY AUTOINCREMENT, folder TEXT, sender TEXT, recipient TEXT,
        subject TEXT, body TEXT, mode TEXT, sent_at TEXT, read INTEGER DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, folder TEXT, content_type TEXT,
        size_bytes INTEGER, data_blob BLOB, uploaded_at TEXT, deleted INTEGER DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, actor TEXT, action TEXT, status TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS automation_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, trigger_type TEXT, action_type TEXT, enabled INTEGER DEFAULT 1)""")
    conn.commit()

    # Seed a demo admin account on first run only
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                   (DEFAULT_ADMIN_USERNAME, hash_password(DEFAULT_ADMIN_PASSWORD), "Admin", now_str()))
        conn.commit()

    # Seed a couple of demo rows so the app isn't empty on first launch
    c.execute("SELECT COUNT(*) FROM documents")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO documents (title, content, owner, modified_at) VALUES (?, ?, ?, ?)",
                   ("Welcome to Nexus Vault",
                    "# Welcome\n\nThis document is stored in a real SQLite database next to this script "
                    "(nexus_vault.db) — edit it, refresh the page, and it will still be here.",
                    "admin", now_str()))
    c.execute("SELECT COUNT(*) FROM sheets")
    if c.fetchone()[0] == 0:
        demo_rows = [{"Item": "Widget A", "Cost": 10, "Qty": 5, "Total": 50},
                     {"Item": "Widget B", "Cost": 20, "Qty": 3, "Total": 60}]
        c.execute("INSERT INTO sheets (name, data_json, owner, modified_at) VALUES (?, ?, ?, ?)",
                   ("Sample Sheet", json.dumps(demo_rows), "admin", now_str()))
    c.execute("SELECT COUNT(*) FROM slide_decks")
    if c.fetchone()[0] == 0:
        demo_slides = [{"title": "Nexus Vault", "body": "Secure. Unified. Persisted.", "layout": "title"},
                       {"title": "Agenda", "body": "1. Storage\n2. Security\n3. Roadmap", "layout": "title-body"}]
        c.execute("INSERT INTO slide_decks (title, slides_json, owner, modified_at) VALUES (?, ?, ?, ?)",
                   ("Welcome Deck", json.dumps(demo_slides), "admin", now_str()))
    c.execute("SELECT COUNT(*) FROM mail")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO mail (folder, sender, recipient, subject, body, mode, sent_at) VALUES (?,?,?,?,?,?,?)",
                   ("inbox", "team@nexusvault.io", "admin", "Welcome to your persisted inbox",
                    "This message is stored in SQLite, not just browser memory.", "demo", now_str()))
    c.execute("SELECT COUNT(*) FROM automation_rules")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO automation_rules (name, trigger_type, action_type, enabled) VALUES (?,?,?,1)",
                   ("Flag large files when storage is heavy", "storage_high", "flag_largest_file"))
    conn.commit()
    conn.close()


def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_audit(actor, action, status="OK"):
    conn = get_conn()
    conn.execute("INSERT INTO audit_log (timestamp, actor, action, status) VALUES (?, ?, ?, ?)",
                 (now_str(), actor, action, status))
    conn.commit()
    conn.close()


# ============================================================================
# PASSWORD HASHING — stdlib only (hashlib + secrets), no extra install needed
# ============================================================================
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$")
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return secrets.compare_digest(check, digest)


init_db()


# ============================================================================
# SESSION STATE + LOGIN GATE
# ============================================================================
for key, default in {"logged_in": False, "username": None, "role": None,
                      "active_doc_id": None, "active_sheet_id": None, "active_deck_id": None,
                      "preview_target": None, "meeting_room": None}.items():
    if key not in st.session_state:
        st.session_state[key] = default

if not st.session_state["logged_in"]:
    left, mid, right = st.columns([1, 1.2, 1])
    with mid:
        st.markdown(f'<div class="nv-header"><h1>🔒 {APP_TITLE}</h1><p>Sign in to your workspace.</p></div>', unsafe_allow_html=True)
        with st.form("login_form"):
            u = st.text_input("Username", value="admin")
            p = st.text_input("Password", type="password", value="admin123")
            go = st.form_submit_button("Sign in", type="primary", use_container_width=True)
        if go:
            conn = get_conn()
            row = conn.execute("SELECT * FROM users WHERE username = ?", (u,)).fetchone()
            conn.close()
            if row and verify_password(p, row["password_hash"]):
                st.session_state.update(logged_in=True, username=row["username"], role=row["role"])
                log_audit(u, "LOGIN", "OK")
                st.rerun()
            else:
                st.error("Invalid username or password.")
                log_audit(u, "LOGIN_FAILED", "DENIED")
        st.caption("Demo login: **admin / admin123** — change `DEFAULT_ADMIN_PASSWORD` near the top of this "
                   "file, delete `nexus_vault.db` once, and restart to reseed with your own password.")
    st.stop()


# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.markdown(f"## 🔒 {APP_TITLE}")
    st.markdown(f'**{st.session_state["username"]}** &nbsp; <span class="nv-badge nv-badge-role">{st.session_state["role"]}</span>', unsafe_allow_html=True)
    if st.button("Sign out", use_container_width=True):
        log_audit(st.session_state["username"], "LOGOUT")
        st.session_state["logged_in"] = False
        st.rerun()
    st.markdown("---")
    nav_options = ["🏠 Home", "📁 Drive", "📄 Docs", "📊 Sheets", "🎞️ Slides", "✉️ Mail",
                    "🎥 Meetings", "⚙️ Automations", "🛡️ Security", "☁️ Storage & Backup"]
    if st.session_state["role"] == "Admin":
        nav_options.append("📋 Admin Audit Log")
    active = st.radio("Navigate", nav_options, label_visibility="collapsed")

st.markdown(f'<div class="nv-header"><h1>🔒 {APP_TITLE}</h1><p>{active} — backed by a real local database, not just browser memory.</p></div>', unsafe_allow_html=True)


def require_editor():
    if st.session_state["role"] == "Viewer":
        st.warning("Your account role is **Viewer** — read-only. Ask an Admin to upgrade your role to Editor to make changes.")
        st.stop()


# ============================================================================
# HOME
# ============================================================================
if active == "🏠 Home":
    conn = get_conn()
    counts = {
        "Files": conn.execute("SELECT COUNT(*) FROM files WHERE deleted=0").fetchone()[0],
        "Documents": conn.execute("SELECT COUNT(*) FROM documents WHERE deleted=0").fetchone()[0],
        "Sheets": conn.execute("SELECT COUNT(*) FROM sheets WHERE deleted=0").fetchone()[0],
        "Slide decks": conn.execute("SELECT COUNT(*) FROM slide_decks WHERE deleted=0").fetchone()[0],
    }
    total_bytes = conn.execute("SELECT COALESCE(SUM(size_bytes),0) FROM files WHERE deleted=0").fetchone()[0]
    conn.close()
    cols = st.columns(4)
    for col, (label, val) in zip(cols, counts.items()):
        col.markdown(f'<div class="nv-card"><div class="nv-card-title">{label}</div><div class="nv-card-value">{val}</div></div>', unsafe_allow_html=True)
    st.caption(f"Total file storage used: {total_bytes/1024:.1f} KB")
    st.info("Everything here reads from and writes to `nexus_vault.db` in this app's folder — a real "
            "file on disk, not just something held in your browser tab.")

# ============================================================================
# DRIVE
# ============================================================================
elif active == "📁 Drive":
    st.subheader("📁 Drive")
    require_editor()
    upload = st.file_uploader("Upload a file")
    if upload is not None:
        data = upload.getvalue()
        conn = get_conn()
        conn.execute("INSERT INTO files (name, folder, content_type, size_bytes, data_blob, uploaded_at) VALUES (?,?,?,?,?,?)",
                     (upload.name, "Uploads", upload.type or "", len(data), data, now_str()))
        conn.commit()
        conn.close()
        log_audit(st.session_state["username"], f"UPLOAD_FILE:{upload.name}")
        st.success(f"Uploaded {upload.name}")
        st.rerun()

    conn = get_conn()
    files = conn.execute("SELECT id, name, folder, content_type, size_bytes, uploaded_at FROM files WHERE deleted=0 ORDER BY uploaded_at DESC").fetchall()
    conn.close()
    if not files:
        st.markdown('<div class="nv-empty">📭 No files yet — upload one above.</div>', unsafe_allow_html=True)
    for f in files:
        c1, c2, c3, c4 = st.columns([4, 2, 1, 1])
        if c1.button(f["name"], key=f"prev_{f['id']}"):
            st.session_state["preview_target"] = f["id"]
        c2.caption(f"{f['size_bytes']/1024:.1f} KB · {f['uploaded_at']}")
        conn = get_conn()
        blob = conn.execute("SELECT data_blob FROM files WHERE id=?", (f["id"],)).fetchone()["data_blob"]
        conn.close()
        c3.download_button("⬇️", data=blob, file_name=f["name"], key=f"dl_{f['id']}")
        if c4.button("🗑️", key=f"del_{f['id']}"):
            conn = get_conn(); conn.execute("UPDATE files SET deleted=1 WHERE id=?", (f["id"],)); conn.commit(); conn.close()
            log_audit(st.session_state["username"], f"TRASH_FILE:{f['id']}")
            st.rerun()

    if st.session_state["preview_target"]:
        conn = get_conn()
        pf = conn.execute("SELECT * FROM files WHERE id=?", (st.session_state["preview_target"],)).fetchone()
        conn.close()
        if pf:
            st.markdown("---")
            st.markdown(f"### 👁️ {pf['name']}")
            if (pf["content_type"] or "").startswith("image/"):
                st.image(pf["data_blob"])
            elif (pf["content_type"] or "").startswith("text/") or pf["name"].endswith((".txt", ".md", ".csv", ".json", ".py")):
                st.code(pf["data_blob"].decode("utf-8", errors="ignore")[:5000])
            else:
                st.caption("No inline preview for this file type — use the download button above.")
            if st.button("Close preview"):
                st.session_state["preview_target"] = None
                st.rerun()

# ============================================================================
# DOCS
# ============================================================================
elif active == "📄 Docs":
    st.subheader("📄 Docs")
    conn = get_conn()
    docs = conn.execute("SELECT * FROM documents WHERE deleted=0 ORDER BY modified_at DESC").fetchall()
    conn.close()

    left, right = st.columns([1, 2.4])
    with left:
        st.markdown("##### Documents")
        if st.button("➕ New document", use_container_width=True):
            require_editor()
            conn = get_conn()
            cur = conn.execute("INSERT INTO documents (title, content, owner, modified_at) VALUES (?,?,?,?)",
                                ("Untitled", "", st.session_state["username"], now_str()))
            conn.commit()
            st.session_state["active_doc_id"] = cur.lastrowid
            conn.close()
            st.rerun()
        for d in docs:
            if st.button(d["title"] or "(untitled)", key=f"doc_{d['id']}", use_container_width=True):
                st.session_state["active_doc_id"] = d["id"]
                st.rerun()

    with right:
        doc = next((d for d in docs if d["id"] == st.session_state["active_doc_id"]), None)
        if doc:
            title = st.text_input("Title", value=doc["title"])
            content = st.text_area("Content (Markdown supported)", value=doc["content"], height=380)
            c1, c2, c3, c4 = st.columns(4)
            if c1.button("💾 Save", type="primary"):
                require_editor()
                conn = get_conn()
                conn.execute("UPDATE documents SET title=?, content=?, modified_at=? WHERE id=?",
                             (title, content, now_str(), doc["id"]))
                conn.commit(); conn.close()
                log_audit(st.session_state["username"], f"SAVE_DOC:{doc['id']}")
                st.toast("Saved", icon="✅")
            if c2.button("🗑️ Delete"):
                require_editor()
                conn = get_conn(); conn.execute("UPDATE documents SET deleted=1 WHERE id=?", (doc["id"],)); conn.commit(); conn.close()
                log_audit(st.session_state["username"], f"TRASH_DOC:{doc['id']}")
                st.session_state["active_doc_id"] = None
                st.rerun()
            if c3.button("📄 Export PDF"):
                if not HAS_PDF:
                    st.warning("Install `fpdf2` to enable PDF export: `pip install fpdf2`")
                else:
                    pdf = FPDF(); pdf.add_page(); pdf.set_font("Helvetica", size=12)
                    pdf.multi_cell(0, 8, txt=f"{title}\n\n{content}")
                    pdf_bytes = pdf.output(dest="S").encode("latin-1", errors="ignore")
                    st.download_button("⬇️ Download PDF", data=pdf_bytes, file_name=f"{title}.pdf")
            c4.download_button("⬇️ Export .md", data=content, file_name=f"{title}.md")
            st.caption(f"Word count: {len(content.split())}")
            with st.expander("👁️ Markdown preview"):
                st.markdown(content)
        else:
            st.markdown('<div class="nv-empty">📄 Select or create a document on the left.</div>', unsafe_allow_html=True)

# ============================================================================
# SHEETS
# ============================================================================
elif active == "📊 Sheets":
    st.subheader("📊 Sheets")
    conn = get_conn()
    sheets = conn.execute("SELECT * FROM sheets WHERE deleted=0 ORDER BY modified_at DESC").fetchall()
    conn.close()

    left, right = st.columns([1, 3])
    with left:
        st.markdown("##### Sheets")
        if st.button("➕ New sheet", use_container_width=True):
            require_editor()
            conn = get_conn()
            cur = conn.execute("INSERT INTO sheets (name, data_json, owner, modified_at) VALUES (?,?,?,?)",
                                ("Untitled Sheet", json.dumps([{"A": "", "B": ""}]), st.session_state["username"], now_str()))
            conn.commit()
            st.session_state["active_sheet_id"] = cur.lastrowid
            conn.close()
            st.rerun()
        for s in sheets:
            if st.button(s["name"], key=f"sheet_{s['id']}", use_container_width=True):
                st.session_state["active_sheet_id"] = s["id"]
                st.rerun()

    with right:
        sheet = next((s for s in sheets if s["id"] == st.session_state["active_sheet_id"]), None)
        if sheet:
            name = st.text_input("Sheet name", value=sheet["name"])

            with st.expander("📥 Import CSV (replaces this sheet's contents)"):
                uploaded_csv = st.file_uploader("Choose a CSV file", type=["csv"], key=f"csv_{sheet['id']}")
                if uploaded_csv is not None:
                    imported_df = pd.read_csv(uploaded_csv)
                    st.dataframe(imported_df, use_container_width=True)
                    if st.button("✅ Load this CSV into the sheet"):
                        require_editor()
                        conn = get_conn()
                        conn.execute("UPDATE sheets SET data_json=?, modified_at=? WHERE id=?",
                                     (json.dumps(imported_df.to_dict("records")), now_str(), sheet["id"]))
                        conn.commit(); conn.close()
                        log_audit(st.session_state["username"], f"IMPORT_CSV_SHEET:{sheet['id']}")
                        st.rerun()

            rows = json.loads(sheet["data_json"])
            df = pd.DataFrame(rows) if rows else pd.DataFrame({"A": [""]})
            edited = st.data_editor(df, num_rows="dynamic", use_container_width=True)

            c1, c2, c3 = st.columns(3)
            if c1.button("💾 Save", type="primary"):
                require_editor()
                conn = get_conn()
                conn.execute("UPDATE sheets SET name=?, data_json=?, modified_at=? WHERE id=?",
                             (name, json.dumps(edited.to_dict("records")), now_str(), sheet["id"]))
                conn.commit(); conn.close()
                log_audit(st.session_state["username"], f"SAVE_SHEET:{sheet['id']}")
                st.toast("Saved", icon="✅")
            if c2.button("🗑️ Delete sheet"):
                require_editor()
                conn = get_conn(); conn.execute("UPDATE sheets SET deleted=1 WHERE id=?", (sheet["id"],)); conn.commit(); conn.close()
                st.session_state["active_sheet_id"] = None
                st.rerun()
            c3.download_button("⬇️ Export CSV", data=edited.to_csv(index=False).encode("utf-8"), file_name=f"{name}.csv")

            numeric_cols = edited.select_dtypes(include=["number"]).columns.tolist()
            if numeric_cols:
                st.markdown("##### Aggregation")
                a1, a2, a3 = st.columns(3)
                target = a1.selectbox("Column", numeric_cols)
                op = a2.selectbox("Operation", ["SUM", "AVERAGE", "MIN", "MAX", "COUNT"])
                val = {"SUM": edited[target].sum(), "AVERAGE": edited[target].mean(),
                       "MIN": edited[target].min(), "MAX": edited[target].max(), "COUNT": edited[target].count()}[op]
                a3.metric(f"{op}({target})", f"{val:,.2f}")
                chart_type = st.radio("Chart", ["Bar", "Line"], horizontal=True)
                x_axis = edited.columns[0]
                (st.bar_chart if chart_type == "Bar" else st.line_chart)(edited.set_index(x_axis)[target])
        else:
            st.markdown('<div class="nv-empty">📊 Select or create a sheet on the left.</div>', unsafe_allow_html=True)

# ============================================================================
# SLIDES
# ============================================================================
elif active == "🎞️ Slides":
    st.subheader("🎞️ Slides")
    conn = get_conn()
    decks = conn.execute("SELECT * FROM slide_decks WHERE deleted=0 ORDER BY modified_at DESC").fetchall()
    conn.close()

    left, right = st.columns([1, 2.4])
    with left:
        st.markdown("##### Decks")
        if st.button("➕ New deck", use_container_width=True):
            require_editor()
            conn = get_conn()
            cur = conn.execute("INSERT INTO slide_decks (title, slides_json, owner, modified_at) VALUES (?,?,?,?)",
                                ("Untitled Deck", json.dumps([{"title": "Slide 1", "body": "", "layout": "title"}]),
                                 st.session_state["username"], now_str()))
            conn.commit()
            st.session_state["active_deck_id"] = cur.lastrowid
            conn.close()
            st.rerun()
        for d in decks:
            if st.button(d["title"], key=f"deck_{d['id']}", use_container_width=True):
                st.session_state["active_deck_id"] = d["id"]
                st.rerun()

    with right:
        deck = next((d for d in decks if d["id"] == st.session_state["active_deck_id"]), None)
        if deck:
            title = st.text_input("Deck title", value=deck["title"])
            slides = json.loads(deck["slides_json"])
            for i, s in enumerate(slides):
                with st.container(border=True):
                    s["title"] = st.text_input(f"Slide {i+1} title", value=s.get("title", ""), key=f"st_{deck['id']}_{i}")
                    s["body"] = st.text_area(f"Slide {i+1} body", value=s.get("body", ""), key=f"sb_{deck['id']}_{i}", height=80)

            c1, c2, c3, c4, c5 = st.columns(5)
            if c1.button("➕ Add slide"):
                require_editor()
                slides.append({"title": "New slide", "body": "", "layout": "title-body"})
                conn = get_conn()
                conn.execute("UPDATE slide_decks SET slides_json=?, modified_at=? WHERE id=?",
                             (json.dumps(slides), now_str(), deck["id"]))
                conn.commit(); conn.close()
                st.rerun()
            if len(slides) > 1 and c2.button("🗑️ Remove last"):
                require_editor()
                slides.pop()
                conn = get_conn()
                conn.execute("UPDATE slide_decks SET slides_json=?, modified_at=? WHERE id=?",
                             (json.dumps(slides), now_str(), deck["id"]))
                conn.commit(); conn.close()
                st.rerun()
            if c3.button("💾 Save", type="primary"):
                require_editor()
                conn = get_conn()
                conn.execute("UPDATE slide_decks SET title=?, slides_json=?, modified_at=? WHERE id=?",
                             (title, json.dumps(slides), now_str(), deck["id"]))
                conn.commit(); conn.close()
                log_audit(st.session_state["username"], f"SAVE_DECK:{deck['id']}")
                st.toast("Saved", icon="✅")
                st.rerun()
            if c4.button("🗑️ Delete deck"):
                require_editor()
                conn = get_conn(); conn.execute("UPDATE slide_decks SET deleted=1 WHERE id=?", (deck["id"],)); conn.commit(); conn.close()
                st.session_state["active_deck_id"] = None
                st.rerun()
            if c5.button("🎞️ Export PPTX"):
                if not HAS_PPTX:
                    st.warning("Install `python-pptx` to enable this: `pip install python-pptx`")
                else:
                    prs = Presentation()
                    title_layout, content_layout = prs.slide_layouts[0], prs.slide_layouts[1]
                    for i, s in enumerate(slides):
                        slide = prs.slides.add_slide(title_layout if i == 0 else content_layout)
                        slide.shapes.title.text = s.get("title", "")
                        if len(slide.placeholders) > 1:
                            slide.placeholders[1].text = s.get("body", "")
                    buf = io.BytesIO(); prs.save(buf)
                    st.download_button("⬇️ Download PPTX", data=buf.getvalue(), file_name=f"{title}.pptx")

            st.markdown("##### 🖥️ Preview")
            for s in slides:
                st.markdown(f"""<div style="background:{INK};color:white;border:1px solid {BRASS}44;border-radius:12px;padding:26px;margin-bottom:10px;text-align:center;">
                <h3 style="color:{BRASS};margin:0;">{s.get('title','')}</h3>
                <p style="white-space:pre-line;opacity:0.85;">{s.get('body','')}</p></div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="nv-empty">🎞️ Select or create a deck on the left.</div>', unsafe_allow_html=True)

# ============================================================================
# MAIL
# ============================================================================
elif active == "✉️ Mail":
    st.subheader("✉️ Mail")
    tab_inbox, tab_compose, tab_sent, tab_settings = st.tabs(["📥 Inbox", "✏️ Compose", "📤 Sent", "⚙️ Settings"])

    with tab_inbox:
        conn = get_conn()
        inbox = conn.execute("SELECT * FROM mail WHERE folder='inbox' ORDER BY sent_at DESC").fetchall()
        conn.close()
        if not inbox:
            st.markdown('<div class="nv-empty">📭 Inbox is empty.</div>', unsafe_allow_html=True)
        for m in inbox:
            with st.container(border=True):
                st.markdown(f"**{m['subject']}**  \n*{m['sender']} · {m['sent_at']}*")
                st.caption(m["body"][:200])

    with tab_compose:
        to = st.text_input("To")
        subject = st.text_input("Subject")
        body = st.text_area("Message", height=180)
        smtp_creds = st.session_state.get("smtp_creds", {})
        if st.button("📨 Send", type="primary"):
            mode = "demo"
            if smtp_creds.get("host") and smtp_creds.get("user") and smtp_creds.get("password"):
                try:
                    import smtplib
                    import ssl
                    from email.mime.text import MIMEText
                    msg = MIMEText(body)
                    msg["Subject"], msg["From"], msg["To"] = subject, smtp_creds["user"], to
                    with smtplib.SMTP_SSL(smtp_creds["host"], 465, context=ssl.create_default_context()) as server:
                        server.login(smtp_creds["user"], smtp_creds["password"])
                        server.sendmail(smtp_creds["user"], [to], msg.as_string())
                    mode = "live"
                except Exception as e:
                    st.error(f"SMTP send failed, saved as demo instead: {e}")
            conn = get_conn()
            conn.execute("INSERT INTO mail (folder, sender, recipient, subject, body, mode, sent_at) VALUES (?,?,?,?,?,?,?)",
                         ("sent", st.session_state["username"], to, subject, body, mode, now_str()))
            conn.commit(); conn.close()
            log_audit(st.session_state["username"], f"SEND_MAIL:{to}:{mode}")
            badge = "nv-badge-live" if mode == "live" else "nv-badge-demo"
            st.markdown(f'<span class="nv-badge {badge}">{mode.upper()}</span> Message recorded.', unsafe_allow_html=True)
            if mode == "demo":
                st.caption("No SMTP credentials set in the Settings tab, so this wasn't actually delivered — just stored.")

    with tab_sent:
        conn = get_conn()
        sent = conn.execute("SELECT * FROM mail WHERE folder='sent' ORDER BY sent_at DESC").fetchall()
        conn.close()
        if not sent:
            st.markdown('<div class="nv-empty">📤 Nothing sent yet.</div>', unsafe_allow_html=True)
        for m in sent:
            badge = "nv-badge-live" if m["mode"] == "live" else "nv-badge-demo"
            with st.container(border=True):
                st.markdown(f'<span class="nv-badge {badge}">{m["mode"].upper()}</span> **{m["subject"]}** → {m["recipient"]}', unsafe_allow_html=True)
                st.caption(m["sent_at"])

    with tab_settings:
        st.caption("Optional: enter your own SMTP details (e.g. a Gmail app password) to actually send mail "
                   "this session. Nothing here is saved to disk — you'll re-enter it each time you restart the app.")
        host = st.text_input("SMTP host", value=st.session_state.get("smtp_creds", {}).get("host", "smtp.gmail.com"))
        user = st.text_input("SMTP username / email", value=st.session_state.get("smtp_creds", {}).get("user", ""))
        pw = st.text_input("SMTP app password", type="password")
        if st.button("Save SMTP settings for this session"):
            st.session_state["smtp_creds"] = {"host": host, "user": user, "password": pw}
            st.success("Saved for this session (not written to disk).")

# ============================================================================
# MEETINGS — real embedded video calls via the free public Jitsi Meet service
# ============================================================================
elif active == "🎥 Meetings":
    st.subheader("🎥 Meetings")
    st.caption("Real video rooms via Jitsi Meet — free, no account or API key needed. Works once this app "
               "is running with internet access (it will not work from an offline sandbox).")
    if not st.session_state["meeting_room"]:
        st.session_state["meeting_room"] = f"nexusvault-{uuid.uuid4().hex[:8]}"
    room = st.session_state["meeting_room"]
    room_url = f"https://meet.jit.si/{room}"
    st.text_input("Meeting link (share this with others)", value=room_url, disabled=True)
    c1, c2 = st.columns(2)
    if c1.button("🔁 New room"):
        st.session_state["meeting_room"] = f"nexusvault-{uuid.uuid4().hex[:8]}"
        st.rerun()
    join = c2.toggle("🎥 Join now")
    if join:
        components.iframe(room_url, height=560)
    else:
        st.markdown('<div class="nv-empty">🎥 Toggle "Join now" to load the live video call.</div>', unsafe_allow_html=True)

# ============================================================================
# AUTOMATIONS
# ============================================================================
elif active == "⚙️ Automations":
    st.subheader("⚙️ Automations")
    conn = get_conn()
    rules = conn.execute("SELECT * FROM automation_rules").fetchall()
    conn.close()
    for r in rules:
        st.markdown(f"**{r['name']}** — {'✅ enabled' if r['enabled'] else '⏸️ disabled'}")

    if st.button("▶️ Run automations now", type="primary"):
        conn = get_conn()
        total = conn.execute("SELECT COALESCE(SUM(size_bytes),0) FROM files WHERE deleted=0").fetchone()[0]
        results = []
        if total > 5 * 1024 * 1024:
            biggest = conn.execute("SELECT name, size_bytes FROM files WHERE deleted=0 ORDER BY size_bytes DESC LIMIT 1").fetchone()
            if biggest:
                results.append(f"Largest file is '{biggest['name']}' ({biggest['size_bytes']/1024:.1f} KB) — consider archiving.")
        else:
            results.append("Storage usage is low — no action needed.")
        conn.close()
        log_audit(st.session_state["username"], "RUN_AUTOMATIONS")
        for line in results:
            st.write(f"- {line}")

# ============================================================================
# SECURITY
# ============================================================================
elif active == "🛡️ Security":
    st.subheader("🛡️ Security")
    if not HAS_CRYPTO:
        st.warning("Install `cryptography` to enable encrypt/decrypt: `pip install cryptography`")
    else:
        if "fernet_key" not in st.session_state:
            st.session_state["fernet_key"] = Fernet.generate_key()
        cipher = Fernet(st.session_state["fernet_key"])
        mode = st.radio("Operation", ["Encrypt", "Decrypt"], horizontal=True)
        text = st.text_area("Text")
        if mode == "Encrypt" and st.button("Encrypt"):
            st.code(cipher.encrypt(text.encode()).decode())
        if mode == "Decrypt" and st.button("Decrypt"):
            try:
                st.code(cipher.decrypt(text.encode()).decode())
            except Exception:
                st.error("Invalid ciphertext for this session's key (the key resets each time the app restarts).")

# ============================================================================
# STORAGE & BACKUP
# ============================================================================
elif active == "☁️ Storage & Backup":
    st.subheader("☁️ Storage & Backup")
    plan = st.selectbox("Plan (label only — this app doesn't enforce a hard limit)", list(STORAGE_PLANS_GB.keys()))
    limit_gb = STORAGE_PLANS_GB[plan]
    conn = get_conn()
    total_bytes = conn.execute("SELECT COALESCE(SUM(size_bytes),0) FROM files WHERE deleted=0").fetchone()[0]
    conn.close()
    used_gb = total_bytes / (1024 ** 3)
    st.progress(min(used_gb / limit_gb, 1.0) if limit_gb else 0)
    st.caption(f"{used_gb:.4f} GB used of {plan}")
    if "Unlimited" in plan:
        st.caption("*'Unlimited' here just means a very high label — actual space is still bounded by your "
                   "computer's or server's real disk. No storage plan is infinite in the literal sense.")

    st.markdown("---")
    st.markdown("##### 💾 Full backup")
    st.caption("Downloads every document, sheet, and slide deck as one JSON file you can keep as a backup.")
    conn = get_conn()
    backup = {
        "documents": [dict(r) for r in conn.execute("SELECT * FROM documents WHERE deleted=0").fetchall()],
        "sheets": [dict(r) for r in conn.execute("SELECT * FROM sheets WHERE deleted=0").fetchall()],
        "slide_decks": [dict(r) for r in conn.execute("SELECT * FROM slide_decks WHERE deleted=0").fetchall()],
        "mail": [dict(r) for r in conn.execute("SELECT * FROM mail").fetchall()],
    }
    conn.close()
    st.download_button("⬇️ Download backup (.json)", data=json.dumps(backup, indent=2, default=str),
                        file_name=f"nexus_vault_backup_{datetime.date.today()}.json", mime="application/json")

# ============================================================================
# ADMIN AUDIT LOG (Admin role only)
# ============================================================================
elif active == "📋 Admin Audit Log":
    st.subheader("📋 Admin Audit Log")
    if st.session_state["role"] != "Admin":
        st.error("Admins only.")
        st.stop()
    conn = get_conn()
    logs = conn.execute("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 200").fetchall()
    conn.close()
    st.dataframe(pd.DataFrame([dict(r) for r in logs]), use_container_width=True, hide_index=True)


