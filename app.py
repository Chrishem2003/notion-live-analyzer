import streamlit as st
import os
import base64

st.set_page_config(
    page_title="Chrishem Science Hub - Sovereign Gateway",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Robust image loader with multiple path fallbacks
def get_image_base64(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    return None

img_base64 = None
for path in ["chrishem.png", "Chrishem.png", r"C:\Users\Admin\Pictures\chrishem.png"]:
    img_base64 = get_image_base64(path)
    if img_base64:
        break

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

if "portal_unlocked" not in st.session_state:
    st.session_state.portal_unlocked = False
if "user_identity" not in st.session_state:
    st.session_state.user_identity = {}

# If NOT logged in, show the custom landing page and stop execution so sidebar modules stay hidden
if not st.session_state.portal_unlocked:
    st.markdown("<div style='height: 2vh;'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 4.5, 1])
    with col2:
        img_tag = f"<img src='data:image/png;base64,{img_base64}' class='profile-img'>" if img_base64 else "<div style='font-size: 60px;'>🧬</div>"
        
        st.markdown(f"""
        <div class="landing-container">
            <div class="profile-img-wrap">{img_tag}</div>
            <div class="hub-title">CHRISHEM SCIENCE HUB &amp; ECOSYSTEM</div>
            <div class="hub-subtitle">Sovereign Enterprise Engine &bull; Advanced Analytics &amp; Bioinformatics Gateway</div>
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
                    st.session_state.portal_unlocked = True
                    st.session_state.user_identity = {
                        "email": si_email.strip().lower() if si_email else "chrishem242@gmail.com",
                        "name": si_name.strip() if si_name else "Chris Shem",
                        "role": "Supreme Architect & System Owner",
                        "is_admin": True
                    }
                    st.rerun()
            with c_b2:
                if st.button("🔵 Instant Google Sign-In", use_container_width=True):
                    st.session_state.portal_unlocked = True
                    st.session_state.user_identity = {
                        "email": "chrishem242@gmail.com",
                        "name": "Chris Shem",
                        "role": "Supreme Architect & System Owner",
                        "is_admin": True
                    }
                    st.rerun()
        
        with tab_signup:
            su_name = st.text_input("Your Preferred Name", placeholder="e.g. Chris Shem", key="su_name_input")
            su_email = st.text_input("Your Email Address", placeholder="e.g. chrishem242@gmail.com", key="su_email_input")
            
            if st.button("✨ Register & Launch Sovereign Engine", use_container_width=True):
                st.session_state.portal_unlocked = True
                st.session_state.user_identity = {
                    "email": su_email.strip().lower() if su_email else "chrishem242@gmail.com",
                    "name": su_name.strip() if su_name else "Chris Shem",
                    "role": "Supreme Architect & System Owner",
                    "is_admin": True
                }
                st.rerun()
        
        st.markdown("<hr style='border-color: rgba(255,255,255,0.1); margin: 25px 0;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center; color: #F8FAFC; font-size: 1.1rem; margin-bottom: 12px;'>📥 Download Complete Portable System Suite</h4>", unsafe_allow_html=True)
        
        d_col1, d_col2, d_col3, d_col4 = st.columns(4)
        with d_col1:
            st.download_button("💻 Windows (.exe)", data=b"Mock Windows Compiled Enterprise Bundle Binary", file_name="ChrishemScienceHub_Win64.zip", use_container_width=True)
        with d_col2:
            st.download_button("🍏 macOS (.app/.dmg)", data=b"Mock macOS Universal Binary Package", file_name="ChrishemScienceHub_macOS.dmg", use_container_width=True)
        with d_col3:
            st.download_button("🐧 Linux (.AppImage)", data=b"Mock Linux Standalone AppImage Binary", file_name="ChrishemScienceHub_Linux.AppImage", use_container_width=True)
        with d_col4:
            st.download_button("📱 Mobile (.apk)", data=b"Mock Android Compiled Client Package", file_name="ChrishemScienceHub_Mobile.apk", use_container_width=True)
    
    st.stop() # Stops execution here so locked users never see the main workspace or sidebar pages

# --- ONCE LOGGED IN: Displays the Hub and unlocks the sidebar pages automatically ---
user = st.session_state.get("user_identity", {})
username = user.get("name", "Chris Shem")
role = user.get("role", "Supreme Architect & System Owner")

st.sidebar.title(f"⚡ Welcome back, {username}!")
st.sidebar.caption(f"Role: {role}")
st.sidebar.success("🛡️ Admin Privileges Active")

if st.sidebar.button("🔒 Lock / Switch Account"):
    st.session_state.portal_unlocked = False
    st.rerun()
    
st.sidebar.markdown("---")

st.title("🧬 Chrishem Science Hub & Workspace")
st.success(f"System Operational. Welcome back, **{username}**.")
st.markdown("""
Your sovereign workspace is fully unlocked. **All your 50+ connected analysis tools and secondary pages are now available in the sidebar navigation menu on the left.** Select any module to launch its dashboard interface.
""")