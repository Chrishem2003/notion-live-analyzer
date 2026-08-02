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

def home_page():
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
                        entered_email = si_email.strip().lower() if si_email else "chrishem242@gmail.com"
                        entered_name = si_name.strip() if si_name else "Chris Shem"
                        is_admin = True
                        
                        st.session_state.portal_unlocked = True
                        st.session_state.user_identity = {
                            "email": entered_email,
                            "name": entered_name,
                            "role": "Supreme Architect & System Owner",
                            "is_admin": is_admin
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
    else:
        user = st.session_state.get("user_identity", {})
        username = user.get("name", "Chris Shem")
        
        st.title("🧬 Chrishem Science Hub & Workspace")
        st.success(f"System Operational. Welcome back, **{username}**.")
        st.markdown("""
        Your sovereign workspace is unlocked and active. 
        **All 50+ connected analysis modules, tools, and notebooks are now fully populated and accessible in the sidebar navigation menu on the left.** 
        
        Select any tool or page to launch its corresponding dashboard interface instantly.
        """)
        
        if st.button("🔒 Lock / Switch Account"):
            st.session_state.portal_unlocked = False
            st.rerun()

# Define navigation structure matching your pages/ directory automatically
if not st.session_state.portal_unlocked:
    # While locked, only show the home login entrypoint
    pg = st.navigation([st.Page(home_page, title="Portal Gateway", icon="🔐")])
else:
    # Once unlocked, dynamically pull all secondary modules from your pages/ directory alongside home
    try:
        pages_dir = "pages"
        dynamic_pages = [st.Page(home_page, title="Hub Control Center", icon="🧬")]
        if os.path.exists(pages_dir):
            for file in sorted(os.listdir(pages_dir)):
                if file.endswith(".py"):
                    file_path = os.path.join(pages_dir, file)
                    page_title = file[:-3].replace("_", " ").title()
                    dynamic_pages.append(st.Page(file_path, title=page_title, icon="📊"))
        pg = st.navigation(dynamic_pages)
    except Exception:
        pg = st.navigation([st.Page(home_page, title="Hub Control Center", icon="🧬")])

pg.run()