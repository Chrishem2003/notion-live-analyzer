"""
🔒 Nexus Vault — All-in-One Secure Cloud Workspace
A single, self-contained Streamlit application that fuses a zero-trust encrypted
Drive, a full productivity suite (Docs / Sheets / Slides), Mail, Calendar,
Team Chat & Meet, Task boards, an AI Assistant, and a live storage-quota system
into one cohesive, colour-coded workspace.
"""

import streamlit as st
import datetime
import uuid

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
STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
code, pre { font-family: 'JetBrains Mono', monospace !important; }

/* ---- Header banner ---- */
.nv-header {
    background: linear-gradient(120deg, #4338CA 0%, #6D28D9 45%, #0EA5E9 100%);
    border-radius: 16px;
    padding: 22px 28px;
    color: white;
    margin-bottom: 18px;
    box-shadow: 0 8px 24px rgba(67,56,202,0.25);
}
.nv-header h1 { margin: 0; font-size: 1.65rem; font-weight: 800; }
.nv-header p { margin: 4px 0 0 0; opacity: 0.9; font-size: 0.92rem; }

/* ---- Metric / stat cards ---- */
.nv-card {
    background: var(--background-secondary-color, #ffffff);
    border: 1px solid rgba(120,120,140,0.15);
    border-radius: 14px;
    padding: 16px 18px;
    box-shadow: 0 2px 8px rgba(20,20,50,0.05);
}
.nv-card-title { font-size: 0.74rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.6px; color: #7B7F9B; }
.nv-card-value { font-size: 1.4rem; font-weight: 800; margin-top: 4px; }

/* ---- App tiles (per module colour identity) ---- */
.nv-tile { border-radius: 12px; padding: 10px 14px; font-weight: 700; color: white;
    display: inline-block; font-size: 0.8rem; margin-right: 6px; }
.nv-drive   { background: #4F46E5; }
.nv-docs    { background: #2563EB; }
.nv-sheets  { background: #16A34A; }
.nv-slides  { background: #EA580C; }
.nv-mail    { background: #DC2626; }
.nv-cal     { background: #7C3AED; }
.nv-chat    { background: #0D9488; }
.nv-tasks   { background: #CA8A04; }
.nv-ai      { background: #DB2777; }
.nv-sec     { background: #334155; }

/* ---- Badges ---- */
.badge { padding: 3px 9px; border-radius: 20px; font-size: 0.72rem; font-weight: 700; }
.badge-green  { background:#D1FAE5; color:#065F46; }
.badge-purple { background:#EDE9FE; color:#5B21B6; }
.badge-blue   { background:#DBEAFE; color:#1E40AF; }
.badge-amber  { background:#FEF3C7; color:#92400E; }
.badge-red    { background:#FEE2E2; color:#991B1B; }
.badge-gray   { background:#F1F5F9; color:#475569; }

/* storage bar tinting handled inline via st.progress + caption color */
hr { margin: 0.6rem 0 1rem 0; }

.nv-file-card { transition: all .15s ease; }
.nv-empty { text-align:center; padding: 40px 10px; color:#94A3B8; }
</style>
"""
st.markdown(STYLE, unsafe_allow_html=True)

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

        "files": [
            {"id": "FILE-001", "name": "BioInformatics_Pipeline_Config.json", "type": "Code / JSON",
             "size_mb": 4.2, "modified": "2026-07-30 14:20", "status": "Encrypted (AES-256)",
             "sharing": "Private", "folder": "Research"},
            {"id": "FILE-002", "name": "Waterborne_Pathogen_Surveillance_Report.pdf", "type": "PDF Document",
             "size_mb": 18.9, "modified": "2026-07-28 09:15", "status": "Encrypted (Post-Quantum)",
             "sharing": "Link (view only)", "folder": "Reports"},
            {"id": "FILE-003", "name": "Regional_Antimicrobial_Resistance_Data.parquet", "type": "Dataset",
             "size_mb": 142.0, "modified": "2026-07-25 18:40", "status": "Encrypted (AES-256)",
             "sharing": "Domain only", "folder": "Research"},
        ],

        "docs": [
            {"id": "DOC-001", "name": "Strategic Project Plan", "modified": now_str(),
             "content": "# Strategic Project Plan\n\n- **Client-side encryption:** Active\n"
                         "- **Zero-knowledge sync:** Live\n\nWrite project notes, findings, or protocols here..."},
        ],

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


# ============================================================================
# 6. SIDEBAR — NAVIGATION + QUICK SETTINGS
# ============================================================================
with st.sidebar:
    st.markdown("## 🔒 Nexus Vault")
    st.caption(f"Signed in as **{st.session_state['user_name']}** · {st.session_state['user_email']}")
    st.markdown("---")

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
        "🛡️ Security & Vault",
        "☁️ Storage & Admin",
    ]
    # normalize the mail label so routing still matches regardless of unread count
    display_to_key = {o: (o.split(" (")[0] if o.startswith("✉️ Mail") else o) for o in nav_options}

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
                    st.session_state["files"].append({
                        "id": new_id("FILE"), "name": uf.name, "type": uf.type or "File",
                        "size_mb": size_mb, "modified": now_str(),
                        "status": "Encrypted (AES-256)", "sharing": "Private", "folder": "Uploads",
                    })
                    added += 1
            if added:
                st.success(f"✅ {added} file(s) encrypted and stored.")
    with ctrl2:
        folder_filter = st.selectbox("Folder", ["All folders"] + sorted({f["folder"] for f in st.session_state["files"]}))
    with ctrl3:
        st.session_state["vault_view_mode"] = st.selectbox("View", ["Grid View", "Table View", "Folder Tree"])

    visible_files = st.session_state["files"] if folder_filter == "All folders" else [
        f for f in st.session_state["files"] if f["folder"] == folder_filter]

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
                    b1, b2, b3 = st.columns(3)
                    b1.button("👁️", key=f"v_{item['id']}", help="Preview")
                    b2.button("🔗", key=f"s_{item['id']}", help="Share")
                    if b3.button("🗑️", key=f"d_{item['id']}", help="Delete"):
                        st.session_state["files"] = [f for f in st.session_state["files"] if f["id"] != item["id"]]
                        st.rerun()

    elif st.session_state["vault_view_mode"] == "Table View":
        st.dataframe(visible_files, use_container_width=True, hide_index=True,
                     column_config={"id": "ID", "name": "Name", "type": "Type", "size_mb": "Size (MB)",
                                    "modified": "Modified", "status": "Status", "sharing": "Sharing",
                                    "folder": "Folder"})

    else:
        tree = {}
        for f in visible_files:
            tree.setdefault(f["folder"], []).append(f["name"])
        st.json(tree)

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
                 "modified": now_str(), "content": "# New document\n\nStart typing..."}
            st.session_state["docs"].append(d)
            st.rerun()
    with right:
        if chosen:
            doc = next(d for d in st.session_state["docs"] if d["name"] == chosen)
            new_name = st.text_input("Title", value=doc["name"])
            new_content = st.text_area("Editor", value=doc["content"], height=320)
            cA, cB, cC = st.columns([1, 1, 3])
            if cA.button("💾 Save", type="primary"):
                doc["name"], doc["content"], doc["modified"] = new_name, new_content, now_str()
                st.success("Saved.")
            if cB.button("🗑️ Delete"):
                st.session_state["docs"] = [d for d in st.session_state["docs"] if d["id"] != doc["id"]]
                st.rerun()
            st.caption(f"Last modified {doc['modified']} · Encrypted client-side")
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
            del st.session_state["sheets"][active_sheet]
            st.rerun()
        st.caption(f"{len(edited)} rows · autosaved to encrypted workspace state")
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
    st.markdown('<span class="nv-tile nv-mail">✉️ Mail</span> Encrypted, integrated inbox.',
                unsafe_allow_html=True)
    tab_inbox, tab_compose, tab_sent = st.tabs(
        [f"📥 Inbox ({unread_mail_count()})", "✏️ Compose", f"📤 Sent ({len(st.session_state['mail_sent'])})"])

    with tab_inbox:
        if not st.session_state["mail_inbox"]:
            st.markdown('<div class="nv-empty">📭 Inbox is empty.</div>', unsafe_allow_html=True)
        for m in st.session_state["mail_inbox"]:
            with st.container(border=True):
                c1, c2 = st.columns([5, 1])
                with c1:
                    weight = "**" if not m["read"] else ""
                    st.markdown(f"{weight}{m['subject']}{weight}  \n*{m['from']} · {m['time']}*")
                    st.caption(m["preview"])
                with c2:
                    if st.button("👁️ Open", key=f"open_{m['id']}"):
                        m["read"] = True
                        st.rerun()
                    if st.button("⭐" if not m["starred"] else "★", key=f"star_{m['id']}"):
                        m["starred"] = not m["starred"]
                        st.rerun()

    with tab_compose:
        to = st.text_input("To", placeholder="name@example.com")
        subj = st.text_input("Subject")
        body = st.text_area("Message", height=200)
        if st.button("📨 Send", type="primary"):
            if to and subj:
                st.session_state["mail_sent"].append(
                    {"id": new_id("M"), "to": to, "subject": subj, "body": body, "time": now_str()})
                st.success(f"Sent to {to}.")
            else:
                st.error("Add a recipient and subject before sending.")

    with tab_sent:
        if not st.session_state["mail_sent"]:
            st.markdown('<div class="nv-empty">📤 Nothing sent yet.</div>', unsafe_allow_html=True)
        for m in reversed(st.session_state["mail_sent"]):
            with st.container(border=True):
                st.markdown(f"**{m['subject']}** → {m['to']}")
                st.caption(f"{m['time']}")
                st.write(m["body"])

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
        st.text_input("Meeting room link", value=f"https://nexusvault.io/meet/{uuid.uuid4().hex[:8]}", disabled=True)
        c1, c2 = st.columns(2)
        c1.button("🎥 Start instant meeting", type="primary", use_container_width=True)
        c2.button("📅 Schedule meeting", use_container_width=True)

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
            _t.sleep(0.6)
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
        st.caption("Split your master key into N shares — require M of N to recover access.")
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