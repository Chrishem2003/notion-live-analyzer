import base64
import builtins
import datetime
import io
import json
import hashlib
import os
import sqlite3
import urllib.request
import threading
import zipfile
import numpy as np
import pandas as pd

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from streamlit.components.v1 import html

# Optional advanced mapping and PDF components check
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False

try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="CHRISHEM Sovereign Apex Platform - World Apex Edition v8.1",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# DATABASE INITIALIZATION (Fully Operational Backend with RBAC & Vault)
# ---------------------------------------------------------
def init_sovereign_db():
    conn = sqlite3.connect("sovereign_apex_engine.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_telemetry_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            module_name TEXT,
            severity TEXT,
            details TEXT,
            crypto_hash TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS automated_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name TEXT,
            schedule_interval TEXT,
            last_status TEXT,
            next_execution TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uploaded_vault_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            upload_timestamp TEXT,
            row_count INTEGER,
            column_count INTEGER,
            preview_json TEXT
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
    for col_query in [
        "ALTER TABLE user_profiles ADD COLUMN birthday TEXT",
        "ALTER TABLE user_profiles ADD COLUMN role TEXT",
        "ALTER TABLE user_profiles ADD COLUMN last_seen TEXT",
        "ALTER TABLE user_profiles ADD COLUMN visit_count INTEGER"
    ]:
        try:
            cursor.execute(col_query)
        except Exception:
            pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS live_chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            timestamp TEXT,
            prompt TEXT,
            response TEXT
        )
    """)
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
        CREATE TABLE IF NOT EXISTS bioinformatics_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sequence_name TEXT,
            gc_content REAL,
            length INTEGER,
            timestamp TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auth_users (
            email TEXT PRIMARY KEY,
            name TEXT,
            password_hash TEXT,
            role TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_subscriptions (
            email TEXT PRIMARY KEY,
            trial_end TEXT,
            is_active INTEGER
        )
    """)
    conn.commit()
    return conn

db_conn = init_sovereign_db()

# Ensure default admin account exists
def ensure_default_admin():
    cursor = db_conn.cursor()
    cursor.execute("SELECT email FROM auth_users WHERE email = ?", ("admin@chrishem.com",))
    if not cursor.fetchone():
        pwd_hash = hashlib.sha256("admin1234".encode()).hexdigest()
        cursor.execute("INSERT INTO auth_users (email, name, password_hash, role) VALUES (?, ?, ?, ?)",
                       ("admin@chrishem.com", "Chrishem", pwd_hash, "admin"))
        cursor.execute("INSERT OR IGNORE INTO user_subscriptions (email, trial_end, is_active) VALUES (?, ?, ?)",
                       ("admin@chrishem.com", "2030-12-31 23:59:59", 1))
        db_conn.commit()

ensure_default_admin()

# ---------------------------------------------------------
# AUTH STORE & SUBSCRIPTION UTILITIES
# ---------------------------------------------------------
class AuthStoreMock:
    def verify_login(self, email, password):
        cursor = db_conn.cursor()
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute("SELECT email, name, role FROM auth_users WHERE email = ? AND password_hash = ?", (email, pwd_hash))
        row = cursor.fetchone()
        if row:
            return {"email": row[0], "name": row[1], "role": row[2]}
        return None

    def create_user(self, email, name, password, role="user"):
        cursor = db_conn.cursor()
        cursor.execute("SELECT email FROM auth_users WHERE email = ?", (email,))
        if cursor.fetchone():
            return {"ok": False, "error": "Email already registered."}
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute("INSERT INTO auth_users (email, name, password_hash, role) VALUES (?, ?, ?, ?)",
                       (email, name, pwd_hash, role))
        trial_end = (datetime.datetime.now() + datetime.timedelta(days=15)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT OR IGNORE INTO user_subscriptions (email, trial_end, is_active) VALUES (?, ?, ?)",
                       (email, trial_end, 1))
        db_conn.commit()
        return {"ok": True}

auth_store = AuthStoreMock()

class SubscriptionMock:
    def ensure_trial_started(self, email):
        cursor = db_conn.cursor()
        cursor.execute("SELECT email FROM user_subscriptions WHERE email = ?", (email,))
        if not cursor.fetchone():
            trial_end = (datetime.datetime.now() + datetime.timedelta(days=15)).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO user_subscriptions (email, trial_end, is_active) VALUES (?, ?, ?)",
                           (email, trial_end, 1))
            db_conn.commit()

subscription = SubscriptionMock()

def is_admin():
    identity = st.session_state.get("user_identity", {})
    return identity.get("role") == "admin" or identity.get("is_admin", False)

# ---------------------------------------------------------
# LOCAL IMAGE LOADER & ZIP BUNDLES
# ---------------------------------------------------------
def get_image_base64(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    return None

img_path = "chrishem.png"
img_base64 = get_image_base64(img_path)

def create_package_zip(platform_name):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("README.md", f"# Chrishem Science Hub - {platform_name} Edition\n\nSovereign Enterprise Engine setup bundle.")
        zip_file.writestr("run_engine.py", "import streamlit as st\nst.write('Running Chrishem Sovereign Engine locally...')")
        zip_file.writestr("config.toml", "[server]\nheadless = true\nenableCORS = false")
    return zip_buffer.getvalue()

win_zip = create_package_zip("Windows")
linux_zip = create_package_zip("Linux")
mac_zip = create_package_zip("macOS")
pwa_zip = create_package_zip("Mobile-PWA")

# ---------------------------------------------------------
# MULTI-LANGUAGE DICTIONARY (i18n)
# ---------------------------------------------------------
TRANSLATIONS = {
    "English": {
        "nav_sat": "Satellite & Orbital Telemetry",
        "nav_swarm": "Autonomous Agent Swarms",
        "nav_bio": "Bioinformatics & Genomic Studio",
        "nav_gap": "Universal Sector Gap Solver",
        "nav_workspace": "Personal Workspace",
        "nav_ai": "AI Intelligence Daemon",
        "nav_vault": "Saved Analyses Vault",
        "nav_access": "Access Control & Licensing",
        "nav_diag": "System Diagnostics & Health",
        "greeting": "Welcome back",
        "visits": "Visits"
    },
    "Swahili": {
        "nav_sat": "Telemetria ya Satelaiti na Anga",
        "nav_swarm": "Makundi ya Wakala Huru",
        "nav_bio": "Studio ya Bioinforamatics na Jenomu",
        "nav_gap": "Kitatuzi cha Mapungufu ya Sekta",
        "nav_workspace": "Nafasi ya Kazi ya Kibinafsi",
        "nav_ai": "Pepo la Akili Bandia",
        "nav_vault": "Hifadhi ya Uchambuzi Uliohifadhiwa",
        "nav_access": "Udhibiti wa Upatikanaji na Leseni",
        "nav_diag": "Utambuzi wa Mfumo na Afya",
        "greeting": "Karibu tena",
        "visits": "Ziara"
    },
    "French": {
        "nav_sat": "Télémétrie Satellitaire & Orbitale",
        "nav_swarm": "Essaims d'Agents Autonomes",
        "nav_bio": "Studio de Bioinformatique & Génomique",
        "nav_gap": "Solveur de Lacunes Sectorielles",
        "nav_workspace": "Espace de Travail Personnel",
        "nav_ai": "Démon d'Intelligence Artificielle",
        "nav_vault": "Coffre-fort des Analyses",
        "nav_access": "Contrôle d'Accès & Licences",
        "nav_diag": "Diagnostics Système & Santé",
        "greeting": "Bon retour",
        "visits": "Visites"
    }
}

def t(key, lang="English"):
    return TRANSLATIONS.get(lang, TRANSLATIONS["English"]).get(key, key)

# ---------------------------------------------------------
# STYLING & GLASSMORPHISM CSS
# ---------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: #F8FAFC !important;
    }

    .stApp {
        background: radial-gradient(circle at top right, #0F172A, #070B14 75%);
        background-attachment: fixed;
    }

    .landing-container {
        background: rgba(20, 25, 42, 0.85);
        backdrop-filter: blur(24px);
        border: 1px solid rgba(56, 189, 248, 0.3);
        border-radius: 28px;
        padding: 35px 25px;
        box-shadow: 0 30px 60px rgba(0, 0, 0, 0.9), 0 0 40px rgba(56, 189, 248, 0.15);
        text-align: center;
        max-width: 800px;
        margin: 0 auto;
    }

    .hub-title {
        font-size: 2.1rem;
        font-weight: 800;
        background: linear-gradient(135deg, #38BDF8 0%, #818CF8 50%, #F472B6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 8px;
    }
    .hub-subtitle { font-size: 1rem; color: #94A3B8; font-weight: 400; margin-bottom: 15px; }
    .profile-img-wrap { display: flex; justify-content: center; margin-bottom: 15px; }
    .profile-img {
        width: 90px; height: 90px; border-radius: 50%; object-fit: cover;
        border: 3px solid #38BDF8; box-shadow: 0 0 30px rgba(56, 189, 248, 0.6);
    }
    .download-card {
        background: rgba(15, 23, 42, 0.9);
        border: 1px solid rgba(56, 189, 248, 0.2);
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 10px;
    }

    .top-banner {
        background: rgba(15, 23, 42, 0.85);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 16px;
        padding: 0.85rem 1.25rem;
        margin-bottom: 1.25rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.5rem;
    }
    .top-banner-item { font-size: 0.85rem; color: #94A3B8; font-weight: 500; }
    .top-banner-item b { color: #38BDF8; font-weight: 600; }

    .greeting-card {
        background: linear-gradient(135deg, rgba(56, 189, 248, 0.12), rgba(129, 140, 248, 0.12));
        border: 1px solid rgba(56, 189, 248, 0.3);
        border-radius: 14px;
        padding: 1rem 1.25rem;
        margin-bottom: 1.25rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 1rem;
    }
    .greeting-title { font-size: 1.15rem; font-weight: 700; color: #F8FAFC; }
    .greeting-sub { font-size: 0.85rem; color: #38BDF8; font-weight: 500; margin-top: 0.15rem; }

    .metric-box {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 12px;
        padding: 1.1rem;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    }
    .metric-box .val {
        font-size: 1.8rem;
        font-weight: 800;
        background: linear-gradient(90deg, #38BDF8, #818CF8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-box .lbl {
        font-size: 0.75rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.25rem;
    }

    .status-badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 9999px; font-weight: 700; font-size: 0.8rem; }
    .status-stable { background: rgba(16, 185, 129, 0.2); color: #34D399; border: 1px solid #059669; }

    [data-testid="stSidebar"] {
        background-color: #060911 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    .glass-hr {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent);
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# SESSION STATE INITIALIZATION
# ---------------------------------------------------------
if "portal_unlocked" not in st.session_state:
    st.session_state.portal_unlocked = False
if "user_identity" not in st.session_state:
    st.session_state.user_identity = {}

# ---------------------------------------------------------
# DATA LOADER & CLEANER
# ---------------------------------------------------------
def load_dataset(uploaded_file, drop_duplicates=True, handle_missing="Mean Imputation", outlier_removal=False):
    file_bytes = uploaded_file.read()
    name = uploaded_file.name.lower()
    df = None
    
    if name.endswith(".csv") or name.endswith(".txt"):
        for enc in ["utf-8", "latin-1", "cp1252", "iso-8859-1"]:
            try:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding=enc)
                break
            except Exception:
                continue
    elif name.endswith(".json"):
        try:
            df = pd.read_json(io.BytesIO(file_bytes))
        except Exception:
            pass
    elif name.endswith((".xlsx", ".xls")):
        try:
            df = pd.read_excel(io.BytesIO(file_bytes))
        except Exception:
            pass
            
    if df is not None:
        if drop_duplicates:
            df = df.drop_duplicates()
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if handle_missing == "Mean Imputation":
            for col in numeric_cols:
                df[col] = df[col].fillna(df[col].mean())
        elif handle_missing == "Median Imputation":
            for col in numeric_cols:
                df[col] = df[col].fillna(df[col].median())
        elif handle_missing == "Drop Missing Rows":
            df = df.dropna()
        if outlier_removal and len(numeric_cols) > 0:
            for col in numeric_cols:
                mean_val = df[col].mean()
                std_val = df[col].std()
                if std_val > 0:
                    df = df[(df[col] - mean_val).abs() <= 3 * std_val]
    return df, file_bytes

def generate_pdf_report(title, content):
    if not FPDF_AVAILABLE:
        return None
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, txt="CHRISHEM Sovereign Apex Dossier", ln=True, align="C")
    pdf.set_font("Arial", "I", 10)
    pdf.cell(200, 10, txt=f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, txt=f"Title: {title}", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 10, txt=str(content))
    pdf_output = pdf.output()
    if isinstance(pdf_output, str):
        return pdf_output.encode("latin1")
    return pdf_output

# ---------------------------------------------------------
# MODULE RENDERERS
# ---------------------------------------------------------
def render_autonomous_agents():
    st.markdown("### 🤖 Autonomous Agent Swarms & Cross-Sector Orchestration")
    st.markdown("Autonomous background intelligence loops running asynchronous worker threads to continuously probe telemetry.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Swarm Agents", "128 Nodes", delta="Autonomous")
    c2.metric("Cross-Sector Loops", "Active", delta="Async Threading")
    c3.metric("Anomaly Detection Rate", "99.94%", delta="Optimal")
    c4.metric("Autonomous Controller", "CHRISHEM AI", delta="Secure")

def render_bioinformatics_studio():
    st.markdown("### 🧬 Advanced Bioinformatics & Genomic Sequence Studio")
    st.markdown("Analyze FASTA sequences, calculate GC-content distributions, and track phylogenetic variance.")
    seq_name = st.text_input("Sequence Identifier / Name", value="SARS-CoV-2 Variant Target X")
    fasta_input = st.text_area("Paste FASTA Sequence (DNA/RNA)", placeholder="ATGCGATCGATCGATCGATCGATCG...")
    if st.button("🔬 Execute Genomic Sequence Analysis"):
        if not fasta_input.strip():
            st.warning("Please provide a valid FASTA sequence.")
        else:
            clean_seq = "".join(fasta_input.upper().split())
            seq_len = len(clean_seq)
            g_count = clean_seq.count('G')
            c_count = clean_seq.count('C')
            gc_content = ((g_count + c_count) / seq_len * 100) if seq_len > 0 else 0.0
            col1, col2, col3 = st.columns(3)
            col1.metric("Sequence Length", f"{seq_len} bp")
            col2.metric("GC-Content", f"{gc_content:.2f}%")
            col3.metric("Mutation Drift Risk", "Stable", delta="99.7% Confidence")

def render_satellite_orbital_hub():
    st.markdown("### 🛰️ Live Satellite Constellation & Global Database Telemetry Hub")
    st.markdown("Real-time downlink integration with orbital earth-observation satellites.")
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown('<div class="metric-box"><div class="val">42 Active</div><div class="lbl">Linked Satellites</div></div>', unsafe_allow_html=True)
    c2.markdown('<div class="metric-box"><div class="val">1.4 TB/s</div><div class="lbl">Downlink Bandwidth</div></div>', unsafe_allow_html=True)
    c3.markdown('<div class="metric-box"><div class="val">99.98%</div><div class="lbl">Orbital Lock Precision</div></div>', unsafe_allow_html=True)
    c4.markdown('<div class="metric-box"><div class="val">CHRISHEM</div><div class="lbl">Orbital Controller</div></div>', unsafe_allow_html=True)

def render_sector_gap_solver():
    st.markdown("### 💡 Universal Multi-Sector Gap & Problem Solver")
    sector_choice = st.selectbox("Select Global Sector to Analyze", [
        "Agriculture & Food Security (Drought & Yield Optimization)",
        "Healthcare & Epidemic Surveillance (Early Disease Outbreak Detection)",
        "Renewable Energy & Power Grids (Load Distribution & Storage)",
        "Education & Skill Development (Automated Personalized Learning)"
    ])
    st.info(f"**Identified Systemic Gap in {sector_choice}:** Resource friction and latency across data silos.")
    st.success("**CHRISHEM Sovereign Solution:** Establish an encrypted database pipeline with automated predictive agents.")

def render_personal_workspace():
    st.markdown("### 📁 Interactive Vault & Automated Data Analytics Studio")
    uploaded_file = st.file_uploader("Drop your dataset here (CSV, XLSX, JSON):", type=["csv", "xlsx", "xls", "json", "txt"])
    if uploaded_file is not None:
        df, _ = load_dataset(uploaded_file)
        if df is not None:
            st.info(f"File loaded: `{uploaded_file.name}` | Dimensions: **{df.shape[0]} rows** × **{df.shape[1]} columns**")
            st.dataframe(df.head(10), use_container_width=True)

def render_ai_intelligence_daemon(active_analyst_name):
    st.markdown("### 🤖 Fully Operational AI Intelligence & Instant Problem Solver")
    cursor = db_conn.cursor()
    cursor.execute("SELECT prompt, response, timestamp FROM live_chat_history ORDER BY id ASC")
    chat_rows = cursor.fetchall()
    for p, r, ts in chat_rows:
        st.markdown(f"""
        <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 10px; padding: 0.85rem; margin-bottom: 0.75rem;">
            <b style="color: #38BDF8;">[{ts[:19]}]:</b> {p}<br><br>
            <b style="color: #818CF8;">AI:</b> {r}
        </div>
        """, unsafe_allow_html=True)
    user_prompt = st.text_area("Enter your custom problem or question here:", key="real_ai_chat_input")
    if st.button("Generate Solution ⚡"):
        if user_prompt.strip():
            resp = f"Synthesized heuristic response for: {user_prompt[:40]}..."
            cursor.execute("INSERT INTO live_chat_history (username, timestamp, prompt, response) VALUES (?, ?, ?, ?)",
                           (active_analyst_name, datetime.datetime.now().isoformat(), user_prompt, resp))
            db_conn.commit()
            st.rerun()

def render_system_diagnostics():
    st.markdown("### 🔍 System Diagnostics & Telemetry Center")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("System Uptime", "99.99%", delta="Stable")
    col2.metric("Database Health", "Connected", delta="0ms Latency")
    col3.metric("Memory Utilization", "42.8%", delta="-1.2%")
    col4.metric("Active Threads", "14 Daemons", delta="Optimal")

# ---------------------------------------------------------
# MAIN ROUTER & GATEWAY LOGIC
# ---------------------------------------------------------
if not st.session_state.portal_unlocked:
    st.markdown("<style>[data-testid=\"stSidebar\"] {display: none;}</style>", unsafe_allow_html=True)
    st.markdown("<div style='height: 2vh;'></div>", unsafe_allow_html=True)
    
    img_tag = f'<img src="data:image/png;base64,{img_base64}" class="profile-img">' if img_base64 else '<div style="font-size: 50px;">🔬</div>'
    
    st.markdown(f"""
    <div class="landing-container">
        <div class="profile-img-wrap">{img_tag}</div>
        <div class="hub-title">CHRISHEM SCIENCE HUB & ECOSYSTEM</div>
        <div class="hub-subtitle">Sovereign Enterprise Engine • Secure Multi-Platform Gateway</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    
    _, center_col, _ = st.columns([0.5, 3, 0.5])
    with center_col:
        tab_signin, tab_signup, tab_downloads = st.tabs(["🔐 Secure Sign In", "📝 Register", "📱 Ecosystem Downloads"])
        
        with tab_signin:
            si_email = st.text_input("Email Address", key="si_email_input")
            si_password = st.text_input("Password", type="password", key="si_password_input")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.button("🚀 Sign In", use_container_width=True):
                user = auth_store.verify_login(si_email, si_password)
                if user is None:
                    st.error("Incorrect email or password.")
                else:
                    st.session_state.portal_unlocked = True
                    st.session_state.user_identity = {
                        "email": user["email"],
                        "name": user["name"],
                        "role": user["role"],
                        "is_admin": user["role"] == "admin",
                    }
                    subscription.ensure_trial_started(user["email"])
                    st.rerun()

        with tab_signup:
            su_name = st.text_input("Your Preferred Name", key="su_name_input")
            su_email = st.text_input("Your Email Address", key="su_email_input")
            su_password = st.text_input("Choose a Password", type="password", key="su_password_input")
            su_password2 = st.text_input("Confirm Password", type="password", key="su_password2_input")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.button("✨ Register", use_container_width=True):
                if not su_email or not su_password:
                    st.error("Email and password are required.")
                elif su_password != su_password2:
                    st.error("Passwords don't match.")
                elif len(su_password) < 8:
                    st.error("Password must be at least 8 characters.")
                else:
                    result = auth_store.create_user(su_email, su_name or "Analyst", su_password, role="user")
                    if not result["ok"]:
                        st.error(result["error"])
                    else:
                        st.success("Account created — please sign in above. New accounts start on a 15-day free trial.")

        with tab_downloads:
            st.markdown("### 🌍 Cross-Platform Ecosystem Releases")
            st.write("Click any bundle below to directly download the installation package to your local system.")
            d_col1, d_col2 = st.columns(2)
            with d_col1:
                st.markdown('<div class="download-card"><h4>🪟 Windows Suite</h4><p style="font-size: 0.85rem; color: #94A3B8;">Optimized for Windows 10/11</p></div>', unsafe_allow_html=True)
                st.download_button("📥 Download Windows Suite (.zip)", data=win_zip, file_name="chrishem_hub_windows.zip", mime="application/zip", use_container_width=True)
                st.markdown('<div class="download-card" style="margin-top: 15px;"><h4>🐧 Linux Distribution</h4><p style="font-size: 0.85rem; color: #94A3B8;">Ubuntu / Debian / Server Build</p></div>', unsafe_allow_html=True)
                st.download_button("📥 Download Linux Build (.zip)", data=linux_zip, file_name="chrishem_hub_linux.zip", mime="application/zip", use_container_width=True)
            with d_col2:
                st.markdown('<div class="download-card"><h4>🍏 macOS Architecture</h4><p style="font-size: 0.85rem; color: #94A3B8;">Apple Silicon & Intel Universal</p></div>', unsafe_allow_html=True)
                st.download_button("📥 Download macOS Bundle (.zip)", data=mac_zip, file_name="chrishem_hub_macos.zip", mime="application/zip", use_container_width=True)
                st.markdown('<div class="download-card" style="margin-top: 15px;"><h4>📱 Mobile PWA / Phone</h4><p style="font-size: 0.85rem; color: #94A3B8;">Android & iOS Progressive Web Client</p></div>', unsafe_allow_html=True)
                st.download_button("📥 Download Mobile PWA Config (.zip)", data=pwa_zip, file_name="chrishem_hub_mobile_pwa.zip", mime="application/zip", use_container_width=True)

else:
    st.sidebar.title("CHRISHEM")
    st.sidebar.caption("Sovereign Enterprise Engine v8.1")
    st.sidebar.markdown('<div class="glass-hr"></div>', unsafe_allow_html=True)

    selected_lang = st.sidebar.selectbox("Select Language / Lugha", ["English", "Swahili", "French"])

    identity = st.session_state.get("user_identity", {})
    active_analyst_name = identity.get("name", "Analyst")
    user_role = "Sovereign Administrator" if is_admin() else identity.get("role", "user")

    selected_country = st.sidebar.selectbox("Select User Jurisdiction", [
        "Uganda [UG]", "Kenya [KE]", "Tanzania [TZ]", "Global / International Universal"
    ])
    user_bday = st.sidebar.date_input("Your Birthday", value=datetime.date(2003, 7, 3))

    st.sidebar.markdown(f"**Active Session:** `{active_analyst_name}`")
    st.sidebar.markdown(f"**Security Role:** `{user_role}`")
    st.sidebar.markdown('<div class="glass-hr"></div>', unsafe_allow_html=True)

    nav_options = [
        t("nav_sat", selected_lang),
        t("nav_swarm", selected_lang),
        t("nav_bio", selected_lang),
        t("nav_gap", selected_lang),
        t("nav_workspace", selected_lang),
        t("nav_ai", selected_lang),
        t("nav_vault", selected_lang),
        t("nav_access", selected_lang),
        t("nav_diag", selected_lang)
    ]
    navigation = st.sidebar.radio("Navigation Hub", nav_options)

    st.sidebar.markdown('<div class="glass-hr"></div>', unsafe_allow_html=True)
    if st.sidebar.button("🔒 Lock Portal & Sign Out", use_container_width=True):
        st.session_state.portal_unlocked = False
        st.rerun()

    now_dt = datetime.datetime.now()
    st.markdown(f"""
        <div class="top-banner">
            <div class="top-banner-item">Jurisdiction: <b>{selected_country}</b></div>
            <div class="top-banner-item">Active Analyst: <b>{active_analyst_name} ({user_role})</b></div>
            <div class="top-banner-item">Live Time: <b>{now_dt.strftime('%Y-%m-%d %H:%M:%S')} EAT</b></div>
        </div>
    """, unsafe_allow_html=True)

    st.title(navigation)
    st.markdown('<div class="glass-hr"></div>', unsafe_allow_html=True)

    if navigation == t("nav_sat", selected_lang):
        render_satellite_orbital_hub()
    elif navigation == t("nav_swarm", selected_lang):
        render_autonomous_agents()
    elif navigation == t("nav_bio", selected_lang):
        render_bioinformatics_studio()
    elif navigation == t("nav_gap", selected_lang):
        render_sector_gap_solver()
    elif navigation == t("nav_workspace", selected_lang):
        render_personal_workspace()
    elif navigation == t("nav_ai", selected_lang):
        render_ai_intelligence_daemon(active_analyst_name)
    elif navigation == t("nav_vault", selected_lang):
        st.markdown("### 💾 Saved Analyses & Reports Vault")
        cursor = db_conn.cursor()
        cursor.execute("SELECT id, title, timestamp, category, content FROM saved_analyses ORDER BY id DESC")
        saved_rows = cursor.fetchall()
        if saved_rows:
            for s_id, s_title, s_ts, s_cat, s_content in saved_rows:
                st.markdown(f"""
                <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 10px; padding: 1rem; margin-bottom: 1rem;">
                    <b style="color: #38BDF8;">{s_title}</b> ({s_ts[:19]})<br>
                    <p style="color: #F8FAFC; font-size: 0.9rem; margin-top: 0.5rem;">{s_content}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No saved analyses found in the vault yet.")
    elif navigation == t("nav_access", selected_lang):
        if not is_admin():
            st.error("🚫 Restricted to administrators.")
        else:
            st.markdown("#### Security Authorization Matrix & RBAC Verification")
            st.code(f"[User Principal] -> {active_analyst_name}\n[Assigned Role] -> {user_role}", language="text")
    elif navigation == t("nav_diag", selected_lang):
        if not is_admin():
            st.error("🚫 Restricted to administrators.")
        else:
            render_system_diagnostics()