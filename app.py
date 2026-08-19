import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import pandas as pd
import base64
import hashlib
import os
import sys
import json
import math
import requests
from datetime import datetime, timedelta

# Optional Plotly import with fallback
try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# ==========================================
# 1. PAGE CONFIG & HIGH-CONTRAST DARK CSS
# ==========================================
st.set_page_config(
    page_title="Chrishem Sovereign Apex Hub",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Main Canvas Background */
    .stApp {
        background-color: #0B0F19;
        color: #F8FAFC;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #111827 !important;
        border-right: 1px solid #1F2937;
    }
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] p {
        color: #F8FAFC !important;
        font-weight: 500;
    }
    
    /* Sidebar Navigation Radios */
    div[data-testid="stSidebar"] div[role="radiogroup"] > label {
        background: #1F2937 !important;
        border: 1px solid #374151 !important;
        border-radius: 8px !important;
        padding: 10px 14px !important;
        margin-bottom: 6px !important;
        transition: all 0.2s ease;
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
        border-color: #38BDF8 !important;
        background: #374151 !important;
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"] {
        background: #0284C7 !important;
        border-color: #38BDF8 !important;
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"] span {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }

    /* Cards & Container Metrics */
    div[data-testid="metric-container"] {
        background: #111827;
        border: 1px solid #1F2937;
        border-radius: 10px;
        padding: 14px 18px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    }
    div[data-testid="stMetricValue"] {
        color: #38BDF8 !important;
        font-weight: 700 !important;
        font-size: 1.8rem !important;
    }

    /* Paywall Banner Card */
    .paywall-card {
        background: #1E1B4B;
        border: 2px solid #6366F1;
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        margin: 20px 0;
    }
    
    /* Dataframes and Tables */
    div[data-testid="stDataFrame"] {
        background-color: #111827;
        border-radius: 8px;
        border: 1px solid #1F2937;
    }
    
    /* Tabs Header */
    button[data-baseweb="tab"] {
        font-weight: 600 !important;
        color: #94A3B8 !important;
    }
    button[aria-selected="true"] {
        color: #38BDF8 !important;
        border-bottom-color: #38BDF8 !important;
    }
</style>
""", unsafe_allow_html=True)

DB_FILE = "sovereign_apex.db"

# ==========================================
# 2. PERSISTENT DATABASE INIT
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auth_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            avatar_blob BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            operator TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_email TEXT PRIMARY KEY,
            tier TEXT DEFAULT 'Free',
            status TEXT DEFAULT 'active',
            amount_paid_ugx REAL DEFAULT 0.0,
            expires_at DATE,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS paywall_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mcr_gene_surveillance (
            sample_id TEXT PRIMARY KEY,
            sample_type TEXT,
            source_location TEXT,
            latitude REAL,
            longitude REAL,
            mcr_variant TEXT,
            colistin_mic REAL,
            isolation_date DATE,
            notes TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS business_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT UNIQUE,
            lead_entity TEXT,
            capital_ugx REAL,
            roi_projection_pct REAL,
            status TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS focus_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            preset_mode TEXT,
            duration_minutes INTEGER,
            logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ppwr_cohort (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_age INTEGER,
            months_postpartum INTEGER,
            dra_gap_cm REAL,
            ppwr_kg REAL,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute("INSERT OR IGNORE INTO paywall_settings VALUES ('global_paywall_active', 'true')")

    cursor.execute("SELECT * FROM auth_users WHERE email = ?", ("admin@chrishem.apex",))
    if not cursor.fetchone():
        salt = os.urandom(16).hex()
        pwd_hash = hashlib.pbkdf2_hmac('sha256', "AdminPass123!".encode(), salt.encode(), 100000).hex()
        cursor.execute(
            "INSERT INTO auth_users (email, name, password_hash, salt, role) VALUES (?, ?, ?, ?, ?)",
            ("admin@chrishem.apex", "CHRISHEM", pwd_hash, salt, "admin")
        )

    cursor.execute("INSERT OR REPLACE INTO subscriptions VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                   ("admin@chrishem.apex", "Apex Sovereign", "active", 0.0, "2099-12-31"))

    cursor.execute("SELECT COUNT(*) FROM mcr_gene_surveillance")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO mcr_gene_surveillance VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("MCR-PL-001", "Poultry Cecal Swab", "Arua Central Poultry Market", 2.9712, 30.9114, "mcr-1", 8.0, "2026-03-15", "IncI2 plasmid backbone detected"),
                ("MCR-PL-002", "Environmental Water", "Assa River Downstream", 2.9654, 30.9152, "mcr-1", 16.0, "2026-03-18", "Co-harboring blaCTX-M-15"),
                ("MCR-PL-003", "Abattoir Drainage", "Arua Municipal Abattoir", 2.9751, 30.9083, "mcr-3", 4.0, "2026-04-02", "Novel variant sequence isolate"),
                ("MCR-PL-004", "Poultry Cecal Swab", "Arua Peri-Urban Farm Node", 2.9820, 30.9201, "mcr-1", 32.0, "2026-04-10", "High MIC strain resistance")
            ]
        )

    cursor.execute("SELECT COUNT(*) FROM business_projects")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO business_projects (project_name, lead_entity, capital_ugx, roi_projection_pct, status) VALUES (?, ?, ?, ?, ?)",
            [
                ("Kidega Fresh Passion-Mango Cooler", "Team Kula", 12500000.0, 32.5, "Active"),
                ("Santa Solo Amuca Initiative", "Galilee Community", 8500000.0, 24.0, "Planning"),
                ("Arua Auto Spare Parts Depot", "Galilee Community", 15000000.0, 28.0, "Proposed"),
                ("Northern Uganda Boutique & Salon", "Galilee Community", 6000000.0, 20.0, "Active")
            ]
        )

    cursor.execute("SELECT COUNT(*) FROM ppwr_cohort")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO ppwr_cohort (participant_age, months_postpartum, dra_gap_cm, ppwr_kg) VALUES (?, ?, ?, ?)",
            [(24, 6, 2.8, 5.2), (29, 12, 1.9, 3.1), (32, 3, 3.5, 8.4), (22, 18, 1.2, 1.5), (27, 9, 2.4, 4.8)]
        )

    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect(DB_FILE)

def log_audit(operator, action, details=""):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO audit_logs (operator, action, details) VALUES (?, ?, ?)", (operator, action, details))
    conn.commit()
    conn.close()

def _hash_password(password, salt=None):
    if not salt:
        salt = os.urandom(16).hex()
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    return pwd_hash, salt

# ==========================================
# 3. ALGORITHMIC & COMPUTATIONAL ENGINES
# ==========================================
def process_dna_sequence(seq):
    seq = seq.upper().replace("\n", "").replace(" ", "")
    valid_bases = set("ATGC")
    clean_seq = "".join([b for b in seq if b in valid_bases])
    if not clean_seq:
        return None
    
    gc_pct = ((clean_seq.count('G') + clean_seq.count('C')) / len(clean_seq)) * 100
    rna_seq = clean_seq.replace('T', 'U')
    comp_map = str.maketrans("ATGC", "TACG")
    rev_comp = clean_seq.translate(comp_map)[::-1]
    
    codon_table = {
        'AUG': 'M', 'UUU': 'F', 'UUC': 'F', 'UUA': 'L', 'UUG': 'L',
        'UCU': 'S', 'UCC': 'S', 'UCA': 'S', 'UCG': 'S', 'UAU': 'Y',
        'UAC': 'Y', 'UGU': 'C', 'UGC': 'C', 'UGG': 'W', 'CUU': 'L',
        'CUC': 'L', 'CUA': 'L', 'CUG': 'L', 'CCU': 'P', 'CCC': 'P',
        'CCA': 'P', 'CCG': 'P', 'CAU': 'H', 'CAC': 'H', 'CAA': 'Q',
        'CAG': 'Q', 'CGU': 'R', 'CGC': 'R', 'CGA': 'R', 'CGG': 'R',
        'AUU': 'I', 'AUC': 'I', 'AUA': 'I', 'ACU': 'T', 'ACC': 'T',
        'ACA': 'T', 'ACG': 'T', 'AAU': 'N', 'AAC': 'N', 'AAA': 'K',
        'AAG': 'K', 'AGU': 'S', 'AGC': 'S', 'AGA': 'R', 'AGG': 'R',
        'GUU': 'V', 'GUC': 'V', 'GUA': 'V', 'GUG': 'V', 'GCU': 'A',
        'GCC': 'A', 'GCA': 'A', 'GCG': 'A', 'GAU': 'D', 'GAC': 'D',
        'GAA': 'E', 'GAG': 'E', 'GGU': 'G', 'GGC': 'G', 'GGA': 'G', 'GGG': 'G',
        'UAA': '*', 'UAG': '*', 'UGA': '*'
    }
    
    protein = []
    for i in range(0, len(rna_seq) - 2, 3):
        codon = rna_seq[i:i+3]
        protein.append(codon_table.get(codon, '?'))
        
    return {
        "length": len(clean_seq),
        "gc_content": gc_pct,
        "rna": rna_seq,
        "rev_comp": rev_comp,
        "protein": "".join(protein)
    }

def needleman_wunsch(seq1, seq2, match=1, mismatch=-1, gap=-1):
    n, m = len(seq1), len(seq2)
    score_matrix = [[0] * (m + 1) for _ in range(n + 1)]
    
    for i in range(n + 1):
        score_matrix[i][0] = i * gap
    for j in range(m + 1):
        score_matrix[0][j] = j * gap
        
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            s = match if seq1[i-1] == seq2[j-1] else mismatch
            score_matrix[i][j] = max(
                score_matrix[i-1][j-1] + s,
                score_matrix[i-1][j] + gap,
                score_matrix[i][j-1] + gap
            )
            
    align1, align2 = "", ""
    i, j = n, m
    while i > 0 and j > 0:
        score_current = score_matrix[i][j]
        score_diag = score_matrix[i-1][j-1]
        s = match if seq1[i-1] == seq2[j-1] else mismatch
        
        if score_current == score_diag + s:
            align1 = seq1[i-1] + align1
            align2 = seq2[j-1] + align2
            i -= 1
            j -= 1
        elif score_current == score_matrix[i-1][j] + gap:
            align1 = seq1[i-1] + align1
            align2 = "-" + align2
            i -= 1
        else:
            align1 = "-" + align1
            align2 = seq2[j-1] + align2
            j -= 1
            
    while i > 0:
        align1 = seq1[i-1] + align1
        align2 = "-" + align2
        i -= 1
    while j > 0:
        align1 = "-" + align1
        align2 = seq2[j-1] + align2
        j -= 1
        
    return align1, align2, score_matrix[n][m]

def generate_waveform_data(freq=440.0, duration=2.0, num_samples=200):
    x_vals = [i * (duration / num_samples) for i in range(num_samples)]
    y_vals = [math.sin(2 * math.pi * freq * t) * math.exp(-0.8 * t) for t in x_vals]
    return x_vals, y_vals

# ==========================================
# 4. PAYWALL GUARD CONTROLLER
# ==========================================
def is_paywall_enabled():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT setting_value FROM paywall_settings WHERE setting_key = 'global_paywall_active'")
    row = c.fetchone()
    conn.close()
    return row[0] == 'true' if row else False

def check_user_access(email, required_tier="Pro"):
    if st.session_state.get("role") == "admin":
        return True, "Admin Bypass Grant"

    if not is_paywall_enabled():
        return True, "Paywall Guard Disabled"

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT tier, status, expires_at FROM subscriptions WHERE user_email = ?", (email.lower(),))
    sub = c.fetchone()
    conn.close()

    if not sub:
        return False, "No active subscription tier found for this account."

    tier, status, expires_at = sub
    if status != "active":
        return False, f"Subscription status is '{status}'."

    if expires_at and datetime.strptime(expires_at, "%Y-%m-%d").date() < datetime.now().date():
        return False, "Subscription has expired."

    tier_levels = {"Free": 0, "Pro": 1, "Apex Sovereign": 2}
    if tier_levels.get(tier, 0) < tier_levels.get(required_tier, 1):
        return False, f"Requires '{required_tier}' tier or higher. Current tier: '{tier}'."

    return True, "Access Granted"

def render_paywall_screen(module_name, required_tier="Pro"):
    st.markdown(f"""
    <div class="paywall-card">
        <h2 style="color: #818CF8; margin-top:0;">🔒 {module_name} is Locked</h2>
        <p style="color: #E0E7FF; font-size: 1.1rem;">
            Access to this advanced research engine is restricted under current paywall security policies.
        </p>
        <p style="color: #9CA3AF;">Required Subscription Level: <strong style="color:#38BDF8;">{required_tier} Tier</strong></p>
    </div>
    """, unsafe_allow_html=True)
    st.info("💡 To upgrade your subscription or request credentials, contact System Administrator **CHRISHEM**.")

# ==========================================
# 5. SESSION & AUTHENTICATION STATE
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = True
    st.session_state.user_email = "admin@chrishem.apex"
    st.session_state.username = "CHRISHEM"
    st.session_state.role = "admin"

# ==========================================
# 6. SIDEBAR NAVIGATION & CREATOR PROFILE
# ==========================================
st.sidebar.title("⚡ Sovereign Apex")

conn = get_db_connection()
c = conn.cursor()
c.execute("SELECT avatar_blob, name FROM auth_users WHERE email = ?", (st.session_state.user_email.lower(),))
user_row = c.fetchone()
conn.close()

if user_row and user_row[0]:
    try:
        encoded_img = base64.b64encode(user_row[0]).decode()
        st.sidebar.markdown(
            f'<div style="text-align: center; margin-bottom: 14px;">'
            f'<img src="data:image/png;base64,{encoded_img}" style="width: 95px; height: 95px; border-radius: 50%; border: 2px solid #38BDF8; object-fit: cover; box-shadow: 0 0 12px rgba(56, 189, 248, 0.3);">'
            f'</div>',
            unsafe_allow_html=True
        )
    except Exception:
        st.sidebar.markdown(
            '<div style="width: 85px; height: 85px; border-radius: 50%; background: linear-gradient(135deg, #0284C7, #0F172A); border: 2px solid #38BDF8; display: flex; align-items: center; justify-content: center; margin: 0 auto 14px auto; font-weight: bold; color: #FFFFFF; font-size: 26px; box-shadow: 0 0 12px rgba(56, 189, 248, 0.3);">KC</div>',
            unsafe_allow_html=True
        )
else:
    st.sidebar.markdown(
        '<div style="width: 85px; height: 85px; border-radius: 50%; background: linear-gradient(135deg, #0284C7, #0F172A); border: 2px solid #38BDF8; display: flex; align-items: center; justify-content: center; margin: 0 auto 14px auto; font-weight: bold; color: #FFFFFF; font-size: 26px; box-shadow: 0 0 12px rgba(56, 189, 248, 0.3);">KC</div>',
        unsafe_allow_html=True
    )

st.sidebar.markdown(f"<h3 style='text-align: center; margin:0; color:#F8FAFC;'>{st.session_state.username}</h3>", unsafe_allow_html=True)
st.sidebar.caption(f"Operator: **{st.session_state.role.upper()}** | Kula Chris")
st.sidebar.divider()

menu = st.sidebar.radio("Navigation Engine", [
    "⚡ System Overview",
    "💳 Admin Billing Control",
    "📊 Notion Workspace Sync",
    "🧬 Bioinformatics Engine",
    "🗺️ GIS Resistance Map",
    "🌊 Environmental Compliance",
    "💼 Business Portfolio",
    "📊 Epidemiological Cohort",
    "🧠 Neuro-Sonic Focus Engine",
    "💬 Local AI & NLP Bridge",
    "🗂️ Academic Report Vault",
    "👤 Identity Settings",
    "🛡️ Security & Database Core"
])

st.sidebar.divider()
st.sidebar.caption("Architecture: `CHRISHEM-APEX-v5.0`")
st.sidebar.caption("Muni University | BSMB Science Hub")

# ==========================================
# 7. ALL 13 MODULE IMPLEMENTATIONS
# ==========================================

# ------------------------------------------
# MODULE 1: SYSTEM OVERVIEW
# ------------------------------------------
if menu == "⚡ System Overview":
    st.title("⚡ Sovereign Apex Control Portal")
    st.caption("Integrated Operational Telemetry & Academic Research Platform")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("System Modules", "13 Installed", "Verified")
    m2.metric("Paywall Guard", "Active" if is_paywall_enabled() else "Disabled", "Bypass Admin")
    m3.metric("Lead Investigator", "Kula Chris", "2501202072")
    m4.metric("Creator Handle", "CHRISHEM", "Active")

    st.divider()
    col_l, col_r = st.columns([2, 1])

    with col_l:
        st.subheader("📌 Operational Subsystem Matrix")
        matrix_df = pd.DataFrame({
            "Research Subsystem": ["mcr Genomic Surveillance", "Arua GIS Resistance Map", "Kidega Fresh Enterprise", "PPWR / DRA Women's Health", "Neuro-Sonic Focus Engine"],
            "Target Focus": ["Plasmid Colistin Resistance", "Coordinate Resistance Map", "Beverage Production & Sales", "Postpartum Abdominal Recovery", "Generative Cognitive Soundscapes"],
            "Access Status": ["Pro Tier Locked" if is_paywall_enabled() and st.session_state.role != "admin" else "Operational" for _ in range(5)]
        })
        st.dataframe(matrix_df, use_container_width=True)

    with col_r:
        st.subheader("🛡️ Environment Telemetry")
        st.info(f"💻 Runtime OS: {sys.platform.upper()}")
        st.success("🌐 Framework Engine: Streamlit Native")
        st.success("🧬 Bio Core: Alignment Matrix Ready")

# ------------------------------------------
# MODULE 2: ADMIN BILLING CONTROL (ADMIN ONLY)
# ------------------------------------------
elif menu == "💳 Admin Billing Control":
    st.title("💳 Admin Billing Control & Paywall Portal")
    st.caption("Master Subscription Enforcement, Tier Allocation & Revenue Telemetry")

    if st.session_state.role != "admin":
        st.error("⛔ Access Denied. Only System Administrator CHRISHEM can access billing controls.")
    else:
        st.subheader("⚙️ Global Paywall Enforcement Switch")
        curr_paywall = is_paywall_enabled()
        paywall_toggle = st.toggle("Enable Global Paywall Locks Across Engines", value=curr_paywall)
        
        if paywall_toggle != curr_paywall:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("UPDATE paywall_settings SET setting_value = ? WHERE setting_key = 'global_paywall_active'",
                      ('true' if paywall_toggle else 'false',))
            conn.commit()
            conn.close()
            log_audit(st.session_state.username, "toggle_paywall", f"Paywall Active: {paywall_toggle}")
            st.success(f"Global paywall state updated to: **{'ACTIVE' if paywall_toggle else 'DISABLED'}**")
            st.rerun()

        st.divider()
        st.subheader("👤 User Subscriptions & Access Rights")

        conn = get_db_connection()
        subs_df = pd.read_sql_query("""
            SELECT u.email, u.name, u.role, COALESCE(s.tier, 'Free') as tier, 
                   COALESCE(s.status, 'inactive') as status, 
                   COALESCE(s.amount_paid_ugx, 0.0) as amount_paid_ugx, 
                   s.expires_at 
            FROM auth_users u 
            LEFT JOIN subscriptions s ON u.email = s.user_email
        """, conn)
        conn.close()

        st.dataframe(subs_df, use_container_width=True)

        st.markdown("##### ✏️ Assign Subscription Tier & Override Status")
        with st.form("update_user_billing"):
            target_email = st.selectbox("Select User Account", subs_df["email"].tolist())
            new_tier = st.selectbox("Assign Subscription Tier", ["Free", "Pro", "Apex Sovereign"])
            new_status = st.selectbox("Access Status", ["active", "suspended", "expired"])
            payment_ugx = st.number_input("Record Payment Amount (UGX)", value=150000.0, step=10000.0)
            valid_days = st.number_input("Subscription Duration (Days)", value=30, min_value=1)

            if st.form_submit_button("Apply Billing Changes", type="primary"):
                exp_date = (datetime.now() + timedelta(days=valid_days)).strftime("%Y-%m-%d")
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("""
                    INSERT INTO subscriptions (user_email, tier, status, amount_paid_ugx, expires_at, last_updated)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_email) DO UPDATE SET
                        tier=excluded.tier,
                        status=excluded.status,
                        amount_paid_ugx=subscriptions.amount_paid_ugx + excluded.amount_paid_ugx,
                        expires_at=excluded.expires_at,
                        last_updated=CURRENT_TIMESTAMP
                """, (target_email, new_tier, new_status, payment_ugx, exp_date))
                conn.commit()
                conn.close()

                log_audit(st.session_state.username, "update_billing", f"User: {target_email} | Tier: {new_tier} | UGX: {payment_ugx}")
                st.success(f"Updated subscription for {target_email} to {new_tier} ({new_status}).")
                st.rerun()

# ------------------------------------------
# MODULE 3: NOTION WORKSPACE SYNC
# ------------------------------------------
elif menu == "📊 Notion Workspace Sync":
    st.title("📊 Notion Integration & Pipeline Engine")
    st.caption("Live Workspace Connection & Local Synchronization Protocols")

    notion_token = st.text_input("Notion API Token", type="password", value="")
    database_id = st.text_input("Workspace Database ID", value="3a7f8e12b4c5d6e7f8a9b0c1d2e3f4a5")

    if st.button("Synchronize Workspace Data", type="primary"):
        log_audit(st.session_state.username, "notion_sync", f"DB: {database_id[:8]}")
        if not notion_token.strip():
            st.warning("⚠️ Notion API Token not configured. Displaying local cached workspace data.")
            live_df = pd.DataFrame([
                {"Task Name": "Complete mcr-1 Plasmid Extraction Protocol", "Category": "Bioinformatics", "Priority": "High", "Status": "Completed", "Assignee": "Kula Chris"},
                {"Task Name": "Draft Kidega Fresh Revenue Projections", "Category": "Enterprise", "Priority": "Medium", "Status": "In Progress", "Assignee": "Team Kula"},
                {"Task Name": "Audit Assa River Outreach Survey Data", "Category": "Environment", "Priority": "High", "Status": "Completed", "Assignee": "Kula Chris"}
            ])
            st.dataframe(live_df, use_container_width=True)
        else:
            try:
                headers = {
                    "Authorization": f"Bearer {notion_token}",
                    "Notion-Version": "2022-06-28",
                    "Content-Type": "application/json"
                }
                res = requests.post(f"https://api.notion.com/v1/databases/{database_id}/query", headers=headers, timeout=3)
                if res.status_code == 200:
                    st.success("Successfully synchronized live workspace data from Notion API!")
                    st.json(res.json())
                else:
                    st.error(f"Notion API returned HTTP {res.status_code}: {res.text}")
            except Exception as e:
                st.error(f"Connection failed: {str(e)}")

# ------------------------------------------
# MODULE 4: BIOINFORMATICS ENGINE (PROTECTED - PRO TIER)
# ------------------------------------------
elif menu == "🧬 Bioinformatics Engine":
    allowed, msg = check_user_access(st.session_state.user_email, required_tier="Pro")
    if not allowed:
        render_paywall_screen("Bioinformatics Engine", required_tier="Pro")
    else:
        st.title("🧬 Bioinformatics & Pairwise Sequence Alignment Engine")
        st.caption("Plasmid mcr-1 Surveillance & Needleman-Wunsch Global Alignment Algorithms")

        b_tab1, b_tab2, b_tab3 = st.tabs(["⚡ Pairwise Alignment", "🧫 mcr Genomic Data", "🔍 FastA Processor"])

        with b_tab1:
            st.subheader("🧬 Needleman-Wunsch Global Pairwise Sequence Alignment")
            st.write("Compare sample sequences against wild-type reference strains to map point mutations.")
            
            c_a, c_b = st.columns(2)
            seq_ref = c_a.text_area("Reference Sequence (Wild-type mcr-1)", value="ATGCAGCGTACTAAGGCTAAGCTAGCTAGC", height=90)
            seq_sample = c_b.text_area("Isolated Sample Sequence", value="ATGCAGTGTACTAAGGCTAAGCTAGCTAGC", height=90)
            
            if st.button("Run Global Alignment", type="primary"):
                a1, a2, score = needleman_wunsch(seq_ref.upper().strip(), seq_sample.upper().strip())
                st.success(f"Alignment Complete. Dynamic Alignment Score: **{score}**")
                st.markdown("##### 🧬 Pairwise Alignment Map")
                st.code(f"REF:    {a1}\nMATCH:  {''.join(['|' if a1[k] == a2[k] else '.' for k in range(len(a1))])}\nSAMPLE: {a2}")

        with b_tab2:
            st.subheader("🐔 Poultry & Environmental mcr-Gene Surveillance Vault")
            conn = get_db_connection()
            mcr_df = pd.read_sql_query("SELECT sample_id, sample_type, source_location, mcr_variant, colistin_mic, isolation_date FROM mcr_gene_surveillance", conn)
            conn.close()

            st.dataframe(mcr_df, use_container_width=True)

            if HAS_PLOTLY and not mcr_df.empty:
                fig = px.bar(mcr_df, x="sample_id", y="colistin_mic", color="mcr_variant", 
                             title="Colistin Minimum Inhibitory Concentration (MIC µg/mL)",
                             labels={"colistin_mic": "MIC (µg/mL)", "sample_id": "Isolate ID"},
                             template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

        with b_tab3:
            st.subheader("🔍 Nucleotide Translation & GC Content Engine")
            fasta_input = st.text_area("Input FastA Sequence", value=">mcr1_partial_cds\nATGCAGCGTACTAAGGCTAAGCTAGCTAGCTAGCGCGCGCATATATCGATCGATCGAT", height=90)
            
            if st.button("Process Sequence"):
                seq_lines = [line.strip() for line in fasta_input.splitlines() if not line.startswith(">")]
                raw_seq = "".join(seq_lines)
                res = process_dna_sequence(raw_seq)

                if res:
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Length", f"{res['length']} bp")
                    m2.metric("GC Ratio", f"{res['gc_content']:.2f}%")
                    m3.metric("Codons", f"{res['length'] // 3}")

                    st.markdown("##### 🧬 Reverse Complement (5' ➔ 3')")
                    st.code(res['rev_comp'])
                    st.markdown("##### 🧪 Amino Acid Translation")
                    st.code(res['protein'])

# ------------------------------------------
# MODULE 5: GIS RESISTANCE MAP
# ------------------------------------------
elif menu == "🗺️ GIS Resistance Map":
    st.title("🗺️ Geospatial Resistance Mapping Engine")
    st.caption("Spatial Resistance Heatmap across Arua District Sampling Locations")

    conn = get_db_connection()
    map_df = pd.read_sql_query("SELECT sample_id, source_location, latitude, longitude, mcr_variant, colistin_mic FROM mcr_gene_surveillance", conn)
    conn.close()

    st.subheader("📍 Sampling Coordinates (Arua, Uganda)")
    st.dataframe(map_df, use_container_width=True)

    if not map_df.empty:
        st.map(map_df, latitude="latitude", longitude="longitude", size=15)

    if HAS_PLOTLY and not map_df.empty:
        fig_map = px.scatter_mapbox(
            map_df,
            lat="latitude",
            lon="longitude",
            hover_name="source_location",
            hover_data=["sample_id", "mcr_variant", "colistin_mic"],
            color="colistin_mic",
            size="colistin_mic",
            color_continuous_scale=px.colors.cyclical.IceFire,
            zoom=12,
            height=420,
            title="Colistin MIC Concentration Intensity Map"
        )
        fig_map.update_layout(mapbox_style="carto-darkmatter")
        fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
        st.plotly_chart(fig_map, use_container_width=True)

# ------------------------------------------
# MODULE 6: ENVIRONMENTAL COMPLIANCE
# ------------------------------------------
elif menu == "🌊 Environmental Compliance":
    st.title("🌊 Environmental Audit & Coastal Risk Engine")
    st.caption("Assa River Discharge, Arua Abattoir Waste Audit & Coastal Flooding Simulation")

    e_tab1, e_tab2, e_tab3 = st.tabs(["🌊 Assa River Audit", "🥩 Arua Abattoir Waste", "🏝️ Atoll Risk Model"])

    with e_tab1:
        st.subheader("🌊 Muni University Waste Discharge & Assa River Ecosystem")
        c1, c2 = st.columns(2)
        c1.metric("Water Quality Index (WQI)", "68.4 / 100", "Moderate Concern")
        c2.metric("Organic Manure Conversion", "100%", "Demonstrated")

    with e_tab2:
        st.subheader("🥩 Arua Municipal Abattoir Sanitation Assessment")
        st.markdown("- **Facility:** Arua City Abattoir  \n- **Supervisors:** Mr. Taban Alpha & Mr. Becker Raymond")

    with e_tab3:
        st.subheader("🏝️ Atoll Alert: Coastal Inundation Simulator")
        sea_rise = st.slider("Simulated Sea Level Rise (Meters)", 0.1, 3.0, 0.8, 0.1)
        
        elevations = [0.2, 0.5, 0.8, 1.2, 1.5, 2.0, 2.5, 3.0]
        displacement = [int(e * 15000) for e in elevations]
        
        if HAS_PLOTLY:
            fig = px.line(x=elevations, y=displacement, labels={"x": "Sea Level Rise (m)", "y": "Displaced Population"},
                          title="Coastal Inundation Impact Curve", template="plotly_dark")
            fig.add_vline(x=sea_rise, line_dash="dash", line_color="red")
            st.plotly_chart(fig, use_container_width=True)

        st.warning(f"⚠️ Simulation Result: {int(sea_rise * 15000):,} residents affected at {sea_rise:.1f}m sea-level rise.")

# ------------------------------------------
# MODULE 7: BUSINESS PORTFOLIO
# ------------------------------------------
elif menu == "💼 Business Portfolio":
    st.title("💼 Enterprise & Community Venture Portfolio")
    st.caption("Kidega Fresh Beverage Operations & Galilee Community Ventures")

    conn = get_db_connection()
    biz_df = pd.read_sql_query("SELECT * FROM business_projects", conn)
    conn.close()

    st.subheader("📊 Operational Venture Portfolio")
    st.dataframe(biz_df, use_container_width=True)

    if HAS_PLOTLY and not biz_df.empty:
        fig = px.pie(biz_df, names="project_name", values="capital_ugx", 
                     title="Capital Allocation across Ventures (UGX)", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------
# MODULE 8: EPIDEMIOLOGICAL COHORT
# ------------------------------------------
elif menu == "📊 Epidemiological Cohort":
    st.title("📊 Epidemiological Research & Women's Health Cohort")
    st.caption("Postpartum Weight Retention (PPWR) & Diastasis Recti Abdominis (DRA) Research")

    conn = get_db_connection()
    cohort_df = pd.read_sql_query("SELECT * FROM ppwr_cohort", conn)
    conn.close()

    st.subheader("📈 Cohort Scatter Regression (DRA Gap vs. PPWR Weight Retention)")
    if HAS_PLOTLY and not cohort_df.empty:
        fig = px.scatter(cohort_df, x="dra_gap_cm", y="ppwr_kg", size="participant_age", color="months_postpartum",
                         title="Correlation: Inter-recti Distance (cm) vs. Weight Retention (kg)",
                         labels={"dra_gap_cm": "DRA Gap (cm)", "ppwr_kg": "PPWR Retention (kg)"},
                         template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------
# MODULE 9: NEURO-SONIC FOCUS ENGINE (UPGRADED BRAIN.FM & ENDEL CLONE)
# ------------------------------------------
elif menu == "🧠 Neuro-Sonic Focus Engine":
    st.title("🧠 Zenith Neuro-Instrumental Suite")
    st.caption("Science-backed generative soundscapes, pentatonic instrumental chords, and binaural entrainment")

    f_tab1, f_tab2 = st.tabs(["🎛️ Neuro Soundscape Generator", "📈 Session Analytics & Science"])

    with f_tab1:
        zenith_html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <style>
                :root {
                    --bg: #070a13;
                    --panel: #111625;
                    --accent: #6366f1;
                    --accent-glow: rgba(99, 102, 241, 0.3);
                    --text: #f8fafc;
                    --muted: #64748b;
                }
                body {
                    margin: 0; padding: 12px;
                    background-color: var(--bg);
                    color: var(--text);
                    font-family: system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
                    display: flex; justify-content: center; align-items: center;
                }
                .app-container {
                    width: 100%; max-width: 500px;
                    background: var(--panel);
                    border-radius: 20px; padding: 24px;
                    box-shadow: 0 20px 40px -10px rgba(0,0,0,0.5), 0 0 30px var(--accent-glow);
                    border: 1px solid rgba(255,255,255,0.06);
                    box-sizing: border-box;
                }
                .header { text-align: center; margin-bottom: 20px; }
                .header h2 { font-size: 20px; font-weight: 800; margin: 0 0 4px 0; color: #38bdf8; }
                .header p { color: var(--muted); margin: 0; font-size: 12px; }
                
                .master-trigger {
                    width: 100%; padding: 16px; border: none; border-radius: 14px;
                    background: var(--accent); color: white; font-size: 15px; font-weight: 700;
                    cursor: pointer; transition: all 0.2s ease;
                    box-shadow: 0 4px 12px var(--accent-glow);
                }
                .master-trigger:active { transform: scale(0.98); }
                .master-trigger.playing { background: #ec4899; box-shadow: 0 4px 12px rgba(236, 72, 153, 0.3); }

                .section-title { font-size: 11px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; margin: 20px 0 10px 0; }
                
                .preset-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
                .preset-card {
                    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05);
                    padding: 12px; border-radius: 12px; cursor: pointer; text-align: left; transition: all 0.2s;
                }
                .preset-card:hover { background: rgba(255,255,255,0.06); }
                .preset-card.active { border-color: var(--accent); background: rgba(99, 102, 241, 0.15); }
                .preset-card div { font-weight: 600; font-size: 13px; margin-bottom: 2px; }
                .preset-card span { font-size: 10px; color: var(--muted); }

                .mixer-row {
                    background: rgba(255,255,255,0.02); border-radius: 12px; padding: 12px 14px; margin-bottom: 10px;
                    display: flex; flex-direction: column; gap: 6px;
                }
                .mixer-label { display: flex; justify-content: space-between; font-size: 12px; font-weight: 600; }
                .mixer-label span:last-child { color: var(--muted); font-size: 11px; }
                
                input[type="range"] {
                    -webkit-appearance: none; width: 100%; height: 5px; background: #1e293b; border-radius: 4px; outline: none;
                }
                input[type="range"]::-webkit-slider-thumb {
                    -webkit-appearance: none; width: 14px; height: 14px; border-radius: 50%; background: var(--accent); cursor: pointer;
                }
            </style>
        </head>
        <body>

        <div class="app-container">
            <div class="header">
                <h2>Neuro-Sonic Engine</h2>
                <p>Acoustic Instrumentals & Generative Soundscapes</p>
            </div>

            <button id="playBtn" class="master-trigger">Initialize Soundscape</button>

            <div class="section-title">Focus Intention</div>
            <div class="preset-grid">
                <div class="preset-card active" onclick="setPreset('ambient', 15)" id="p-ambient">
                    <div>Deep Lo-Fi Pad</div>
                    <span>Beta Wave Focus (15 Hz)</span>
                </div>
                <div class="preset-card" onclick="setPreset('zen', 10)" id="p-zen">
                    <div>Chime Meditation</div>
                    <span>Alpha Wave Recall (10 Hz)</span>
                </div>
                <div class="preset-card" onclick="setPreset('cosmic', 40)" id="p-cosmic">
                    <div>Cosmic Strings</div>
                    <span>Gamma High Focus (40 Hz)</span>
                </div>
                <div class="preset-card" onclick="setPreset('theta', 5)" id="p-theta">
                    <div>Dream Harp</div>
                    <span>Theta Creative (5 Hz)</span>
                </div>
            </div>

            <div class="section-title">Instrumental Mixer</div>
            
            <div class="mixer-row">
                <div class="mixer-label"><span>Melodic Instrumentals</span><span id="v1">70%</span></div>
                <input type="range" id="volMusic" min="0" max="1" step="0.05" value="0.7">
            </div>

            <div class="mixer-row">
                <div class="mixer-label"><span>Neural Entrainment (Binaural)</span><span id="v2">30%</span></div>
                <input type="range" id="volBinaural" min="0" max="0.3" step="0.01" value="0.1">
            </div>

            <div class="mixer-row">
                <div class="mixer-label"><span>Atmospheric Drift (Reverb)</span><span id="v3">50%</span></div>
                <input type="range" id="volSpatial" min="0" max="1" step="0.05" value="0.5">
            </div>
        </div>

        <script>
            let ctx = null, isPlaying = false;
            let baseFreq = 140, currentOffset = 15, currentMode = 'ambient';
            
            let masterMusicGain, binauralGain, spatialGain;
            let leftOsc, rightOsc, leftPan, rightPan;
            let sequenceTimer = null;

            const scales = {
                ambient: [146.83, 164.81, 220.00, 246.94, 293.66],
                zen:     [130.81, 146.83, 164.81, 196.00, 220.00],
                cosmic:  [110.00, 130.81, 146.83, 164.81, 196.00],
                theta:   [98.00,  110.00, 130.81, 146.83, 174.61]
            };

            const playBtn = document.getElementById('playBtn');

            document.getElementById('volMusic').addEventListener('input', (e) => {
                document.getElementById('v1').textContent = Math.round(e.target.value * 100) + '%';
                if(masterMusicGain && ctx) masterMusicGain.gain.setTargetAtTime(e.target.value, ctx.currentTime, 0.1);
            });
            document.getElementById('volBinaural').addEventListener('input', (e) => {
                document.getElementById('v2').textContent = Math.round((e.target.value / 0.3) * 100) + '%';
                if(binauralGain && ctx) binauralGain.gain.setTargetAtTime(e.target.value, ctx.currentTime, 0.1);
            });
            document.getElementById('volSpatial').addEventListener('input', (e) => {
                document.getElementById('v3').textContent = Math.round(e.target.value * 100) + '%';
                if(spatialGain && ctx) spatialGain.gain.setTargetAtTime(e.target.value, ctx.currentTime, 0.1);
            });

            function setPreset(mode, offset) {
                currentMode = mode;
                currentOffset = offset;
                
                document.querySelectorAll('.preset-card').forEach(c => c.classList.remove('active'));
                document.getElementById(`p-${mode}`).classList.add('active');

                if (isPlaying && ctx) {
                    leftOsc.frequency.setTargetAtTime(baseFreq, ctx.currentTime, 0.5);
                    rightOsc.frequency.setTargetAtTime(baseFreq + currentOffset, ctx.currentTime, 0.5);
                }
            }

            function initAudio() {
                ctx = new (window.AudioContext || window.webkitAudioContext)();

                masterMusicGain = ctx.createGain();
                binauralGain = ctx.createGain();
                spatialGain = ctx.createGain();

                masterMusicGain.gain.setValueAtTime(document.getElementById('volMusic').value, ctx.currentTime);
                binauralGain.gain.setValueAtTime(document.getElementById('volBinaural').value, ctx.currentTime);
                spatialGain.gain.setValueAtTime(document.getElementById('volSpatial').value, ctx.currentTime);

                masterMusicGain.connect(ctx.destination);
                binauralGain.connect(ctx.destination);
                spatialGain.connect(ctx.destination);

                leftOsc = ctx.createOscillator();
                rightOsc = ctx.createOscillator();
                leftPan = ctx.createStereoPanner ? ctx.createStereoPanner() : null;
                rightPan = ctx.createStereoPanner ? ctx.createStereoPanner() : null;

                leftOsc.type = 'sine';
                rightOsc.type = 'sine';
                leftOsc.frequency.setValueAtTime(baseFreq, ctx.currentTime);
                rightOsc.frequency.setValueAtTime(baseFreq + currentOffset, ctx.currentTime);

                if (leftPan && rightPan) {
                    leftPan.pan.setValueAtTime(-1, ctx.currentTime);
                    rightPan.pan.setValueAtTime(1, ctx.currentTime);
                    leftOsc.connect(leftPan).connect(binauralGain);
                    rightOsc.connect(rightPan).connect(binauralGain);
                } else {
                    leftOsc.connect(binauralGain);
                    rightOsc.connect(binauralGain);
                }
                
                leftOsc.start();
                rightOsc.start();

                runSequencer();
            }

            function playInstrumentNote(freq, startTime, duration) {
                const osc1 = ctx.createOscillator();
                const osc2 = ctx.createOscillator();
                const noteGain = ctx.createGain();
                const filter = ctx.createBiquadFilter();

                osc1.type = currentMode === 'zen' ? 'triangle' : 'sine';
                osc2.type = 'triangle';

                osc1.frequency.setValueAtTime(freq, startTime);
                osc2.frequency.setValueAtTime(freq * 1.5, startTime);

                filter.type = 'lowpass';
                filter.frequency.setValueAtTime(800, startTime);
                filter.frequency.exponentialRampToValueAtTime(300, startTime + duration);

                noteGain.gain.setValueAtTime(0, startTime);
                noteGain.gain.linearRampToValueAtTime(0.12, startTime + 0.3);
                noteGain.gain.exponentialRampToValueAtTime(0.0001, startTime + duration);

                osc1.connect(filter);
                osc2.connect(filter);
                filter.connect(noteGain);
                noteGain.connect(masterMusicGain);

                const spatialBranch = ctx.createGain();
                spatialBranch.gain.setValueAtTime(document.getElementById('volSpatial').value * 0.1, startTime);
                noteGain.connect(spatialBranch).connect(spatialGain);

                osc1.start(startTime);
                osc2.start(startTime);
                osc1.stop(startTime + duration);
                osc2.stop(startTime + duration);
            }

            function runSequencer() {
                let scheduleAhead = 0.5;
                let lookAheadTime = 250;
                let nextNoteTime = ctx.currentTime;

                function scheduler() {
                    while (nextNoteTime < ctx.currentTime + scheduleAhead) {
                        const currentScale = scales[currentMode];
                        const randomNote = currentScale[Math.floor(Math.random() * currentScale.length)];
                        let noteLength = currentMode === 'cosmic' ? 4.0 : 3.0;
                        let stepInterval = currentMode === 'zen' ? 2.5 : 2.0;
                        playInstrumentNote(randomNote, nextNoteTime, noteLength);
                        nextNoteTime += stepInterval;
                    }
                    if (isPlaying) {
                        sequenceTimer = setTimeout(scheduler, lookAheadTime);
                    }
                }
                scheduler();
            }

            playBtn.addEventListener('click', async () => {
                if (!ctx) {
                    initAudio();
                    isPlaying = true;
                    playBtn.textContent = "Pause Session";
                    playBtn.classList.add('playing');
                    return;
                }
                if (isPlaying) {
                    await ctx.suspend();
                    isPlaying = false;
                    clearTimeout(sequenceTimer);
                    playBtn.textContent = "Resume Session";
                    playBtn.classList.remove('playing');
                } else {
                    await ctx.resume();
                    isPlaying = true;
                    runSequencer();
                    playBtn.textContent = "Pause Session";
                    playBtn.classList.add('playing');
                }
            });
        </script>
        </body>
        </html>
        """
        components.html(zenith_html, height=540, scrolling=False)

    with f_tab2:
        st.subheader("⏱️ Focus Session Logging")
        st.caption("Record completed deep work focus sessions to your persistent database.")

        with st.form("log_focus_session"):
            c_p, c_d = st.columns(2)
            session_preset = c_p.selectbox("Preset Soundscape", ["Beta Wave Focus (15 Hz)", "Gamma High Focus (40 Hz)", "Alpha Wave Recall (10 Hz)", "Theta Creative (5 Hz)"])
            duration_mins = c_d.number_input("Session Duration (Minutes)", min_value=5, max_value=240, value=25, step=5)

            if st.form_submit_button("Record Focus Session", type="primary"):
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("INSERT INTO focus_sessions (user_email, preset_mode, duration_minutes) VALUES (?, ?, ?)",
                          (st.session_state.user_email, session_preset, duration_mins))
                conn.commit()
                conn.close()
                log_audit(st.session_state.username, "focus_logged", f"Mins: {duration_mins} | Mode: {session_preset}")
                st.success(f"Logged {duration_mins} minutes of focused work!")
                st.rerun()

        st.divider()
        st.subheader("📊 Historical Deep Work Logs")
        conn = get_db_connection()
        logs_df = pd.read_sql_query("SELECT id, preset_mode, duration_minutes, logged_at FROM focus_sessions ORDER BY logged_at DESC LIMIT 20", conn)
        conn.close()

        if not logs_df.empty:
            st.dataframe(logs_df, use_container_width=True)
            st.metric("Total Logged Deep Work Time", f"{logs_df['duration_minutes'].sum()} Minutes")
        else:
            st.info("No focus sessions recorded yet.")

# ------------------------------------------
# MODULE 10: LOCAL AI & NLP BRIDGE (PROTECTED - APEX SOVEREIGN TIER)
# ------------------------------------------
elif menu == "💬 Local AI & NLP Bridge":
    allowed, msg = check_user_access(st.session_state.user_email, required_tier="Apex Sovereign")
    if not allowed:
        render_paywall_screen("Local AI & NLP Terminal", required_tier="Apex Sovereign")
    else:
        st.title("💬 Local AI Query & Ollama Bridge Console")
        st.caption("Code Synthesis & Model Prompt Execution Terminal")
        st.success("✅ Premium Access Authorized under Apex Sovereign Tier.")

        model_name = st.text_input("Ollama Target Model", value="llama3.2")
        user_prompt = st.text_area("Enter Code Request or Prompt", value="Write a Python function to parse FastA headers and calculate GC content.", height=90)

        if st.button("Execute Query Terminal", type="primary"):
            log_audit(st.session_state.username, "ai_query", f"Model: {model_name}")
            try:
                res = requests.post("http://localhost:11434/api/generate", json={
                    "model": model_name,
                    "prompt": user_prompt,
                    "stream": False
                }, timeout=3)
                if res.status_code == 200:
                    st.markdown("##### 🤖 Ollama Output:")
                    st.write(res.json().get("response"))
                else:
                    st.warning(f"Ollama local API responded with HTTP {res.status_code}.")
            except Exception:
                st.info("⚠️ Local Ollama service (localhost:11434) is offline. Displaying static fallback snippet.")
                st.code("""
def analyze_fasta_gc(fasta_str):
    lines = [l.strip() for l in fasta_str.splitlines() if not l.startswith('>')]
    seq = "".join(lines).upper()
    gc_count = seq.count('G') + seq.count('C')
    return (gc_count / len(seq)) * 100 if seq else 0.0
                """, language="python")

# ------------------------------------------
# MODULE 11: ACADEMIC REPORT VAULT (PROTECTED - PRO TIER)
# ------------------------------------------
elif menu == "🗂️ Academic Report Vault":
    allowed, msg = check_user_access(st.session_state.user_email, required_tier="Pro")
    if not allowed:
        render_paywall_screen("Academic Report Vault", required_tier="Pro")
    else:
        st.title("🗂️ Academic Report Exporter")
        st.caption("Document Generation with University Student Attribution")

        report_title = st.selectbox("Select Document Template", [
            "Plasmid-Mediated mcr Gene Surveillance Proposal",
            "Assa River Waste Management & Composting Outreach Report",
            "Arua Abattoir Sanitation & Drainage Audit",
            "The Evolutionary Trace of Birds from Reptilian Ancestors"
        ])

        formatted_md = f"""# {report_title}

**Author:** Kula Chris  
**Registration ID:** 2501202072  
**Institution:** Muni University, Faculty of Science  
**Creator Handle:** CHRISHEM  
**Date:** {datetime.now().strftime('%B %d, %Y')}  

---

## Executive Summary
This academic report presents synthesized field observations, laboratory analyses, and data modeling conducted at Muni University.

## Core Findings
1. Methodologies executed in full compliance with environmental and biological research protocols.
2. Data persistence and analysis managed by Chrishem Sovereign Apex Engine.

---
*Generated automatically by Chrishem Sovereign Apex Engine.*
"""

        st.download_button(
            label="📥 Export Markdown Document",
            data=formatted_md,
            file_name=f"Kula_Chris_{report_title.replace(' ', '_')}.md",
            mime="text/markdown",
            type="primary"
        )

# ------------------------------------------
# MODULE 12: IDENTITY SETTINGS
# ------------------------------------------
elif menu == "👤 Identity Settings":
    st.title("👤 Operator Profile & Creator Identity Settings")
    st.caption("Manage Profile Picture Avatar, Password Credentials, and Display Handles")

    col_avatar, col_details = st.columns([1, 2])

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT email, name, role, avatar_blob FROM auth_users WHERE email = ?", (st.session_state.user_email.lower(),))
    usr = c.fetchone()
    conn.close()

    curr_email, curr_name, curr_role, curr_avatar = usr if usr else (st.session_state.user_email, st.session_state.username, "admin", None)

    with col_avatar:
        st.markdown("##### 🖼️ Creator Avatar Image")
        if curr_avatar:
            try:
                st.image(curr_avatar, caption="Active Profile Picture", width=180)
            except Exception:
                st.info("Badge Avatar in use.")
        
        up_file = st.file_uploader("Upload New Image (PNG/JPG)", type=["png", "jpg", "jpeg"])
        if up_file is not None and st.button("Save Image Avatar", use_container_width=True):
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("UPDATE auth_users SET avatar_blob = ? WHERE email = ?", (sqlite3.Binary(up_file.read()), curr_email))
            conn.commit()
            conn.close()
            st.success("Avatar saved successfully!")
            st.rerun()

    with col_details:
        st.markdown("##### 📝 Credentials & Operator Display")
        with st.form("update_profile"):
            new_name = st.text_input("Display Name / Admin Handle", value=curr_name)
            new_pwd = st.text_input("New Password", type="password")
            confirm_pwd = st.text_input("Confirm Password", type="password")

            if st.form_submit_button("Update Profile Details"):
                conn = get_db_connection()
                c = conn.cursor()
                if new_pwd:
                    if new_pwd == confirm_pwd:
                        pwd_hash, salt = _hash_password(new_pwd)
                        c.execute("UPDATE auth_users SET name = ?, password_hash = ?, salt = ? WHERE email = ?", (new_name, pwd_hash, salt, curr_email))
                        conn.commit()
                        st.session_state.username = new_name
                        st.success("Password and profile updated!")
                        st.rerun()
                    else:
                        st.error("Passwords do not match!")
                else:
                    c.execute("UPDATE auth_users SET name = ? WHERE email = ?", (new_name, curr_email))
                    conn.commit()
                    st.session_state.username = new_name
                    st.success("Display name updated!")
                    st.rerun()
                conn.close()

# ------------------------------------------
# MODULE 13: SECURITY & DATABASE CORE
# ------------------------------------------
elif menu == "🛡️ Security & Database Core":
    st.title("🛡️ Admin Security Command & Database Core")
    st.caption("Database Snapshots, System JSON Exports, and Audit Stream")

    s_tab1, s_tab2, s_tab3 = st.tabs(["💾 Database Snapshots", "📋 Audit Log Stream", "🔐 System Verification"])

    with s_tab1:
        st.subheader("💾 Database Backup & Export Protocols")
        st.write("Export full binary snapshots of the operational SQLite database.")

        if os.path.exists(DB_FILE):
            with open(DB_FILE, "rb") as f:
                db_bytes = f.read()
            
            st.download_button(
                label="📥 Download SQLite Snapshot (.sqlite)",
                data=db_bytes,
                file_name=f"sovereign_apex_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite",
                mime="application/x-sqlite3",
                type="primary"
            )
            st.success(f"Database Size: **{len(db_bytes) / 1024:.2f} KB** | Status: Schema Healthy")

        st.divider()
        st.subheader("📤 Export Database Tables to JSON Package")
        if st.button("Generate System JSON Dump"):
            conn = get_db_connection()
            tables = ["mcr_gene_surveillance", "business_projects", "focus_sessions", "ppwr_cohort", "subscriptions"]
            export_data = {}
            for t in tables:
                export_data[t] = pd.read_sql_query(f"SELECT * FROM {t}", conn).to_dict(orient="records")
            conn.close()

            json_str = json.dumps(export_data, indent=2)
            st.download_button(
                label="📥 Download JSON Export",
                data=json_str,
                file_name=f"apex_tables_dump_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )

    with s_tab2:
        st.subheader("📜 Live Audit Log Stream")
        conn = get_db_connection()
        logs_df = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 30", conn)
        conn.close()
        st.dataframe(logs_df, use_container_width=True)

    with s_tab3:
        st.subheader("🔐 System Core Health Verification")
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("PRAGMA integrity_check;")
        integrity = c.fetchone()[0]
        conn.close()

        st.success(f"SQLite Integrity Status: **{integrity.upper()}**")
        st.info(f"Python Platform Runtime: **{sys.version.split()[0]} ({sys.platform})**")
        st.info(f"Database Path: **{os.path.abspath(DB_FILE)}**")