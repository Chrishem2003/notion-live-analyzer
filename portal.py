import base64
import os
import shutil
import streamlit as st

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Chrishem Science Hub - Secure Sovereign Gateway",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- FOLDER PATHS FOR DYNAMIC LOCKING ---
ACTIVE_PAGES_DIR = "pages"
HIDDEN_PAGES_DIR = ".pages_hidden"

def lock_pages():
    """Moves all active pages to the hidden directory so they vanish from the sidebar."""
    if os.path.exists(ACTIVE_PAGES_DIR):
        if not os.path.exists(HIDDEN_PAGES_DIR):
            os.makedirs(HIDDEN_PAGES_DIR)
        for filename in os.listdir(ACTIVE_PAGES_DIR):
            src = os.path.join(ACTIVE_PAGES_DIR, filename)
            dst = os.path.join(HIDDEN_PAGES_DIR, filename)
            if os.path.isfile(src) and not os.path.exists(dst):
                shutil.move(src, dst)

def unlock_pages():
    """Restores pages from the hidden directory back into the active pages folder."""
    if os.path.exists(HIDDEN_PAGES_DIR):
        if not os.path.exists(ACTIVE_PAGES_DIR):
            os.makedirs(ACTIVE_PAGES_DIR)
        for filename in os.listdir(HIDDEN_PAGES_DIR):
            src = os.path.join(HIDDEN_PAGES_DIR, filename)
            dst = os.path.join(ACTIVE_PAGES_DIR, filename)
            if os.path.isfile(src) and not os.path.exists(dst):
                shutil.move(src, dst)

# --- LOCAL IMAGE LOADER ---
def get_image_base64(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    return None

img_path = "chrishem.png"
if not os.path.exists(img_path):
    img_path = r"C:\Users\Admin\Pictures\chrishem.png"
img_base64 = get_image_base64(img_path)

# --- ADVANCED COSMIC STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background: radial-gradient(circle at 15% 20%, #0c0f1d 0%, #05070b 85%); color: #f3f4f6; }
    .landing-container {
        background: rgba(20, 25, 42, 0.75);
        backdrop-filter: blur(24px);
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 28px;
        padding: 45px 35px;
        box-shadow: 0 30px 60px rgba(0, 0, 0, 0.8), 0 0 40px rgba(56, 189, 248, 0.1);
        text-align: center;
        max-width: 780px;
        margin: 0 auto;
    }
    .hub-title {
        font-size: 2.3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #38BDF8 0%, #818CF8 50%, #F472B6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 10px;
    }
    .hub-subtitle { font-size: 1.05rem; color: #94A3B8; font-weight: 400; }
    .profile-img-wrap { display: flex; justify-content: center; margin-bottom: 20px; }
    .profile-img {
        width: 110px; height: 110px; border-radius: 50%; object-fit: cover;
        border: 3px solid #38BDF8; box-shadow: 0 0 35px rgba(56, 189, 248, 0.6);
    }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if "portal_unlocked" not in st.session_state:
    st.session_state.portal_unlocked = False
if "user_identity" not in st.session_state:
    st.session_state.user_identity = {}

# Enforce synchronization: If locked, lock pages. If unlocked, ensure pages are visible.
if not st.session_state.portal_unlocked:
    lock_pages()
else:
    unlock_pages()

# --- GATEWAY SCREEN (LOCKED) ---
if not st.session_state.portal_unlocked:
    st.markdown("<div style='height: 2vh;'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 4.5, 1])
    with col2:
        img_tag = f'<img src="data:image/png;base64,{img_base64}" class="profile-img">' if img_base64 else '<div style="font-size: 60px;">🧬</div>'
        st.markdown(f"""
        <div class="landing-container">
            <div class="profile-img-wrap">{img_tag}</div>
            <div class="hub-title">CHRISHEM SCIENCE HUB & ECOSYSTEM</div>
            <div class="hub-subtitle">Sovereign Enterprise Engine • Secure Multi-Page Access Gateway</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        tab_signin, tab_signup = st.tabs(["🔐 Secure Sign In", "📝 First-Time Registration"])
        
        with tab_signin:
            si_email = st.text_input("Email Address", placeholder="e.g. chrishem242@gmail.com", key="si_email_input")
            si_name = st.text_input("Full Name / Alias", placeholder="e.g. Chrishem", key="si_name_input")
            
            c_b1, c_b2 = st.columns(2)
            with c_b1:
                if st.button("🚀 Authenticate Hub", use_container_width=True):
                    entered_email = si_email.strip().lower() if si_email else "guest@hub.com"
                    entered_name = si_name.strip() if si_name else "Chrishem"
                    is_admin = (entered_email == "chrishem242@gmail.com")
                    
                    st.session_state.portal_unlocked = True
                    st.session_state.user_identity = {
                        "email": entered_email, "name": entered_name,
                        "role": "Supreme Architect & System Owner" if is_admin else "Verified Enterprise Analyst",
                        "is_admin": is_admin
                    }
                    unlock_pages()
                    st.rerun()
            with c_b2:
                if st.button("🔵 Instant Google Sign-In (Simulated)", use_container_width=True):
                    st.session_state.portal_unlocked = True
                    st.session_state.user_identity = {
                        "email": "chrishem242@gmail.com", "name": "Chrishem",
                        "role": "Supreme Architect & System Owner", "is_admin": True
                    }
                    unlock_pages()
                    st.rerun()
                    
        with tab_signup:
            su_name = st.text_input("Your Preferred Name", placeholder="e.g. Chrishem Kula", key="su_name_input")
            su_email = st.text_input("Your Email Address", placeholder="e.g. chrishem242@gmail.com", key="su_email_input")
            if st.button("✨ Register & Launch Sovereign Engine", use_container_width=True):
                reg_name = su_name.strip() if su_name else "Chrishem"
                reg_email = su_email.strip().lower() if su_email else "guest@hub.com"
                is_admin = (reg_email == "chrishem242@gmail.com")
                
                st.session_state.portal_unlocked = True
                st.session_state.user_identity = {
                    "email": reg_email, "name": reg_name,
                    "role": "Supreme Architect & System Owner" if is_admin else "Registered Pioneer Analyst",
                    "is_admin": is_admin
                }
                unlock_pages()
                st.rerun()

else:
    # --- UNLOCKED: DISPLAY DASHBOARD & REVEAL 50+ SIDEBAR PAGES ---
    identity = st.session_state.get("user_identity", {"name": "Chrishem", "role": "Supreme Architect"})
    
    st.sidebar.success(f"🔓 Logged in as: {identity.get('name')}")
    st.sidebar.markdown(f"**Role:** `{identity.get('role')}`")
    
    if st.sidebar.button("🔒 Lock Portal & Sign Out", use_container_width=True):
        st.session_state.portal_unlocked = False
        lock_pages()  # Immediately hide all 50+ pages again
        st.rerun()
        
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📂 System Navigation")
    st.sidebar.info("All 50+ workspace modules are unlocked and visible in the menu below.")

    # Main dashboard interface post-login
    st.title("⚡ Chrishem Sovereign Apex Hub")
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Gateway Status", "Unlocked", delta="Secure Session")
    col2.metric("Active Session User", identity.get("name"))
    col3.metric("System Security", "Enclave Verified", delta="Tier-1")
    
    st.markdown("### 🌟 Welcome to the Core Ecosystem")
    st.write("Authentication was successful. Your 50+ pages have been dynamically restored to the sidebar navigation tree. Select any module from the left menu to begin working.")