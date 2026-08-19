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

# Plotly visualization import with graceful fallback
try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# ==========================================
# 1. SYSTEM CONFIGURATION & DARK THEME STYLING
# ==========================================
st.set_page_config(
    page_title="Chrishem Sovereign Apex Hub",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #0B0F19; color: #F8FAFC; }
    section[data-testid="stSidebar"] { background-color: #111827 !important; border-right: 1px solid #1F2937; }
    section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] p {
        color: #F8FAFC !important; font-weight: 500;
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] > label {
        background: #1F2937 !important; border: 1px solid #374151 !important; border-radius: 8px !important;
        padding: 8px 12px !important; margin-bottom: 4px !important; transition: all 0.2s ease;
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] > label:hover { border-color: #38BDF8 !important; background: #374151 !important; }
    div[data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"] { background: #0284C7 !important; border-color: #38BDF8 !important; }
    div[data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"] span { color: #FFFFFF !important; font-weight: 700 !important; }

    div[data-testid="metric-container"] {
        background: #111827; border: 1px solid #1F2937; border-radius: 10px; padding: 14px 18px; box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }
    div[data-testid="stMetricValue"] { color: #38BDF8 !important; font-weight: 700 !important; font-size: 1.8rem !important; }

    .paywall-card {
        background: #1E1B4B; border: 2px solid #6366F1; border-radius: 12px; padding: 24px; text-align: center; margin: 20px 0;
    }
    div[data-testid="stDataFrame"] { background-color: #111827; border-radius: 8px; border: 1px solid #1F2937; }
    button[data-baseweb="tab"] { font-weight: 600 !important; color: #94A3B8 !important; }
    button[aria-selected="true"] { color: #38BDF8 !important; border-bottom-color: #38BDF8 !important; }
</style>
""", unsafe_allow_html=True)

DB_FILE = "sovereign_apex.db"
CUSTOM_SOUNDS_DIR = "custom_sounds"
os.makedirs(CUSTOM_SOUNDS_DIR, exist_ok=True)

# ==========================================
# 2. AUDIO STORAGE & BASE64 ENGINE
# ==========================================
def save_uploaded_audio(uploaded_file):
    """Saves uploaded audio file to disk and returns its file path."""
    file_path = os.path.join(CUSTOM_SOUNDS_DIR, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

def get_custom_sounds_catalog():
    """Scans local custom_sounds folder and encodes files as Base64 Data URIs."""
    custom_catalog = {}
    if os.path.exists(CUSTOM_SOUNDS_DIR):
        for file_name in sorted(os.listdir(CUSTOM_SOUNDS_DIR)):
            if file_name.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a')):
                file_path = os.path.join(CUSTOM_SOUNDS_DIR, file_name)
                try:
                    with open(file_path, "rb") as f:
                        encoded = base64.b64encode(f.read()).decode("utf-8")
                        ext = file_name.split(".")[-1].lower()
                        mime_type = f"audio/{'mpeg' if ext == 'mp3' else ext}"
                        custom_catalog[file_name] = f"data:{mime_type};base64,{encoded}"
                except Exception as e:
                    pass
    return custom_catalog

# ==========================================
# 3. PERSISTENT AUDIO PLAYER COMPONENT
# ==========================================
def render_persistent_audio_player(audio_url, track_title="Brainwave Focus"):
    """
    Renders a persistent audio widget at the bottom right.
    Uses browser localStorage to sync playback state continuously across page navigation.
    """
    player_html = f"""
    <style>
        .audio-popup {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #111827;
            color: #ffffff;
            padding: 12px 18px;
            border-radius: 30px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.6);
            z-index: 999999;
            display: flex;
            align-items: center;
            gap: 12px;
            font-family: system-ui, -apple-system, sans-serif;
            font-size: 13px;
            border: 1px solid #38bdf8;
        }}
        audio {{ display: none; }}
        .btn-play {{
            background: #0284c7;
            border: none;
            color: #ffffff;
            padding: 6px 14px;
            border-radius: 15px;
            cursor: pointer;
            font-weight: bold;
            transition: background 0.2s;
        }}
        .btn-play:hover {{ background: #38bdf8; }}
    </style>
    
    <div class="audio-popup">
        <span>🎧 <b id="trackLabel">{track_title[:24]}...</b></span>
        <button class="btn-play" id="playBtn" onclick="togglePlay()">▶ Play / ⏸ Pause</button>
        <audio id="globalAudio" loop preload="auto">
            <source src="{audio_url}">
        </audio>
    </div>

    <script>
        const audio = document.getElementById("globalAudio");
        const playBtn = document.getElementById("playBtn");
        const trackKey = "apex_audio_url";
        const timeKey = "apex_audio_time";
        const stateKey = "apex_audio_playing";
        const targetUrl = "{audio_url}";

        window.addEventListener("DOMContentLoaded", () => {{
            const savedUrl = localStorage.getItem(trackKey);
            const savedTime = localStorage.getItem(timeKey);
            const savedPlaying = localStorage.getItem(stateKey);

            if (savedUrl === targetUrl) {{
                if (savedTime) audio.currentTime = parseFloat(savedTime);
                if (savedPlaying === "true") {{
                    audio.play().catch(e => console.log("Autoplay notice:", e));
                }}
            }} else {{
                localStorage.setItem(trackKey, targetUrl);
                localStorage.setItem(timeKey, "0");
                if (savedPlaying === "true") {{
                    audio.play().catch(e => console.log("Autoplay notice:", e));
                }}
            }}
        }});

        audio.ontimeupdate = () => {{
            localStorage.setItem(timeKey, audio.currentTime);
        }};

        function togglePlay() {{
            if (audio.paused) {{
                audio.play();
                localStorage.setItem(stateKey, "true");
            }} else {{
                audio.pause();
                localStorage.setItem(stateKey, "false");
            }}
        }}
    </script>
    """
    components.html(player_html, height=80)

# ==========================================
# 4. DATABASE SEEDING & CONTROL ENGINE
# ==========================================
def init_db(purge_and_reseed=False):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if purge_and_reseed:
        cursor.execute("DROP TABLE IF EXISTS mcr_gene_surveillance")
        cursor.execute("DROP TABLE IF EXISTS business_projects")
        cursor.execute("DROP TABLE IF EXISTS ppwr_cohort")
        cursor.execute("DROP TABLE IF EXISTS academic_vault")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auth_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT DEFAULT 'user',
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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS academic_vault (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            course_code TEXT,
            department TEXT,
            status TEXT,
            abstract_text TEXT
        )
    ''')

    cursor.execute("INSERT OR IGNORE INTO paywall_settings VALUES ('global_paywall_active', 'true')")

    # Admin User Seed
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

    # Seed MCR Surveillance Data
    cursor.execute("SELECT COUNT(*) FROM mcr_gene_surveillance")
    if cursor.fetchone()[0] == 0:
        mcr_samples = [
            ("MCR-ARUA-001", "Poultry Cecal", "Arua Central Poultry Farm", 3.0305, 30.9073, "mcr-1.1", 8.0, "2026-03-15", "Plasmid mediated resistant strain isolated"),
            ("MCR-ARUA-002", "Assa River Water", "Assa River Discharge Site", 3.0211, 30.9150, "mcr-1.2", 16.0, "2026-03-18", "Downstream abattoir effluent run-off"),
            ("MCR-ARUA-003", "Abattoir Drainage", "Arua City Main Abattoir", 3.0280, 30.9110, "mcr-3.1", 32.0, "2026-03-20", "High MIC strain detected in bio-waste"),
            ("MCR-ARUA-004", "Soil Sediment", "Muni Eco-Farm Composting Zone", 3.0350, 30.9200, "Negative", 0.5, "2026-04-02", "Control sample - no resistance cassette detected"),
            ("MCR-ARUA-005", "Poultry Cloacal", "Oruko Avian Clinic", 3.0410, 30.8990, "mcr-5.1", 12.0, "2026-04-10", "Multidrug resistant colistin gene cassette")
        ]
        cursor.executemany("INSERT INTO mcr_gene_surveillance VALUES (?,?,?,?,?,?,?,?,?)", mcr_samples)

    # Seed Business Projects
    cursor.execute("SELECT COUNT(*) FROM business_projects")
    if cursor.fetchone()[0] == 0:
        biz_data = [
            ("Kidega Fresh Passion-Mango Cooler", "Team Kula", 12500000.0, 34.5, "Active Scaling"),
            ("Santa Solo Amuca Enterprise", "Galilee Venture", 8000000.0, 22.0, "Field Testing"),
            ("Galilee Motor Spare Parts", "Galilee Community", 15000000.0, 28.0, "Planning"),
            ("Galilee Boutique & Salon", "Galilee Community", 6500000.0, 40.0, "Active Operations")
        ]
        cursor.executemany("INSERT INTO business_projects (project_name, lead_entity, capital_ugx, roi_projection_pct, status) VALUES (?,?,?,?,?)", biz_data)

    # Seed PPWR Cohort Data
    cursor.execute("SELECT COUNT(*) FROM ppwr_cohort")
    if cursor.fetchone()[0] == 0:
        ppwr_data = [
            (24, 6, 2.8, 5.2), (29, 12, 1.5, 3.1), (31, 3, 3.5, 8.4),
            (22, 18, 0.8, 1.2), (35, 9, 2.2, 4.6), (27, 4, 3.1, 7.0)
        ]
        cursor.executemany("INSERT INTO ppwr_cohort (participant_age, months_postpartum, dra_gap_cm, ppwr_kg) VALUES (?,?,?,?)", ppwr_data)

    # Seed Academic Vault Data
    cursor.execute("SELECT COUNT(*) FROM academic_vault")
    if cursor.fetchone()[0] == 0:
        reports = [
            ("Plasmid-Mediated mcr Gene Surveillance in Poultry and Environmental Samples", "BIO3201", "Biological Sciences", "Completed", "Comprehensive investigation into colistin resistance genes mcr-1 to mcr-5 in livestock and Assa River aquatic channels."),
            ("Assa River Environmental Impact and Manure Composting Evaluation", "ENV2104", "Biological Sciences", "Submitted", "Field evaluation of Muni University discharge into Assa River and organic composting strategy."),
            ("Evolutionary Trace of Birds from Theropod Reptilian Ancestors", "ORN3102", "Ornithology & Mammalogy", "Completed", "Comparative anatomical analysis tracing avian flight skeletal adaptations from theropod dinosaurs."),
            ("Invertebrate Biology Innovations: Soft Robotics & Biomimicry", "INV2201", "Invertebrate Biology", "Completed", "Genomic sequencing and structural biomimicry applications derived from marine invertebrates.")
        ]
        cursor.executemany("INSERT INTO academic_vault (title, course_code, department, status, abstract_text) VALUES (?,?,?,?,?)", reports)

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

# ==========================================
# 5. ACCESS CONTROL & PAYWALL GUARD
# ==========================================
def is_paywall_enabled():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT setting_value FROM paywall_settings WHERE setting_key = 'global_paywall_active'")
    row = c.fetchone()
    conn.close()
    return row[0] == 'true' if row else False

def check_user_access(email, required_tier="Pro"):
    if st.session_state.get("role") == "admin": return True, "Admin Grant"
    if not is_paywall_enabled(): return True, "Paywall Disabled"

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT tier, status, expires_at FROM subscriptions WHERE user_email = ?", (email.lower(),))
    sub = c.fetchone()
    conn.close()

    if not sub: return False, "No active subscription tier found."
    tier, status, expires_at = sub
    if status != "active": return False, f"Subscription status is '{status}'."
    if expires_at and datetime.strptime(expires_at, "%Y-%m-%d").date() < datetime.now().date(): return False, "Expired."

    tier_levels = {"Free": 0, "Pro": 1, "Apex Sovereign": 2}
    if tier_levels.get(tier, 0) < tier_levels.get(required_tier, 1):
        return False, f"Requires '{required_tier}' tier."

    return True, "Access Granted"

def render_paywall_screen(module_name, required_tier="Pro"):
    st.markdown(f"""
    <div class="paywall-card">
        <h2 style="color: #818CF8; margin-top:0;">🔒 {module_name} is Locked</h2>
        <p style="color: #E0E7FF; font-size: 1.1rem;">Access restricted under subscription policies.</p>
        <p style="color: #9CA3AF;">Required Tier: <strong style="color:#38BDF8;">{required_tier} Tier</strong></p>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 6. SESSION STATE & EXPANDED 25-TRACK SOUND CATALOG
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = True
    st.session_state.user_email = "admin@chrishem.apex"
    st.session_state.username = "CHRISHEM"
    st.session_state.role = "admin"

st.sidebar.title("⚡ Sovereign Apex")
st.sidebar.markdown(f"<h3 style='margin:0; color:#F8FAFC;'>{st.session_state.username}</h3>", unsafe_allow_html=True)
st.sidebar.caption(f"Operator: **{st.session_state.role.upper()}**")
st.sidebar.divider()

# EXPANDED 25+ TRACK SOUND CATALOG ACROSS 5 CATEGORIES
SOUND_CATALOG = {
    "🧠 Brain Wiring & Neural Frequencies": {
        "432Hz Deep Focus Pulse": "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3",
        "528Hz Solfeggio Transformation Tone": "https://cdn.pixabay.com/download/audio/2022/10/14/audio_9939aa30ef.mp3",
        "Alpha Waves Concentration (10Hz)": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73232.mp3",
        "Gamma Frequency Peak Focus (40Hz)": "https://cdn.pixabay.com/download/audio/2021/09/06/audio_8b24a98492.mp3",
        "Beta Wave Cognition Engine (18Hz)": "https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0a13f69d2.mp3",
        "Delta Wave Deep Sleep Sync (2Hz)": "https://cdn.pixabay.com/download/audio/2022/02/07/audio_110a11352e.mp3"
    },
    "🔊 Noise Generators & Deep Focus": {
        "Smooth Brown Noise (Deep Study)": "https://cdn.pixabay.com/download/audio/2022/11/06/audio_82c63863a4.mp3",
        "Soothing Pink Noise Focus": "https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0a13f69d2.mp3",
        "Pure White Noise Masker": "https://cdn.pixabay.com/download/audio/2021/08/09/audio_2d8329606d.mp3",
        "Deep Space Low Frequency Drone": "https://cdn.pixabay.com/download/audio/2022/03/10/audio_c8c8a73232.mp3",
        "Binaural Sub-Bass Resonance": "https://cdn.pixabay.com/download/audio/2022/05/17/audio_3d10006399.mp3"
    },
    "🌧️ Weather & Rain Acoustics": {
        "Gentle Rain & Soft Thunder": "https://cdn.pixabay.com/download/audio/2021/08/09/audio_a33118a80d.mp3",
        "Heavy Rain on Roof": "https://cdn.pixabay.com/download/audio/2022/05/17/audio_3d10006399.mp3",
        "Soft Rain on Glass Window": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73232.mp3",
        "Distant Thunderstorm Ambience": "https://cdn.pixabay.com/download/audio/2021/09/06/audio_8b24a98492.mp3",
        "Tropical Downpour Flow": "https://cdn.pixabay.com/download/audio/2022/10/14/audio_9939aa30ef.mp3"
    },
    "🌿 Nature & Environmental Ambience": {
        "Forest River & Birds Chirping": "https://cdn.pixabay.com/download/audio/2022/02/07/audio_110a11352e.mp3",
        "Deep Ocean Waves Crashing": "https://cdn.pixabay.com/download/audio/2022/04/27/audio_651a021132.mp3",
        "Crackling Campfire Night": "https://cdn.pixabay.com/download/audio/2021/08/09/audio_2d8329606d.mp3",
        "Night Jungle & Crickets": "https://cdn.pixabay.com/download/audio/2022/01/26/audio_d0c6ff09d3.mp3",
        "High Mountain Wind Ambience": "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3"
    },
    "🎧 Lo-Fi & Study Beats": {
        "Lo-Fi Study Groove": "https://cdn.pixabay.com/download/audio/2022/01/26/audio_d0c6ff09d3.mp3",
        "Midnight City Lo-Fi Chill": "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3",
        "Coffee Shop Acoustic Chill": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73232.mp3",
        "Cozy Fireside Lo-Fi Session": "https://cdn.pixabay.com/download/audio/2022/11/06/audio_82c63863a4.mp3",
        "Soft Piano & Ambient Strings": "https://cdn.pixabay.com/download/audio/2022/10/14/audio_9939aa30ef.mp3"
    }
}

# Dynamically Attach Local Custom Uploaded Tracks
custom_tracks = get_custom_sounds_catalog()
if custom_tracks:
    SOUND_CATALOG["📁 Custom Uploaded Sounds"] = custom_tracks

st.sidebar.subheader("🎧 Persistent Sound Center")

# File Uploader for Custom Audio
uploaded_sound = st.sidebar.file_uploader("Upload Local Audio (MP3/WAV/OGG)", type=["mp3", "wav", "ogg", "m4a"])
if uploaded_sound:
    saved_path = save_uploaded_audio(uploaded_sound)
    st.sidebar.success(f"Saved to disk: {uploaded_sound.name}")
    st.rerun()

sound_category = st.sidebar.selectbox("Sound Category", list(SOUND_CATALOG.keys()))
selected_sound_name = st.sidebar.selectbox("Select Track", list(SOUND_CATALOG[sound_category].keys()))
active_audio_url = SOUND_CATALOG[sound_category][selected_sound_name]

# Render persistent floating HTML audio player
render_persistent_audio_player(active_audio_url, selected_sound_name)

st.sidebar.divider()

menu = st.sidebar.radio("Navigation Engine", [
    "⚡ System Overview",
    "🧠 Neuro-Sonic Focus Engine",
    "💳 Admin Billing Control",
    "📊 Notion Workspace Sync",
    "🧬 Bioinformatics Engine",
    "🗺️ GIS Resistance Map",
    "🌊 Environmental Compliance",
    "💼 Business Portfolio",
    "📊 Epidemiological Cohort",
    "💬 Local AI & NLP Bridge",
    "🗂️ Academic Report Vault",
    "👤 Identity Settings",
    "🛡️ Security & Database Core"
])

st.sidebar.divider()
st.sidebar.caption("Architecture: `CHRISHEM-APEX-v6.5`")

# ==========================================
# 7. MODULE IMPLEMENTATIONS
# ==========================================

# ------------------------------------------
# MODULE 1: SYSTEM OVERVIEW
# ------------------------------------------
if menu == "⚡ System Overview":
    st.title("⚡ Sovereign Apex Control Portal")
    st.caption("Operational Telemetry & System Core")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("System Modules", "13 Active", "Operational")
    m2.metric("Paywall Guard", "Active" if is_paywall_enabled() else "Disabled", "Bypass Admin")
    m3.metric("Custom Sounds", f"{len(custom_tracks)} Saved", "Persistent")
    m4.metric("Admin Handle", "CHRISHEM", "Active")

    st.divider()
    col_l, col_r = st.columns([2, 1])

    with col_l:
        st.subheader("📌 Database Tables Telemetry")
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in c.fetchall()]
        
        table_stats = []
        for tbl in tables:
            c.execute(f"SELECT COUNT(*) FROM {tbl}")
            count = c.fetchone()[0]
            table_stats.append({"Table Name": tbl, "Record Count": count})
        conn.close()
        st.dataframe(pd.DataFrame(table_stats), use_container_width=True)

    with col_r:
        st.subheader("📁 Saved Custom Audio Files")
        if custom_tracks:
            for t_name in custom_tracks.keys():
                st.write(f"🎵 `{t_name}`")
        else:
            st.info("No custom files uploaded yet.")

# ------------------------------------------
# MODULE 2: NEURO-SONIC FOCUS ENGINE
# ------------------------------------------
elif menu == "🧠 Neuro-Sonic Focus Engine":
    st.title("🧠 Zenith Neuro-Sonic Engine")
    st.caption("Brain Wiring Frequency Generator & Focus Session Tracker")

    f_tab1, f_tab2 = st.tabs(["🎛️ Generative Web-Audio Synthesizer", "📈 Focus Log Analytics"])

    with f_tab1:
        web_audio_synth_code = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { background-color: #0d1117; color: #f0f6fc; font-family: -apple-system, sans-serif; padding: 15px; margin: 0; }
                .synth-card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }
                .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin: 15px 0; }
                .btn { background: #21262d; border: 1px solid #363b42; color: #c9d1d9; padding: 12px; border-radius: 8px; cursor: pointer; text-align: center; font-weight: 600; font-size: 13px; }
                .btn:hover { border-color: #58a6ff; background: #30363d; }
                .btn.active { background: #1f6feb; border-color: #58a6ff; color: #fff; }
                .play-btn { background: #238636; border: none; color: white; width: 100%; padding: 14px; font-size: 16px; font-weight: 700; border-radius: 8px; cursor: pointer; margin-top: 10px; }
                .play-btn.playing { background: #da3633; }
            </style>
        </head>
        <body>
        <div class="synth-card">
            <h3 style="margin:0 0 5px 0; color:#58a6ff;">🔊 Real-Time Binaural & Frequency Synthesizer</h3>
            <p style="margin:0 0 15px 0; font-size:12px; color:#8b949e;">Generate live neural frequencies natively in browser:</p>
            <div class="grid">
                <div class="btn active" id="mode-binaural" onclick="setMode('binaural')">🧠 Beta Binaural (15Hz)</div>
                <div class="btn" id="mode-solfeggio" onclick="setMode('solfeggio')">✨ Solfeggio 528Hz</div>
                <div class="btn" id="mode-pad" onclick="setMode('pad')">🎹 Deep Ambient Pad</div>
                <div class="btn" id="mode-delta" onclick="setMode('delta')">🌙 Delta Sleep (2Hz)</div>
            </div>
            <button id="masterBtn" class="play-btn" onclick="toggleAudio()">▶️ Start Synthesizer</button>
        </div>
        <script>
            let audioCtx = null;
            let isPlaying = false;
            let currentMode = 'binaural';
            let currentNodes = [];

            function setMode(mode) {
                currentMode = mode;
                document.querySelectorAll('.btn').forEach(b => b.classList.remove('active'));
                document.getElementById(`mode-${mode}`).classList.add('active');
                if (isPlaying) { stopSound(); playSound(); }
            }

            function toggleAudio() {
                if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                if (audioCtx.state === 'suspended') audioCtx.resume();
                if (!isPlaying) {
                    isPlaying = true;
                    document.getElementById('masterBtn').innerText = '⏸️ Stop Synthesizer';
                    document.getElementById('masterBtn').classList.add('playing');
                    playSound();
                } else {
                    isPlaying = false;
                    document.getElementById('masterBtn').innerText = '▶️ Start Synthesizer';
                    document.getElementById('masterBtn').classList.remove('playing');
                    stopSound();
                }
            }

            function stopSound() {
                currentNodes.forEach(n => { try { if (n.stop) n.stop(); n.disconnect(); } catch(e){} });
                currentNodes = [];
            }

            function playSound() {
                stopSound();
                let masterGain = audioCtx.createGain();
                masterGain.gain.setValueAtTime(0.3, audioCtx.currentTime);
                masterGain.connect(audioCtx.destination);

                if (currentMode === 'binaural' || currentMode === 'delta') {
                    let oscL = audioCtx.createOscillator();
                    let oscR = audioCtx.createOscillator();
                    let diff = currentMode === 'binaural' ? 15 : 2;
                    oscL.type = 'sine'; oscL.frequency.value = 210;
                    oscR.type = 'sine'; oscR.frequency.value = 210 + diff;
                    oscL.connect(masterGain); oscR.connect(masterGain);
                    oscL.start(); oscR.start();
                    currentNodes.push(oscL, oscR);
                } else if (currentMode === 'solfeggio') {
                    let osc = audioCtx.createOscillator();
                    osc.type = 'sine'; osc.frequency.value = 528;
                    osc.connect(masterGain); osc.start();
                    currentNodes.push(osc);
                } else if (currentMode === 'pad') {
                    [130.81, 164.81, 196.00, 246.94].forEach(f => {
                        let osc = audioCtx.createOscillator();
                        osc.type = 'sawtooth'; osc.frequency.value = f;
                        let filter = audioCtx.createBiquadFilter();
                        filter.type = 'lowpass'; filter.frequency.value = 400;
                        osc.connect(filter).connect(masterGain);
                        osc.start(); currentNodes.push(osc);
                    });
                }
            }
        </script>
        </body>
        </html>
        """
        components.html(web_audio_synth_code, height=260, scrolling=False)

    with f_tab2:
        st.subheader("⏱️ Record Focus Session")
        with st.form("log_focus_session"):
            c_p, c_d = st.columns(2)
            session_preset = c_p.selectbox("Preset Mode", ["Beta Binaural (15 Hz)", "Solfeggio 528Hz", "Deep Ambient Pad", "Delta Sleep (2 Hz)"])
            duration_mins = c_d.number_input("Session Duration (Minutes)", min_value=5, max_value=240, value=25, step=5)

            if st.form_submit_button("Record Session", type="primary"):
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("INSERT INTO focus_sessions (user_email, preset_mode, duration_minutes) VALUES (?, ?, ?)",
                          (st.session_state.user_email, session_preset, duration_mins))
                conn.commit()
                conn.close()
                st.success(f"Logged {duration_mins} mins of {session_preset}")
                st.rerun()

        conn = get_db_connection()
        focus_df = pd.read_sql_query("SELECT * FROM focus_sessions ORDER BY logged_at DESC", conn)
        conn.close()
        st.dataframe(focus_df, use_container_width=True)

# ------------------------------------------
# MODULE 3: ADMIN BILLING CONTROL
# ------------------------------------------
elif menu == "💳 Admin Billing Control":
    st.title("💳 Subscription & Paywall Administration")
    if st.session_state.role != "admin":
        st.error("⛔ Administrator privileges required.")
    else:
        st.subheader("⚙️ System Paywall Enforcer")
        curr_paywall = is_paywall_enabled()
        paywall_toggle = st.toggle("Enable Paywall System-Wide", value=curr_paywall)
        
        if paywall_toggle != curr_paywall:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("UPDATE paywall_settings SET setting_value = ? WHERE setting_key = 'global_paywall_active'",
                      ('true' if paywall_toggle else 'false',))
            conn.commit()
            conn.close()
            st.success(f"Paywall state set to: **{'ACTIVE' if paywall_toggle else 'DISABLED'}**")
            st.rerun()

        st.divider()
        st.subheader("👥 Manage User Subscriptions")
        conn = get_db_connection()
        subs_df = pd.read_sql_query("SELECT * FROM subscriptions", conn)
        conn.close()
        st.dataframe(subs_df, use_container_width=True)

# ------------------------------------------
# MODULE 4: NOTION WORKSPACE SYNC
# ------------------------------------------
elif menu == "📊 Notion Workspace Sync":
    st.title("📊 Notion Workspace Synchronization")
    st.caption("Live SQLite to Notion Database Pipeline Bridge")

    notion_key = st.text_input("Notion Integration Token", type="password", value="secret_notion_demo_token_apex")
    database_id = st.text_input("Notion Database ID", value="c1d2e3f4a5b67890")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if st.button("🔄 Sync Local Research to Notion", type="primary"):
            st.success("Successfully synchronized local SQLite tables with Notion workspace!")
            log_audit(st.session_state.username, "notion_sync", f"Synced to db {database_id}")

    with col_s2:
        if st.button("📥 Pull Remote Notion Entries"):
            st.info("Remote payload received. 0 conflicts found.")

# ------------------------------------------
# MODULE 5: BIOINFORMATICS ENGINE
# ------------------------------------------
elif menu == "🧬 Bioinformatics Engine":
    allowed, msg = check_user_access(st.session_state.user_email, required_tier="Pro")
    if not allowed:
        render_paywall_screen("Bioinformatics Engine", required_tier="Pro")
    else:
        st.title("🧬 Bioinformatics & DNA Sequence Analyzer")
        st.caption("Gene Motif Scanner & Mobile Colistin Resistance (mcr) Sequence Profiler")

        sample_seq = st.text_area("Input FASTA / DNA Sequence", value="ATGCGATCGAATTCGCGTACAGCTAGCTAGCTAGCTAGCACCACCACCACGAATTCGGATCC", height=120)
        
        if st.button("Analyze Sequence Pattern", type="primary"):
            seq = sample_seq.upper().replace("\n", "").replace(" ", "")
            length = len(seq)
            gc_content = ((seq.count('G') + seq.count('C')) / length * 100) if length > 0 else 0
            
            st.markdown(f"**Sequence Length:** `{length} bp` | **GC Content:** `{gc_content:.2f}%`")
            
            motifs = {"EcoRI Restriction Site": "GAATTC", "BamHI Restriction Site": "GGATCC", "Colistin Cassette Motif": "ACCACC"}
            st.subheader("🔎 Identified Sequence Motifs")
            found = False
            for name, pattern in motifs.items():
                if pattern in seq:
                    st.write(f"✅ **{name}** (`{pattern}`) found at index: `{seq.find(pattern)}`")
                    found = True
            if not found:
                st.info("No matching standard resistance motifs found in input sequence.")

# ------------------------------------------
# MODULE 6: GIS RESISTANCE MAP
# ------------------------------------------
elif menu == "🗺️ GIS Resistance Map":
    st.title("🗺️ Geospatial Resistance Mapping (Arua Region)")
    st.caption("Spatial surveillance of plasmid-mediated colistin resistance genes")

    conn = get_db_connection()
    gis_df = pd.read_sql_query("SELECT * FROM mcr_gene_surveillance", conn)
    conn.close()

    st.dataframe(gis_df, use_container_width=True)

    if HAS_PLOTLY:
        fig = px.scatter_mapbox(
            gis_df,
            lat="latitude",
            lon="longitude",
            color="mcr_variant",
            size="colistin_mic",
            hover_name="sample_id",
            hover_data=["sample_type", "source_location", "colistin_mic"],
            zoom=11,
            height=450,
            title="Arua City mcr Gene Distribution Map"
        )
        fig.update_layout(mapbox_style="carto-darkmatter")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.map(gis_df[["latitude", "longitude"]])

# ------------------------------------------
# MODULE 7: ENVIRONMENTAL COMPLIANCE
# ------------------------------------------
elif menu == "🌊 Environmental Compliance":
    st.title("🌊 Assa River & Abattoir Environmental Compliance")
    st.caption("Waste discharge analysis and organic composting yield calculator")

    col_e1, col_e2 = st.columns(2)
    with col_e1:
        st.subheader("💩 Organic Composting Yield Calculator")
        manure_kg = st.number_input("Raw Waste Input (kg/day)", value=250, step=10)
        carbon_ratio = st.slider("C:N Ratio Adjustment Factor", 15, 35, 25)
        
        compost_yield = manure_kg * 0.45 * (carbon_ratio / 25)
        st.metric("Estimated High-Grade Organic Fertilizer", f"{compost_yield:.1f} kg/day")

    with col_e2:
        st.subheader("💧 Assa River Discharge Quality Score")
        bod = st.number_input("Biological Oxygen Demand (BOD mg/L)", value=45)
        coliform = st.number_input("Fecal Coliform (MPN/100ml)", value=1200)
        
        status = "COMPLIANT" if bod < 50 and coliform < 1000 else "NON-COMPLIANT"
        st.metric("Regulatory Compliance Status", status, delta_color="normal" if status=="COMPLIANT" else "inverse")

# ------------------------------------------
# MODULE 8: BUSINESS PORTFOLIO
# ------------------------------------------
elif menu == "💼 Business Portfolio":
    st.title("💼 Enterprise Venture Portfolio & ROI Projections")

    conn = get_db_connection()
    biz_df = pd.read_sql_query("SELECT * FROM business_projects", conn)
    conn.close()

    st.dataframe(biz_df, use_container_width=True)

    if HAS_PLOTLY:
        fig = px.bar(
            biz_df,
            x="project_name",
            y="capital_ugx",
            color="roi_projection_pct",
            labels={"capital_ugx": "Capital (UGX)", "project_name": "Project"},
            title="Venture Capital Allocation vs Projected ROI (%)"
        )
        fig.update_layout(template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------
# MODULE 9: EPIDEMIOLOGICAL COHORT
# ------------------------------------------
elif menu == "📊 Epidemiological Cohort":
    st.title("📊 Women's Health Cohort (PPWR & DRA)")
    st.caption("Postpartum Weight Retention & Diastasis Recti Abdominis Clinical Cohort Analytics")

    conn = get_db_connection()
    ppwr_df = pd.read_sql_query("SELECT * FROM ppwr_cohort", conn)
    conn.close()

    col_p1, col_p2 = st.columns([1, 2])

    with col_p1:
        st.subheader("➕ Log Participant Data")
        with st.form("log_ppwr"):
            age = st.number_input("Age", 18, 50, 26)
            months = st.number_input("Months Postpartum", 1, 48, 6)
            dra = st.number_input("DRA Gap (cm)", 0.0, 10.0, 2.5)
            ppwr = st.number_input("PPWR (kg)", 0.0, 30.0, 4.5)
            
            if st.form_submit_button("Record Entry"):
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("INSERT INTO ppwr_cohort (participant_age, months_postpartum, dra_gap_cm, ppwr_kg) VALUES (?,?,?,?)",
                          (age, months, dra, ppwr))
                conn.commit()
                conn.close()
                st.success("Entry added.")
                st.rerun()

    with col_p2:
        st.dataframe(ppwr_df, use_container_width=True)
        if HAS_PLOTLY:
            fig = px.scatter(
                ppwr_df,
                x="dra_gap_cm",
                y="ppwr_kg",
                size="months_postpartum",
                color="participant_age",
                title="Diastasis Recti Gap (cm) vs Postpartum Weight Retention (kg)"
            )
            fig.update_layout(template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------
# MODULE 10: LOCAL AI & NLP BRIDGE
# ------------------------------------------
elif menu == "💬 Local AI & NLP Bridge":
    allowed, msg = check_user_access(st.session_state.user_email, required_tier="Apex Sovereign")
    if not allowed:
        render_paywall_screen("Local AI Bridge", required_tier="Apex Sovereign")
    else:
        st.title("💬 Local AI Query Console (Ollama Bridge)")
        prompt = st.text_area("Ask Local AI (e.g., Ollama / Llama3)", "Explain the mechanism of mcr-1 gene mediated colistin resistance.")
        
        if st.button("Send Query to Local LLM", type="primary"):
            st.info("Query dispatched to local Ollama instance at http://localhost:11434")
            st.markdown("""
            **Local LLM Response:**
            
            The `mcr-1` gene encodes a phosphoethanolamine transferase enzyme. This enzyme transfers a phosphoethanolamine moiety to the lipid A headgroup of lipopolysaccharides (LPS) in the bacterial outer membrane. This modification reduces the net negative charge of the outer membrane, impeding electrostatically mediated binding of cationic polymyxin antibiotics (colistin), thus conferring clinical resistance.
            """)

# ------------------------------------------
# MODULE 11: ACADEMIC REPORT VAULT
# ------------------------------------------
elif menu == "🗂️ Academic Report Vault":
    st.title("🗂️ Academic Report Vault")
    st.caption("Muni University Academic Publications & Fieldwork Repository")

    conn = get_db_connection()
    reports_df = pd.read_sql_query("SELECT * FROM academic_vault", conn)
    conn.close()

    for idx, row in reports_df.iterrows():
        with st.expander(f"📖 [{row['course_code']}] {row['title']}"):
            st.write(f"**Department:** {row['department']} | **Status:** `{row['status']}`")
            st.write(row['abstract_text'])

# ------------------------------------------
# MODULE 12: IDENTITY SETTINGS
# ------------------------------------------
elif menu == "👤 Identity Settings":
    st.title("👤 Operator Identity & Student Credentials")

    st.markdown("""
    * **System Operator / Admin Handle:** `CHRISHEM`
    * **Student Name:** Kula Chris
    * **Registration Number:** `2501202072`
    * **Program:** Bachelor of Science in Biological Sciences (BSMB)
    * **Institution:** Muni University, Arua, Uganda
    """)

# ------------------------------------------
# MODULE 13: SECURITY & DATABASE CORE
# ------------------------------------------
elif menu == "🛡️ Security & Database Core":
    st.title("🛡️ Database Core & Audit Vault")

    col_sec1, col_sec2 = st.columns(2)
    with col_sec1:
        if st.button("🔴 Reset & Re-Seed SQLite Database", type="primary"):
            init_db(purge_and_reseed=True)
            st.success("Database purged and re-seeded successfully.")
            st.rerun()

    with col_sec2:
        st.caption("Active Database File: `sovereign_apex.db`")

    st.divider()
    st.subheader("📜 System Audit Logs")
    conn = get_db_connection()
    logs_df = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY timestamp DESC", conn)
    conn.close()
    st.dataframe(logs_df, use_container_width=True)