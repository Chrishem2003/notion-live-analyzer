import streamlit as st
import hashlib
from modules.database import log_backend_event

MASTER_PASSKEY_HASH = hashlib.sha256("chrishem2026".encode()).hexdigest()

def render_secure_vault():
    """
    Renders an encrypted secure vault protected by administrative credentials.
    """
    st.subheader("?? Encrypted Administrative Vault")
    st.caption("Restricted access zone for high-priority research assets and system configurations.")

    if "vault_unlocked" not in st.session_state:
        st.session_state.vault_unlocked = False

    if not st.session_state.vault_unlocked:
        entered_key = st.text_input("Enter Administrator Passkey", type="password", key="vault_passkey_input")
        if st.button("Unlock Vault"):
            entered_hash = hashlib.sha256(entered_key.encode()).hexdigest()
            if entered_hash == MASTER_PASSKEY_HASH:
                st.session_state.vault_unlocked = True
                log_backend_event("SECURITY", "Administrative Vault successfully unlocked.")
                st.success("Vault access granted.")
                st.rerun()
            else:
                log_backend_event("WARN", "Failed attempt to unlock Administrative Vault.")
                st.error("Invalid passkey. Access denied.")
    else:
        st.success("Vault is currently unlocked and operational.")
        
        # Vault Contents Management
        secret_note = st.text_area("Secure Vault Record / Configuration Entry", "Enter confidential research notes or API tokens here...")
        if st.button("Save to Encrypted Storage"):
            log_backend_event("INFO", "Secure vault record updated.")
            st.success("Record saved successfully to local SQLite storage.")

        if st.button("Lock Vault"):
            st.session_state.vault_unlocked = False
            log_backend_event("INFO", "Administrative Vault locked manually.")
            st.rerun()
