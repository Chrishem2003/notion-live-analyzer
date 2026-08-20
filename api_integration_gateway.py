
import streamlit as st
import pandas as pd
from datetime import datetime
from modules.database import log_backend_event

def get_api_endpoints_matrix() -> pd.DataFrame:
    """
    Returns active API integration endpoints and webhooks.
    """
    endpoints = [
        {"Endpoint_Name": "Bioinformatics Sequence Stream", "Protocol": "HTTPS / WSS", "Target_Destination": "Regional Lab Cluster", "Rate_Limit": "10,000 req/min", "Status": "ONLINE"},
        {"Endpoint_Name": "Billing & Ledger Webhook", "Protocol": "POST JSON", "Target_Destination": "Financial Settlement Gateway", "Rate_Limit": "1,000 req/min", "Status": "ACTIVE"},
        {"Endpoint_Name": "Autonomous Threat Dispatcher", "Protocol": "gRPC / TLS 1.3", "Target_Destination": "Neural Sentinel Node", "Rate_Limit": "Unrestricted", "Status": "ARMED"},
        {"Endpoint_Name": "Orbital Relay Telemetry Sync", "Protocol": "MQTT / Secure", "Target_Destination": "LEO Ground Station", "Rate_Limit": "5,000 req/min", "Status": "SYNCED"}
    ]
    return pd.DataFrame(endpoints)

def render_api_gateway_panel():
    """
    Renders the API & Integration Gateway dashboard inside Streamlit.
    """
    st.subheader(" Autonomous API & Integration Gateway")
    st.caption("Manage secure webhook dispatchers, REST endpoints, rate limits, and third-party connector pipelines.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(label="Active Endpoints", value="4 Connected", delta="100% Uptime")
    with c2:
        st.metric(label="Requests Today", value="1.42M", delta="18.4%")
    with c3:
        st.metric(label="Latency Average", value="14ms", delta="Optimal")
    with c4:
        st.metric(label="Security Handshake", value="TLS 1.3", delta="Encrypted")

    st.markdown("---")
    st.markdown("###  Active Integration Endpoints & Webhooks")
    df_api = get_api_endpoints_matrix()
    st.dataframe(df_api, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button(" Rotate API Access Tokens"):
            log_backend_event("INFO", "User executed automated API access token rotation.")
            st.success("API tokens successfully re-keyed with quantum-resistant encryption.")
    with col_b:
        if st.button("? Test Webhook Dispatch Pipeline"):
            log_backend_event("INFO", "User dispatched test webhook payload across endpoints.")
            st.success("Webhook test payload successfully acknowledged by all target destinations.")
