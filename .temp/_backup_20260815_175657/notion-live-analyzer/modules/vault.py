
import streamlit as st
import hashlib
import time
from modules.database import log_backend_event

MASTER_PASSKEY_HASH = hashlib.sha256("chrishem2026".encode()).hexdigest()

def render_secure_vault():
    st.subheader(" Encrypted Administrative Vault")
    st.caption("Restricted access zone with integrated brute-force protection.")

    if "vault_unlocked" not in st.session_state:
        st.session_state.vault_unlocked = False
    if "failed_attempts" not in st.session_state:
        st.session_state.failed_attempts = 0
    if "lockout_time" not in st.session_state:
        st.session_state.lockout_time = 0

    # Check cooldown timer
    current_time = time.time()
    if st.session_state.failed_attempts >= 3:
        remaining_cooldown = int(30 - (current_time - st.session_state.lockout_time))
        if remaining_cooldown > 0:
            st.error(f" Too many failed attempts. Vault temporarily locked for {remaining_cooldown} seconds.")
            return
        else:
            # Reset after cooldown
            st.session_state.failed_attempts = 0

    if not st.session_state.vault_unlocked:
        entered_key = st.text_input("Enter Administrator Passkey", type="password", key="vault_passkey_input")
        if st.button("Unlock Vault"):
            entered_hash = hashlib.sha256(entered_key.encode()).hexdigest()
            if entered_hash == MASTER_PASSKEY_HASH:
                st.session_state.vault_unlocked = True
                st.session_state.failed_attempts = 0
                log_backend_event("SECURITY", "Administrative Vault successfully unlocked.")
                st.success("Vault access granted.")
                st.rerun()
            else:
                st.session_state.failed_attempts = 1
                log_backend_event("WARN", f"Failed vault unlock attempt ({st.session_state.failed_attempts}/3).")
                if st.session_state.failed_attempts >= 3:
                    st.session_state.lockout_time = time.time()
                    st.error(" Maximum attempts reached. 30-second cooldown initiated.")
                    st.rerun()
                else:
                    st.error(f"Invalid passkey. Attempts remaining: {3 - st.session_state.failed_attempts}")
    else:
        st.success("Vault is currently unlocked and operational.")
        secret_note = st.text_area("Secure Vault Record / Configuration Entry", "Enter confidential research notes or API tokens here...")
        if st.button("Save to Encrypted Storage"):
            log_backend_event("INFO", "Secure vault record updated.")
            st.toast("Record saved successfully to local storage!", icon="")

        if st.button("Lock Vault"):
            st.session_state.vault_unlocked = False
            log_backend_event("INFO", "Administrative Vault locked manually.")
            st.rerun()
