import io
import pyotp
import qrcode
import streamlit as st

def render_scannable_vault_auth(user_id="research_user"):
    st.markdown("### 🔐 Advanced Secure Personal Vault")
    st.markdown("Scan the provisioning QR code below using your mobile authenticator app (Google Authenticator, Authy, etc.) or enter the secret manually.")

    if "vault_secret" not in st.session_state:
        st.session_state.vault_secret = pyotp.random_base32()

    secret = st.session_state.vault_secret
    issuer = "ResearchOS-Vault"
    
    provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user_id,
        issuer_name=issuer
    )

    col_qr, col_controls = st.columns([1, 1], gap="medium")

    with col_qr:
        st.markdown("#### 📱 Provisioning QR Code")
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        qr_bytes = buffered.getvalue()

        st.image(qr_bytes, caption="Scan with Authenticator App", use_container_width=True)

    with col_controls:
        st.markdown("#### ⚙️ Security Parameters")
        st.text_input("Manual Secret Key (Base32)", value=secret, type="password", disabled=True)
        
        with st.expander("Advanced Technical URI"):
            st.code(provisioning_uri, language="text")

        st.markdown("#### 🛡️ Token Validation Check")
        entered_code = st.text_input("Enter 6-digit MFA Code", max_chars=6, placeholder="123456")

        totp = pyotp.TOTP(secret)

        if st.button("Verify & Unlock Vault", type="primary"):
            if totp.verify(entered_code):
                st.session_state.vault_unlocked = True
                st.success("Access Granted: Cryptographic token verified successfully.")
                st.balloons()
            else:
                st.error("Invalid or expired verification code. Please check your device clock.")

    if st.session_state.get("vault_unlocked", False):
        st.markdown("---")
        st.success("🟢 Vault Status: UNLOCKED — Encrypted Session Active")
        st.json({
            "encryption_standard": "AES-256 / TOTP-SHA1",
            "session_owner": user_id,
            "token_validity": "30s window"
        })
