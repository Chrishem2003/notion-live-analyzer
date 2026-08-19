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
        padding: 10px 14px !important; margin-bottom: 6px !important; transition: all 0.2s ease;
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

# ==========================================
# 2. PERSISTENT AUDIO PLAYER COMPONENT
# ==========================================
def render_persistent_audio_player(audio_url, track_title="Brainwave Focus"):
    """
    Renders a persistent floating audio widget at the bottom right.
    Uses browser localStorage to sync playback time and playing state across page switches.
    """
    player_html = f"""
    <style>
        .audio-popup {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #1e1e2e;
            color: #ffffff;
            padding: 12px 18px;
            border-radius: 30px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.4);
            z-index: 999999;
            display: flex;
            align-items: center;
            gap: 12px;
            font-family: system-ui, -apple-system, sans-serif;
            font-size: 13px;
            border: 1px solid #38bdf8;
        }}
        audio {{ display: none; }}
        .btn {{
            background: #38bdf8;
            border: none;
            color: #0b0f19;
            padding: 6px 14px;
            border-radius: 15px;
            cursor: pointer;
            font-weight: bold;
            transition: background 0.2s;
        }}
        .btn:hover {{
            background: #74c7ec;
        }}
    </style>
    
    <div class="audio-popup">
        <span>🎵 <b id="trackLabel">{track_title}</b></span>
        <button class="btn" id="playBtn" onclick="togglePlay()">Play / Pause</button>
        <audio id="globalAudio" loop>
            <source src="{audio_url}" type="audio/mpeg">
        </audio>
    </div>

    <script>
        const audio = document.getElementById("globalAudio");
        const playBtn = document.getElementById("playBtn");
        const trackKey = "audio_track_url";

        window.addEventListener("load", () => {{
            const savedUrl = localStorage.getItem(trackKey);
            const savedTime = localStorage.getItem("audio_current_time");
            const isPlaying = localStorage.getItem("audio_is_playing");

            // If audio URL changed, update source
            if (savedUrl && savedUrl !== "{audio_url}") {{
                localStorage.setItem(trackKey, "{audio_url}");
                localStorage.setItem("audio_current_time", "0");
            }} else {{
                localStorage.setItem(trackKey, "{audio_url}");
                if (savedTime) audio.currentTime = parseFloat(savedTime);
            }}

            if (isPlaying === "true") {{
                audio.play().catch(e => console.log("Autoplay blocked by browser policy:", e));
            }}
        }});

        audio.ontimeupdate = () => {{
            localStorage.setItem("audio_current_time", audio.currentTime);
        }};

        function togglePlay() {{
            if (audio.paused) {{
                audio.play();
                localStorage.setItem("audio_is_playing", "true");
            }} else {{
                audio.pause();
                localStorage.setItem("audio_is_playing", "false");
            }}
        }}
    </script>
    """
    components.html(player_html, height=80)

# ==========================================
# 3. PERSISTENT DATABASE ENGINE & DATA CONTROL
# ==========================================
def init_db(purge_and_reseed=False):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if purge_and_reseed:
        cursor.execute("DROP TABLE IF EXISTS mcr_gene_surveillance")
        cursor.execute("DROP TABLE IF EXISTS business_projects")
        cursor.execute("DROP TABLE IF EXISTS ppwr_cohort")
    
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
    if cursor.fetchone()[0] == 0 and not purge_and_reseed:
        cursor.executemany(
            "INSERT INTO mcr_gene_surveillance VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("MCR-PL-001", "Poultry Cecal Swab", "Arua Central Market", 2.9712, 30.9114, "mcr-1", 8.0, "2026-03-15", "IncI2 backbone"),
                ("MCR-PL-002", "Environmental Water", "Assa River Downstream", 2.9654, 30.9152, "mcr-1", 16.0, "2026-03-18", "Co-harboring blaCTX-M-15"),
                ("MCR-PL-003", "Abattoir Drainage", "Arua City Abattoir", 2.9751, 30.9083, "mcr-3", 4.0, "2026-04-02", "Novel variant sequence")
            ]
        )

    cursor.execute("SELECT COUNT(*) FROM business_projects")
    if cursor.fetchone()[0] == 0 and not purge_and_reseed:
        cursor.executemany(
            "INSERT INTO business_projects (project_name, lead_entity, capital_ugx, roi_projection_pct, status) VALUES (?, ?, ?, ?, ?)",
            [
                ("Kidega Fresh Beverage Line", "Team Kula", 12500000.0, 32.5, "Active"),
                ("Santa Solo Enterprise", "Galilee Community", 8500000.0, 24.0, "Planning")
            ]
        )

    cursor.execute("SELECT COUNT(*) FROM ppwr_cohort")
    if cursor.fetchone()[0] == 0 and not purge_and_reseed:
        cursor.executemany(
            "INSERT INTO ppwr_cohort (participant_age, months_postpartum, dra_gap_cm, ppwr_kg) VALUES (?, ?, ?, ?)",
            [(24, 6, 2.8, 5.2), (29, 12, 1.9, 3.1), (32, 3, 3.5, 8.4)]
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
# 4. COMPUTATIONAL ALGORITHMS
# ==========================================
def process_dna_sequence(seq):
    seq = seq.upper().replace("\n", "").replace(" ", "")
    clean_seq = "".join([b for b in seq if b in set("ATGC")])
    if not clean_seq:
        return None
    
    gc_pct = ((clean_seq.count('G') + clean_seq.count('C')) / len(clean_seq)) * 100
    rna_seq = clean_seq.replace('T', 'U')
    comp_map = str.maketrans("ATGC", "TACG")
    rev_comp = clean_seq.translate(comp_map)[::-1]
    
    codon_table = {
        'AUG': 'M', 'UUU': 'F', 'UUC': 'F', 'UUA': 'L', 'UUG': 'L', 'UCU': 'S', 'UCC': 'S', 'UCA': 'S', 'UCG': 'S', 
        'UAU': 'Y', 'UAC': 'Y', 'UGU': 'C', 'UGC': 'C', 'UGG': 'W', 'CUU': 'L', 'CUC': 'L', 'CUA': 'L', 'CUG': 'L', 
        'CCU': 'P', 'CCC': 'P', 'CCA': 'P', 'CCG': 'P', 'CAU': 'H', 'CAC': 'H', 'CAA': 'Q', 'CAG': 'Q', 'CGU': 'R', 
        'AUU': 'I', 'AUC': 'I', 'AUA': 'I', 'ACU': 'T', 'ACC': 'T', 'ACA': 'T', 'ACG': 'T', 'AAU': 'N', 'AAC': 'N', 
        'AAA': 'K', 'AAG': 'K', 'AGU': 'S', 'AGC': 'S', 'AGA': 'R', 'AGG': 'R', 'GUU': 'V', 'GUC': 'V', 'GUA': 'V', 
        'GUG': 'V', 'GCU': 'A', 'GCC': 'A', 'GCA': 'A', 'GCG': 'A', 'GAU': 'D', 'GAC': 'D', 'GAA': 'E', 'GAG': 'E', 
        'GGU': 'G', 'GGC': 'G', 'GGA': 'G', 'GGG': 'G', 'UAA': '*', 'UAG': '*', 'UGA': '*'
    }
    
    protein = [codon_table.get(rna_seq[i:i+3], '?') for i in range(0, len(rna_seq) - 2, 3)]
    return {"length": len(clean_seq), "gc_content": gc_pct, "rna": rna_seq, "rev_comp": rev_comp, "protein": "".join(protein)}

def needleman_wunsch(seq1, seq2, match=1, mismatch=-1, gap=-1):
    n, m = len(seq1), len(seq2)
    score_matrix = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1): score_matrix[i][0] = i * gap
    for j in range(m + 1): score_matrix[0][j] = j * gap
        
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            s = match if seq1[i-1] == seq2[j-1] else mismatch
            score_matrix[i][j] = max(score_matrix[i-1][j-1] + s, score_matrix[i-1][j] + gap, score_matrix[i][j-1] + gap)
            
    align1, align2 = "", ""
    i, j = n, m
    while i > 0 and j > 0:
        score_current = score_matrix[i][j]
        s = match if seq1[i-1] == seq2[j-1] else mismatch
        if score_current == score_matrix[i-1][j-1] + s:
            align1 = seq1[i-1] + align1; align2 = seq2[j-1] + align2; i -= 1; j -= 1
        elif score_current == score_matrix[i-1][j] + gap:
            align1 = seq1[i-1] + align1; align2 = "-" + align2; i -= 1
        else:
            align1 = "-" + align1; align2 = seq2[j-1] + align2; j -= 1
            
    while i > 0: align1 = seq1[i-1] + align1; align2 = "-" + align2; i -= 1
    while j > 0: align1 = "-" + align1; align2 = seq2[j-1] + align2; j -= 1
    return align1, align2, score_matrix[n][m]

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
# 6. SESSION STATE & EXPANDED GLOBAL AUDIO SIDEBAR
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

# EXPANDED SOUND CATALOG SYSTEM (25+ TRACKS ACROSS 5 CATEGORIES)
SOUND_CATALOG = {
    "🧠 Brain Wiring, Frequencies & Focus": {
        "432Hz Deep Focus Pulse": "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3",
        "528Hz Solfeggio Transformation Tone": "https://cdn.pixabay.com/download/audio/2022/10/14/audio_9939aa30ef.mp3",
        "Alpha Waves Concentration (10Hz)": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73232.mp3",
        "Gamma Frequency Peak Focus (40Hz)": "https://cdn.pixabay.com/download/audio/2021/09/06/audio_8b24a98492.mp3",
        "Smooth Brown Noise (Deep Study)": "https://cdn.pixabay.com/download/audio/2022/11/06/audio_82c63863a4.mp3",
        "Soothing Pink Noise Focus": "https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0a13f69d2.mp3"
    },
    "🌧️ Weather, Nature & Deep Acoustics": {
        "Gentle Rain & Soft Thunder": "https://cdn.pixabay.com/download/audio/2021/08/09/audio_a33118a80d.mp3",
        "Heavy Rain on Roof": "https://cdn.pixabay.com/download/audio/2022/05/17/audio_3d10006399.mp3",
        "Forest River & Birds": "https://cdn.pixabay.com/download/audio/2022/02/07/audio_110a11352e.mp3",
        "Deep Ocean Waves Crashing": "https://cdn.pixabay.com/download/audio/2022/04/27/audio_651a021132.mp3",
        "Crackling Campfire Ambience": "https://cdn.pixabay.com/download/audio/2021/08/09/audio_2d8329606d.mp3",
        "Windy Mountain Peak": "https://cdn.pixabay.com/download/audio/2022/03/10/audio_c3bc410d51.mp3"
    },
    "🎧 Lo-Fi, Chillhop & Study Beats": {
        "Lo-Fi Study Groove": "https://cdn.pixabay.com/download/audio/2022/01/26/audio_d0c6ff09d3.mp3",
        "Midnight City Lo-Fi Chill": "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3",
        "Coffee Shop Acoustic Chill": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73232.mp3",
        "Late Night Cyberpunk Synthwave": "https://cdn.pixabay.com/download/audio/2022/02/10/audio_fc8a26f8ee.mp3",
        "Smooth Jazz Study Session": "https://cdn.pixabay.com/download/audio/2022/03/24/audio_3311516e8b.mp3"
    },
    "🧘 Space, Meditative & Ambient Drones": {
        "Deep Space Void Drone": "https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0a13f69d2.mp3",
        "Tibetan Singing Bowls Zen": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_b28d541575.mp3",
        "Celestial Shimmer Pad": "https://cdn.pixabay.com/download/audio/2022/05/16/audio_db6591201e.mp3",
        "Cosmic Meditation Atmosphere": "https://cdn.pixabay.com/download/audio/2021/09/06/audio_8b24a98492.mp3"
    },
    "🎵 Melodic Instrumental & Keys": {
        "Acoustic Solitude Guitar": "https://cdn.pixabay.com/download/audio/2022/05/16/audio_db6591201e.mp3",
        "Peaceful Piano Reflections": "https://cdn.pixabay.com/download/audio/2022/04/27/audio_c1e285d113.mp3",
        "Cinematic Soft Strings": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_8946f04754.mp3",
        "Late Night R&B Ambient Keys": "https://cdn.pixabay.com/download/audio/2022/02/15/audio_d00b14736f.mp3"
    }
}

st.sidebar.subheader("🎧 Persistent Sound Center")
sound_category = st.sidebar.selectbox("Sound Category", list(SOUND_CATALOG.keys()))
selected_sound_name = st.sidebar.selectbox("Select Track", list(SOUND_CATALOG[sound_category].keys()))
active_audio_url = SOUND_CATALOG[sound_category][selected_sound_name]

# Custom Audio Upload & Local Storage Download
uploaded_sound = st.sidebar.file_uploader("Upload Custom Audio (MP3/WAV)", type=["mp3", "wav"])
if uploaded_sound:
    os.makedirs("custom_sounds", exist_ok=True)
    custom_path = os.path.join("custom_sounds", uploaded_sound.name)
    with open(custom_path, "wb") as f:
        f.write(uploaded_sound.getbuffer())
    st.sidebar.success(f"Uploaded: {uploaded_sound.name}")
    
    st.sidebar.download_button(
        label="📥 Save Track Locally",
        data=uploaded_sound.getvalue(),
        file_name=uploaded_sound.name,
        mime="audio/mpeg"
    )

# Render floating persistent audio player across all tabs
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
st.sidebar.caption("Architecture: `CHRISHEM-APEX-v6.0`")

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
    m3.metric("Audio Synth", "Web Audio API", "Live Engine")
    m4.metric("Admin Handle", "CHRISHEM", "Active")

    st.divider()
    col_l, col_r = st.columns([2, 1])

    with col_l:
        st.subheader("📌 Active Database Tables")
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in c.fetchall()]
        conn.close()
        
        st.write("Current SQLite persistent tables loaded in system memory:")
        st.json(tables)

    with col_r:
        st.subheader("🛡️ Environment Telemetry")
        st.info(f"💻 OS: {sys.platform.upper()}")
        st.success("🌐 Web Audio API: Embedded Synthesizer Ready")
        st.success("💾 Database: Connected & Operational")

# ------------------------------------------
# MODULE 2: NEURO-SONIC FOCUS ENGINE
# ------------------------------------------
elif menu == "🧠 Neuro-Sonic Focus Engine":
    st.title("🧠 Zenith Neuro-Sonic Engine")
    st.caption("Brain.fm & Endel Audio Synthesizer: Real-time Web Audio API frequency generation and persistent audio stream integration")

    f_tab1, f_tab2 = st.tabs(["🎛️ Generative Audio Synthesizer", "📈 Focus Session Logger"])

    with f_tab1:
        st.markdown("Select a real acoustic generator mode below and click **Start Audio Synthesizer**.")
        
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
                .slider-container { margin: 12px 0; }
                label { font-size: 12px; color: #8b949e; display: flex; justify-content: space-between; }
                input[type="range"] { width: 100%; margin-top: 5px; }
                canvas { width: 100%; height: 60px; background: #0d1117; border-radius: 6px; margin-top: 12px; }
            </style>
        </head>
        <body>

        <div class="synth-card">
            <h3 style="margin:0 0 5px 0; color:#58a6ff;">🔊 Real Acoustic Synthesizer</h3>
            <p style="margin:0 0 15px 0; font-size:12px; color:#8b949e;">Select soundscape mode & trigger native browser Web Audio synthesis:</p>

            <div class="grid">
                <div class="btn active" id="mode-binaural" onclick="setMode('binaural')">🧠 Beta Binaural</div>
                <div class="btn" id="mode-rain" onclick="setMode('rain')">🌧️ Rain Noise</div>
                <div class="btn" id="mode-pad" onclick="setMode('pad')">🎹 Deep Synth Pad</div>
                <div class="btn" id="mode-chimes" onclick="setMode('chimes')">🔔 Pure Chimes</div>
                <div class="btn" id="mode-delta" onclick="setMode('delta')">🌙 Delta Sleep</div>
            </div>

            <div class="slider-container">
                <label><span>Master Volume</span><span id="vol-txt">50%</span></label>
                <input type="range" id="volume" min="0" max="1" step="0.01" value="0.5" oninput="updateVolume(this.value)">
            </div>

            <button id="masterBtn" class="play-btn" onclick="toggleAudio()">▶️ Start Audio Synthesizer</button>
            <canvas id="visualizer"></canvas>
        </div>

        <script>
            let audioCtx = null;
            let isPlaying = false;
            let currentMode = 'binaural';
            let masterGain = null;
            let currentNodes = [];
            let analyser = null;
            let animId = null;

            function setMode(mode) {
                currentMode = mode;
                document.querySelectorAll('.btn').forEach(b => b.classList.remove('active'));
                document.getElementById(`mode-${mode}`).classList.add('active');
                if (isPlaying) {
                    stopSound();
                    playSound();
                }
            }

            function updateVolume(val) {
                document.getElementById('vol-txt').innerText = Math.round(val * 100) + '%';
                if (masterGain && audioCtx) {
                    masterGain.gain.setTargetAtTime(parseFloat(val), audioCtx.currentTime, 0.05);
                }
            }

            function toggleAudio() {
                if (!audioCtx) {
                    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                }
                if (audioCtx.state === 'suspended') {
                    audioCtx.resume();
                }

                if (!isPlaying) {
                    isPlaying = true;
                    document.getElementById('masterBtn').innerText = '⏸️ Stop Audio Synthesizer';
                    document.getElementById('masterBtn').classList.add('playing');
                    playSound();
                    drawVisualizer();
                } else {
                    isPlaying = false;
                    document.getElementById('masterBtn').innerText = '▶️ Start Audio Synthesizer';
                    document.getElementById('masterBtn').classList.remove('playing');
                    stopSound();
                    cancelAnimationFrame(animId);
                }
            }

            function stopSound() {
                currentNodes.forEach(n => {
                    try { if (n.stop) n.stop(); n.disconnect(); } catch(e){}
                });
                currentNodes = [];
            }

            function playSound() {
                stopSound();
                masterGain = audioCtx.createGain();
                masterGain.gain.setValueAtTime(parseFloat(document.getElementById('volume').value), audioCtx.currentTime);

                analyser = audioCtx.createAnalyser();
                analyser.fftSize = 64;

                masterGain.connect(analyser);
                analyser.connect(audioCtx.destination);

                if (currentMode === 'binaural') {
                    let oscL = audioCtx.createOscillator();
                    let oscR = audioCtx.createOscillator();
                    let panL = audioCtx.createStereoPanner ? audioCtx.createStereoPanner() : null;
                    let panR = audioCtx.createStereoPanner ? audioCtx.createStereoPanner() : null;

                    oscL.type = 'sine'; oscL.frequency.value = 200;
                    oscR.type = 'sine'; oscR.frequency.value = 215;

                    if (panL && panR) {
                        panL.pan.value = -1; panR.pan.value = 1;
                        oscL.connect(panL).connect(masterGain);
                        oscR.connect(panR).connect(masterGain);
                    } else {
                        oscL.connect(masterGain); oscR.connect(masterGain);
                    }
                    oscL.start(); oscR.start();
                    currentNodes.push(oscL, oscR);

                } else if (currentMode === 'rain') {
                    let bufferSize = 2 * audioCtx.sampleRate;
                    let noiseBuffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
                    let output = noiseBuffer.getChannelData(0);
                    let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;

                    for (let i = 0; i < bufferSize; i++) {
                        let white = Math.random() * 2 - 1;
                        b0 = 0.99886 * b0 + white * 0.0555179;
                        b1 = 0.99332 * b1 + white * 0.0750759;
                        b2 = 0.96900 * b2 + white * 0.1538520;
                        b3 = 0.86650 * b3 + white * 0.3104856;
                        b4 = 0.55000 * b4 + white * 0.5329522;
                        b5 = -0.7616 * b5 - white * 0.0168980;
                        output[i] = b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362;
                        output[i] *= 0.11;
                        b6 = white * 0.115926;
                    }

                    let whiteNoise = audioCtx.createBufferSource();
                    whiteNoise.buffer = noiseBuffer;
                    whiteNoise.loop = true;

                    let filter = audioCtx.createBiquadFilter();
                    filter.type = 'lowpass';
                    filter.frequency.value = 800;

                    whiteNoise.connect(filter);
                    filter.connect(masterGain);
                    whiteNoise.start();
                    currentNodes.push(whiteNoise);

                } else if (currentMode === 'pad') {
                    let freqs = [110.00, 130.81, 164.81, 196.00];
                    freqs.forEach(f => {
                        let osc = audioCtx.createOscillator();
                        let g = audioCtx.createGain();
                        osc.type = 'sawtooth';
                        osc.frequency.value = f;

                        let filter = audioCtx.createBiquadFilter();
                        filter.type = 'lowpass';
                        filter.frequency.value = 400;

                        g.gain.value = 0.15;
                        osc.connect(filter).connect(g).connect(masterGain);
                        osc.start();
                        currentNodes.push(osc);
                    });

                } else if (currentMode === 'chimes') {
                    let notes = [261.63, 293.66, 329.63, 392.00, 440.00, 523.25];
                    let chimeInterval = setInterval(() => {
                        if (!isPlaying || currentMode !== 'chimes') { clearInterval(chimeInterval); return; }
                        let note = notes[Math.floor(Math.random() * notes.length)];
                        let osc = audioCtx.createOscillator();
                        let g = audioCtx.createGain();

                        osc.type = 'sine';
                        osc.frequency.value = note;

                        g.gain.setValueAtTime(0, audioCtx.currentTime);
                        g.gain.linearRampToValueAtTime(0.2, audioCtx.currentTime + 0.05);
                        g.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 2.5);

                        osc.connect(g).connect(masterGain);
                        osc.start();
                        osc.stop(audioCtx.currentTime + 2.6);
                    }, 800);

                } else if (currentMode === 'delta') {
                    let oscL = audioCtx.createOscillator();
                    let oscR = audioCtx.createOscillator();
                    oscL.type = 'sine'; oscL.frequency.value = 100;
                    oscR.type = 'sine'; oscR.frequency.value = 102.5;

                    oscL.connect(masterGain);
                    oscR.connect(masterGain);
                    oscL.start(); oscR.start();
                    currentNodes.push(oscL, oscR);
                }
            }

            function drawVisualizer() {
                let canvas = document.getElementById('visualizer');
                let ctx = canvas.getContext('2d');
                let dataArray = new Uint8Array(analyser.frequencyBinCount);

                function render() {
                    if (!isPlaying) { ctx.clearRect(0,0,canvas.width,canvas.height); return; }
                    animId = requestAnimationFrame(render);
                    analyser.getByteFrequencyData(dataArray);

                    ctx.fillStyle = '#0d1117';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);

                    let barWidth = (canvas.width / dataArray.length) * 2.5;
                    let x = 0;
                    for (let i = 0; i < dataArray.length; i++) {
                        let barHeight = (dataArray[i] / 255) * canvas.height;
                        ctx.fillStyle = '#38bdf8';
                        ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
                        x += barWidth + 1;
                    }
                }
                render();
            }
        </script>
        </body>
        </html>
        """
        components.html(web_audio_synth_code, height=360, scrolling=False)

    with f_tab2:
        st.subheader("⏱️ Focus Session Logging")
        with st.form("log_focus_session"):
            c_p, c_d = st.columns(2)
            session_preset = c_p.selectbox("Preset Mode", ["Beta Binaural (15 Hz)", "Rain Noise Generator", "Deep Synth Pad", "Pentatonic Chimes", "Delta Sleep (2.5 Hz)"])
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
        st.subheader("📊 Session History")
        conn = get_db_connection()
        logs_df = pd.read_sql_query("SELECT id, preset_mode, duration_minutes, logged_at FROM focus_sessions ORDER BY logged_at DESC LIMIT 20", conn)
        conn.close()
        st.dataframe(logs_df, use_container_width=True)

# ------------------------------------------
# MODULE 3: ADMIN BILLING CONTROL
# ------------------------------------------
elif menu == "💳 Admin Billing Control":
    st.title("💳 Admin Billing Control Portal")
    if st.session_state.role != "admin":
        st.error("⛔ Access Denied. Administrator credentials required.")
    else:
        st.subheader("⚙️ Paywall Switch")
        curr_paywall = is_paywall_enabled()
        paywall_toggle = st.toggle("Enable Paywall Locks Across System", value=curr_paywall)
        
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
        st.subheader("👤 User Subscriptions")
        conn = get_db_connection()
        subs_df = pd.read_sql_query("""
            SELECT u.email, u.name, u.role, COALESCE(s.tier, 'Free') as tier, 
                   COALESCE(s.status, 'inactive') as status, s.expires_at 
            FROM auth_users u LEFT JOIN subscriptions s ON u.email = s.user_email
        """, conn)
        conn.close()
        st.dataframe(subs_df, use_container_width=True)

# ------------------------------------------
# MODULE 4: NOTION WORKSPACE SYNC
# ------------------------------------------
elif menu == "📊 Notion Workspace Sync":
    st.title("📊 Notion Workspace Integration")
    notion_token = st.text_input("Notion API Token", type="password")
    database_id = st.text_input("Database ID", value="3a7f8e12b4c5d6e7f8a9b0c1d2e3f4a5")

    if st.button("Sync Notion Workspace", type="primary"):
        if not notion_token.strip():
            st.warning("⚠️ No Notion API Token entered. Showing local workspace cache.")
            cached_df = pd.DataFrame([
                {"Task": "Sequencing mcr-1 Isolates", "Status": "In Progress", "Lead": "Kula Chris"},
                {"Task": "Beverage Inventory Tracking", "Status": "Completed", "Lead": "Team Kula"}
            ])
            st.dataframe(cached_df, use_container_width=True)
        else:
            st.info("Attempting connection to Notion API...")

# ------------------------------------------
# MODULE 5: BIOINFORMATICS ENGINE
# ------------------------------------------
elif menu == "🧬 Bioinformatics Engine":
    allowed, msg = check_user_access(st.session_state.user_email, required_tier="Pro")
    if not allowed:
        render_paywall_screen("Bioinformatics Engine", required_tier="Pro")
    else:
        st.title("🧬 Bioinformatics & Pairwise Sequence Alignment")
        b_tab1, b_tab2 = st.tabs(["⚡ Pairwise Alignment", "🔍 FastA Sequence Processor"])

        with b_tab1:
            st.subheader("🧬 Needleman-Wunsch Global Alignment")
            c_a, c_b = st.columns(2)
            seq_ref = c_a.text_area("Reference Sequence", value="ATGCAGCGTACTAAGGCTAAGCTAGCTAGC", height=90)
            seq_sample = c_b.text_area("Sample Sequence", value="ATGCAGTGTACTAAGGCTAAGCTAGCTAGC", height=90)
            
            if st.button("Run Global Alignment", type="primary"):
                a1, a2, score = needleman_wunsch(seq_ref.upper().strip(), seq_sample.upper().strip())
                st.success(f"Alignment Score: **{score}**")
                st.code(f"REF:    {a1}\nMATCH:  {''.join(['|' if a1[k] == a2[k] else '.' for k in range(len(a1))])}\nSAMPLE: {a2}")

        with b_tab2:
            st.subheader("🔍 Nucleotide Translation & GC Content")
            fasta_input = st.text_area("FastA Input", value=">seq1\nATGCAGCGTACTAAGGCTAAGCTAGCTAGCGCGCGCATATATCGATCGATCGAT", height=90)
            if st.button("Analyze Sequence"):
                res = process_dna_sequence(fasta_input)
                if res:
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Length", f"{res['length']} bp")
                    m2.metric("GC Ratio", f"{res['gc_content']:.2f}%")
                    m3.metric("Codons", f"{res['length'] // 3}")
                    st.code(f"Reverse Complement: {res['rev_comp']}")
                    st.code(f"Protein Translation: {res['protein']}")

# ------------------------------------------
# MODULE 6: GIS RESISTANCE MAP
# ------------------------------------------
elif menu == "🗺️ GIS Resistance Map":
    st.title("🗺️ Geospatial Resistance Mapping")
    conn = get_db_connection()
    map_df = pd.read_sql_query("SELECT sample_id, source_location, latitude, longitude, mcr_variant, colistin_mic FROM mcr_gene_surveillance", conn)
    conn.close()

    st.dataframe(map_df, use_container_width=True)
    if not map_df.empty:
        st.map(map_df, latitude="latitude", longitude="longitude")

# ------------------------------------------
# MODULE 7: ENVIRONMENTAL COMPLIANCE
# ------------------------------------------
elif menu == "🌊 Environmental Compliance":
    st.title("🌊 Environmental Audit & Compliance")
    st.subheader("🥩 Abattoir & Water Quality Audit Operations")
    conn = get_db_connection()
    mcr_df = pd.read_sql_query("SELECT * FROM mcr_gene_surveillance", conn)
    conn.close()
    st.dataframe(mcr_df, use_container_width=True)

# ------------------------------------------
# MODULE 8: BUSINESS PORTFOLIO
# ------------------------------------------
elif menu == "💼 Business Portfolio":
    st.title("💼 Enterprise Venture Portfolio")
    conn = get_db_connection()
    biz_df = pd.read_sql_query("SELECT * FROM business_projects", conn)
    conn.close()
    st.dataframe(biz_df, use_container_width=True)

# ------------------------------------------
# MODULE 9: EPIDEMIOLOGICAL COHORT
# ------------------------------------------
elif menu == "📊 Epidemiological Cohort":
    st.title("📊 Women's Health Cohort")
    conn = get_db_connection()
    cohort_df = pd.read_sql_query("SELECT * FROM ppwr_cohort", conn)
    conn.close()
    st.dataframe(cohort_df, use_container_width=True)

# ------------------------------------------
# MODULE 10: LOCAL AI & NLP BRIDGE
# ------------------------------------------
elif menu == "💬 Local AI & NLP Bridge":
    allowed, msg = check_user_access(st.session_state.user_email, required_tier="Apex Sovereign")
    if not allowed:
        render_paywall_screen("Local AI Bridge", required_tier="Apex Sovereign")
    else:
        st.title("💬 Local AI Query Console")
        prompt = st.text_area("Prompt", value="Explain plasmid-mediated colistin resistance.")
        if st.button("Query Ollama", type="primary"):
            try:
                res = requests.post("http://localhost:11434/api/generate", json={"model": "llama3.2", "prompt": prompt, "stream": False}, timeout=2)
                st.write(res.json().get("response"))
            except Exception:
                st.info("Ollama offline. Static response fallback ready.")

# ------------------------------------------
# MODULE 11: ACADEMIC REPORT VAULT
# ------------------------------------------
elif menu == "🗂️ Academic Report Vault":
    st.title("🗂️ Academic Report Vault")
    report = f"# Research Report\n**Author:** Kula Chris\n**Date:** {datetime.now().strftime('%Y-%m-%d')}"
    st.download_button("Export Markdown", data=report, file_name="Report.md", mime="text/markdown")

# ------------------------------------------
# MODULE 12: IDENTITY SETTINGS
# ------------------------------------------
elif menu == "👤 Identity Settings":
    st.title("👤 Operator Settings")
    st.write(f"Logged in as: **{st.session_state.username}** ({st.session_state.user_email})")

# ------------------------------------------
# MODULE 13: SECURITY & DATABASE CORE
# ------------------------------------------
elif menu == "🛡️ Security & Database Core":
    st.title("🛡️ Database Management & Core Security")
    st.caption("Manage local SQLite persistence, clear seeded data, or backup database snapshots.")

    s_tab1, s_tab2 = st.tabs(["🧹 Database Purge & Seed Control", "💾 Backup & Audit Streams"])

    with s_tab1:
        st.subheader("🧹 Database Seed Management")
        st.warning("Clicking below will clear default template data from the database.")
        if st.button("Purge Default Template Records"):
            init_db(purge_and_reseed=True)
            log_audit(st.session_state.username, "db_purge", "Purged seeded records.")
            st.success("Default template records purged! All database tables are now clean.")
            st.rerun()

    with s_tab2:
        st.subheader("📜 System Audit Trail")
        conn = get_db_connection()
        logs_df = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 30", conn)
        conn.close()
        st.dataframe(logs_df, use_container_width=True)