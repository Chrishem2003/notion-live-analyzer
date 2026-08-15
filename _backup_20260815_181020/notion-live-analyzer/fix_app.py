code = """import streamlit as st
import os
import base64

st.set_page_config(
    page_title="Chrishem Science Hub - Sovereign Gateway",
    page_icon="??",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def get_image_base64(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    return None

img_path = "chrishem.png"
if not os.path.exists(img_path):
    img_path = r"C:\\Users\\Admin\\Pictures\\chrishem.png"
img_base64 = get_image_base64(img_path)

st.markdown(\"\"\"
<style>
@import url(\x27https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap\x27);
html, body, [class*="css"] { font-family: \x27Plus Jakarta Sans\x27, sans-serif; }
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
\"\"\", unsafe_allow_html=True)

if "portal_unlocked" not in st.session_state:
    st.session_state.portal_unlocked = False
if "user_identity" not in st.session_state:
    st.session_state.user_identity = {}

def main():
    if not st.session_state.portal_unlocked:
        st.markdown("<div style=\"height: 2vh;\"></div>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 4.5, 1])
        with col2:
            img_tag = f\"<img src=\x27data:image/png;base64,{img_base64}\x27 class=\x27profile-img\x27>\" if img_base64 else \"<div style=\x27font-size: 60px;\x27>??</div>\"
            
            st.markdown(f\"\"\"
            <div class=\"landing-container\">
                <div class=\"profile-img-wrap\">{img_tag}</div>
                <div class=\"hub-title\">CHRISHEM SCIENCE HUB &amp; ECOSYSTEM</div>
                <div class=\"hub-subtitle\">Sovereign Enterprise Engine &bull; Advanced Analytics &amp; Bioinformatics Gateway</div>
            </div>
            \"\"\", unsafe_allow_html=True)
            
            st.markdown("<div style=\"height: 20px;\"></div>", unsafe_allow_html=True)
            
            tab_signin, tab_signup = st.tabs(["?? Secure Sign In", "?? First-Time Registration"])
            
            with tab_signin:
                si_email = st.text_input("Email Address", placeholder="e.g. chrishem242@gmail.com", key="si_email_input")
                si_name = st.text_input("Full Name / Alias", placeholder="e.g. Chrishem", key="si_name_input")
                
                c_b1, c_b2 = st.columns(2)
                with c_b1:
                    if st.button("?? Authenticate Hub", use_container_width=True):
                        entered_email = si_email.strip().lower() if si_email else "guest@hub.com"
                        entered_name = si_name.strip() if si_name else "Chrishem"
                        is_admin = (entered_email == "chrishem242@gmail.com")
                        
                        st.session_state.portal_unlocked = True
                        st.session_state.user_identity = {
                            "email": entered_email,
                            "name": entered_name,
                            "role": "Supreme Architect & System Owner" if is_admin else "Verified Enterprise Analyst",
                            "is_admin": is_admin
                        }
                        st.rerun()
                with c_b2:
                    if st.button("?? Instant Google Sign-In (Simulated)", use_container_width=True):
                        st.session_state.portal_unlocked = True
                        st.session_state.user_identity = {
                            "email": "chrishem242@gmail.com",
                            "name": "Chrishem",
                            "role": "Supreme Architect & System Owner",
                            "is_admin": True
                        }
                        st.rerun()
            
            with tab_signup:
                su_name = st.text_input("Your Preferred Name", placeholder="e.g. Chrishem Kula", key="su_name_input")
                su_email = st.text_input("Your Email Address", placeholder="e.g. chrishem242@gmail.com", key="su_email_input")
                
                if st.button("? Register & Launch Sovereign Engine", use_container_width=True):
                    reg_name = su_name.strip() if su_name else "Chrishem"
                    reg_email = su_email.strip().lower() if su_email else "guest@hub.com"
                    is_admin = (reg_email == "chrishem242@gmail.com")
                    
                    st.session_state.portal_unlocked = True
                    st.session_state.user_identity = {
                        "email": reg_email,
                        "name": reg_name,
                        "role": "Supreme Architect & System Owner" if is_admin else "Registered Pioneer Analyst",
                        "is_admin": is_admin
                    }
                    st.rerun()
            
            st.markdown("<hr style=\"border-color: rgba(255,255,255,0.1); margin: 25px 0;\">", unsafe_allow_html=True)
            st.markdown("<h4 style=\"text-align: center; color: #F8FAFC; font-size: 1.1rem; margin-bottom: 12px;\">?? Download Complete Portable System Suite</h4>", unsafe_allow_html=True)
            
            d_col1, d_col2, d_col3, d_col4 = st.columns(4)
            with d_col1:
                st.download_button("?? Windows (.exe)", data=b"Mock Windows Compiled Enterprise Bundle Binary", file_name="ChrishemScienceHub_Win64.zip", use_container_width=True)
            with d_col2:
                st.download_button("?? macOS (.app/.dmg)", data=b"Mock macOS Universal Binary Package", file_name="ChrishemScienceHub_macOS.dmg", use_container_width=True)
            with d_col3:
                st.download_button("?? Linux (.AppImage)", data=b"Mock Linux Standalone AppImage Binary", file_name="ChrishemScienceHub_Linux.AppImage", use_container_width=True)
            with d_col4:
                st.download_button("?? Mobile (.apk)", data=b"Mock Android Compiled Client Package", file_name="ChrishemScienceHub_Mobile.apk", use_container_width=True)
    else:
        user = st.session_state.get("user_identity", {})
        username = user.get("name", "Chrishem")
        role = user.get("role", "Analyst")
        is_admin = user.get("is_admin", False)
        
        st.sidebar.title(f"? Welcome back, {username}!")
        st.sidebar.caption(f"Role: {role}")
        if is_admin:
            st.sidebar.success("??? Admin Privileges Active")
            
        if st.sidebar.button("?? Lock / Switch Account"):
            st.session_state.portal_unlocked = False
            st.rerun()
            
        st.sidebar.markdown("---")
        st.success(f"System Operational. Welcome to the workspace, **{username}**.")
        st.info("Your full module suite and multi-page analytics engine are now active via the sidebar navigation.")

if __name__ == "__main__":
    main()
"""

with open("App.py", "w", encoding="utf-8") as f:
    f.write(code)
print("App.py successfully generated!")

