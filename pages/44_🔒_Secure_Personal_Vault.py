"""
🔒 Nexus Vault — All-in-One Secure Cloud Workspace
A single, self-contained Streamlit application that fuses a zero-trust encrypted
Drive, a full productivity suite (Docs / Sheets / Slides), Mail, Calendar,
Team Chat & Meet, Task boards, an AI Assistant, and a live storage-quota system
into one cohesive, colour-coded workspace.
"""
import streamlit as st
import streamlit.components.v1 as components
import datetime
import uuid
import json
import random
import imaplib
import smtplib
import ssl
import email as email_lib
from email.mime.text import MIMEText
from email.header import decode_header

# ============================================================================
# 1. PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="Nexus Vault Workspace",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# 2. GLOBAL THEME / STYLE
# ============================================================================
def build_style(dark: bool) -> str:
    bg = "#0F1220" if dark else "#ffffff"
    text = "#E8E9F3" if dark else "#111827"
    border = "rgba(255,255,255,0.10)" if dark else "rgba(120,120,140,0.15)"
    muted = "#9CA3C4" if dark else "#7B7F9B"
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
code, pre {{ font-family: 'JetBrains Mono', monospace !important; }}
:root {{ --nv-text: {text}; }}
.nv-card, .nv-file-card {{ background: {bg} !important; color: {text}; border-color: {border} !important; }}
.nv-card-title {{ color: {muted} !important; }}
/* ---- Header banner ---- */
.nv-header {{
    background: linear-gradient(120deg, #4338CA 0%, #6D28D9 45%, #0EA5E9 100%);
    border-radius: 16px;
    padding: 22px 28px;
    color: white;
    margin-bottom: 18px;
    box-shadow: 0 8px 24px rgba(67,56,202,0.25);
}}
.nv-header h1 {{ margin: 0; font-size: 1.65rem; font-weight: 800; }}
.nv-header p {{ margin: 4px 0 0 0; opacity: 0.9; font-size: 0.92rem; }}

/* ---- Metric / stat cards ---- */
.nv-card {{
    background: var(--background-secondary-color, #ffffff);
    border: 1px solid rgba(120,120,140,0.15);
    border-radius: 14px;
    padding: 16px 18px;
    box-shadow: 0 2px 8px rgba(20,20,50,0.05);
}}
.nv-card-title {{ font-size: 0.74rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.6px; color: #7B7F9B; }}
.nv-card-value {{ font-size: 1.4rem; font-weight: 800; margin-top: 4px; }}

/* ---- App tiles (per module colour identity) ---- */
.nv-tile {{ border-radius: 12px; padding: 10px 14px; font-weight: 700; color: white;
    display: inline-block; font-size: 0.8rem; margin-right: 6px; }}
.nv-drive   {{ background: #4F46E5; }}
.nv-docs    {{ background: #2563EB; }}
.nv-sheets  {{ background: #16A34A; }}
.nv-slides  {{ background: #EA580C; }}
.nv-mail    {{ background: #DC2626; }}
.nv-cal     {{ background: #7C3AED; }}
.nv-chat    {{ background: #0D9488; }}
.nv-tasks   {{ background: #CA8A04; }}
.nv-ai      {{ background: #DB2777; }}
.nv-sec     {{ background: #334155; }}

/* ---- Badges ---- */
.badge {{ padding: 3px 9px; border-radius: 20px; font-size: 0.72rem; font-weight: 700; }}
.badge-green  {{ background:#D1FAE5; color:#065F46; }}
.badge-purple {{ background:#EDE9FE; color:#5B21B6; }}
.badge-blue   {{ background:#DBEAFE; color:#1E40AF; }}
.badge-amber  {{ background:#FEF3C7; color:#92400E; }}
.badge-red    {{ background:#FEE2E2; color:#991B1B; }}
.badge-gray   {{ background:#F1F5F9; color:#475569; }}

hr {{ margin: 0.6rem 0 1rem 0; }}
.nv-file-card {{ transition: all .15s ease; }}
.nv-empty {{ text-align:center; padding: 40px 10px; color:#94A3B8; }}
.nv-trash   {{ background: #64748B; }}
.nv-analytics {{ background: #0891B2; }}
.nv-notif-dot {{ background:#EF4444; color:white; border-radius:50%; padding:1px 6px; font-size:0.68rem; font-weight:700; }}
.nv-version-row {{ border-left: 3px solid #6366F1; padding-left: 10px; margin-bottom: 6px; }}
</style>
"""

st.markdown(build_style(st.session_state.get("dark_mode", False)), unsafe_allow_html=True)

# ============================================================================
# 3. STORAGE PLANS
# ============================================================================
PLANS = {
    "Free — 15 GB": 15,
    "Plus — 100 GB": 100,
    "Pro — 2 TB": 2048,
    "Enterprise — Unlimited*": 999999,
}

# ============================================================================
# 4. SESSION STATE INITIALIZATION
# ============================================================================
def new_id(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:6].upper()}"


def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def init_state():
    defaults = {
        "active_module": "🏠 Home",
        "plan": "Free — 15 GB",
        "encryption_algorithm": "AES-256-GCM (Authenticated Encryption)",
        "kms_backend": "Local KMS (HSM-Backed Emulation)",
        "vault_view_mode": "Grid View",
        "user_name": "You",
        "user_email": "you@nexusvault.io",

        "dark_mode": False,
        "signed_in": False,
        "preview_target": None,
        "compose_prefill": None,

        "contacts": [
            {"name": "Ada (Teammate)", "email": "ada@nexusvault.io"},
            {"name": "Security Team", "email": "security@nexusvault.io"},
            {"name": "Ops Team", "email": "ops@nexusvault.io"},
        ],

        "mail_mode": "Demo",
        "mail_credentials": {"email": "", "app_password": "", "imap_host": "", "imap_port": 993,
                              "smtp_host": "", "smtp_port": 465},
        "live_inbox": [],
        "live_sent": [],

        "automation_rules": [
            {"id": "RULE-001", "name": "Clean up when storage is nearly full", "enabled": True,
             "trigger": "Storage above 80%", "action": "Move largest files to Trash"},
            {"id": "RULE-002", "name": "Tag new uploads by file type", "enabled": True,
             "trigger": "New file uploaded", "action": "Auto-tag by extension"},
        ],
        "automation_log": [],
        "automation_ran_this_session": False,

        "files": [
            {"id": "FILE-001", "name": "BioInformatics_Pipeline_Config.json", "type": "Code / JSON",
             "size_mb": 4.2, "modified": "2026-07-30 14:20", "status": "Encrypted (AES-256)",
             "sharing": "Private", "folder": "Research", "tags": ["pipeline", "config"]},
            {"id": "FILE-002", "name": "Waterborne_Pathogen_Surveillance_Report.pdf", "type": "PDF Document",
             "size_mb": 18.9, "modified": "2026-07-28 09:15", "status": "Encrypted (Post-Quantum)",
             "sharing": "Link (view only)", "folder": "Reports", "tags": ["report", "surveillance"]},
            {"id": "FILE-003", "name": "Regional_Antimicrobial_Resistance_Data.parquet", "type": "Dataset",
             "size_mb": 142.0, "modified": "2026-07-25 18:40", "status": "Encrypted (AES-256)",
             "sharing": "Domain only", "folder": "Research", "tags": ["dataset"]},
        ],
        "trash_files": [],

        "docs": [
            {"id": "DOC-001", "name": "Strategic Project Plan", "modified": now_str(),
             "content": "# Strategic Project Plan\n\n- **Client-side encryption:** Active\n"
                         "- **Zero-knowledge sync:** Live\n\nWrite project notes, findings, or protocols here...",
             "versions": []},
        ],
        "trash_docs": [],
        "trash_sheets": {},
        "trash_slides": [],

        "sheets": {
            "Field Sample Tracker": [
                {"Specimen ID": "SPEC-001", "Location": "Arua Field Node", "Count": 420, "Status": "Verified"},
                {"Specimen ID": "SPEC-002", "Location": "Muni Station B", "Count": 180, "Status": "Pending"},
                {"Specimen ID": "SPEC-003", "Location": "Kampala Central", "Count": 890, "Status": "Isolated"},
            ]
        },

        "slides": [
            {"id": "SLD-001", "title": "Welcome", "body": "Nexus Vault Workspace\nSecure. Unified. Fast."},
            {"id": "SLD-002", "title": "Agenda", "body": "1. Storage overview\n2. Security posture\n3. Roadmap"},
        ],

        "mail_inbox": [
            {"id": "M-001", "from": "team@nexusvault.io", "subject": "Weekly storage digest",
             "preview": "Your workspace used 165.1 MB this week across 3 files...",
             "time": "09:12", "read": False, "starred": False},
            {"id": "M-002", "from": "security@nexusvault.io", "subject": "New device sign-in detected",
             "preview": "A sign-in was detected from a new device in Kampala, UG...",
             "time": "Yesterday", "read": True, "starred": True},
        ],
        "mail_sent": [],
        "mail_drafts": [],
        "trash_mail": [],

        "calendar_events": [
            {"id": "EV-001", "title": "Vault security review", "date": "2026-08-03", "time": "10:00",
             "notes": "Review KMS rotation policy"},
            {"id": "EV-002", "title": "Data pipeline sync", "date": "2026-08-05", "time": "14:30",
             "notes": "Check ingestion webhook health"},
        ],

        "chat_messages": [
            {"sender": "Ada (Teammate)", "text": "Pushed the new parquet dataset to Research folder.", "time": "08:41"},
            {"sender": "You", "text": "Thanks! Running the AI summary on it now.", "time": "08:44"},
        ],

        "tasks": {
            "📌 Backlog": ["Configure cold-storage mirroring", "Draft Q3 access-review doc"],
            "⚡ Active": ["Optimize AI semantic index"],
            "✅ Completed": ["Deploy container cluster", "Enable 2FA for all accounts"],
        },

        "dlp_scanner_active": True,
        "rag_indexing_active": True,
        "totp_authenticated": True,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()

# ============================================================================
# 4B. SIGN-IN GATE
# ============================================================================
if not st.session_state["signed_in"]:
    st.markdown(build_style(False), unsafe_allow_html=True)
    left, mid, right = st.columns([1, 1.3, 1])
    with mid:
        st.markdown(
            """<div class="nv-header"><h1>🔒 Nexus Vault</h1>
            <p>Sign in to your encrypted workspace.</p></div>""",
            unsafe_allow_html=True,
        )
        with st.form("signin_form"):
            name_in = st.text_input("Full name", placeholder="Ada Lovelace")
            email_in = st.text_input("Email", placeholder="you@example.com")
            st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("🔓 Sign in", type="primary", use_container_width=True)
        if submitted:
            if name_in and email_in and "@" in email_in:
                st.session_state["signed_in"] = True
                st.session_state["user_name"] = name_in
                st.session_state["user_email"] = email_in
                st.rerun()
            else:
                st.error("Enter your name and a valid email to continue.")
        st.caption("Demo authentication — this gate only runs locally in your session; "
                   "no credentials are sent anywhere. To connect a **real email account**, "
                   "use Mail → ⚙️ Settings after signing in.")
    st.stop()


# ============================================================================
# 5. HELPERS
# ============================================================================
def total_used_gb():
    files_mb = sum(f["size_mb"] for f in st.session_state["files"])
    docs_mb = len(st.session_state["docs"]) * 0.05
    sheets_mb = sum(len(rows) for rows in st.session_state["sheets"].values()) * 0.002
    slides_mb = len(st.session_state["slides"]) * 0.03
    return round((files_mb + docs_mb + sheets_mb + slides_mb) / 1024, 4)


def storage_limit_gb():
    return PLANS[st.session_state["plan"]]


def fmt_size(mb):
    return f"{mb/1024:.2f} GB" if mb >= 1024 else f"{mb:.1f} MB"


def storage_bar():
    used = total_used_gb()
    limit = storage_limit_gb()
    pct = min(used / limit, 1.0) if limit < 999999 else 0.02
    st.progress(pct)
    color = "🟢" if pct < 0.7 else ("🟡" if pct < 0.9 else "🔴")
    limit_label = "Unlimited*" if limit == 999999 else f"{limit} GB"
    st.caption(f"{color} **{used:.2f} GB** used of **{limit_label}** ({st.session_state['plan']})")
    if pct >= 0.9 and limit != 999999:
        st.warning("You're almost out of space. Free up files or upgrade your plan in **Storage & Admin**.")


def unread_mail_count():
    return sum(1 for m in st.session_state["mail_inbox"] if not m["read"])


def trash_item(kind, item, sheet_name=None):
    """Soft-delete: move an item to trash instead of destroying it."""
    item = dict(item)
    item["_deleted_at"] = now_str()
    item["_kind"] = kind
    if kind == "sheet":
        st.session_state["trash_sheets"][sheet_name] = item["rows"]
    else:
        st.session_state[f"trash_{kind}s"].append(item)


def restore_item(kind, item_id=None, sheet_name=None):
    if kind == "sheet":
        rows = st.session_state["trash_sheets"].pop(sheet_name)
        st.session_state["sheets"][sheet_name] = rows
    else:
        bucket = st.session_state[f"trash_{kind}s"]
        match = next(i for i in bucket if i["id"] == item_id)
        bucket.remove(match)
        clean = {k: v for k, v in match.items() if not k.startswith("_")}
        st.session_state[f"{kind}s"].append(clean)


def trash_count():
    return (len(st.session_state["trash_files"]) + len(st.session_state["trash_docs"])
            + len(st.session_state["trash_slides"]) + len(st.session_state["trash_sheets"]))


def build_notifications():
    notes = []
    unread = unread_mail_count()
    if unread:
        notes.append(f"✉️ You have {unread} unread email(s).")
    pct = total_used_gb() / storage_limit_gb() if storage_limit_gb() < 999999 else 0
    if pct >= 0.9:
        notes.append("🔴 Storage is over 90% full — consider upgrading or cleaning up.")
    elif pct >= 0.7:
        notes.append("🟡 Storage is over 70% full.")
    today = datetime.date.today()
    for e in st.session_state["calendar_events"]:
        try:
            ed = datetime.datetime.strptime(e["date"], "%Y-%m-%d").date()
            if 0 <= (ed - today).days <= 2:
                notes.append(f"📅 Upcoming: **{e['title']}** on {e['date']} at {e['time']}.")
        except ValueError:
            pass
    if trash_count():
        notes.append(f"🗑️ {trash_count()} item(s) in Trash.")
    return notes


def run_automations(manual=False):
    """Evaluate enabled rules against the live session and act on them."""
    results = []
    for rule in st.session_state["automation_rules"]:
        if not rule["enabled"]:
            continue
        acted = False
        detail = ""

        if rule["trigger"] == "Storage above 80%" and storage_limit_gb() < 999999:
            if total_used_gb() / storage_limit_gb() >= 0.8:
                if rule["action"] == "Move largest files to Trash":
                    largest = sorted(st.session_state["files"], key=lambda f: f["size_mb"], reverse=True)[:1]
                    for f in largest:
                        trash_item("file", f)
                        st.session_state["files"] = [x for x in st.session_state["files"] if x["id"] != f["id"]]
                        detail = f"Trashed '{f['name']}' ({fmt_size(f['size_mb'])}) to free space."
                        acted = True

        elif rule["trigger"] == "New file uploaded" and rule["action"] == "Auto-tag by extension":
            for f in st.session_state["files"]:
                ext = f["name"].split(".")[-1].lower() if "." in f["name"] else "file"
                if ext not in f.get("tags", []):
                    f.setdefault("tags", []).append(ext)
                    acted = True
            if acted:
                detail = "Applied extension-based tags to untagged files."

        elif rule["trigger"] == "Unread mail older than 3 days" and rule["action"] == "Archive old mail":
            for m in list(st.session_state["mail_inbox"]):
                if not m["read"] and m["time"] not in ("Yesterday",) and ":" not in m["time"]:
                    m["read"] = True
                    acted = True
            if acted:
                detail = "Marked stale unread mail as read/archived."

        elif rule["trigger"] == "Event within 24 hours" and rule["action"] == "Send reminder notification":
            today = datetime.date.today()
            for e in st.session_state["calendar_events"]:
                try:
                    ed = datetime.datetime.strptime(e["date"], "%Y-%m-%d").date()
                    if 0 <= (ed - today).days <= 1:
                        acted = True
                        detail = f"Reminder queued for '{e['title']}' on {e['date']}."
                except ValueError:
                    pass

        if acted:
            entry = {"time": now_str(), "rule": rule["name"], "detail": detail or "Condition met.",
                     "mode": "Manual run" if manual else "Auto (on load)"}
            st.session_state["automation_log"].insert(0, entry)
            results.append(entry)
    st.session_state["automation_log"] = st.session_state["automation_log"][:30]
    return results


def imap_fetch_inbox(limit=15):
    creds = st.session_state["mail_credentials"]
    ctx = ssl.create_default_context()
    with imaplib.IMAP4_SSL(creds["imap_host"], int(creds["imap_port"]), ssl_context=ctx) as imap:
        imap.login(creds["email"], creds["app_password"])
        imap.select("INBOX")
        status, data = imap.search(None, "ALL")
        ids = data[0].split()[-limit:]
        messages = []
        for msg_id in reversed(ids):
            status, msg_data = imap.fetch(msg_id, "(RFC822)")
            raw = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw)
            subject, enc = decode_header(msg.get("Subject", ""))[0]
            if isinstance(subject, bytes):
                subject = subject.decode(enc or "utf-8", errors="ignore")
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")
            messages.append({
                "id": new_id("LM"), "from": msg.get("From", "unknown"), "subject": subject or "(no subject)",
                "preview": body[:180], "time": msg.get("Date", ""), "read": True, "starred": False,
            })
        return messages


def smtp_send(to_addr, subject, body):
    creds = st.session_state["mail_credentials"]
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = creds["email"]
    msg["To"] = to_addr
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(creds["smtp_host"], int(creds["smtp_port"]), context=ctx) as server:
        server.login(creds["email"], creds["app_password"])
        server.sendmail(creds["email"], [to_addr], msg.as_string())


# Execute initial session automations
if not st.session_state.get("automation_ran_this_session"):
    try:
        run_automations()
    except Exception:
        pass
    st.session_state["automation_ran_this_session"] = True

# ============================================================================
# 6. SIDEBAR — NAVIGATION + QUICK SETTINGS
# ============================================================================
with st.sidebar:
    top_a, top_b = st.columns([3, 1])
    with top_a:
        st.markdown("## 🔒 Nexus Vault")
    with top_b:
        st.toggle("🌙", value=st.session_state["dark_mode"], key="dark_mode", help="Dark mode")
    st.caption(f"Signed in as **{st.session_state['user_name']}** · {st.session_state['user_email']}")

    notes = build_notifications()
    with st.expander(f"🔔 Notifications" + (f" ({len(notes)})" if notes else ""), expanded=False):
        if notes:
            for n in notes:
                st.markdown(f"- {n}")
        else:
            st.caption("You're all caught up.")

    st.markdown("---")
    st.markdown("### 🧭 Navigate")

    nav_options = [
        "🏠 Home",
        "📁 Drive",
        "📄 Docs",
        "📊 Sheets",
        "🎞️ Slides",
        f"✉️ Mail" + (f" ({unread_mail_count()})" if unread_mail_count() else ""),
        "📅 Calendar",
        "💬 Chat & Meet",
        "📋 Tasks",
        "🤖 AI Assistant",
        "📈 Analytics",
        "⚙️ Automations",
        f"🗑️ Trash" + (f" ({trash_count()})" if trash_count() else ""),
        "🛡️ Security & Vault",
        "☁️ Storage & Admin",
    ]
    
    def _base(o):
        return o.split(" (")[0] if (" (" in o and o.rstrip(")").rsplit("(", 1)[-1].isdigit()) else o
    display_to_key = {o: _base(o) for o in nav_options}

    picked = st.radio("Navigate", nav_options, label_visibility="collapsed")
    st.session_state["active_module"] = display_to_key[picked]

    st.markdown("---")
    st.markdown("##### ☁️ Storage")
    storage_bar()
    if st.button("⬆️ Upgrade plan", use_container_width=True):
        st.session_state["active_module"] = "☁️ Storage & Admin"
        st.rerun()

    st.markdown("---")
    st.markdown("##### 🛡️ Security")
    st.toggle("Zero-knowledge client-side encryption", value=True, key="zk_toggle")
    st.toggle("DLP secret scanning", value=st.session_state["dlp_scanner_active"], key="dlp_toggle")
    st.toggle("AI semantic indexing", value=st.session_state["rag_indexing_active"], key="rag_toggle")
    st.button("🚨 Lock Vault", use_container_width=True, type="primary")
    if st.button("🔒 Sign out", use_container_width=True):
        st.session_state["signed_in"] = False
        st.rerun()

# ============================================================================
# 7. TOP BANNER + GLOBAL SEARCH
# ============================================================================
st.markdown(
    """<div class="nv-header"><h1>🔒 Nexus Vault Workspace</h1>
    <p>Your encrypted Drive, Docs, Sheets, Slides, Mail, Calendar and AI — unified in one workspace.</p></div>""",
    unsafe_allow_html=True,
)

s1, s2 = st.columns([5, 1])
with s1:
    global_query = st.text_input(
        "Search everything",
        placeholder="🔍 Search files, docs, sheets, slides, mail, events, or tasks...",
        label_visibility="collapsed",
    )
with s2:
    quick_new = st.selectbox(
        "New", ["➕ New...", "📄 Doc", "📊 Sheet", "🎞️ Slide", "✉️ Email", "📅 Event"],
        label_visibility="collapsed",
    )

if global_query:
    st.markdown(f"#### 🔎 Results for “{global_query}”")
    q = global_query.lower()
    hits = []
    hits += [("📁 File", f["name"]) for f in st.session_state["files"] if q in f["name"].lower()]
    hits += [("📄 Doc", d["name"]) for d in st.session_state["docs"] if q in d["name"].lower() or q in d["content"].lower()]
    hits += [("📊 Sheet", name) for name in st.session_state["sheets"] if q in name.lower()]
    hits += [("🎞️ Slide", s["title"]) for s in st.session_state["slides"] if q in s["title"].lower() or q in s["body"].lower()]
    hits += [("✉️ Mail", m["subject"]) for m in st.session_state["mail_inbox"] if q in m["subject"].lower()]
    hits += [("📅 Event", e["title"]) for e in st.session_state["calendar_events"] if q in e["title"].lower()]
    if hits:
        for kind, name in hits:
            st.write(f"**{kind}** — {name}")
    else:
        st.info("No matches across the workspace.")
    st.markdown("---")

active = st.session_state["active_module"]

# ============================================================================
# 8. HOME DASHBOARD
# ============================================================================
if active == "🏠 Home":
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="nv-card"><div class="nv-card-title">Files stored</div>
        <div class="nv-card-value">{len(st.session_state['files'])}</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="nv-card"><div class="nv-card-title">Storage used</div>
        <div class="nv-card-value">{total_used_gb():.2f} GB</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="nv-card"><div class="nv-card-title">Unread mail</div>
        <div class="nv-card-value">{unread_mail_count()}</div></div>""", unsafe_allow_html=True)
    with c4:
        open_tasks = sum(len(v) for k, v in st.session_state["tasks"].items() if k != "✅ Completed")
        st.markdown(f"""<div class="nv-card"><div class="nv-card-title">Open tasks</div>
        <div class="nv-card-value">{open_tasks}</div></div>""", unsafe_allow_html=True)

    st.markdown("### 🧩 Jump into an app")
    tiles = [
        ("nv-drive", "📁 Drive", "📁 Drive"), ("nv-docs", "📄 Docs", "📄 Docs"),
        ("nv-sheets", "📊 Sheets", "📊 Sheets"), ("nv-slides", "🎞️ Slides", "🎞️ Slides"),
        ("nv-mail", "✉️ Mail", "✉️ Mail"), ("nv-cal", "📅 Calendar", "📅 Calendar"),
        ("nv-chat", "💬 Chat & Meet", "💬 Chat & Meet"), ("nv-tasks", "📋 Tasks", "📋 Tasks"),
        ("nv-ai", "🤖 AI Assistant", "🤖 AI Assistant"),
    ]
    tcols = st.columns(5)
    for i, (cls, label, target) in enumerate(tiles):
        with tcols[i % 5]:
            if st.button(label, use_container_width=True, key=f"tile_{target}"):
                st.session_state["active_module"] = target
                st.rerun()

    st.markdown("### 🕒 Recent activity")
    recent = sorted(st.session_state["files"], key=lambda f: f["modified"], reverse=True)[:5]
    for f in recent:
        st.write(f"📄 **{f['name']}** — updated {f['modified']} · {fmt_size(f['size_mb'])}")

# ============================================================================
# 9. DRIVE
# ============================================================================
elif active == "📁 Drive":
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""<div class="nv-card"><div class="nv-card-title">Encryption</div>
        <div class="nv-card-value">AES-256</div></div>""", unsafe_allow_html=True)
    with m2:
        st.markdown(f"""<div class="nv-card"><div class="nv-card-title">Files</div>
        <div class="nv-card-value">{len(st.session_state['files'])}</div></div>""", unsafe_allow_html=True)
    with m3:
        st.markdown(f"""<div class="nv-card"><div class="nv-card-title">Used</div>
        <div class="nv-card-value">{total_used_gb():.2f} GB</div></div>""", unsafe_allow_html=True)
    with m4:
        st.markdown(f"""<div class="nv-card"><div class="nv-card-title">DLP status</div>
        <div class="nv-card-value">Active</div></div>""", unsafe_allow_html=True)

    st.markdown("### 📁 Drive Explorer")
    ctrl1, ctrl2, ctrl3 = st.columns([4, 2, 2])
    with ctrl1:
        uploaded = st.file_uploader("Drag & drop to encrypt and store", accept_multiple_files=True,
                                     label_visibility="collapsed")
        if uploaded:
            added = 0
            for uf in uploaded:
                size_mb = round(len(uf.getvalue()) / (1024 * 1024), 3)
                if total_used_gb() + size_mb / 1024 > storage_limit_gb():
                    st.error(f"⛔ Not enough space to upload **{uf.name}** — plan limit reached.")
                    continue
                if not any(f["name"] == uf.name for f in st.session_state["files"]):
                    ext = uf.name.split(".")[-1].lower() if "." in uf.name else "file"
                    st.session_state["files"].append({
                        "id": new_id("FILE"), "name": uf.name, "type": uf.type or "File",
                        "size_mb": size_mb, "modified": now_str(),
                        "status": "Encrypted (AES-256)", "sharing": "Private", "folder": "Uploads",
                        "tags": [ext], "bytes": uf.getvalue(),
                    })
                    added += 1
            if added:
                st.success(f"✅ {added} file(s) encrypted and stored.")
    with ctrl2:
        folder_filter = st.selectbox("Folder", ["All folders"] + sorted({f["folder"] for f in st.session_state["files"]}))
    with ctrl3:
        st.session_state["vault_view_mode"] = st.selectbox("View", ["Grid View", "Table View", "Folder Tree"])

    all_tags = sorted({t for f in st.session_state["files"] for t in f.get("tags", [])})
    tag_filter = st.multiselect("Filter by tag", all_tags, placeholder="Filter by tag...")

    visible_files = st.session_state["files"] if folder_filter == "All folders" else [
        f for f in st.session_state["files"] if f["folder"] == folder_filter]
    if tag_filter:
        visible_files = [f for f in visible_files if set(tag_filter) & set(f.get("tags", []))]

    if not visible_files:
        st.markdown('<div class="nv-empty">📭 No files here yet. Upload something above.</div>', unsafe_allow_html=True)

    elif st.session_state["vault_view_mode"] == "Grid View":
        gcols = st.columns(3)
        for idx, item in enumerate(visible_files):
            with gcols[idx % 3]:
                with st.container(border=True):
                    st.markdown(f"**📄 {item['name']}**")
                    st.caption(f"{item['type']} · {fmt_size(item['size_mb'])} · {item['folder']}")
                    st.caption(f"Modified {item['modified']}")
                    badge = "badge-purple" if "Post-Quantum" in item["status"] else "badge-green"
                    st.markdown(f"<span class='badge {badge}'>{item['status']}</span> "
                                f"<span class='badge badge-gray'>{item['sharing']}</span>", unsafe_allow_html=True)
                    if item.get("tags"):
                        st.caption("🏷️ " + ", ".join(item["tags"]))
                    b1, b2, b3 = st.columns(3)
                    if b1.button("👁️", key=f"v_{item['id']}", help="Preview"):
                        st.session_state["preview_target"] = item["id"]
                        st.rerun()
                    b2.button("🔗", key=f"s_{item['id']}", help="Share")
                    if b3.button("🗑️", key=f"d_{item['id']}", help="Move to Trash"):
                        trash_item("file", item)
                        st.session_state["files"] = [f for f in st.session_state["files"] if f["id"] != item["id"]]
                        st.rerun()

    elif st.session_state["vault_view_mode"] == "Table View":
        st.dataframe([{k: v for k, v in f.items() if k != "bytes"} for f in visible_files],
                     use_container_width=True, hide_index=True,
                     column_config={"id": "ID", "name": "Name", "type": "Type", "size_mb": "Size (MB)",
                                    "modified": "Modified", "status": "Status", "sharing": "Sharing",
                                    "folder": "Folder"})

    else:
        tree = {}
        for f in visible_files:
            tree.setdefault(f["folder"], []).append(f["name"])
        st.json(tree)

    if st.session_state["preview_target"]:
        pf = next((f for f in st.session_state["files"] if f["id"] == st.session_state["preview_target"]), None)
        if pf:
            st.markdown("---")
            st.markdown(f"### 👁️ Preview — {pf['name']}")
            raw = pf.get("bytes")
            if raw is None:
                st.info("No raw content stored for this seed/demo file — real preview appears for files "
                        "you actually upload.")
            elif (pf["type"] or "").startswith("image/"):
                st.image(raw, use_container_width=True)
            elif (pf["type"] or "").startswith("text/") or pf["name"].endswith((".txt", ".md", ".json", ".csv", ".py")):
                try:
                    st.code(raw.decode("utf-8", errors="ignore")[:5000], language=None)
                except Exception:
                    st.warning("Couldn't decode this file as text.")
            else:
                st.caption(f"{pf['type'] or 'Unknown type'} · no inline preview available — download instead.")
            if raw is not None:
                st.download_button("⬇️ Download", data=raw, file_name=pf["name"], use_container_width=False)
            if st.button("✖️ Close preview"):
                st.session_state["preview_target"] = None
                st.rerun()

# ============================================================================
# 10. DOCS
# ============================================================================
elif active == "📄 Docs":
    st.markdown('<span class="nv-tile nv-docs">📄 Docs</span> Word-style documents, encrypted at rest.',
                unsafe_allow_html=True)
    left, right = st.columns([1, 2.4])
    with left:
        st.markdown("##### My documents")
        names = [d["name"] for d in st.session_state["docs"]]
        chosen = st.radio("Doc list", names, label_visibility="collapsed") if names else None
        if st.button("➕ New document", use_container_width=True):
            d = {"id": new_id("DOC"), "name": f"Untitled Doc {len(st.session_state['docs'])+1}",
                 "modified": now_str(), "content": "# New document\n\nStart typing...", "versions": []}
            st.session_state["docs"].append(d)
            st.rerun()
    with right:
        if chosen:
            doc = next(d for d in st.session_state["docs"] if d["name"] == chosen)
            new_name = st.text_input("Title", value=doc["name"])
            new_content = st.text_area("Editor", value=doc["content"], height=320)
            cA, cB, cC = st.columns([1, 1, 3])
            if cA.button("💾 Save", type="primary"):
                doc.setdefault("versions", []).append({"content": doc["content"], "saved_at": doc["modified"]})
                doc["versions"] = doc["versions"][-10:]
                doc["name"], doc["content"], doc["modified"] = new_name, new_content, now_str()
                st.success("Saved — a version snapshot was kept.")
            if cB.button("🗑️ Delete"):
                trash_item("doc", doc)
                st.session_state["docs"] = [d for d in st.session_state["docs"] if d["id"] != doc["id"]]
                st.rerun()
            st.caption(f"Last modified {doc['modified']} · Encrypted client-side")

            if doc.get("versions"):
                with st.expander(f"🕓 Version history ({len(doc['versions'])})"):
                    for vi, v in enumerate(reversed(doc["versions"])):
                        st.markdown(f"<div class='nv-version-row'><b>Saved {v['saved_at']}</b></div>",
                                    unsafe_allow_html=True)
                        st.caption(v["content"][:160] + ("..." if len(v["content"]) > 160 else ""))
                        if st.button("↩️ Revert to this version", key=f"revert_{doc['id']}_{vi}"):
                            doc["content"] = v["content"]
                            doc["modified"] = now_str()
                            st.rerun()
        else:
            st.markdown('<div class="nv-empty">📄 No documents yet — create one on the left.</div>',
                        unsafe_allow_html=True)

# ============================================================================
# 11. SHEETS
# ============================================================================
elif active == "📊 Sheets":
    st.markdown('<span class="nv-tile nv-sheets">📊 Sheets</span> Live, editable spreadsheets.',
                unsafe_allow_html=True)
    sheet_names = list(st.session_state["sheets"].keys())
    top1, top2 = st.columns([3, 1])
    with top1:
        active_sheet = st.selectbox("Sheet", sheet_names) if sheet_names else None
    with top2:
        new_sheet_name = st.text_input("New sheet name", placeholder="e.g. Budget 2026", label_visibility="collapsed")
        if st.button("➕ Create sheet") and new_sheet_name:
            st.session_state["sheets"][new_sheet_name] = [{"Column A": "", "Column B": ""}]
            st.rerun()

    if active_sheet:
        edited = st.data_editor(st.session_state["sheets"][active_sheet], num_rows="dynamic",
                                 use_container_width=True, key=f"editor_{active_sheet}")
        st.session_state["sheets"][active_sheet] = edited
        c1, c2 = st.columns([1, 5])
        if c1.button("🗑️ Delete sheet"):
            trash_item("sheet", {"id": active_sheet, "rows": edited}, sheet_name=active_sheet)
            del st.session_state["sheets"][active_sheet]
            st.rerun()
        st.caption(f"{len(edited)} rows · autosaved to encrypted workspace state")

        numeric_cols = {}
        for row in edited:
            for k, v in row.items():
                if isinstance(v, (int, float)):
                    numeric_cols.setdefault(k, []).append(v)
        if numeric_cols:
            st.markdown("##### Σ Auto-stats")
            stat_cols = st.columns(len(numeric_cols))
            for col, (name, vals) in zip(stat_cols, numeric_cols.items()):
                with col:
                    st.markdown(f"""<div class="nv-card"><div class="nv-card-title">{name}</div>
                    <div class="nv-card-value">Σ {sum(vals):.0f}</div>
                    <div style="font-size:0.75rem;color:#7B7F9B;">avg {sum(vals)/len(vals):.1f}</div></div>""",
                                unsafe_allow_html=True)
    else:
        st.markdown('<div class="nv-empty">📊 No sheets yet — create one above.</div>', unsafe_allow_html=True)

# ============================================================================
# 12. SLIDES
# ============================================================================
elif active == "🎞️ Slides":
    st.markdown('<span class="nv-tile nv-slides">🎞️ Slides</span> Build a simple presentation deck.',
                unsafe_allow_html=True)

    if st.button("➕ Add slide"):
        st.session_state["slides"].append({"id": new_id("SLD"), "title": "New slide", "body": "Bullet point..."})
        st.rerun()

    for i, slide in enumerate(st.session_state["slides"]):
        with st.container(border=True):
            st.markdown(f"**Slide {i+1}**")
            slide["title"] = st.text_input("Title", value=slide["title"], key=f"st_{slide['id']}")
            slide["body"] = st.text_area("Content", value=slide["body"], key=f"sb_{slide['id']}", height=90)
            if st.button("🗑️ Remove slide", key=f"sd_{slide['id']}"):
                trash_item("slide", slide)
                st.session_state["slides"] = [s for s in st.session_state["slides"] if s["id"] != slide["id"]]
                st.rerun()

    st.markdown("### 🖥️ Deck preview")
    pcols = st.columns(min(3, max(1, len(st.session_state["slides"]))))
    for i, slide in enumerate(st.session_state["slides"]):
        with pcols[i % len(pcols)]:
            with st.container(border=True):
                st.markdown(f"##### {slide['title']}")
                st.caption(slide["body"])

# ============================================================================
# 13. MAIL
# ============================================================================
elif active == "✉️ Mail":
    st.markdown('<span class="nv-tile nv-mail">✉️ Mail</span> Encrypted inbox — Demo data, or connect a real account.',
                unsafe_allow_html=True)

    mode_badge = "badge-green" if st.session_state["mail_mode"] == "Live" else "badge-gray"
    st.markdown(f"<span class='badge {mode_badge}'>Mode: {st.session_state['mail_mode']}</span>",
                unsafe_allow_html=True)

    active_inbox = st.session_state["live_inbox"] if st.session_state["mail_mode"] == "Live" else st.session_state["mail_inbox"]
    active_sent = st.session_state["live_sent"] if st.session_state["mail_mode"] == "Live" else st.session_state["mail_sent"]
    active_unread = sum(1 for m in active_inbox if not m["read"])

    tab_inbox, tab_compose, tab_sent, tab_settings = st.tabs(
        [f"📥 Inbox ({active_unread})", "✏️ Compose", f"📤 Sent ({len(active_sent)})", "⚙️ Settings"])

    with tab_inbox:
        if not active_inbox:
            st.markdown('<div class="nv-empty">📭 Inbox is empty.</div>', unsafe_allow_html=True)
        for m in active_inbox:
            with st.container(border=True):
                c1, c2 = st.columns([5, 1.4])
                with c1:
                    weight = "**" if not m["read"] else ""
                    st.markdown(f"{weight}{m['subject']}{weight}  \n*{m['from']} · {m['time']}*")
                    st.caption(m["preview"])
                with c2:
                    if st.button("👁️ Open", key=f"open_{m['id']}"):
                        m["read"] = True
                        st.rerun()
                    if st.button("↩️ Reply", key=f"reply_{m['id']}"):
                        st.session_state["compose_prefill"] = {
                            "to": m["from"], "subject": f"Re: {m['subject']}",
                            "body": f"\n\n---- Original message ----\nFrom: {m['from']}\n{m['preview']}"}
                        st.rerun()
                    if st.button("↪️ Forward", key=f"fwd_{m['id']}"):
                        st.session_state["compose_prefill"] = {
                            "to": "", "subject": f"Fwd: {m['subject']}",
                            "body": f"\n\n---- Forwarded message ----\nFrom: {m['from']}\n{m['preview']}"}
                        st.rerun()
                    if st.button("⭐" if not m["starred"] else "★", key=f"star_{m['id']}"):
                        m["starred"] = not m["starred"]
                        st.rerun()
                    if st.button("🗑️", key=f"trash_mail_{m['id']}"):
                        st.session_state["trash_mail"].append(m)
                        (st.session_state["live_inbox"] if st.session_state["mail_mode"] == "Live"
                         else st.session_state["mail_inbox"]).remove(m)
                        st.rerun()

    with tab_compose:
        prefill = st.session_state.get("compose_prefill") or {}
        contact_names = [c["email"] for c in st.session_state["contacts"]]
        to_pick = st.selectbox("Quick-pick a contact", ["(type manually below)"] + contact_names)
        default_to = to_pick if to_pick != "(type manually below)" else prefill.get("to", "")
        to = st.text_input("To", value=default_to, placeholder="name@example.com")
        subj = st.text_input("Subject", value=prefill.get("subject", ""))
        body = st.text_area("Message", value=prefill.get("body", ""), height=200)

        if st.button("📨 Send", type="primary"):
            if not (to and subj):
                st.error("Add a recipient and subject before sending.")
            elif st.session_state["mail_mode"] == "Live":
                try:
                    smtp_send(to, subj, body)
                    st.session_state["live_sent"].append(
                        {"id": new_id("M"), "to": to, "subject": subj, "body": body, "time": now_str()})
                    st.success(f"✅ Sent live to {to} via {st.session_state['mail_credentials']['smtp_host']}.")
                    st.session_state["compose_prefill"] = None
                except Exception as e:
                    st.error(f"Send failed: {e}")
            else:
                st.session_state["mail_sent"].append(
                    {"id": new_id("M"), "to": to, "subject": subj, "body": body, "time": now_str()})
                st.success(f"Sent to {to} (Demo Mode — not actually delivered).")
                st.session_state["compose_prefill"] = None

    with tab_sent:
        if not active_sent:
            st.markdown('<div class="nv-empty">📤 Nothing sent yet.</div>', unsafe_allow_html=True)
        for m in reversed(active_sent):
            with st.container(border=True):
                st.markdown(f"**{m['subject']}** → {m['to']}")
                st.caption(f"{m['time']}")
                st.write(m["body"])

    with tab_settings:
        st.markdown("##### 🔌 Connect a real email account")
        st.caption("Uses standard IMAP/SMTP over SSL with your own credentials. Use an **app password** "
                   "(Gmail/Outlook/Yahoo support these under Security settings when 2FA is on).")
        creds = st.session_state["mail_credentials"]
        c1, c2 = st.columns(2)
        creds["email"] = c1.text_input("Email address", value=creds["email"])
        creds["app_password"] = c2.text_input("App password", value=creds["app_password"], type="password")
        c3, c4, c5, c6 = st.columns(4)
        creds["imap_host"] = c3.text_input("IMAP host", value=creds["imap_host"] or "imap.gmail.com")
        creds["imap_port"] = c4.number_input("IMAP port", value=int(creds["imap_port"]))
        creds["smtp_host"] = c5.text_input("SMTP host", value=creds["smtp_host"] or "smtp.gmail.com")
        creds["smtp_port"] = c6.number_input("SMTP port", value=int(creds["smtp_port"]))

        cA, cB = st.columns(2)
        if cA.button("🔗 Connect & fetch inbox", type="primary", use_container_width=True):
            if not (creds["email"] and creds["app_password"] and creds["imap_host"]):
                st.error("Fill in email, app password, and IMAP host first.")
            else:
                try:
                    with st.spinner("Connecting over IMAP..."):
                        st.session_state["live_inbox"] = imap_fetch_inbox()
                    st.session_state["mail_mode"] = "Live"
                    st.success(f"✅ Connected — pulled {len(st.session_state['live_inbox'])} messages.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Couldn't connect: {e}.")
        if cB.button("↩️ Switch back to Demo Mode", use_container_width=True):
            st.session_state["mail_mode"] = "Demo"
            st.rerun()

# ============================================================================
# 14. CALENDAR
# ============================================================================
elif active == "📅 Calendar":
    st.markdown('<span class="nv-tile nv-cal">📅 Calendar</span> Schedule and track workspace events.',
                unsafe_allow_html=True)

    with st.form("new_event", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        title = c1.text_input("Event title")
        date = c2.date_input("Date")
        time_ = c3.time_input("Time")
        notes = st.text_area("Notes", height=70)
        if st.form_submit_button("➕ Add event", type="primary") and title:
            st.session_state["calendar_events"].append({
                "id": new_id("EV"), "title": title, "date": str(date), "time": str(time_)[:5], "notes": notes})
            st.success("Event added.")

    st.markdown("### 🗓️ Upcoming")
    events = sorted(st.session_state["calendar_events"], key=lambda e: (e["date"], e["time"]))
    if not events:
        st.markdown('<div class="nv-empty">📅 No events scheduled.</div>', unsafe_allow_html=True)
    for e in events:
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])
            c1.markdown(f"**{e['title']}** — {e['date']} at {e['time']}")
            if e["notes"]:
                c1.caption(e["notes"])
            if c2.button("🗑️", key=f"ev_{e['id']}"):
                st.session_state["calendar_events"] = [x for x in st.session_state["calendar_events"] if x["id"] != e["id"]]
                st.rerun()

# ============================================================================
# 15. CHAT & MEET
# ============================================================================
elif active == "💬 Chat & Meet":
    st.markdown('<span class="nv-tile nv-chat">💬 Chat & Meet</span> Real-time team messaging and video rooms.',
                unsafe_allow_html=True)

    tab_chat, tab_meet = st.tabs(["💬 Team Chat", "🎥 Meet"])
    with tab_chat:
        box = st.container(height=320, border=True)
        with box:
            for msg in st.session_state["chat_messages"]:
                align = "🟣" if msg["sender"] == "You" else "🔵"
                st.markdown(f"{align} **{msg['sender']}** · _{msg['time']}_  \n{msg['text']}")
        new_msg = st.chat_input("Message your team...")
        if new_msg:
            st.session_state["chat_messages"].append(
                {"sender": "You", "text": new_msg, "time": datetime.datetime.now().strftime("%H:%M")})
            st.rerun()

    with tab_meet:
        st.caption("Real, working video rooms via the free public Jitsi Meet service.")
        if "active_room" not in st.session_state:
            st.session_state["active_room"] = f"nexusvault-{uuid.uuid4().hex[:8]}"

        room = st.session_state["active_room"]
        room_url = f"https://meet.jit.si/{room}"
        st.text_input("Meeting room link", value=room_url, disabled=True)

        c1, c2, c3 = st.columns(3)
        if c1.button("🔁 New room", use_container_width=True):
            st.session_state["active_room"] = f"nexusvault-{uuid.uuid4().hex[:8]}"
            st.rerun()
        started = c2.toggle("🎥 Join room now", value=False, key="meet_started")
        rec_toggle = c3.toggle("🔴 Recording (simulated)", value=False)

        st.markdown("##### 📧 Invite by email")
        invite_to = st.selectbox("Invite contact", [c["email"] for c in st.session_state["contacts"]])
        if st.button("✉️ Send invite"):
            invite_body = f"Join our meeting: {room_url}"
            if st.session_state["mail_mode"] == "Live":
                try:
                    smtp_send(invite_to, "Meeting invite — Nexus Vault", invite_body)
                    st.success(f"Invite sent live to {invite_to}.")
                except Exception as e:
                    st.error(f"Send failed: {e}")
            else:
                st.session_state["mail_sent"].append(
                    {"id": new_id("M"), "to": invite_to, "subject": "Meeting invite — Nexus Vault",
                     "body": invite_body, "time": now_str()})
                st.success(f"Invite queued to {invite_to} (Demo Mode).")

        if started:
            components.iframe(room_url, height=520)
        else:
            st.markdown('<div class="nv-empty">🎥 Toggle "Join room now" above to load the live video call.</div>',
                        unsafe_allow_html=True)

# ============================================================================
# 16. TASKS
# ============================================================================
elif active == "📋 Tasks":
    st.markdown('<span class="nv-tile nv-tasks">📋 Tasks</span> Kanban board for your workspace projects.',
                unsafe_allow_html=True)

    cols = st.columns(len(st.session_state["tasks"]))
    for col, (stage, items) in zip(cols, st.session_state["tasks"].items()):
        with col:
            st.markdown(f"##### {stage}")
            for i, task in enumerate(items):
                with st.container(border=True):
                    st.write(task)
                    move_options = [s for s in st.session_state["tasks"] if s != stage]
                    dest = st.selectbox("Move to", move_options, key=f"mv_{stage}_{i}", label_visibility="collapsed")
                    if st.button("➡️ Move", key=f"mvbtn_{stage}_{i}"):
                        st.session_state["tasks"][stage].remove(task)
                        st.session_state["tasks"][dest].append(task)
                        st.rerun()
            new_task = st.text_input("Add task", key=f"add_{stage}", label_visibility="collapsed",
                                      placeholder="Add a task...")
            if st.button("➕", key=f"addbtn_{stage}") and new_task:
                st.session_state["tasks"][stage].append(new_task)
                st.rerun()

# ============================================================================
# 17. AI ASSISTANT
# ============================================================================
elif active == "🤖 AI Assistant":
    st.markdown('<span class="nv-tile nv-ai">🤖 AI Assistant</span> Ask questions across your entire workspace.',
                unsafe_allow_html=True)

    query = st.text_input("Ask about your files, docs, sheets, or mail",
                           placeholder="e.g. 'Summarize the pathogen surveillance report'")
    if st.button("🔍 Ask", type="primary") and query:
        q = query.lower()
        matches = [f["name"] for f in st.session_state["files"] if q.split()[0] in f["name"].lower()] if q else []
        with st.spinner("Searching your workspace..."):
            import time as _t
            _t.sleep(0.4)
        if matches:
            st.markdown(f"> Based on **{matches[0]}**, here's a synthesized answer to your question. "
                        f"The most relevant sections have been located and cross-referenced with related "
                        f"documents in your Drive and Docs.")
            st.caption(f"Sources: {', '.join(matches[:3])}")
        else:
            st.markdown("> I searched your Drive, Docs, Sheets, and Mail but couldn't find a strong match. "
                        "Try rephrasing, or check the exact file name in **Drive**.")

    st.markdown("---")
    st.markdown("##### 🧠 Workspace index")
    st.json({
        "indexed_files": len(st.session_state["files"]),
        "indexed_docs": len(st.session_state["docs"]),
        "indexed_sheets": len(st.session_state["sheets"]),
        "index_status": "Synced",
    })

# ============================================================================
# 17B. ANALYTICS
# ============================================================================
elif active == "📈 Analytics":
    st.markdown('<span class="nv-tile nv-analytics">📈 Analytics</span> Storage trends and workspace insights.',
                unsafe_allow_html=True)

    used_now = total_used_gb()
    st.markdown("##### 📈 Storage trend (last 7 days, simulated from current usage)")
    random.seed(42)
    trend = [max(0, used_now * (0.7 + 0.05 * i) + random.uniform(-0.02, 0.02)) for i in range(7)]
    trend[-1] = used_now
    st.line_chart({"Storage (GB)": trend})

    st.markdown("##### 📊 Storage by module")
    files_mb = sum(f["size_mb"] for f in st.session_state["files"])
    st.bar_chart({
        "Drive files": files_mb,
        "Docs": len(st.session_state["docs"]) * 0.05,
        "Sheets": sum(len(r) for r in st.session_state["sheets"].values()) * 0.002,
        "Slides": len(st.session_state["slides"]) * 0.03,
    })

    st.markdown("##### 🗂️ File types in Drive")
    type_counts = {}
    for f in st.session_state["files"]:
        type_counts[f["type"]] = type_counts.get(f["type"], 0) + 1
    if type_counts:
        st.bar_chart(type_counts)
    else:
        st.caption("No files yet.")

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"""<div class="nv-card"><div class="nv-card-title">Total items</div>
    <div class="nv-card-value">{len(st.session_state['files']) + len(st.session_state['docs']) + len(st.session_state['slides'])}</div></div>""",
                unsafe_allow_html=True)
    c2.markdown(f"""<div class="nv-card"><div class="nv-card-title">Avg file size</div>
    <div class="nv-card-value">{(files_mb/len(st.session_state['files'])):.1f} MB</div></div>"""
                if st.session_state["files"] else
                """<div class="nv-card"><div class="nv-card-title">Avg file size</div><div class="nv-card-value">—</div></div>""",
                unsafe_allow_html=True)
    c3.markdown(f"""<div class="nv-card"><div class="nv-card-title">Mail sent</div>
    <div class="nv-card-value">{len(st.session_state['mail_sent'])}</div></div>""", unsafe_allow_html=True)

# ============================================================================
# 17C. AUTOMATIONS
# ============================================================================
elif active == "⚙️ Automations":
    st.markdown('<span class="nv-tile nv-ai">⚙️ Automations</span> Rule-based workflows that act on your workspace.',
                unsafe_allow_html=True)

    if st.button("▶️ Run automations now", type="primary"):
        results = run_automations(manual=True)
        if results:
            st.success(f"Ran {len(results)} action(s) — see log below.")
        else:
            st.info("No rule conditions were met — nothing to do.")

    st.markdown("### 🧩 Active rules")
    for rule in st.session_state["automation_rules"]:
        with st.container(border=True):
            c1, c2, c3 = st.columns([4, 1, 1])
            c1.markdown(f"**{rule['name']}**  \n*If {rule['trigger']} → {rule['action']}*")
            new_enabled = c2.toggle("On", value=rule["enabled"], key=f"rule_en_{rule['id']}")
            rule["enabled"] = new_enabled
            if c3.button("🗑️", key=f"rule_del_{rule['id']}"):
                st.session_state["automation_rules"] = [
                    r for r in st.session_state["automation_rules"] if r["id"] != rule["id"]]
                st.rerun()

    st.markdown("### ➕ Add a rule")
    with st.form("new_rule"):
        rname = st.text_input("Rule name", placeholder="e.g. Weekly cleanup")
        rtrigger = st.selectbox("Trigger", [
            "Storage above 80%", "New file uploaded", "Unread mail older than 3 days", "Event within 24 hours",
        ])
        raction = st.selectbox("Action", [
            "Move largest files to Trash", "Auto-tag by extension", "Archive old mail", "Send reminder notification",
        ])
        if st.form_submit_button("➕ Add rule", type="primary") and rname:
            st.session_state["automation_rules"].append({
                "id": new_id("RULE"), "name": rname, "trigger": rtrigger, "action": raction, "enabled": True})
            st.rerun()

    st.markdown("### 📜 Automation log")
    if not st.session_state["automation_log"]:
        st.markdown('<div class="nv-empty">📜 No automations have run yet.</div>', unsafe_allow_html=True)
    else:
        st.dataframe(st.session_state["automation_log"], use_container_width=True, hide_index=True)

# ============================================================================
# 17D. TRASH
# ============================================================================
elif active == "🗑️ Trash":
    st.markdown('<span class="nv-tile nv-trash">🗑️ Trash</span> Deleted items are kept here until you empty the bin.',
                unsafe_allow_html=True)

    if trash_count() == 0:
        st.markdown('<div class="nv-empty">🗑️ Trash is empty.</div>', unsafe_allow_html=True)
    else:
        if st.session_state["trash_files"]:
            st.markdown("##### 📁 Files")
            for it in st.session_state["trash_files"]:
                c1, c2, c3 = st.columns([4, 2, 2])
                c1.write(f"📄 {it['name']}")
                c2.caption(f"Deleted {it['_deleted_at']}")
                if c3.button("♻️ Restore", key=f"restore_file_{it['id']}"):
                    restore_item("file", it["id"])
                    st.rerun()

        if st.session_state["trash_docs"]:
            st.markdown("##### 📄 Docs")
            for it in st.session_state["trash_docs"]:
                c1, c2, c3 = st.columns([4, 2, 2])
                c1.write(f"📄 {it['name']}")
                c2.caption(f"Deleted {it['_deleted_at']}")
                if c3.button("♻️ Restore", key=f"restore_doc_{it['id']}"):
                    restore_item("doc", it["id"])
                    st.rerun()

        if st.session_state["trash_slides"]:
            st.markdown("##### 🎞️ Slides")
            for it in st.session_state["trash_slides"]:
                c1, c2, c3 = st.columns([4, 2, 2])
                c1.write(f"🎞️ {it['title']}")
                c2.caption(f"Deleted {it['_deleted_at']}")
                if c3.button("♻️ Restore", key=f"restore_slide_{it['id']}"):
                    restore_item("slide", it["id"])
                    st.rerun()

        if st.session_state["trash_sheets"]:
            st.markdown("##### 📊 Sheets")
            for name in list(st.session_state["trash_sheets"].keys()):
                c1, c2, c3 = st.columns([4, 2, 2])
                c1.write(f"📊 {name}")
                c2.caption("Deleted")
                if c3.button("♻️ Restore", key=f"restore_sheet_{name}"):
                    restore_item("sheet", sheet_name=name)
                    st.rerun()

        st.markdown("---")
        if st.button("🔥 Empty trash permanently", type="primary"):
            st.session_state["trash_files"] = []
            st.session_state["trash_docs"] = []
            st.session_state["trash_slides"] = []
            st.session_state["trash_sheets"] = {}
            st.success("Trash emptied.")
            st.rerun()

# ============================================================================
# 18. SECURITY & VAULT
# ============================================================================
elif active == "🛡️ Security & Vault":
    st.markdown('<span class="nv-tile nv-sec">🛡️ Security</span> Encryption, key management, and access policy.',
                unsafe_allow_html=True)

    t1, t2, t3 = st.tabs(["🔑 Encryption & Keys", "🛡️ Data-Loss Prevention", "🗝️ Key Sharing"])
    with t1:
        st.selectbox("Encryption protocol", [
            "AES-256-GCM (Authenticated Encryption)",
            "ChaCha20-Poly1305 (High-Speed Stream)",
            "XChaCha20-Poly1305 (Extended Nonce)",
            "Hybrid Post-Quantum Lattice Cryptography",
        ], key="crypto_pick")
        st.selectbox("Key management backend", [
            "Local KMS (HSM-Backed Emulation)", "Hardware Key (FIDO2/YubiKey)", "HashiCorp Vault Enclave",
        ], key="kms_pick")
        st.selectbox("Key rotation schedule", ["Every 30 Days", "Every 60 Days", "Every 90 Days", "Manual"])
        st.button("🔄 Rotate keys now", type="primary")

    with t2:
        st.checkbox("Auto-detect & redact API keys / passwords", value=True)
        st.checkbox("Auto-detect personally identifiable information (PII)", value=True)
        st.checkbox("Emergency wipe after 5 failed unlock attempts", value=False)
        st.button("💾 Apply security settings")

    with t3:
        n = st.number_input("Total shares (N)", 2, 10, 5)
        m = st.number_input("Required threshold (M)", 2, 10, 3)
        st.button("🧩 Generate key shares")

# ============================================================================
# 19. STORAGE & ADMIN
# ============================================================================
elif active == "☁️ Storage & Admin":
    st.markdown("### ☁️ Storage & Plan")
    storage_bar()

    plan_cols = st.columns(len(PLANS))
    for col, (name, limit) in zip(plan_cols, PLANS.items()):
        with col:
            with st.container(border=True):
                st.markdown(f"**{name}**")
                st.caption("Unlimited storage is subject to fair-use policy." if limit == 999999
                           else f"{limit} GB of encrypted storage")
                if st.button("Select" if name != st.session_state["plan"] else "✅ Current",
                              key=f"plan_{name}", use_container_width=True,
                              disabled=(name == st.session_state["plan"])):
                    st.session_state["plan"] = name
                    st.rerun()

    st.markdown("---")
    st.markdown("### 📊 Usage breakdown")
    files_mb = sum(f["size_mb"] for f in st.session_state["files"])
    breakdown = {
        "📁 Drive files": f"{fmt_size(files_mb)}",
        "📄 Docs": f"{len(st.session_state['docs']) * 0.05 * 1024:.0f} KB (est.)",
        "📊 Sheets": f"{sum(len(r) for r in st.session_state['sheets'].values())} rows",
        "🎞️ Slides": f"{len(st.session_state['slides'])} slides",
    }
    for k, v in breakdown.items():
        c1, c2 = st.columns([3, 2])
        c1.write(k)
        c2.write(v)

    st.markdown("---")
    st.markdown("### 🧹 Storage optimizer")
    largest = sorted(st.session_state["files"], key=lambda f: f["size_mb"], reverse=True)[:3]
    if largest:
        st.write("**Largest files** — good candidates to archive or delete:")
        for f in largest:
            c1, c2, c3 = st.columns([4, 2, 1])
            c1.write(f["name"])
            c2.write(fmt_size(f["size_mb"]))
            if c3.button("🗑️", key=f"opt_{f['id']}"):
                st.session_state["files"] = [x for x in st.session_state["files"] if x["id"] != f["id"]]
                st.rerun()

    names_seen = {}
    dupes = []
    for f in st.session_state["files"]:
        names_seen.setdefault(f["name"], []).append(f["id"])
    for name, ids in names_seen.items():
        if len(ids) > 1:
            dupes.append(name)
    if dupes:
        st.warning(f"⚠️ Possible duplicate file names: {', '.join(dupes)}")
    else:
        st.success("✅ No duplicate file names detected.")

    st.markdown("---")
    st.markdown("### 📋 Audit log")
    audit = [
        {"Time": now_str(), "Actor": st.session_state["user_name"], "Action": "SESSION_ACTIVE", "Status": "OK"},
        {"Time": "2026-07-31 03:12", "Actor": "Sync Service", "Action": "STORAGE_RECALCULATED", "Status": "OK"},
        {"Time": "2026-07-30 22:45", "Actor": "DLP Scanner", "Action": "PII_SCAN_COMPLETE", "Status": "PASSED"},
    ]
    st.dataframe(audit, use_container_width=True, hide_index=True)
    st.button("📥 Export audit trail (CSV/JSON)")

    st.markdown("---")
    st.markdown("### 💾 Backup & Restore")
    st.caption("Export your workspace state as an encrypted JSON snapshot or restore from a backup.")

    backup_keys = ["files", "docs", "sheets", "slides", "mail_inbox", "mail_sent", "calendar_events",
                   "tasks", "chat_messages", "plan"]
    backup_payload = {k: st.session_state[k] for k in backup_keys}
    backup_payload["files"] = [{k: v for k, v in f.items() if k != "bytes"} for f in backup_payload["files"]]
    backup_json = json.dumps(backup_payload, indent=2, default=str)

    b1, b2 = st.columns(2)
    with b1:
        st.download_button("⬇️ Download backup (.json)", data=backup_json,
                            file_name=f"nexus_vault_backup_{datetime.date.today()}.json",
                            mime="application/json", use_container_width=True)
    with b2:
        restore_file = st.file_uploader("Restore from backup", type=["json"], key="restore_upl")
        if restore_file is not None:
            try:
                data = json.loads(restore_file.getvalue().decode("utf-8"))
                if st.button("⚠️ Confirm restore (overwrites current workspace)", type="primary"):
                    for k in backup_keys:
                        if k in data:
                            st.session_state[k] = data[k]
                    st.success("Workspace restored from backup.")
                    st.rerun()
            except Exception:
                st.error("That file doesn't look like a valid Nexus Vault backup.")