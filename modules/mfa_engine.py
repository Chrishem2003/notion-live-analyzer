

import streamlit as st
import pyotp
import qrcode
import io
import base64
from modules.database import log_backend_event

def generate_mfa_secret():
    """Generates a base32 secret key for TOTP multi-factor authentication."""
    return pyotp.random_base32()

def render_mfa_setup(username: str):
    """
    Renders an interactive TOTP setup interface with QR code generation for authenticator apps.
    """
    st.subheader("? Multi-Factor Authentication (MFA) Setup")
    st.caption("Secure your enterprise session using an authenticator app (Google Authenticator, Authy, etc.).")

    if 'mfa_secret' not in st.session_state:
        st.session_state.mfa_secret = generate_mfa_secret()

    secret = st.session_state.mfa_secret
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=username, issuer_name="CHRISHEM Enterprise Engine")

    col1, col2 = st.columns([1, 2])

    with col1:
        # Generate QR code image in memory
        img = qrcode.make(provisioning_uri)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        byte_im = buf.getvalue()
        st.image(byte_im, caption="Scan with Authenticator App", width=180)

    with col2:
        st.markdown(f"**Manual Secret Key:** {secret}")
        st.info("Scan the QR code above with your authenticator app, then enter the 6-digit verification code below.")
        
        user_code = st.text_input("Enter 6-Digit TOTP Code", max_chars=6, key="mfa_verification_input")
        
        if st.button("Verify & Activate MFA"):
            if totp.verify(user_code):
                st.success("MFA successfully verified and activated for this session!")
                st.session_state.mfa_verified = True
                log_backend_event("INFO", f"User {username} successfully authenticated via MFA.")
            else:
                st.error("Invalid verification code. Please try again.")
                log_backend_event("WARNING", f"Failed MFA attempt for user {username}.")
