"""
Page 66 — Telemetry, Webhooks & Threat Response
Exposes the live telemetry, telemetry alerting, webhook UI, threat response,
orbital relay, port scanner, and spatial audio modules for real-time
monitoring, integrations, and defensive operations.
"""
import sys
from pathlib import Path

import streamlit as st

current_file = Path(__file__).resolve()
root_dir = current_file.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

st.set_page_config(
    page_title="Telemetry, Webhooks & Threat Response",
    page_icon="📡",
    layout="wide",
)


def _hero(title, subtitle, badge):
    st.markdown(
        f"""
        <div style="padding:1.6rem;background:linear-gradient(135deg,rgba(245,158,11,.14),rgba(11,19,33,.96));border-radius:14px;border:1px solid rgba(245,158,11,.4);margin-bottom:1.2rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem;">
                <h1 style="color:#fbbf24 !important;font-size:1.9rem;margin:0;font-weight:800;">{title}</h1>
                <span style="background:rgba(245,158,11,.16);color:#fbbf24;padding:.3rem .8rem;border-radius:999px;font-size:.75rem;font-weight:700;border:1px solid #fbbf24;">{badge}</span>
            </div>
            <p style="color:#cbd5e1 !important;margin:.4rem 0 0;font-size:.95rem;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


_hero(
    "📡 Telemetry, Webhooks & Threat Response",
    "Live system telemetry, automated alerting, webhook integrations, threat response, orbital relay monitoring, port scanning, and spatial audio capabilities.",
    "Real-Time Telemetry & Defense Core",
)

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    [
        "📊 Live Telemetry",
        "🔔 Telemetry Alerting",
        "🔗 Webhooks",
        "🚨 Threat Response",
        "🛰️ Orbital Relay",
        "🔍 Port Scanner",
        "🎧 Spatial Audio",
    ]
)

with tab1:
    try:
        from modules.live_telemetry import render_live_telemetry_panel

        render_live_telemetry_panel()
    except Exception as e:
        st.error(f"Live telemetry failed to load: {e}")

with tab2:
    try:
        from modules.telemetry_alerting import render_telemetry_alerting_panel

        render_telemetry_alerting_panel()
    except Exception as e:
        st.error(f"Telemetry alerting failed to load: {e}")

with tab3:
    try:
        from modules.webhook_ui import render_webhook_panel

        render_webhook_panel()
    except Exception as e:
        st.error(f"Webhook panel failed to load: {e}")

with tab4:
    try:
        from modules.threat_response import render_threat_response_panel

        render_threat_response_panel()
    except Exception as e:
        st.error(f"Threat response failed to load: {e}")

with tab5:
    try:
        from modules.orbital_relay import render_orbital_relay_panel

        render_orbital_relay_panel()
    except Exception as e:
        st.error(f"Orbital relay failed to load: {e}")

with tab6:
    try:
        from modules.port_scanner import render_port_scanner_panel

        render_port_scanner_panel()
    except Exception as e:
        st.error(f"Port scanner failed to load: {e}")

with tab7:
    try:
        from modules.spatial_audio import render_spatial_audio_panel

        render_spatial_audio_panel()
    except Exception as e:
        st.error(f"Spatial audio failed to load: {e}")

st.markdown("---")
st.caption("CHRISHEM Multi-Problem Solver • Telemetry, Webhooks & Threat Response Module")
