import base64
import io
import os
import zipfile
import builtins
import datetime
import json
import hashlib
import sqlite3
import urllib.request
import threading
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

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Chrishem Science Hub - Secure Gateway",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- LOCAL IMAGE LOADER ---
def get_image_base64(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    return None

img_path = "chrishem.png"
img_base64 = get_image_base64(img_path)

# --- GENERATE IN-MEMORY ARCHIVE BUNDLES FOR REAL DOWNLOADS ---
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

# --- COSMIC STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; color: #F8FAFC !important; }
    .stApp { background: radial-gradient(circle at 15% 20%, #0c0f1d 0%, #05070b 85%); color: #f3f4f6; }
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
    .status-critical { background: rgba(239, 68, 68, 0.2); color: #F87171; border: 1px solid #DC2626; }
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

# --- SESSION STATE INITIALIZATION ---
if "portal_unlocked" not in st.session_state:
    st.session_state.portal_unlocked = False
if "user_identity" not in st.session_state:
    st.session_state.user_identity = {}

# --- DATABASE SETUP ---
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
    conn.commit()
    return conn

db_conn = init_sovereign_db()

# --- MULTI-LANGUAGE DICTIONARY (i18n) ---
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

# --- HELPER FUNCTIONS ---
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

# --- GATEWAY SCREEN (LOCKED STATE) ---
if not st.session_state.portal_unlocked:
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {display: none;}
        </style>
    """, unsafe_allow_html=True)

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
                # Mock or hook authentication verification here
                if si_email and si_password:
                    st.session_state.portal_unlocked = True
                    st.session_state.user_identity = {
                        "email": si_email,
                        "name": "Chrishem",
                        "role": "admin",
                        "is_admin": True,
                    }
                    st.rerun()
                else:
                    st.error("Please provide email and password.")

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
                    st.success("Account created — please sign in above.")

        with tab_downloads:
            st.markdown("### 🌐 Cross-Platform Ecosystem Releases")
            st.write("Click any bundle below to directly download the installation package to your local system.")
            
            d_col1, d_col2 = st.columns(2)
            
            with d_col1:
                st.markdown("""
                <div class="download-card">
                    <h4>🪟 Windows Suite</h4>
                    <p style='font-size: 0.85rem; color: #94A3B8;'>Optimized for Windows 10/11 (WSL2 / Desktop Engine)</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.download_button(
                    label="📥 Download Windows Suite (.zip)",
                    data=win_zip,
                    file_name="chrishem_hub_windows.zip",
                    mime="application/zip",
                    use_container_width=True
                )

                st.markdown("""
                <div class="download-card" style="margin-top: 15px;">
                    <h4>🐧 Linux Distribution</h4>
                    <p style='font-size: 0.85rem; color: #94A3B8;'>Ubuntu / Debian / Enterprise Server Build</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.download_button(
                    label="📥 Download Linux Build (.zip)",
                    data=linux_zip,
                    file_name="chrishem_hub_linux.zip",
                    mime="application/zip",
                    use_container_width=True
                )

            with d_col2:
                st.markdown("""
                <div class="download-card">
                    <h4>🍎 macOS Architecture</h4>
                    <p style='font-size: 0.85rem; color: #94A3B8;'>Apple Silicon (M1/M2/M3) & Intel Universal</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.download_button(
                    label="📥 Download macOS Bundle (.zip)",
                    data=mac_zip,
                    file_name="chrishem_hub_macos.zip",
                    mime="application/zip",
                    use_container_width=True
                )

                st.markdown("""
                <div class="download-card" style="margin-top: 15px;">
                    <h4>📱 Mobile PWA / Phone</h4>
                    <p style='font-size: 0.85rem; color: #94A3B8;'>Android & iOS Progressive Web Client</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.download_button(
                    label="📥 Download Mobile PWA Config (.zip)",
                    data=pwa_zip,
                    file_name="chrishem_hub_mobile_pwa.zip",
                    mime="application/zip",
                    use_container_width=True
                )

# --- UNLOCKED DASHBOARD STATE ---
else:
    identity = st.session_state.get("user_identity", {"name": "Chrishem", "role": "Supreme Architect"})
    
    st.sidebar.success(f"🔓 Logged in as: {identity.get('name')}")
    st.sidebar.markdown(f"**Role:** `{identity.get('role')}`")
    
    if st.sidebar.button("🔒 Lock Portal & Sign Out", use_container_width=True):
        st.session_state.portal_unlocked = False
        st.rerun()
        
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📁 System Navigation")
    
    selected_lang = st.sidebar.selectbox("Select Language / Lugha", ["English", "Swahili", "French"])
    
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

    st.title("⚡ Chrishem Sovereign Apex Hub")
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Gateway Status", "Unlocked", delta="Secure Session")
    col2.metric("Active User", identity.get("name"))
    col3.metric("Security Level", "Enclave Verified", delta="Tier-1")
    
    st.markdown("### 🌟 Welcome to the Core Ecosystem")
    st.write("Authentication verified. Use the sidebar navigation menu to access your complete portfolio of tools and analytical pages.")
```[cite: 1]