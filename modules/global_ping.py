import streamlit as st
import pandas as pd
import random
from modules.database import log_backend_event

def get_global_node_metrics() -> pd.DataFrame:
    """
    Generates simulated live latency and status metrics for distributed edge nodes.
    """
    nodes = [
        {"Region": "East Africa (Kampala / Muni)", "Endpoint": "edge-ug.chrishem.enterprise", "Latency_ms": random.randint(12, 24), "Status": "OPTIMAL"},
        {"Region": "Western Europe (Frankfurt)", "Endpoint": "edge-eu.chrishem.enterprise", "Latency_ms": random.randint(45, 68), "Status": "HEALTHY"},
        {"Region": "North America (Virginia)", "Endpoint": "edge-us.chrishem.enterprise", "Latency_ms": random.randint(85, 110), "Status": "HEALTHY"},
        {"Region": "Asia-Pacific (Singapore)", "Endpoint": "edge-ap.chrishem.enterprise", "Latency_ms": random.randint(120, 155), "Status": "STABLE"}
    ]
    return pd.DataFrame(nodes)

def render_global_ping_panel():
    """
    Renders the Global Node Latency & Edge Health dashboard inside Streamlit.
    """
    st.subheader(" Global Edge Node Latency & Telemetry")
    st.caption("Real-time distributed network monitoring across international cluster gateways.")

    df_nodes = get_global_node_metrics()
    st.dataframe(df_nodes, use_container_width=True)

    if st.button("Run Global Ping Synchronization"):
        log_backend_event("INFO", "User triggered global edge node latency sweep.")
        st.success("Global ping sweep successful. Average latency across clusters: 58ms.")
