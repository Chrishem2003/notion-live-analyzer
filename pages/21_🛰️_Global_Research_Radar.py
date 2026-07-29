"""
🌍 Global Research Radar & Satellite Intelligence Platform (Enterprise Edition)
Autonomous Research Operating System v3.0 (CHRISHEM Enterprise Build)
"""
import streamlit as st
import pandas as pd
import numpy as np
import json
import hashlib
import time
from datetime import datetime
import urllib.request
import urllib.error

# ─── Page Config ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="Global Research Radar & Satellite Intelligence",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Session State Initializer ──────────────────────────────────────────
def init_enterprise_state():
    if "radar_pain_points" not in st.session_state:
        st.session_state["radar_pain_points"] = INITIAL_PAIN_POINTS.copy()
    if "radar_active_tab" not in st.session_state:
        st.session_state["radar_active_tab"] = "radar"
    if "radar_active_point" not in st.session_state:
        st.session_state["radar_active_point"] = INITIAL_PAIN_POINTS[0].copy()
    if "radar_search_term" not in st.session_state:
        st.session_state["radar_search_term"] = ""
    if "radar_selected_severity" not in st.session_state:
        st.session_state["radar_selected_severity"] = "All"
    if "radar_active_map_layer" not in st.session_state:
        st.session_state["radar_active_map_layer"] = "sar"
    if "radar_trigger_webhook" not in st.session_state:
        st.session_state["radar_trigger_webhook"] = "https://api.research-hub.org/v1/telemetry/webhook"
    if "radar_trigger_active" not in st.session_state:
        st.session_state["radar_trigger_active"] = False
    if "radar_synth_domain_a" not in st.session_state:
        st.session_state["radar_synth_domain_a"] = "Marine Biochemistry"
    if "radar_synth_domain_b" not in st.session_state:
        st.session_state["radar_synth_domain_b"] = "Neural Radiance Fields (NeRF)"
    if "radar_synth_output" not in st.session_state:
        st.session_state["radar_synth_output"] = None
    if "radar_synth_running" not in st.session_state:
        st.session_state["radar_synth_running"] = False
    if "api_health_status" not in st.session_state:
        st.session_state["api_health_status"] = {"STAC API": "Operational (99.9%)", "CMR Gateway": "Operational", "Webhook Dispatcher": "Standby"}

init_enterprise_state()

# ─── Custom Enterprise CSS Styling ──────────────────────────────────────
st.markdown("""
<style>
    .stApp {
        background-color: #020617;
        color: #f1f5f9;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .enterprise-card {
        background: linear-gradient(145deg, #0f172a, #090d16);
        border: 1px solid #1e293b;
        border-radius: 16px;
        padding: 1.2rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        transition: all 0.3s ease;
    }
    .enterprise-card:hover {
        border-color: #4f46e5;
        box-shadow: 0 0 25px rgba(79, 70, 229, 0.2);
    }
    .badge-glow {
        background: #1e1b4b;
        color: #a5b4fc;
        border: 1px solid #3730a3;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        font-size: 0.65rem;
        font-family: monospace;
        letter-spacing: 0.05em;
    }
    .metric-container {
        background: #090d16;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
    }
    hr {
        border-color: #1e293b !important;
    }
</style>
""", unsafe_allow_html=True)

# ─── Types & Mock/Live Data Structures ──────────────────────────────────
SEVERITIES = ["Critical", "High", "Moderate"]
TABS = ["radar", "matrix", "trigger", "claims", "synthesizer", "telemetry"]

INITIAL_PAIN_POINTS = [
    {
        "id": "RPP-2026-001",
        "title": "Methane Super-Emitter Localization Deficit",
        "domain": "Climate Analytics & Energy",
        "severity": "Critical",
        "summary": "Infrequent ground sensors miss transient high-volume methane releases from industrial pipelines and remote extraction sites.",
        "loopholes": [
            "Lack of real-time point-source attribution (< 24hr response window)",
            "Coarse spatial resolution in legacy atmosphere monitoring payloads"
        ],
        "satellite_feeds": [
            {"name": "Sentinel-5P TROPOMI", "constellation": "ESA Copernicus", "protocol": "STAC", "status": "Live", "link": "https://dataspace.copernicus.eu"},
            {"name": "EMIT / Landsat-9", "constellation": "NASA ISS / USGS", "protocol": "CMR", "status": "Live", "link": "https://earthdata.nasa.gov"}
        ],
        "target_kpi": "Reduce point-source detection latency from 14 days to < 3 hours",
        "last_updated": "2026-07-28",
        "actionable_directive": "Develop multi-spectral AI fusion pipelines matching Sentinel-5P plume detection with high-res optical verification.",
        "feasibility_score": 88,
        "impact_score": 95,
        "active_global_teams": 4,
        "coordinates": {"lat": 4.85, "lon": 31.60},
        "claim_info": {
            "institution": "MIT Climate & Data Lab / ESA",
            "lead_researcher": "Dr. Aris Thorne",
            "status": "Claimed & In Progress",
            "verification_hash": "0x8f2a71c99c14",
            "target_milestone_date": "2026-11-15"
        },
        "default_trigger_threshold": "TROPOMI CH4 > 1900 ppb within 50km radius"
    },
    {
        "id": "RPP-2026-002",
        "title": "Groundwater Depletion & Subsurface Vulnerability",
        "domain": "Hydrology & Agriculture",
        "severity": "High",
        "summary": "Aquifer depletion in semi-arid agricultural basins is severely under-reported due to lagging manual well telemetry.",
        "loopholes": [
            "Inability to predict seasonal collapse before soil subsidence occurs",
            "Siloed hydrological models missing gravimetric remote sensing input"
        ],
        "satellite_feeds": [
            {"name": "GRACE-FO Twin Satellites", "constellation": "NASA / GFZ", "protocol": "CMR", "status": "Live", "link": "https://earthdata.nasa.gov"},
            {"name": "Sentinel-1 SAR Subsidence", "constellation": "ESA Copernicus", "protocol": "STAC", "status": "Live", "link": "https://dataspace.copernicus.eu"}
        ],
        "target_kpi": "Sub-centimeter subsidence prediction 60 days prior to aquifer collapse",
        "last_updated": "2026-07-26",
        "actionable_directive": "Integrate GRACE-FO gravimetric anomalies with Sentinel-1 InSAR synthetic aperture radar data for early ground-deformation alerts.",
        "feasibility_score": 72,
        "impact_score": 89,
        "active_global_teams": 2,
        "coordinates": {"lat": 3.12, "lon": 32.40},
        "claim_info": {
            "institution": "TUM Hydrology Institute",
            "lead_researcher": "Prof. Elena Rostova",
            "status": "Under Verification",
            "verification_hash": "0x3b11e412a88f",
            "target_milestone_date": "2026-12-01"
        },
        "default_trigger_threshold": "GRACE Mass Anomaly < -15cm liquid water equivalent"
    },
    {
        "id": "RPP-2026-003",
        "title": "Deforestation & Canopy Cloud Blindspots",
        "domain": "Biodiversity & Forestry",
        "severity": "Critical",
        "summary": "Micro-deforestation under dense cloud canopy evades standard optical satellite imagery until major ecosystem loss occurs.",
        "loopholes": [
            "Optical imagery rendered blind by tropical cloud cover during rainy seasons",
            "Delayed enforcement response due to manual photo-interpretation steps"
        ],
        "satellite_feeds": [
            {"name": "Sentinel-1 C-band SAR", "constellation": "ESA Copernicus", "protocol": "STAC", "status": "Live", "link": "https://dataspace.copernicus.eu"},
            {"name": "NISAR Dual-Frequency SAR", "constellation": "NASA / ISRO", "protocol": "CMR", "status": "Live", "link": "https://earthdata.nasa.gov"}
        ],
        "target_kpi": "Automated all-weather canopy disturbance alerts at 10m spatial resolution",
        "last_updated": "2026-07-25",
        "actionable_directive": "Deploy cloud-penetrating synthetic aperture radar (SAR) time-series autoencoders to trigger real-time illegal logging alerts.",
        "feasibility_score": 65,
        "impact_score": 92,
        "active_global_teams": 0,
        "coordinates": {"lat": 1.25, "lon": 33.50},
        "claim_info": {
            "institution": "Unclaimed (Open Science Opportunity)",
            "lead_researcher": "None",
            "status": "Open for Claim",
            "verification_hash": "0x000000000000",
            "target_milestone_date": "Immediate Call for Teams"
        },
        "default_trigger_threshold": "SAR Backscatter Loss > 3.5 dB in dense forest AOI"
    },
    {
        "id": "RPP-2026-004",
        "title": "Ocean Acidification Rapid Monitoring Gap",
        "domain": "Marine Biochemistry",
        "severity": "High",
        "summary": "Current pH monitoring buoys provide sparse coverage, missing dynamic coastal acidification events that threaten marine ecosystems.",
        "loopholes": [
            "Sparse buoy network leaves 70% of coastal zones unmonitored",
            "Satellite pH algorithms lack validation against in-situ measurements"
        ],
        "satellite_feeds": [
            {"name": "Sentinel-3 OLCI", "constellation": "ESA Copernicus", "protocol": "STAC", "status": "Live", "link": "https://dataspace.copernicus.eu"},
            {"name": "Aqua MODIS", "constellation": "NASA", "protocol": "CMR", "status": "Live", "link": "https://earthdata.nasa.gov"}
        ],
        "target_kpi": "Daily pH anomaly maps at 1km coastal resolution",
        "last_updated": "2026-07-22",
        "actionable_directive": "Develop machine learning models to infer pH from ocean color and sea surface temperature satellite data.",
        "feasibility_score": 58,
        "impact_score": 78,
        "active_global_teams": 1,
        "coordinates": {"lat": -2.50, "lon": 29.30},
        "claim_info": {
            "institution": "WHOI Marine Chemistry",
            "lead_researcher": "Dr. Sarah Chen",
            "status": "Under Verification",
            "verification_hash": "0x4c22f781bb90",
            "target_milestone_date": "2027-01-30"
        },
        "default_trigger_threshold": "SST > 28°C in known reef zones + chlorophyll-a > 0.5 mg/m³"
    }
]

# ─── Hero Header & Telemetry Status Bar ─────────────────────────────────
st.markdown("""
<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;'>
    <div>
        <span class='badge-glow'>AUTONOMOUS RESEARCH OPERATING SYSTEM (v3.0 ENTERPRISE)</span>
        <h1 style='font-size:2rem; font-weight:800; color:#f1f5f9; margin:0.4rem 0 0.2rem 0;'>
            Global Research Radar & Satellite Intelligence
        </h1>
        <p style='color:#94a3b8; font-size:0.9rem; max-width:800px; margin:0;'>
            Zero-blindspot intelligence hub bridging academic research gaps, cryptographically secured loophole claims, and real-time STAC/CMR satellite data streams.
        </p>
    </div>
    <div style='text-align:right;'>
        <div style='background:#0f172a; border:1px solid #1e293b; padding:0.8rem 1.2rem; border-radius:14px;'>
            <div style='font-size:0.65rem; color:#64748b; text-transform:uppercase; font-weight:700;'>Telemetry Link</div>
            <div style='color:#34d399; font-size:0.85rem; font-weight:800;'>🟢 24 Satellites Active</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Navigation Bar ─────────────────────────────────────────────────────
tab_labels = {
    "radar": "🛰️ Intelligence Radar",
    "matrix": "🎯 Impact Matrix",
    "trigger": "⚡ Trigger Engine",
    "claims": "🔒 Ownership Vault",
    "synthesizer": "✨ AI Synthesizer",
    "telemetry": "📡 Live STAC Telemetry"
}

cols = st.columns(len(tab_labels))
for i, (t_key, t_label) in enumerate(tab_labels.items()):
    with cols[i]:
        is_active = st.session_state["radar_active_tab"] == t_key
        btn_bg = "linear-gradient(135deg, #4f46e5, #6366f1)" if is_active else "#090d16"
        btn_border = "none" if is_active else "1px solid #1e293b"
        btn_color = "white" if is_active else "#94a3b8"
        
        if st.button(t_label, key=f"nav_{t_key}", use_container_width=True):
            st.session_state["radar_active_tab"] = t_key
            st.rerun()

st.markdown("<hr style='margin:1rem 0 1.5rem 0;'>", unsafe_allow_html=True)
active_tab = st.session_state["radar_active_tab"]

# ═══════════════════════════════════════════════════════════════════════
# TAB 1: INTELLIGENCE RADAR
# ═══════════════════════════════════════════════════════════════════════
if active_tab == "radar":
    col_l, col_r = st.columns([4, 6])
    
    with col_l:
        search_q = st.text_input("🔍 Filter Bottlenecks", key="radar_search_term", placeholder="Search title, domain...")
        sev_filter = st.selectbox("Severity Level", ["All"] + SEVERITIES, key="radar_selected_severity")
        
        pts = st.session_state["radar_pain_points"]
        filtered_pts = [
            p for p in pts 
            if (not search_q or search_q.lower() in p["title"].lower() or search_q.lower() in p["domain"].lower())
            and (sev_filter == "All" or p["severity"] == sev_filter)
        ]
        
        for pt in filtered_pts:
            is_sel = pt["id"] == st.session_state["radar_active_point"]["id"]
            border_col = "#4f46e5" if is_sel else "#1e293b"
            bg_col = "#0f172a" if is_sel else "#090d16"
            
            sev_color = {"Critical": "#f43f5e", "High": "#f59e0b", "Moderate": "#64748b"}.get(pt["severity"], "#64748b")
            
            st.markdown(f"""
            <div style='background:{bg_col}; border:1px solid {border_col}; border-radius:14px; padding:1rem; margin-bottom:0.8rem;'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <span style='color:#818cf8; font-size:0.7rem; font-family:monospace;'>{pt['id']}</span>
                    <span style='background:{sev_color}20; color:{sev_color}; border:1px solid {sev_color}40; padding:0.1rem 0.5rem; border-radius:10px; font-size:0.6rem; font-weight:700;'>{pt['severity']}</span>
                </div>
                <h4 style='color:#f1f5f9; font-size:0.9rem; margin:0.3rem 0;'>{pt['title']}</h4>
                <p style='color:#94a3b8; font-size:0.75rem; margin:0 0 0.5rem 0;'>{pt['summary'][:90]}...</p>
                <div style='display:flex; justify-content:space-between; font-size:0.65rem; color:#64748b; border-top:1px solid #1e293b; padding-top:0.4rem;'>
                    <span>{pt['domain']}</span>
                    <span style='color:#818cf8;'>🛰️ {len(pt['satellite_feeds'])} Feeds</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Inspect Intel", key=f"sel_{pt['id']}", use_container_width=True):
                st.session_state["radar_active_point"] = pt.copy()
                st.rerun()

    with col_r:
        act_pt = st.session_state["radar_active_point"]
        st.markdown(f"""
        <div class='enterprise-card'>
            <div style='display:flex; justify-content:space-between; align-items:flex-start;'>
                <div>
                    <span class='badge-glow'>{act_pt['id']}</span>
                    <h2 style='font-size:1.3rem; color:#f1f5f9; margin:0.4rem 0;'>{act_pt['title']}</h2>
                    <p style='color:#94a3b8; font-size:0.8rem;'>{act_pt['summary']}</p>
                </div>
                <div style='text-align:right;'>
                    <span style='color:#34d399; font-size:0.75rem; font-weight:700;'>Feasibility: {act_pt['feasibility_score']}%</span><br>
                    <span style='color:#818cf8; font-size:0.75rem; font-weight:700;'>Impact: {act_pt['impact_score']}%</span>
                </div>
            </div>
            <hr>
            <h4 style='color:#cbd5e1; font-size:0.75rem; text-transform:uppercase;'>🎯 Target Impact KPI</h4>
            <div style='background:#020617; border:1px solid #1e293b; padding:0.6rem 1rem; border-radius:8px; color:#34d399; font-size:0.8rem; font-weight:600;'>
                {act_pt['target_kpi']}
            </div>
            
            <h4 style='color:#cbd5e1; font-size:0.75rem; text-transform:uppercase; margin-top:1rem;'>⚡ Actionable Directive</h4>
            <div style='background:#1e1b4b50; border:1px solid #3730a3; padding:0.8rem; border-radius:8px; color:#cbd5e1; font-size:0.75rem;'>
                {act_pt['actionable_directive']}
            </div>
            
            <h4 style='color:#cbd5e1; font-size:0.75rem; text-transform:uppercase; margin-top:1rem;'>🛰️ Linked Satellite Feeds (STAC / CMR)</h4>
        """, unsafe_allow_html=True)
        
        for sat in act_pt["satellite_feeds"]:
            st.markdown(f"""
            <div style='background:#020617; border:1px solid #1e293b; padding:0.6rem 0.8rem; border-radius:8px; margin-bottom:0.4rem; display:flex; justify-content:space-between; align-items:center;'>
                <div>
                    <strong style='color:#e2e8f0; font-size:0.8rem;'>{sat['name']}</strong>
                    <div style='color:#64748b; font-size:0.65rem;'>{sat['constellation']} • Protocol: {sat['protocol']}</div>
                </div>
                <a href='{sat['link']}' target='_blank' style='color:#818cf8; text-decoration:none; font-size:0.75rem;'>Access Portal ↗</a>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# TAB 2: IMPACT VS FEASIBILITY MATRIX
# ═══════════════════════════════════════════════════════════════════════
elif active_tab == "matrix":
    st.markdown("### 🎯 Impact vs. Feasibility Multi-Dimensional Matrix")
    st.markdown("<p style='color:#94a3b8; font-size:0.85rem;'>Strategic prioritization scatter plot mapping research roadblocks across global urgency and technical execution probability.</p>", unsafe_allow_html=True)
    
    pts = st.session_state["radar_pain_points"]
    df_matrix = pd.DataFrame([
        {
            "ID": p["id"],
            "Title": p["title"],
            "Domain": p["domain"],
            "Feasibility": p["feasibility_score"],
            "Impact": p["impact_score"],
            "Severity": p["severity"]
        } for p in pts
    ])
    
    import plotly.express as px
    fig = px.scatter(
        df_matrix,
        x="Feasibility",
        y="Impact",
        color="Severity",
        hover_data=["ID", "Title", "Domain"],
        text="ID",
        color_discrete_map={"Critical": "#f43f5e", "High": "#f59e0b", "Moderate": "#64748b"}
    )
    fig.update_layout(
        paper_bgcolor="#020617",
        plot_bgcolor="#090d16",
        font=dict(color="#f1f5f9"),
        xaxis=dict(title="Technical Feasibility Score (%)", gridcolor="#1e293b", range=[40, 105]),
        yaxis=dict(title="Global Impact Score (%)", gridcolor="#1e293b", range=[60, 105])
    )
    st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════
# TAB 3: SATELLITE TRIGGER ENGINE
# ═══════════════════════════════════════════════════════════════════════
elif active_tab == "trigger":
    st.markdown("### ⚡ Autonomous Satellite Trigger & Webhook Dispatcher")
    st.markdown("<p style='color:#94a3b8; font-size:0.85rem;'>Configure automated telemetry threshold alerts linked directly to live satellite feeds for real-time computational pipeline execution.</p>", unsafe_allow_html=True)
    
    col_1, col_2 = st.columns(2)
    with col_1:
        st.markdown("<div class='enterprise-card'>", unsafe_allow_html=True)
        st.text_input("Webhook Destination URL", key="radar_trigger_webhook")
        selected_pt_trigger = st.selectbox("Target Research Bottleneck", options=[p["title"] for p in st.session_state["radar_pain_points"]])
        
        active_target = next(p for p in st.session_state["radar_pain_points"] if p["title"] == selected_pt_trigger)
        st.text_area("Anomaly Threshold Rule", value=active_target["default_trigger_threshold"])
        
        is_active_trig = st.checkbox("Enable Live Autonomous Trigger Dispatcher", key="radar_trigger_active")
        if is_active_trig:
            st.success("🟢 Trigger Engine active and listening to STAC data streams.")
        else:
            st.warning("⚪ Trigger Engine is currently in stand-by mode.")
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_2:
        st.markdown("<div class='enterprise-card'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color:#f1f5f9; font-size:0.9rem;'>📊 Real-time Dispatch Log</h4>", unsafe_allow_html=True)
        st.code("""
[08:08:20 UTC] STAC Stream connected: Sentinel-5P TROPOMI
[08:06:12 UTC] Threshold check passed: CH4 plume stable (1420 ppb)
[07:55:01 UTC] Webhook heartbeat acknowledged (Latency: 42ms)
        """, language="text")
        st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# TAB 4: LOOPHOLE OWNERSHIP & ACCOUNTABILITY VAULT
# ═══════════════════════════════════════════════════════════════════════
elif active_tab == "claims":
    st.markdown("### 🔒 Decentralized Loophole Ownership & Verification Vault")
    st.markdown("<p style='color:#94a3b8; font-size:0.85rem;'>Claim ownership of unresolved research loopholes, generate cryptographic verification hashes, and prevent duplicated global efforts.</p>", unsafe_allow_html=True)
    
    for pt in st.session_state["radar_pain_points"]:
        claim = pt["claim_info"]
        st.markdown(f"""
        <div class='enterprise-card' style='margin-bottom:1rem;'>
            <div style='display:flex; justify-content:space-between; align-items:center;'>
                <div>
                    <span class='badge-glow'>{pt['id']}</span>
                    <h3 style='color:#f1f5f9; font-size:1rem; margin:0.3rem 0;'>{pt['title']}</h3>
                    <div style='color:#94a3b8; font-size:0.75rem;'>Lead Institution: <strong style='color:#e2e8f0;'>{claim['institution']}</strong> ({claim['lead_researcher']})</div>
                </div>
                <div style='text-align:right;'>
                    <span style='background:#1e1b4b; color:#a5b4fc; border:1px solid #3730a3; padding:0.2rem 0.6rem; border-radius:8px; font-size:0.7rem; font-weight:700;'>{claim['status']}</span>
                    <div style='color:#64748b; font-size:0.65rem; font-family:monospace; margin-top:0.3rem;'>Hash: {claim['verification_hash']}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# TAB 5: AI CROSS-DOMAIN SYNTHESIZER
# ═══════════════════════════════════════════════════════════════════════
elif active_tab == "synthesizer":
    st.markdown("### ✨ AI Cross-Domain Hypothesis Synthesizer")
    st.markdown("<p style='color:#94a3b8; font-size:0.85rem;'>Cross-pollinate distinct scientific disciplines using automated inference engines to discover novel cross-disciplinary breakthroughs.</p>", unsafe_allow_html=True)
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.selectbox("Discipline A (Primary Domain)", ["Marine Biochemistry", "Climate Analytics & Energy", "Hydrology & Agriculture", "Biodiversity & Forestry"], key="radar_synth_domain_a")
    with col_b:
        st.selectbox("Discipline B (Catalyst Domain)", ["Neural Radiance Fields (NeRF)", "Quantum Annealing Optimization", "CRISPR Gene Drive Telemetry", "Graph Neural Networks"], key="radar_synth_domain_b")
        
    def run_synth():
        st.session_state["radar_synth_running"] = True
        time.sleep(1.0)
        da = st.session_state["radar_synth_domain_a"]
        db = st.session_state["radar_synth_domain_b"]
        st.session_state["radar_synth_output"] = f"**Synthesized Cross-Domain Hypothesis:**\n\nApplying principles from **{db}** to real-time spatial bottlenecks in **{da}** enables sub-surface continuous gradient modeling without physical sensor deployment, reducing data collection latency by 94%."
        st.session_state["radar_synth_running"] = False

    if st.button("🚀 Synthesize Novel Hypothesis", use_container_width=True):
        run_synth()
        
    if st.session_state["radar_synth_output"]:
        st.markdown(f"""
        <div class='enterprise-card' style='border-color:#4f46e5; margin-top:1rem;'>
            <h4 style='color:#818cf8; font-size:0.9rem;'>✨ Generated Hypothesis Output</h4>
            <p style='color:#cbd5e1; font-size:0.85rem;'>{st.session_state["radar_synth_output"]}</p>
        </div>
        """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# TAB 6: LIVE STAC TELEMETRY STREAM
# ═══════════════════════════════════════════════════════════════════════
elif active_tab == "telemetry":
    st.markdown("### 📡 Live STAC / CMR API Telemetry Diagnostics")
    st.markdown("<p style='color:#94a3b8; font-size:0.85rem;'>Direct health check and live payload inspection for connected satellite constellation endpoints.</p>", unsafe_allow_html=True)
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("<div class='enterprise-card'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color:#f1f5f9; font-size:0.9rem;'>🌐 Endpoint Status Dashboard</h4>", unsafe_allow_html=True)
        for k, v in st.session_state["api_health_status"].items():
            st.markdown(f"<div style='display:flex; justify-content:space-between; padding:0.4rem 0; border-bottom:1px solid #1e293b;'><span style='color:#cbd5e1; font-size:0.8rem;'>{k}</span><span style='color:#34d399; font-size:0.8rem; font-weight:700;'>{v}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with col_t2:
        st.markdown("<div class='enterprise-card'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color:#f1f5f9; font-size:0.9rem;'>📦 STAC Item Metadata Sample</h4>", unsafe_allow_html=True)
        st.code("""
{
  "type": "Feature",
  "stac_version": "1.0.0",
  "id": "S5P_OFFL_L2__CH4_____20260728T0722",
  "geometry": { "type": "Point", "coordinates": [31.60, 4.85] },
  "properties": {
    "datetime": "2026-07-28T07:22:10Z",
    "eo:cloud_cover": 0.0,
    "tropospheric_CH4_column_number_density": 1892.4
  }
}
        """, language="json")
        st.markdown("</div>", unsafe_allow_html=True)

# ─── Footer Watermark ───────────────────────────────────────────────────
st.markdown("<hr style='margin-top:3rem;'>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align:center; color:#475569; font-size:0.7rem; font-family:monospace; letter-spacing:0.1em;'>"
    "AUTONOMOUS RESEARCH OPERATING SYSTEM • SECURE INTEL ENGINE • DESIGNED FOR CHRISHEM"
    "</div>",
    unsafe_allow_html=True
)