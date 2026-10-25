"""Fail-closed placeholder for the retired shared-TOTP vault demo.

The former implementation embedded one shared TOTP seed in source code and
showed the same enrollment QR to every visitor. That is not per-user MFA and
must never protect private data. The vault stays locked until a per-user
enrollment and verification flow is implemented.
"""
import streamlit as st


def render_secure_vault_auth():
    """Keep the vault locked until proper per-user MFA exists."""
    st.error("Secure vault access is disabled.")
    st.warning(
        "The former shared-TOTP demo was retired because a shared seed cannot "
        "identify individual users. No vault access is granted by this screen. "
        "A per-user enrollment, recovery, and verification flow is required."
    )
    st.stop()
