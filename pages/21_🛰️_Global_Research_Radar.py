"""
🌍 Global Research Radar & Satellite Intelligence Platform
Based on the Advanced Research Operating System concept, this page provides:
  1. Global Intelligence Radar — Search/filter research pain points with satellite feeds
  2. Impact vs Feasibility Matrix — 2D scatter quadrant visualization
  3. Satellite Trigger Engine — Webhook configuration for anomaly thresholds
  4. Loophole Accountability & Ownership — Claim/verification tracking
  5. AI Cross-Domain Synthesizer — Cross-pollinate disciplines for novel hypotheses
"""

import streamlit as st
st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>", unsafe_allow_html=True)
import pandas as pd
import numpy as np
import json
import hashlib
import time
from datetime import datetime

st.set_page_config(
    page_title="Global Research Radar",
    page_icon="🛰️",
    layout="wide",
)

from modules.config import init_session_state
from modules.ui_components import hero_card, load_css, watermark, section_header

# ─── Init ─────────────────────────────────────────────────────────────
init_session_state()
load_css(is_dark=True)
hero_card(
    "🛰️ Global Research Pain Points & Satellite Intelligence Platform",
    "A unified, zero-blindspot hub for researchers worldwide to detect critical scientific gaps, "
    "claim unsolved loopholes, and link directly to real-time satellite telemetry.",
    badge_text="Autonomous Research Operating System v2.6"
)
watermark("CHRISHEM")

# ═══════════════════════════════════════════════════════════════════════
# TYPES & DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════

SEVERITIES = ["Critical", "High", "Moderate"]
TABS = ["radar", "matrix", "trigger", "claims", "synthesizer"]

# ─── Initial Research Pain Points ──────────────────────────────────
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
        "last_updated": "2026-07-24",
        "actionable_directive": "Develop multi-spectral AI fusion pipelines matching Sentinel-5P plume detection with high-res optical verification.",
        "feasibility_score": 88,
        "impact_score": 95,
        "active_global_teams": 4,
        "claim_info": {
            "institution": "MIT Climate & Data Lab / ESA",
            "lead_researcher": "Dr. Aris Thorne",
            "status": "Claimed & In Progress",
            "verification_hash": "0x8f2a...9c14",
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
        "last_updated": "2026-07-22",
        "actionable_directive": "Integrate GRACE-FO gravimetric anomalies with Sentinel-1 InSAR synthetic aperture radar data for early ground-deformation alerts.",
        "feasibility_score": 72,
        "impact_score": 89,
        "active_global_teams": 2,
        "claim_info": {
            "institution": "TUM Hydrology Institute",
            "lead_researcher": "Prof. Elena Rostova",
            "status": "Under Verification",
            "verification_hash": "0x3b11...e412",
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
        "last_updated": "2026-07-20",
        "actionable_directive": "Deploy cloud-penetrating synthetic aperture radar (SAR) time-series autoencoders to trigger real-time illegal logging alerts.",
        "feasibility_score": 65,
        "impact_score": 92,
        "active_global_teams": 0,
        "claim_info": {
            "institution": "Unclaimed (Open Science Opportunity)",
            "lead_researcher": "None",
            "status": "Open for Claim",
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
        "last_updated": "2026-07-19",
        "actionable_directive": "Develop machine learning models to infer pH from ocean color and sea surface temperature satellite data.",
        "feasibility_score": 58,
        "impact_score": 78,
        "active_global_teams": 1,
        "claim_info": {
            "institution": "WHOI Marine Chemistry",
            "lead_researcher": "Dr. Sarah Chen",
            "status": "Under Verification",
            "verification_hash": "0x4c22...f781",
            "target_milestone_date": "2027-01-30"
        },
        "default_trigger_threshold": "SST > 28°C in known reef zones + chlorophyll-a > 0.5 mg/m³"
    },
    {
        "id": "RPP-2026-005",
        "title": "Urban Heat Island & Energy Poverty Nexus",
        "domain": "Urban Climate & Energy",
        "severity": "Moderate",
        "summary": "Urban heat island effects disproportionately affect low-income neighborhoods, but high-resolution thermal data remains inaccessible for local planning.",
        "loopholes": [
            "Thermal infrared satellites lack resolution for neighborhood-scale analysis",
            "Energy poverty data not integrated with land surface temperature products"
        ],
        "satellite_feeds": [
            {"name": "ECOSTRESS (ISS)", "constellation": "NASA", "protocol": "CMR", "status": "Live", "link": "https://earthdata.nasa.gov"},
            {"name": "Landsat-8/9 TIRS", "constellation": "USGS/NASA", "protocol": "STAC", "status": "Live", "link": "https://dataspace.copernicus.eu"}
        ],
        "target_kpi": "100m resolution thermal stress index for urban planning",
        "last_updated": "2026-07-15",
        "actionable_directive": "Fuse ECOSTRESS 70m thermal data with socioeconomic indicators to create urban heat vulnerability maps.",
        "feasibility_score": 82,
        "impact_score": 71,
        "active_global_teams": 3,
        "claim_info": {
            "institution": "C40 Cities / Urban Climate Lab",
            "lead_researcher": "Dr. Marcus Wei",
            "status": "Claimed & In Progress",
            "verification_hash": "0x9e55...ab32",
            "target_milestone_date": "2026-09-15"
        },
        "default_trigger_threshold": "LST > 40°C in residential zones with >30% impervious surface"
    },
]

# ═══════════════════════════════════════════════════════════════════════
# SESSION STATE INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════

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


# ─── Helper: Handle Claim ──────────────────────────────────────────
def handle_claim_loophole(point_id: str):
    pts = st.session_state["radar_pain_points"]
    for i, pt in enumerate(pts):
        if pt["id"] == point_id:
            pts[i]["claim_info"] = {
                "institution": "My Autonomous Research Team",
                "lead_researcher": "Principal Investigator",
                "status": "Claimed & In Progress",
                "verification_hash": "0x7a99..." + hashlib.md5(str(time.time()).encode()).hexdigest()[:4],
                "target_milestone_date": "2026-10-30"
            }
            pts[i]["active_global_teams"] = pt["active_global_teams"] + 1
            break
    st.session_state["radar_pain_points"] = pts
    # Update active point if it matches
    if st.session_state["radar_active_point"]["id"] == point_id:
        st.session_state["radar_active_point"] = next(
            (p for p in pts if p["id"] == point_id), pts[0]
        )


# ─── Helper: Run Synthesizer ───────────────────────────────────────
def handle_run_synthesizer():
    st.session_state["radar_synth_running"] = True
    st.session_state["radar_synth_output"] = None

    domain_a = st.session_state.get("radar_synth_domain_a", "Marine Biochemistry")
    domain_b = st.session_state.get("radar_synth_domain_b", "Neural Radiance Fields (NeRF)")

    # Simulate AI synthesis (in production, this would call an LLM)
    time.sleep(1.2)
    output = (
        f"**Cross-Domain Breakthrough Idea:**\n\n"
        f"Apply continuous 3D NeRF neural implicit representations from "
        f"[**{domain_b}**] to satellite thermal plume dynamics in "
        f"[**{domain_a}**]. This will reconstruct under-surface temperature "
        f"gradient layers without needing high-density mooring buoy arrays, "
        f"enabling global-scale ocean thermal monitoring at a fraction of "
        f"the cost of in-situ sensor networks."
    )
    st.session_state["radar_synth_output"] = output
    st.session_state["radar_synth_running"] = False


# ═══════════════════════════════════════════════════════════════════════
# FILTER PAIN POINTS
# ═══════════════════════════════════════════════════════════════════════

def get_filtered_points():
    pts = st.session_state["radar_pain_points"]
    search_term = st.session_state.get("radar_search_term", "").lower()
    severity = st.session_state.get("radar_selected_severity", "All")

    filtered = []
    for pt in pts:
        if search_term and search_term not in pt["title"].lower() and search_term not in pt["domain"].lower():
            continue
        if severity != "All" and pt["severity"] != severity:
            continue
        filtered.append(pt)
    return filtered


# ═══════════════════════════════════════════════════════════════════════
# GLOBAL HEADER WIDGET
# ═══════════════════════════════════════════════════════════════════════

col1, col2 = st.columns([3, 1])
with col1:
    st.markdown(
        "<div style='display:flex;align-items:center;gap:0.5rem;'>"
        "<span style='color:#818cf8;font-size:0.75rem;font-weight:600;letter-spacing:0.1em;'>"
        "AUTONOMOUS RESEARCH OPERATING SYSTEM (v2.6)</span>"
        "<span style='background:#1e1b4b;color:#a5b4fc;border:1px solid #3730a3;"
        "padding:0.1rem 0.5rem;border-radius:4px;font-size:0.65rem;font-family:monospace;'>"
        "STAC / CMR Live API</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h1 style='font-size:1.8rem;font-weight:800;margin:0.3rem 0;color:#f1f5f9;'>"
        "Global Research Pain Points & Satellite Intelligence Platform</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#94a3b8;font-size:0.85rem;max-width:700px;'>"
        "A unified, zero-blindspot hub for researchers worldwide to detect critical scientific gaps, "
        "claim unsolved loopholes, and link directly to real-time satellite telemetry.</p>",
        unsafe_allow_html=True,
    )

with col2:
    pts = st.session_state["radar_pain_points"]
    st.markdown(
        f"<div style='background:#0f172a;border:1px solid #1e293b;padding:1rem;border-radius:16px;'>"
        f"<div style='display:flex;align-items:center;gap:1rem;'>"
        f"<div style='border-right:1px solid #1e293b;padding-right:1rem;'>"
        f"<div style='color:#64748b;font-size:0.65rem;text-transform:uppercase;font-weight:600;'>Satellite Stream</div>"
        f"<div style='color:#34d399;font-size:0.8rem;font-weight:700;'>📡 18 Satellites Linked</div>"
        f"</div>"
        f"<div>"
        f"<div style='color:#64748b;font-size:0.65rem;text-transform:uppercase;font-weight:600;'>Active Loopholes</div>"
        f"<div style='color:#818cf8;font-size:0.8rem;font-weight:700;'>{len(pts)} Tracked Pain Points</div>"
        f"</div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )

# ═══════════════════════════════════════════════════════════════════════
# TAB NAVIGATION
# ═══════════════════════════════════════════════════════════════════════

tab_labels = {
    "radar": "🛰️ Global Intelligence Radar",
    "matrix": "🎯 Impact vs Feasibility Matrix",
    "trigger": "⚡ Satellite Trigger Engine",
    "claims": "🔒 Loophole Ownership",
    "synthesizer": "✨ AI Cross-Domain Synthesizer",
}

cols = st.columns(5)
for i, (tab_key, tab_label) in enumerate(tab_labels.items()):
    with cols[i]:
        active = st.session_state["radar_active_tab"] == tab_key
        btn_style = (
            "background:linear-gradient(135deg,#4f46e5,#6366f1);color:white;border:none;"
            if active
            else "background:#0f172a;color:#94a3b8;border:1px solid #1e293b;"
        )
        if st.button(
            tab_label,
            key=f"nav_{tab_key}",
            use_container_width=True,
            help=f"Switch to {tab_label}",
        ):
            st.session_state["radar_active_tab"] = tab_key
            st.rerun()

st.markdown("<hr style='border-color:#1e293b;margin:0 0 1.5rem 0;'>", unsafe_allow_html=True)

active_tab = st.session_state["radar_active_tab"]

# ═══════════════════════════════════════════════════════════════════════
# TAB 1: GLOBAL INTELLIGENCE RADAR
# ═══════════════════════════════════════════════════════════════════════

if active_tab == "radar":

    col_left, col_right = st.columns([5, 7])

    with col_left:
        # Search & Filter
        search_col, filter_col = st.columns([3, 1])
        with search_col:
            st.text_input(
                "🔍 Search bottlenecks, domains, or sensors...",
                key="radar_search_term",
                placeholder="e.g., methane, deforestation, hydrology",
                label_visibility="collapsed",
            )
        with filter_col:
            st.selectbox(
                "Severity",
                options=["All"] + SEVERITIES,
                key="radar_selected_severity",
                label_visibility="collapsed",
            )

        # Pain Point Cards
        filtered = get_filtered_points()
        active_id = st.session_state["radar_active_point"]["id"]

        with st.container():
            for pt in filtered:
                is_selected = pt["id"] == active_id
                border_color = "#4f46e5" if is_selected else "#1e293b"
                bg_color = "#0f172a" if is_selected else "#0f172a80"

                severity_colors = {
                    "Critical": "#f43f5e",
                    "High": "#f59e0b",
                    "Moderate": "#64748b",
                }
                sev_color = severity_colors.get(pt["severity"], "#64748b")

                card_html = f"""
                <div onclick="document.querySelector('[data-point=\\'{pt['id']}\\']')?.click()"
                     style="cursor:pointer;padding:1rem;margin:0.5rem 0;border-radius:16px;
                            border:1px solid {border_color};background:{bg_color};
                            transition:all 0.2s;
                            {'box-shadow:0 0 20px rgba(79,70,229,0.15);' if is_selected else ''}">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.4rem;">
                        <span style="color:#818cf8;font-size:0.7rem;font-family:monospace;font-weight:600;">{pt['id']}</span>
                        <span style="font-size:0.6rem;padding:0.15rem 0.5rem;border-radius:999px;
                                   background:{sev_color}20;color:{sev_color};border:1px solid {sev_color}40;
                                   font-weight:700;text-transform:uppercase;letter-spacing:0.05em;">
                            {pt['severity']}
                        </span>
                    </div>
                    <h3 style="font-size:0.85rem;font-weight:600;color:#f1f5f9;margin:0.2rem 0;
                               overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                        {pt['title']}
                    </h3>
                    <p style="font-size:0.75rem;color:#94a3b8;margin:0.2rem 0 0.5rem 0;
                              overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                        {pt['summary']}
                    </p>
                    <div style="display:flex;justify-content:space-between;font-size:0.65rem;color:#64748b;
                                border-top:1px solid #1e293b;padding-top:0.4rem;">
                        <span>{pt['domain']}</span>
                        <span style="color:#818cf8;font-family:monospace;">🛰️ {len(pt['satellite_feeds'])} Sat Feeds</span>
                    </div>
                </div>
                """

                st.markdown(card_html, unsafe_allow_html=True)

                # Hidden button for selection
                btn_key = f"select_{pt['id']}"
                btn_label = f"data-point={pt['id']}"
                if st.button(
                    "Select",
                    key=btn_key,
                    help=f"Select {pt['title']}",
                    use_container_width=True,
                ):
                    st.session_state["radar_active_point"] = pt.copy()
                    st.rerun()

    with col_right:
        active_point = st.session_state["radar_active_point"]

        # Active Pain Point Header
        sev_color = severity_colors.get(active_point["severity"], "#64748b")
        st.markdown(
            f"""
            <div style="background:#0f172a;border:1px solid #1e293b;border-radius:24px;padding:1.5rem;">
                <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:1rem;">
                    <div>
                        <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem;">
                            <span style="font-size:0.65rem;font-family:monospace;padding:0.15rem 0.5rem;
                                       border-radius:4px;background:#1e1b4b;color:#a5b4fc;border:1px solid #3730a3;">
                                {active_point['id']}
                            </span>
                            <span style="font-size:0.7rem;color:#94a3b8;">
                                Domain: <strong style="color:#e2e8f0;">{active_point['domain']}</strong>
                            </span>
                        </div>
                        <h2 style="font-size:1.4rem;font-weight:800;color:#f1f5f9;margin:0.3rem 0;">
                            {active_point['title']}
                        </h2>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:0.6rem;color:#64748b;text-transform:uppercase;font-weight:600;">
                            Target Impact Metric
                        </div>
                        <div style="font-size:0.75rem;font-weight:700;color:#34d399;max-width:200px;margin-top:0.2rem;">
                            {active_point['target_kpi']}
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Interactive Earth Observation Visualizer Preview
        active_layer = st.session_state.get("radar_active_map_layer", "sar")
        layer_descriptions = {
            "sar": "Synthetic Aperture Radar: Cloud-penetrating ground surface deformation detection active.",
            "optical": "High-Resolution Optical Multispectral: Surface vegetation index (NDVI) rendering.",
            "atmosphere": "TROPOMI Atmospheric Spectroscopy: Gas density anomaly mapping active.",
        }

        st.markdown(
            f"""
            <div style="background:#020617;border:1px solid #1e293b;border-radius:16px;padding:1rem;margin:1rem 0;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
                    <span style="font-size:0.75rem;font-weight:600;color:#cbd5e1;">
                        🧭 Live Layer Overlay Visualizer
                    </span>
                    <span style="font-size:0.6rem;color:#818cf8;background:#1e1b4b;padding:0.15rem 0.4rem;border-radius:4px;font-family:monospace;">
                        {active_layer.upper()}
                    </span>
                </div>
                <div style="height:120px;border-radius:12px;background:linear-gradient(135deg,#0f172a,#1e1b4b,#020617);
                           display:flex;align-items:center;justify-content:center;border:1px solid #1e293b;position:relative;">
                    <div style="text-align:center;padding:0.5rem;">
                        <div style="font-size:0.7rem;font-family:monospace;color:#818cf8;margin-bottom:0.3rem;">
                            Active Sensor Stream Mode: <strong style="color:white;text-transform:uppercase;">{active_layer}</strong>
                        </div>
                        <div style="font-size:0.65rem;color:#64748b;max-width:400px;">
                            {layer_descriptions.get(active_layer, "")}
                        </div>
                    </div>
                    <div style="position:absolute;bottom:0.4rem;left:0.8rem;font-size:0.6rem;font-family:monospace;color:#475569;">
                        Grid Ref: 4°10'N 31°20'E | Resolution: 10m Ground Pixel
                    </div>
                </div>
                <div style="display:flex;gap:0.3rem;margin-top:0.5rem;">
                    {''.join(
                        f'<button style="flex:1;padding:0.3rem 0.2rem;border-radius:8px;font-size:0.6rem;font-family:monospace;'
                        f'{"background:#4f46e5;color:white;border:none;" if layer == active_layer else "background:#0f172a;color:#64748b;border:1px solid #1e293b;"}'
                        f'cursor:pointer;">{layer.upper()}</button>'
                        for layer in ["sar", "optical", "atmosphere"]
                    )}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Layer switching via selectbox
        st.selectbox(
            "Active Layer",
            options=["sar", "optical", "atmosphere"],
            index=["sar", "optical", "atmosphere"].index(active_layer),
            key="radar_active_map_layer",
            label_visibility="collapsed",
            format_func=lambda x: {"sar": "🛰️ SAR Radar", "optical": "🌿 Optical 10m", "atmosphere": "🌪️ Gas Composition"}[x],
        )

        # Loopholes Section
        st.markdown(
            "<h4 style='font-size:0.7rem;font-weight:600;color:#94a3b8;text-transform:uppercase;"
            "letter-spacing:0.05em;margin:1rem 0 0.5rem 0;'>⚠️ Current Gaps & Research Loopholes</h4>",
            unsafe_allow_html=True,
        )
        for loophole in active_point["loopholes"]:
            st.markdown(
                f"<div style='padding:0.5rem 0.8rem;margin:0.3rem 0;border-radius:10px;"
                f"background:#020617;border:1px solid #1e293b;font-size:0.75rem;color:#cbd5e1;"
                f"display:flex;align-items:start;gap:0.5rem;'>"
                f"<span style='color:#f59e0b;margin-top:0.2rem;'>●</span>"
                f"<span>{loophole}</span></div>",
                unsafe_allow_html=True,
            )

        # Satellite Feeds
        st.markdown(
            "<h4 style='font-size:0.7rem;font-weight:600;color:#94a3b8;text-transform:uppercase;"
            "letter-spacing:0.05em;margin:1rem 0 0.5rem 0;'>🛰️ Direct Satellite API Endpoints (STAC / CMR)</h4>",
            unsafe_allow_html=True,
        )

        feed_cols = st.columns(2)
        for idx, sat in enumerate(active_point["satellite_feeds"]):
            with feed_cols[idx % 2]:
                st.markdown(
                    f"<a href='{sat['link']}' target='_blank' style='text-decoration:none;'>"
                    f"<div style='padding:0.7rem;border-radius:12px;background:#020617;border:1px solid #1e293b;"
                    f"margin:0.3rem 0;transition:all 0.2s;cursor:pointer;'>"
                    f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:0.3rem;'>"
                    f"<span style='font-size:0.75rem;font-weight:700;color:#e2e8f0;'>{sat['name']}</span>"
                    f"<span style='font-size:0.65rem;color:#64748b;'>↗</span>"
                    f"</div>"
                    f"<div style='display:flex;justify-content:space-between;font-size:0.65rem;color:#64748b;'>"
                    f"<span>{sat['constellation']}</span>"
                    f"<span style='color:#818cf8;background:#1e1b4b;padding:0.1rem 0.4rem;border-radius:4px;font-family:monospace;font-size:0.6rem;'>{sat['protocol']}</span>"
                    f"</div></div></a>",
                    unsafe_allow_html=True,
                )

        # Actionable Directive
        st.markdown(
            f"<div style='padding:0.8rem;border-radius:12px;background:#1e1b4b80;border:1px solid #3730a3;margin:1rem 0;'>"
            f"<div style='display:flex;align-items:center;gap:0.3rem;font-size:0.7rem;font-weight:600;color:#818cf8;margin-bottom:0.3rem;'>"
            f"⚡ Actionable Directive for Researchers</div>"
            f"<p style='font-size:0.75rem;color:#cbd5e1;margin:0;'>{active_point['actionable_directive']}</p></div>",
            unsafe_allow_html=True,
        )

        # Footer
        st.markdown(
            f"<div style='display:flex;justify-content:space-between;font-size:0.6rem;color:#475569;"
            f"border-top:1px solid #1e293b;padding-top:0.5rem;margin-top:0.5rem;'>"
            f"<span>✅ Verified Open Science Standard</span>"
            f"<span>Last Synced: {active_point['last_updated']}</span></div>",
            unsafe_allow_html=True,
        )

# ═══════════════════════════════════════════════════════════════════════
# TAB 2: IMPACT VS FEASIBILITY MATRIX
# ═══════════════════════════════════════════════════════════════════════

elif active_tab == "matrix":
    pts = st.session_state["radar_pain_points"]

    st.markdown(
        "<h2 style='font-size:1.3rem;font-weight:700;color:#f1f5f9;display:flex;align-items:center;gap:0.5rem;'>"
        "🎯 Global Research Impact Matrix</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#94a3b8;font-size:0.8rem;margin:-0.3rem 0 1.5rem 0;'>"
        "Positions research pain points based on practical feasibility and global urgency.</p>",
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([7, 5])

    with col_left:
        # 2D Scatter Plot Matrix
        import plotly.graph_objects as go

        fig = go.Figure()

        # Add quadrant shading
        fig.add_shape(type="rect", x0=0, y0=50, x1=50, y1=100, fillcolor="rgba(239,68,68,0.05)", line=dict(width=0), layer="below")
        fig.add_shape(type="rect", x0=50, y0=50, x1=100, y1=100, fillcolor="rgba(34,197,94,0.05)", line=dict(width=0), layer="below")
        fig.add_shape(type="rect", x0=0, y0=0, x1=50, y1=50, fillcolor="rgba(234,179,8,0.05)", line=dict(width=0), layer="below")
        fig.add_shape(type="rect", x0=50, y0=0, x1=100, y1=50, fillcolor="rgba(59,130,246,0.05)", line=dict(width=0), layer="below")

        # Quadrant lines
        fig.add_vline(x=50, line=dict(color="rgba(148,163,184,0.3)", width=1, dash="dash"))
        fig.add_hline(y=50, line=dict(color="rgba(148,163,184,0.3)", width=1, dash="dash"))

        # Quadrant labels
        fig.add_annotation(x=25, y=95, text="⚠️ High Impact<br>Low Feasibility", showarrow=False,
                          font=dict(size=9, color="#f87171"), opacity=0.6)
        fig.add_annotation(x=75, y=95, text="✅ High Impact<br>High Feasibility", showarrow=False,
                          font=dict(size=9, color="#4ade80"), opacity=0.6)
        fig.add_annotation(x=25, y=5, text="🔬 Low Priority", showarrow=False,
                          font=dict(size=9, color="#a3a3a3"), opacity=0.6)
        fig.add_annotation(x=75, y=5, text="🛠️ Feasible but<br>Lower Impact", showarrow=False,
                          font=dict(size=9, color="#60a5fa"), opacity=0.6)

        # Severity colors
        sev_colors_map = {"Critical": "#f43f5e", "High": "#f59e0b", "Moderate": "#64748b"}

        for pt in pts:
            color = sev_colors_map.get(pt["severity"], "#64748b")
            fig.add_trace(go.Scatter(
                x=[pt["feasibility_score"]],
                y=[pt["impact_score"]],
                mode="markers+text",
                marker=dict(
                    size=14 + pt["active_global_teams"] * 2,
                    color=color,
                    line=dict(color="white", width=1),
                    symbol="diamond",
                ),
                text=[pt["id"]],
                textposition="top center",
                textfont=dict(size=8, color="#e2e8f0"),
                name=pt["title"],
                hovertemplate=(
                    f"<b>{pt['title']}</b><br>"
                    f"Domain: {pt['domain']}<br>"
                    f"Impact: {pt['impact_score']} | Feasibility: {pt['feasibility_score']}<br>"
                    f"Teams: {pt['active_global_teams']} | Severity: {pt['severity']}"
                    "<extra></extra>"
                ),
            ))

        fig.update_layout(
            title=dict(text="Research Pain Point Matrix", font=dict(size=14, color="#e2e8f0")),
            xaxis=dict(title="Technical Feasibility Score", range=[-5, 105], gridcolor="#1e293b"),
            yaxis=dict(title="Global Impact Score", range=[-5, 105], gridcolor="#1e293b"),
            height=500,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8"),
            hovermode="closest",
            margin=dict(l=50, r=30, t=50, b=50),
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown(
            "<div style='text-align:center;font-size:0.7rem;color:#475569;font-family:monospace;'>"
            "Click any point to inspect detailed telemetry requirements</div>",
            unsafe_allow_html=True,
        )

    with col_right:
        st.markdown(
            "<h3 style='font-size:0.75rem;font-weight:600;color:#94a3b8;text-transform:uppercase;"
            "letter-spacing:0.05em;margin-bottom:0.8rem;'>Prioritized Research Queue</h3>",
            unsafe_allow_html=True,
        )

        # Sort by impact score descending
        sorted_pts = sorted(pts, key=lambda p: p["impact_score"], reverse=True)

        for pt in sorted_pts:
            impact_color = "#34d399" if pt["impact_score"] >= 80 else "#f59e0b" if pt["impact_score"] >= 60 else "#64748b"
            feas_color = "#818cf8" if pt["feasibility_score"] >= 80 else "#f59e0b" if pt["feasibility_score"] >= 60 else "#64748b"

            st.markdown(
                f"""
                <div style="padding:0.8rem;margin:0.4rem 0;border-radius:12px;background:#020617;border:1px solid #1e293b;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.3rem;">
                        <span style="font-size:0.65rem;font-family:monospace;color:#818cf8;font-weight:600;">{pt['id']}</span>
                        <span style="font-size:0.6rem;color:#64748b;">{pt['active_global_teams']} Teams Active</span>
                    </div>
                    <div style="font-size:0.75rem;font-weight:600;color:#f1f5f9;margin-bottom:0.5rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                        {pt['title']}
                    </div>
                    <div style="margin-bottom:0.3rem;">
                        <div style="display:flex;justify-content:space-between;font-size:0.6rem;color:#64748b;margin-bottom:0.1rem;">
                            <span>Global Impact</span>
                            <span style="font-weight:700;color:{impact_color};">{pt['impact_score']}/100</span>
                        </div>
                        <div style="height:4px;border-radius:999px;background:#0f172a;overflow:hidden;">
                            <div style="height:100%;width:{pt['impact_score']}%;background:{impact_color};border-radius:999px;"></div>
                        </div>
                    </div>
                    <div>
                        <div style="display:flex;justify-content:space-between;font-size:0.6rem;color:#64748b;margin-bottom:0.1rem;">
                            <span>Technical Feasibility</span>
                            <span style="font-weight:700;color:{feas_color};">{pt['feasibility_score']}/100</span>
                        </div>
                        <div style="height:4px;border-radius:999px;background:#0f172a;overflow:hidden;">
                            <div style="height:100%;width:{pt['feasibility_score']}%;background:{feas_color};border-radius:999px;"></div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ═══════════════════════════════════════════════════════════════════════
# TAB 3: SATELLITE TRIGGER ENGINE
# ═══════════════════════════════════════════════════════════════════════

elif active_tab == "trigger":
    pts = st.session_state["radar_pain_points"]
    active_point = st.session_state["radar_active_point"]

    st.markdown(
        "<h2 style='font-size:1.3rem;font-weight:700;color:#f1f5f9;display:flex;align-items:center;gap:0.5rem;'>"
        "⚡ Automated Satellite Telemetry Trigger Engine</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#94a3b8;font-size:0.8rem;margin:-0.3rem 0 1.5rem 0;'>"
        "Configure real-time webhooks. When satellite constellations detect an anomaly threshold "
        "over your target AOI, your research server will automatically receive the dataset.</p>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            "<div style='background:#020617;border:1px solid #1e293b;border-radius:16px;padding:1.5rem;'>",
            unsafe_allow_html=True,
        )

        # Target Pain Point
        point_options = {pt["id"]: f"{pt['id']}: {pt['title']}" for pt in pts}
        selected_id = st.selectbox(
            "🎯 Target Research Pain Point",
            options=list(point_options.keys()),
            format_func=lambda x: point_options.get(x, x),
            index=next(i for i, pt in enumerate(pts) if pt["id"] == active_point["id"]),
            key="trigger_point_select",
        )

        # Update active point if changed
        if selected_id != active_point["id"]:
            st.session_state["radar_active_point"] = next(
                (p for p in pts if p["id"] == selected_id), pts[0]
            )
            st.rerun()

        # Threshold display
        st.markdown(
            f"<div style='margin:0.8rem 0;'>"
            f"<div style='font-size:0.7rem;font-weight:600;color:#cbd5e1;margin-bottom:0.3rem;'>"
            f"Configured Sensor Anomaly Threshold</div>"
            f"<div style='padding:0.6rem;border-radius:10px;background:#0f172a;border:1px solid #1e293b;"
            f"font-size:0.75rem;font-family:monospace;color:#818cf8;'>{active_point['default_trigger_threshold']}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Webhook URL
        st.text_input(
            "🔗 Research Endpoint Webhook URL",
            key="radar_trigger_webhook",
            placeholder="https://api.research-hub.org/v1/telemetry/webhook",
        )

        # Deploy Button
        is_active = st.session_state.get("radar_trigger_active", False)
        btn_color = "#059669" if is_active else "#4f46e5"
        btn_text = "📡 Webhook Monitoring Active (Live)" if is_active else "🚀 Deploy Satellite Webhook Trigger"

        if st.button(btn_text, use_container_width=True, type="primary" if not is_active else "secondary"):
            st.session_state["radar_trigger_active"] = not is_active
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # Webhook Payload Preview
        st.markdown(
            f"""
            <div style="background:#020617;border:1px solid #1e293b;border-radius:16px;padding:1.5rem;
                        font-family:monospace;font-size:0.7rem;">
                <div style="display:flex;justify-content:space-between;align-items:center;
                           border-bottom:1px solid #1e293b;padding-bottom:0.5rem;margin-bottom:0.8rem;">
                    <span style="display:flex;align-items:center;gap:0.3rem;color:#64748b;">
                        <span style="color:#34d399;">⎔</span> Webhook Payload Preview
                    </span>
                    <span style="font-size:0.6rem;color:#34d399;">JSON Schema Valid</span>
                </div>
                <pre style="font-size:0.65rem;color:#34d399;background:#0f172a;padding:0.8rem;border-radius:10px;
                           border:1px solid #1e293b;overflow-x:auto;white-space:pre-wrap;">
{{
  "event": "SATELLITE_THRESHOLD_EXCEEDED",
  "painPointId": "{active_point['id']}",
  "satellite": "{active_point['satellite_feeds'][0]['name'] if active_point['satellite_feeds'] else 'Sentinel-5P'}",
  "triggerCondition": "{active_point['default_trigger_threshold']}",
  "coordinates": {{ "lat": 4.166, "lon": 31.333 }},
  "stacCatalogUrl": "{active_point['satellite_feeds'][0]['link'] if active_point['satellite_feeds'] else ''}",
  "timestamp": "{datetime.now().isoformat()}"
}}
                </pre>
                <div style="margin-top:0.8rem;font-size:0.6rem;color:#475569;display:flex;align-items:center;gap:0.3rem;">
                    🔒 End-to-end encrypted telemetry transport via STAC API standard
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ═══════════════════════════════════════════════════════════════════════
# TAB 4: LOOPHOLE ACCOUNTABILITY & OWNERSHIP
# ═══════════════════════════════════════════════════════════════════════

elif active_tab == "claims":
    pts = st.session_state["radar_pain_points"]

    st.markdown(
        "<h2 style='font-size:1.3rem;font-weight:700;color:#f1f5f9;display:flex;align-items:center;gap:0.5rem;'>"
        "🔒 Global Loophole Accountability Registry</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#94a3b8;font-size:0.8rem;margin:-0.3rem 0 1.5rem 0;'>"
        "Eliminate redundant effort. Researchers and institutions claim specific research gaps "
        "and publish verified milestones so no critical problem is left neglected.</p>",
        unsafe_allow_html=True,
    )

    # Table Header
    st.markdown(
        """
        <div style="display:grid;grid-template-columns:2.5fr 1.5fr 1.5fr 1fr 1fr;
                    gap:0.5rem;padding:0.5rem 0.8rem;font-size:0.65rem;font-weight:600;
                    color:#64748b;text-transform:uppercase;letter-spacing:0.05em;
                    border-bottom:1px solid #1e293b;margin-bottom:0.5rem;">
            <div>Loophole ID & Title</div>
            <div>Claimed Institution / Lead</div>
            <div>Verification Status</div>
            <div>Target Milestone</div>
            <div style="text-align:right;">Action</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for pt in pts:
        status = pt["claim_info"]["status"]
        status_colors = {
            "Claimed & In Progress": ("#34d399", "#34d39920", "#34d39940"),
            "Under Verification": ("#f59e0b", "#f59e0b20", "#f59e0b40"),
            "Open for Claim": ("#f43f5e", "#f43f5e20", "#f43f5e40"),
        }
        sc = status_colors.get(status, ("#64748b", "#64748b20", "#64748b40"))

        st.markdown(
            f"""
            <div style="display:grid;grid-template-columns:2.5fr 1.5fr 1.5fr 1fr 1fr;
                        gap:0.5rem;padding:0.8rem;align-items:center;
                        border-bottom:1px solid #1e293b80;font-size:0.72rem;">
                <div>
                    <div style="font-weight:600;color:#f1f5f9;">{pt['title']}</div>
                    <div style="font-size:0.6rem;font-family:monospace;color:#818cf8;">{pt['id']}</div>
                </div>
                <div>
                    <div style="color:#cbd5e1;">{pt['claim_info']['institution']}</div>
                    <div style="font-size:0.6rem;color:#64748b;">{pt['claim_info']['lead_researcher']}</div>
                </div>
                <div>
                    <span style="padding:0.15rem 0.5rem;border-radius:999px;font-size:0.6rem;font-weight:600;
                               background:{sc[1]};color:{sc[0]};border:1px solid {sc[2]};">
                        ● {status}
                    </span>
                </div>
                <div style="font-family:monospace;color:#cbd5e1;">{pt['claim_info']['target_milestone_date']}</div>
                <div style="text-align:right;">
            """,
            unsafe_allow_html=True,
        )

        if status == "Open for Claim":
            if st.button(f"🔓 Claim Loophole", key=f"claim_{pt['id']}", use_container_width=True):
                handle_claim_loophole(pt["id"])
                st.success(f"✅ Claimed '{pt['title']}'! You are now the lead researcher.")
                st.rerun()
        else:
            st.markdown(
                f"<span style='font-size:0.6rem;font-family:monospace;color:#475569;'>{pt['claim_info'].get('verification_hash', 'Verified')}</span>",
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# TAB 5: AI CROSS-DOMAIN SYNTHESIZER
# ═══════════════════════════════════════════════════════════════════════

elif active_tab == "synthesizer":
    st.markdown(
        "<h2 style='font-size:1.3rem;font-weight:700;color:#f1f5f9;display:flex;align-items:center;gap:0.5rem;'>"
        "✨ AI Cross-Domain Paradigm Synthesizer</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#94a3b8;font-size:0.8rem;margin:-0.3rem 0 1.5rem 0;'>"
        "Cross-pollinate methods across non-obvious disciplines to create breakthrough "
        "methodologies for satellite remote sensing problems.</p>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            "<div style='background:#020617;border:1px solid #1e293b;border-radius:16px;padding:1.5rem;'>",
            unsafe_allow_html=True,
        )

        st.text_input(
            "🎯 Target Satellite / Earth Problem Domain",
            key="radar_synth_domain_a",
            placeholder="e.g., Marine Biochemistry, Deforestation, Urban Heat",
        )

        st.text_input(
            "🧠 Unrelated Technical Discipline to Synthesize",
            key="radar_synth_domain_b",
            placeholder="e.g., Neural Radiance Fields, Quantum Computing, Game Theory",
        )

        is_running = st.session_state.get("radar_synth_running", False)
        btn_label = "⏳ Synthesizing..." if is_running else "✨ Synthesize Novel Research Hypothesis"

        if st.button(btn_label, use_container_width=True, disabled=is_running, type="primary"):
            handle_run_synthesizer()
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        synth_output = st.session_state.get("radar_synth_output")

        st.markdown(
            "<div style='background:#020617;border:1px solid #1e293b;border-radius:16px;padding:1.5rem;min-height:250px;display:flex;flex-direction:column;'>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<div style='font-size:0.7rem;font-weight:600;color:#f59e0b;text-transform:uppercase;"
            "letter-spacing:0.05em;margin-bottom:0.8rem;display:flex;align-items:center;gap:0.3rem;'>"
            "⚙️ Synthesized Hypothesis Output</div>",
            unsafe_allow_html=True,
        )

        if synth_output:
            st.markdown(
                f"<div style='padding:0.8rem;border-radius:10px;background:#0f172a;border:1px solid #1e293b;"
                f"font-size:0.75rem;color:#e2e8f0;line-height:1.6;white-space:pre-wrap;'>{synth_output}</div>",
                unsafe_allow_html=True,
            )
        elif is_running:
            st.markdown(
                "<div style='text-align:center;padding:3rem 1rem;color:#64748b;font-style:italic;font-size:0.8rem;'>"
                "⏳ Synthesizing cross-domain hypothesis...</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='text-align:center;padding:3rem 1rem;color:#475569;font-style:italic;font-size:0.8rem;'>"
                "✨ Select two domains and click synthesize to generate a novel cross-disciplinary research approach.</div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            "<div style='margin-top:auto;font-size:0.6rem;color:#475569;padding-top:0.8rem;"
            "border-top:1px solid #1e293b80;'>"
            "AI cross-pollination engine trained on 10M+ open science literature datasets.</div>",
            unsafe_allow_html=True,
        )

        st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# SIDEBAR NAVIGATION HINT
# ═══════════════════════════════════════════════════════════════════════

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    ### 🌍 Explore the Radar
    - **🛰️ Intelligence Radar** — Browse & analyze pain points
    - **🎯 Impact Matrix** — Prioritize by impact/feasibility
    - **⚡ Trigger Engine** — Configure satellite webhooks
    - **🔒 Ownership** — Claim & track research gaps
    - **✨ Synthesizer** — Cross-domain innovation
    """
)

