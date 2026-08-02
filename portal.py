import base64
import os
import streamlit as st

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Chrishem Science Hub - Sovereign Gateway",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# --- LOCAL IMAGE LOADER (Base64 Safe Encoding) ---
def get_image_base64(image_path):
  if os.path.exists(image_path):
    with open(image_path, "rb") as img_file:
      return base64.b64encode(img_file.read()).decode("utf-8")
  return None


# Target path provided by user
img_path = r"C:\Users\Admin\Pictures\chrishem.png"
img_base64 = get_image_base64(img_path)

# --- BREATHTAKING PREMIUM STYLING & ANIMATED GLOW CSS ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Cosmic Deep Space Background */
    .stApp {
        background: radial-gradient(circle at 15% 20%, #0c0f1d 0%, #05070b 85%);
        color: #f3f4f6;
    }

    /* Hide default streamlit layout clutter on the portal screen */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Premium Glassmorphic Landing Container */
    .landing-container {
        background: rgba(20, 25, 42, 0.75);
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 28px;
        padding: 50px 40px;
        box-shadow: 0 30px 60px rgba(0, 0, 0, 0.8), 0 0 40px rgba(56, 189, 248, 0.1);
        text-align: center;
        max-width: 750px;
        margin: 0 auto;
    }

    /* Gradient Typography */
    .hub-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #38BDF8 0%, #818CF8 50%, #F472B6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 12px;
        letter-spacing: -0.5px;
    }

    .hub-subtitle {
        font-size: 1.1rem;
        color: #94A3B8;
        font-weight: 400;
        letter-spacing: 0.2px;
    }

    /* Glowing Circular Profile Graphic */
    .profile-img-wrap {
        display: flex;
        justify-content: center;
        margin-bottom: 25px;
    }

    .profile-img {
        width: 120px;
        height: 120px;
        border-radius: 50%;
        object-fit: cover;
        border: 3px solid #38BDF8;
        box-shadow: 0 0 35px rgba(56, 189, 248, 0.6);
    }

    /* Custom Button Enhancements */
    .stButton>button {
        border-radius: 14px;
        font-weight: 600;
        padding: 0.75rem 1rem;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(56, 189, 248, 0.4);
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- SESSION STATE INITIALIZATION ---
if "portal_unlocked" not in st.session_state:
  st.session_state.portal_unlocked = False

# --- FRONT-DOOR LANDING GATEWAY ---
if not st.session_state.portal_unlocked:
  st.markdown("<div style='height: 4vh;'></div>", unsafe_allow_html=True)

  col1, col2, col3 = st.columns([1, 4, 1])
  with col2:
    # Render local image or fallback icon
    img_tag = (
        f'<img src="data:image/png;base64,{img_base64}" class="profile-img">'
        if img_base64
        else '<div style="font-size: 60px;">🧬</div>'
    )

    st.markdown(
        f"""
        <div class="landing-container">
            <div class="profile-img-wrap">
                {img_tag}
            </div>
            <div class="hub-title">WELCOME TO CHRISHEM SCIENCE HUB</div>
            <div class="hub-subtitle">Sovereign Enterprise Engine & Live Analytics Ecosystem</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<h3 style='text-align: center; font-size: 1.25rem; color: #F8FAFC;"
        " margin-bottom: 20px; font-weight: 600;'>First-Time Access & Sign-In"
        " Gateway</h3>",
        unsafe_allow_html=True,
    )

    # Authentication Action Buttons
    c_auth1, c_auth2 = st.columns(2)
    with c_auth1:
      if st.button("🔵 Sign in with Google", use_container_width=True):
        st.session_state.portal_unlocked = True
        st.rerun()
    with c_auth2:
      if st.button("✉️ Continue with Email", use_container_width=True):
        st.session_state.portal_unlocked = True
        st.rerun()

    st.markdown(
        "<hr style='border-color: rgba(255,255,255,0.1); margin: 30px 0;'>",
        unsafe_allow_html=True,
    )

    # Operating Options & Download Suite
    st.markdown(
        "<p style='text-align: center; color: #94A3B8; font-size: 0.95rem;"
        " margin-bottom: 15px;'>Choose how you want to experience the"
        " platform:</p>",
        unsafe_allow_html=True,
    )

    c_opt1, c_opt2 = st.columns(2)
    with c_opt1:
      if st.button("🌐 Launch in Web Browser", use_container_width=True):
        st.session_state.portal_unlocked = True
        st.rerun()
    with c_opt2:
      with st.popover(
          "📥 Download Full System Versions", use_container_width=True
      ):
        st.markdown("### Target Platform Packages:")
        st.download_button(
            "💻 Windows Installer (.exe)",
            data=b"Mock Windows Binaries",
            file_name="ChrishemScienceHub_Setup.zip",
        )
        st.download_button(
            "🍏 macOS Version",
            data=b"Mock Mac Binaries",
            file_name="ChrishemScienceHub_Mac.zip",
        )
        st.download_button(
            "📱 Mobile App (.apk)",
            data=b"Mock Android APK",
            file_name="ChrishemScienceHub.apk",
        )

else:
  # --- UNLOCKED: RESTORE PAGES FOLDER & LAUNCH APP CORE ---
  hidden_dir = r"D:\notion-live-analyzer\.pages_hidden"
  active_dir = r"D:\notion-live-analyzer\pages"

  # Automatically unhide your 50+ pages directory the moment the user unlocks the gate
  if os.path.exists(hidden_dir) and not os.path.exists(active_dir):
    os.rename(hidden_dir, active_dir)

  # Import and execute your main App script logic safely
  import App

  App.main()