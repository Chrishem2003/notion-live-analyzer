"""Fail-closed placeholder for the retired demo authentication gateway.

This module previously marked sessions authenticated after a button click or
non-empty username/password fields. Those actions are not identity verification.
Use the application's real, server-validated authentication flow instead.
"""
import streamlit as st


def render_auth_gateway():
    """Prevent the old demo gateway from granting access."""
    st.error("This demo authentication gateway is disabled.")
    st.warning(
        "No OAuth, passkey, enterprise directory, or wallet provider is "
        "configured by this module. Use the application's verified sign-in "
        "flow; this screen cannot authenticate users."
    )
    st.stop()
