import base64
import os
import streamlit as st

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Chrishem Science Hub - Gateway",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed",  # Keeps sidebar hidden initially
)

# --- LOCAL IMAGE LOADER ---


def get_image_base64(image_path):
  if os.path.exists(image_path):
    with open(image_path, "rb") as img_file:
      return base64.b64encode(img_file.read()).decode("utf-8")
  return None


img_path = r"C:\Users\Admin\Pictures\chrishem.png"
img_base64 = get_image_base64(img_path)

# --- STYLING ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    .stApp { background: radial-gradient(circle at 20% 20%, #0c0f1d 0%, #05070b 85%); color: #f3f4f6; font-family: 'Plus Jakarta Sans', sans-serif; }
    .landing-card { background: rgba(25, 30, 48, 0.7); backdrop-filter: blur(20px); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 24px; padding: 45px; box-shadow: 0 25px 50px rgba(0, 0, 0, 0.7); text-align: center; max-width: 700px; margin: 0 auto; }
    .hub-title { font-size: 2.4rem; font-weight: 800; background: linear-gradient(135deg, #38BDF8 0%, #818CF8 50%, #F472B6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 12px; }
    .profile-img { width: 110px; height: 110px; border-radius: 50%; object-fit: cover; border: 3px solid #38BDF8; box-shadow: 0 0 30px rgba(56, 189, 248, 0.5); margin-bottom: 20px; }
    </style>
""",
    unsafe_allow_html=True,
)

# --- SESSION STATE ---
if "portal_unlocked" not in st.session_state:
  st.session_state.portal_unlocked = False

# --- LANDING PAGE GATEWAY ---
if not st.session_state.portal_unlocked:
  st.markdown("<div style='height: 6vh;'></div>", unsafe_allow_html=True)

  col1, col2, col3 = st.columns([1, 3, 1])
  with col2:
    img_html = (
        f'<img src="data:image/png;base64,{img_base64}" class="profile-img">'
        if img_base64
        else '<div style="font-size: 50px;">🧬</div>'
    )

    st.markdown(
        f"""
        <div class="landing-card">
            {img_html}
            <div class="hub-title">WELCOME TO CHRISHEM SCIENCE HUB</div>
            <p style="color: #94A3B8; font-size: 1.05rem; margin-bottom: 0;">Sovereign Enterprise Engine & Live Analytics Ecosystem</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<h3 style='text-align: center; font-size: 1.2rem; color: #F8FAFC;"
        " margin-bottom: 20px;'>First-Time Access & Sign-In Gateway</h3>",
        unsafe_allow_html=True,
    )

    sc1, sc2 = st.columns(2)
    with sc1:
      if st.button("🔵 Sign in with Google", use_container_width=True):
        st.session_state.portal_unlocked = True
        st.rerun()
    with sc2:
      if st.button("✉️ Continue with Email", use_container_width=True):
        st.session_state.portal_unlocked = True
        st.rerun()

    st.markdown(
        "<hr style='border-color: rgba(255,255,255,0.1); margin: 25px 0;'>",
        unsafe_allow_html=True,
    )

    bc1, bc2 = st.columns(2)
    with bc1:
      if st.button("🌐 Launch in Web Browser", use_container_width=True):
        st.session_state.portal_unlocked = True
        st.rerun()
    with bc2:
      with st.popover(
          "📥 Download Full System Versions", use_container_width=True
      ):
        st.markdown("### Choose your target platform:")
        st.download_button(
            "💻 Download for Windows (.exe)",
            data=b"Mock Windows Binaries",
            file_name="ChrishemScienceHub_Setup.zip",
        )
        st.download_button(
            "🍏 Download for macOS",
            data=b"Mock macOS Binaries",
            file_name="ChrishemScienceHub_Mac.zip",
        )
        st.download_button(
            "📱 Download Mobile App (APK)",
            data=b"Mock Android APK",
            file_name="ChrishemScienceHub.apk",
        )

else:
  # --- ONCE UNLOCKED: LOADS YOUR FULL APP & REVEALS SIDEBAR PAGES ---
  import App

  App.main()