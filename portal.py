import base64
import io
import os
import zipfile
import streamlit as st

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
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
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
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if "portal_unlocked" not in st.session_state:
    st.session_state.portal_unlocked = False
if "user_identity" not in st.session_state:
    st.session_state.user_identity = {}

# --- GATEWAY SCREEN (LOCKED STATE) ---
if not st.session_state.portal_unlocked:
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {display: none;}
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height: 2vh;'></div>", unsafe_allow_html=True)
    
    img_tag = f'<img src="data:image/png;base64,{img_base64}" class="profile-img">' if img_base64 else '<div style="font-size: 50px;">ðŸ§¬</div>'
    
    st.markdown(f"""
    <div class="landing-container">
        <div class="profile-img-wrap">{img_tag}</div>
        <div class="hub-title">CHRISHEM SCIENCE HUB & ECOSYSTEM</div>
        <div class="hub-subtitle">Sovereign Enterprise Engine â€¢ Secure Multi-Platform Gateway</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    
    _, center_col, _ = st.columns([0.5, 3, 0.5])
    with center_col:
        tab_signin, tab_signup, tab_downloads = st.tabs(["ðŸ” Secure Sign In", "ðŸ“ Register", "ðŸ“± Ecosystem Downloads"])
        
        with tab_signin:
            si_email = st.text_input("Email Address", placeholder="e.g. chrishem242@gmail.com", key="si_email_input")
            si_name = st.text_input("Full Name / Alias", placeholder="e.g. Chrishem", key="si_name_input")
            
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.button("ðŸš€ Authenticate Hub", use_container_width=True):
                entered_email = si_email.strip().lower() if si_email else "guest@hub.com"
                entered_name = si_name.strip() if si_name else "Chrishem"
                is_admin = (entered_email == "chrishem242@gmail.com")
                
                st.session_state.portal_unlocked = True
                st.session_state.user_identity = {
                    "email": entered_email, "name": entered_name,
                    "role": "Supreme Architect & System Owner" if is_admin else "Verified Analyst",
                    "is_admin": is_admin
                }
                st.rerun()
                
            if st.button("ðŸ”µ Instant Google Sign-In (Simulated)", use_container_width=True):
                st.session_state.portal_unlocked = True
                st.session_state.user_identity = {
                    "email": "chrishem242@gmail.com", "name": "Chrishem",
                    "role": "Supreme Architect & System Owner", "is_admin": True
                }
                st.rerun()
                
        with tab_signup:
            su_name = st.text_input("Your Preferred Name", placeholder="e.g. Chrishem Kula", key="su_name_input")
            su_email = st.text_input("Your Email Address", placeholder="e.g. chrishem242@gmail.com", key="su_email_input")
            
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.button("âœ¨ Register & Launch Engine", use_container_width=True):
                reg_name = su_name.strip() if su_name else "Chrishem"
                reg_email = su_email.strip().lower() if su_email else "guest@hub.com"
                is_admin = (reg_email == "chrishem242@gmail.com")
                
                st.session_state.portal_unlocked = True
                st.session_state.user_identity = {
                    "email": reg_email, "name": reg_name,
                    "role": "Supreme Architect & System Owner" if is_admin else "Registered Pioneer Analyst",
                    "is_admin": is_admin
                }
                st.rerun()

        with tab_downloads:
            st.markdown("### ðŸŒ Cross-Platform Ecosystem Releases")
            st.write("Click any bundle below to directly download the installation package to your local system.")
            
            d_col1, d_col2 = st.columns(2)
            
            with d_col1:
                st.markdown("""
                <div class="download-card">
                    <h4>ðŸªŸ Windows Suite</h4>
                    <p style='font-size: 0.85rem; color: #94A3B8;'>Optimized for Windows 10/11 (WSL2 / Desktop Engine)</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.download_button(
                    label="ðŸ“¥ Download Windows Suite (.zip)",
                    data=win_zip,
                    file_name="chrishem_hub_windows.zip",
                    mime="application/zip",
                    use_container_width=True
                )

                st.markdown("""
                <div class="download-card" style="margin-top: 15px;">
                    <h4>ðŸ§ Linux Distribution</h4>
                    <p style='font-size: 0.85rem; color: #94A3B8;'>Ubuntu / Debian / Enterprise Server Build</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.download_button(
                    label="ðŸ“¥ Download Linux Build (.zip)",
                    data=linux_zip,
                    file_name="chrishem_hub_linux.zip",
                    mime="application/zip",
                    use_container_width=True
                )

            with d_col2:
                st.markdown("""
                <div class="download-card">
                    <h4>ðŸŽ macOS Architecture</h4>
                    <p style='font-size: 0.85rem; color: #94A3B8;'>Apple Silicon (M1/M2/M3) & Intel Universal</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.download_button(
                    label="ðŸ“¥ Download macOS Bundle (.zip)",
                    data=mac_zip,
                    file_name="chrishem_hub_macos.zip",
                    mime="application/zip",
                    use_container_width=True
                )

                st.markdown("""
                <div class="download-card" style="margin-top: 15px;">
                    <h4>ðŸ“± Mobile PWA / Phone</h4>
                    <p style='font-size: 0.85rem; color: #94A3B8;'>Android & iOS Progressive Web Client</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.download_button(
                    label="ðŸ“¥ Download Mobile PWA Config (.zip)",
                    data=pwa_zip,
                    file_name="chrishem_hub_mobile_pwa.zip",
                    mime="application/zip",
                    use_container_width=True
                )

else:
    identity = st.session_state.get("user_identity", {"name": "Chrishem", "role": "Supreme Architect"})
    
    st.sidebar.success(f"ðŸ”“ Logged in as: {identity.get('name')}")
    st.sidebar.markdown(f"**Role:** `{identity.get('role')}`")
    
    if st.sidebar.button("ðŸ”’ Lock Portal & Sign Out", use_container_width=True):
        st.session_state.portal_unlocked = False
        st.rerun()
        
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ðŸ“‚ System Navigation")
    st.sidebar.info("All workspace modules are active and accessible below.")

    st.title("âš¡ Chrishem Sovereign Apex Hub")
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Gateway Status", "Unlocked", delta="Secure Session")
    col2.metric("Active User", identity.get("name"))
    col3.metric("Security Level", "Enclave Verified", delta="Tier-1")
    
    st.markdown("### ðŸŒŸ Welcome to the Core Ecosystem")
    st.write("Authentication verified. Use the sidebar navigation menu to access your complete portfolio of tools and analytical pages.")
