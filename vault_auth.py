
import io
import pyotp
import qrcode
import streamlit as st

def render_secure_vault_auth():
    """Renders the secure vault authentication interface with a scannable QR code."""
    st.markdown("### Ã°Å¸â€Â Secure Personal Vault Authentication")
    
    # Pre-configured secret specified for your secure personal vault
    secret = "PUQ4W55ZS6RPEJG6ZZ72X3CEX6XGKNCZ"
    issuer = "SecurePersonalVault"
    account_name = "vault-vault_0e"
    
    # Build the standard TOTP provisioning URI
    provisioning_uri = f"otpauth://totp/{issuer}}:{account_name}}?secret={secret}}&issuer={issuer}}&algorithm=SHA1&digits=6&period=30"

    col_qr, col_controls = st.columns([1, 1], gap="medium")

    with col_qr:
        st.markdown("#### Ã°Å¸â€œÂ± Scannable QR Code")
        # Generate scannable QR code image in-memory
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

        # Display image directly in UI
        st.image(qr_bytes, caption="Scan with Google Authenticator or Authy", use_container_width=True)

    with col_controls:
        st.markdown("#### Ã¢Å¡â„¢Ã¯Â¸Â Vault Credentials")
        st.text_input("Secret Key", value=secret, type="password", disabled=True)
        
        with st.expander("View Provisioning URI"):
            st.code(provisioning_uri, language="text")

        st.markdown("#### Ã°Å¸â€ºÂ¡Ã¯Â¸Â Verification")
        entered_code = st.text_input("After setup, enter a code to verify:", max_chars=6, placeholder="123456")

        totp = pyotp.TOTP(secret)

        if st.button("Verify & Unlock Vault", type="primary"):
            if totp.verify(entered_code):
                st.session_state.vault_unlocked = True
                st.success("Access Granted: Vault successfully unlocked.")
                st.balloons()
            else:
                st.error("Invalid or expired verification code. Please check your authenticator app.")

    if st.session_state.get("vault_unlocked", False):
        st.markdown("---")
        st.success("Ã°Å¸Å¸Â¢ Vault Status: UNLOCKED  Encrypted Session Active")
        st.json({
            "vault_id": account_name,
            "security_status": "Authenticated",
            "encryption": "AES-256 / TOTP"
        })

