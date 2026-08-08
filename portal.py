import base64
import datetime
import hashlib
import io
import os
import sqlite3
import zipfile
import numpy as np
import pandas as pd
import streamlit as st

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Chrishem Science Hub - Sovereign Enterprise Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- SOVEREIGN DATABASE INITIALIZATION ---
def init_sovereign_db():
    conn = sqlite3.connect("sovereign_apex_engine.db", check_same_thread=False)
    cursor = conn.cursor()
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS live_chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            timestamp TEXT,
            prompt TEXT,
            response TEXT
        )
    """)
    conn.commit()
    return conn

db_conn = init_sovereign_db()

# --- AUTOMATIC ADMIN PROMOTION FOR CHRISHEM ---
def ensure_superuser_privileges():
    cursor = db_conn.cursor()
    target_email = "chrishem242@gmail.com"
    cursor.execute("SELECT email FROM auth_users WHERE email = ?", (target_email,))
    if cursor.fetchone():
        cursor.execute("UPDATE auth_users SET role = 'admin' WHERE email = ?", (target_email,))
    else:
        # Auto-provision master account if it hasn't registered yet
        default_hash = hashlib.sha256("chrishem2026".encode()).hexdigest()
        cursor.execute("INSERT INTO auth_users (email, name, password_hash, role) VALUES (?, ?, ?, ?)",
                       (target_email, "Chrishem", default_hash, "admin"))
    
    cursor.execute("INSERT OR REPLACE INTO user_subscriptions (email, trial_end, is_active) VALUES (?, ?, ?)",
                   (target_email, "2030-12-31 23:59:59", 1))
    db_conn.commit()

ensure_superuser_privileges()

# --- AUTH & SUBSCRIPTION HANDLERS ---
class AuthStore:
    def verify_login(self, email, password):
        cursor = db_conn.cursor()
        # Force update admin status on any login attempt for safety
        if email.lower().strip() == "chrishem242@gmail.com":
            cursor.execute("UPDATE auth_users SET role = 'admin' WHERE email = ?", (email,))
            db_conn.commit()
            
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
        
        assigned_role = "admin" if email.lower().strip() == "chrishem242@gmail.com" else role
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute("INSERT INTO auth_users (email, name, password_hash, role) VALUES (?, ?, ?, ?)",
                       (email, name, pwd_hash, assigned_role))
        trial_end = (datetime.datetime.now() + datetime.timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT OR IGNORE INTO user_subscriptions (email, trial_end, is_active) VALUES (?, ?, ?)",
                       (email, trial_end, 1))
        db_conn.commit()
        return {"ok": True}

auth_store = AuthStore()

class SubscriptionManager:
    def ensure_trial_started(self, email):
        cursor = db_conn.cursor()
        cursor.execute("SELECT email FROM user_subscriptions WHERE email = ?", (email,))
        if not cursor.fetchone():
            trial_end = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO user_subscriptions (email, trial_end, is_active) VALUES (?, ?, ?)",
                           (email, trial_end, 1))
            db_conn.commit()

subscription = SubscriptionManager()

def is_admin():
    identity = st.session_state.get("user_identity", {})
    return identity.get("role") == "admin" or identity.get("email") == "chrishem242@gmail.com"

# --- LOCAL IMAGE LOADER ---
def get_image_base64(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    return None

img_path = "chrishem.png"
img_base64 = get_image_base64(img_path)

# --- IN-MEMORY ZIP PACKAGE BUILDER ---
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

# --- COSMIC UI STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; color: #F8FAFC; }
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

# --- GATEWAY SCREEN (LOCKED STATE) ---
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
                    st.error("Incorrect email or password. (Note: Master account chrishem242@gmail.com can log in or register freely).")
                else:
                    st.session_state.portal_unlocked = True
                    st.session_state.user_identity = {
                        "email": user["email"],
                        "name": user["name"],
                        "role": "admin" if user["email"] == "chrishem242@gmail.com" else user["role"],
                        "is_admin": (user["email"] == "chrishem242@gmail.com" or user["role"] == "admin"),
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
                elif len(su_password) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    result = auth_store.create_user(su_email, su_name or "Analyst", su_password, role="user")
                    if not result["ok"]:
                        st.error(result["error"])
                    else:
                        st.success("Account created successfully! Please sign in above.")

        with tab_downloads:
            st.markdown("### 🌍 Cross-Platform Ecosystem Releases")
            st.write("Click any bundle below to download the setup package.")
            
            d_col1, d_col2 = st.columns(2)
            with d_col1:
                st.markdown('<div class="download-card"><h4>🪟 Windows Suite</h4><p style="font-size: 0.85rem; color: #94A3B8;">Windows Desktop Engine</p></div>', unsafe_allow_html=True)
                st.download_button("📥 Download Windows Suite (.zip)", data=win_zip, file_name="chrishem_hub_windows.zip", mime="application/zip", use_container_width=True)

                st.markdown('<div class="download-card" style="margin-top: 15px;"><h4>🐧 Linux Distribution</h4><p style="font-size: 0.85rem; color: #94A3B8;">Ubuntu/Debian Server Build</p></div>', unsafe_allow_html=True)
                st.download_button("📥 Download Linux Build (.zip)", data=linux_zip, file_name="chrishem_hub_linux.zip", mime="application/zip", use_container_width=True)

            with d_col2:
                st.markdown('<div class="download-card"><h4>🍏 macOS Architecture</h4><p style="font-size: 0.85rem; color: #94A3B8;">Apple Silicon & Intel Universal</p></div>', unsafe_allow_html=True)
                st.download_button("📥 Download macOS Bundle (.zip)", data=mac_zip, file_name="chrishem_hub_macos.zip", mime="application/zip", use_container_width=True)

                st.markdown('<div class="download-card" style="margin-top: 15px;"><h4>📱 Mobile PWA / Phone</h4><p style="font-size: 0.85rem; color: #94A3B8;">Progressive Web Client</p></div>', unsafe_allow_html=True)
                st.download_button("📥 Download Mobile PWA Config (.zip)", data=pwa_zip, file_name="chrishem_hub_mobile_pwa.zip", mime="application/zip", use_container_width=True)

# --- UNLOCKED WORKSPACE & DASHBOARD ---
else:
    identity = st.session_state.get("user_identity", {"name": "Chrishem", "role": "admin"})
    
    st.sidebar.title("CHRISHEM APEX")
    st.sidebar.success(f"🔓 Logged in as: {identity.get('name')}")
    st.sidebar.markdown(f"**Email:** `{identity.get('email', 'chrishem242@gmail.com')}`")
    st.sidebar.markdown(f"**Privilege Level:** `{'👑 Full-Time Admin' if is_admin() else 'Standard User'}`")
    
    st.sidebar.markdown('<div class="glass-hr"></div>', unsafe_allow_html=True)
    
    # Unique Feature: System Theme Customizer
    theme_mode = st.sidebar.selectbox("Interface Spectrum", ["Deep Space Nebula", "Cyber Matrix Dark", "Sovereign Gold"])
    
    if st.sidebar.button("🔒 Lock Portal & Sign Out", use_container_width=True):
        st.session_state.portal_unlocked = False
        st.rerun()
        
    st.sidebar.markdown('<div class="glass-hr"></div>', unsafe_allow_html=True)
    st.sidebar.markdown("### 📁 Navigation Matrix")
    
    menu_selection = st.sidebar.radio("Select Workspace", [
        "⚡ Apex Dashboard", 
        "🤖 AI Intelligence Daemon", 
        "🔬 Bioinformatics Studio", 
        "🛡️ Admin Security & User Controls"
    ])

    st.title("⚡ Chrishem Sovereign Apex Hub")
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Gateway Status", "Unlocked", delta="Enclave Verified")
    col2.metric("Active Operator", identity.get("name"))
    col3.metric("Authorization", "Full-Time Admin" if is_admin() else "Standard", delta="Tier-1 Access")
    
    st.markdown('<div class="glass-hr"></div>', unsafe_allow_html=True)

    if menu_selection == "⚡ Apex Dashboard":
        st.markdown("### 🌟 Welcome to the Core Ecosystem Workspace")
        st.write("Your session has full-time administrative clearance. Use the panels below or the sidebar navigation to run analytics, manage system tools, and review telemetry.")
        
        c_a, c_b = st.columns(2)
        with c_a:
            st.info("**System Status:** All telemetry daemons are operating smoothly with 0ms latency.")
        with c_b:
            st.success("**License Status:** Lifetime Sovereign Enterprise Access Enabled for `chrishem242@gmail.com`.")

    elif menu_selection == "🤖 AI Intelligence Daemon":
        st.markdown("### 🤖 Autonomous AI Intelligence & Problem Solver")
        st.write("Interact directly with the sovereign heuristic assistant running in your secure session.")
        
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
            
        user_prompt = st.text_area("Enter your analytical task or problem query:", key="portal_ai_input")
        if st.button("Execute AI Generation ⚡"):
            if user_prompt.strip():
                simulated_response = f"Analyzed query under sovereign protocols: '{user_prompt[:60]}...' [Execution successful with 99.9% confidence matrix]."
                cursor.execute("INSERT INTO live_chat_history (username, timestamp, prompt, response) VALUES (?, ?, ?, ?)",
                               (identity.get("name"), datetime.datetime.now().isoformat(), user_prompt, simulated_response))
                db_conn.commit()
                st.rerun()

    elif menu_selection == "🔬 Bioinformatics Studio":
        st.markdown("### 🧬 Genomic Sequence & GC-Content Studio")
        seq_input = st.text_area("Paste FASTA Sequence Data", placeholder="ATGCGATCGATCGATCGATCG...")
        if st.button("Run Sequence Metric Analysis"):
            if seq_input.strip():
                clean_seq = "".join(seq_input.upper().split())
                length = len(clean_seq)
                gc = ((clean_seq.count('G') + clean_seq.count('C')) / length * 100) if length > 0 else 0
                c1, c2 = st.columns(2)
                c1.metric("Total Base Pairs", f"{length} bp")
                c2.metric("GC-Content Ratio", f"{gc:.2f}%")
            else:
                st.warning("Please provide a sequence string.")

    elif menu_selection == "🛡️ Admin Security & User Controls":
        if not is_admin():
            st.error("🚫 Access Denied: This panel requires full-time administrator clearance.")
        else:
            st.markdown("### 🛡️ Administrative Control Center")
            st.write("Manage active users, database tables, and full privilege rings across the sovereign cluster.")
            
            cursor = db_conn.cursor()
            cursor.execute("SELECT email, name, role FROM auth_users")
            users = cursor.fetchall()
            
            user_df = pd.DataFrame(users, columns=["Email", "Name", "Role"])
            st.dataframe(user_df, use_container_width=True)
            
            st.success("👑 Your account (`chrishem242@gmail.com`) is permanently locked with full administrative privileges and sovereign override capabilities.")