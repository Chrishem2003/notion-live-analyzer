import os
import shutil

app_path = "App.py"
backup_path = "App_backup.py"

if not os.path.exists(app_path):
  print("Error: App.py not found in the current directory!")
  exit()

# Create a safety backup
shutil.copy(app_path, backup_path)
print(f"Safety backup created: {backup_path}")

with open(app_path, "r", encoding="utf-8") as f:
  content = f.read()

# The gateway code snippet to inject
gateway_code = """
# --- CHRISHEM GATEWAY GATEKEEPER ---
def get_image_base64(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    return None
# ------------------------------------
"""

gatekeeper_logic = """
    # --- AUTHENTICATION GATEWAY CHECK ---
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        
    if not st.session_state.authenticated:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<div style='height: 4vh;'></div>", unsafe_allow_html=True)
            img_path = r"C:\\Users\\Admin\\Pictures\\chrishem.png"
            img_base64 = get_image_base64(img_path)
            
            img_html = f'''
            <div style="display: flex; justify-content: center; margin-bottom: 20px;">
                <img src="data:image/png;base64,{img_base64}" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover; border: 3px solid #38BDF8; box-shadow: 0 0 25px rgba(56, 189, 248, 0.4);">
            </div>
            ''' if img_base64 else '<div style="text-align: center; font-size: 40px;">⚡</div>'
            
            st.markdown(f'''
            <div style="background: rgba(30, 41, 59, 0.65); backdrop-filter: blur(16px); border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 20px; padding: 35px; text-align: center; box-shadow: 0 20px 40px rgba(0,0,0,0.6);">
                {img_html}
                <h1 style="font-size: 2.2rem; font-weight: 800; background: linear-gradient(135deg, #38BDF8 0%, #818CF8 50%, #F472B6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px;">WELCOME TO CHRISHEM SCIENCE HUB</h1>
                <p style="color: #94A3B8; font-size: 1rem;">Sovereign Enterprise Engine & Live Analyzer Gateway</p>
            </div>
            ''', unsafe_allow_html=True)
            
            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
            st.markdown("<h3 style='text-align: center; font-size: 1.2rem; color: #F8FAFC; margin-bottom: 15px;'>First-Time Sign-In Portal</h3>", unsafe_allow_html=True)
            
            g_col1, g_col2 = st.columns(2)
            with g_col1:
                if st.button("🔵 Sign in with Google", use_container_width=True):
                    st.session_state.authenticated = True
                    st.session_state.analyst_name = "Kula Chris"
                    st.rerun()
            with g_col2:
                if st.button("✉️ Continue with Email", use_container_width=True):
                    st.session_state.authenticated = True
                    st.session_state.analyst_name = "Guest Analyst"
                    st.rerun()
                    
            st.markdown("<hr style='border-color: rgba(255,255,255,0.1); margin: 20px 0;'>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #94A3B8; font-size: 0.9rem; margin-bottom: 10px;'>Select your operating preference:</p>", unsafe_allow_html=True)
            
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                if st.button("🌐 Use in Web Browser", use_container_width=True):
                    st.session_state.authenticated = True
                    st.session_state.analyst_name = "Web Explorer"
                    st.rerun()
            with b_col2:
                with st.popover("📥 Download Full System (PC/Mobile)", use_container_width=True):
                    st.markdown("### Choose version package:")
                    st.download_button("💻 Windows Installer (.exe)", data=b"Mock Windows Binaries", file_name="ChrishemScienceHub_Windows.zip")
                    st.download_button("🍏 macOS Version", data=b"Mock Mac Binaries", file_name="ChrishemScienceHub_Mac.zip")
                    st.download_button("📱 Mobile App (.apk)", data=b"Mock APK", file_name="ChrishemScienceHub.apk")
        return
"""

# Check if base64 is imported, add if missing
if "import base64" not in content:
  content = "import base64\n" + content

# Inject gateway helper above main() and gatekeeper check inside main()
if "def main():" in content and "--- AUTHENTICATION GATEWAY CHECK ---" not in content:
  content = content.replace("def main():", gateway_code + "\ndef main():\n" + gatekeeper_logic)
  with open(app_path, "w", encoding="utf-8") as f:
    f.write(content)
  print("App.py successfully patched with the welcome login gateway!")
else:
  print("Patch already exists or 'def main():' signature was not found.")