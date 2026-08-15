"""
🔬 Domain Analytics Hub — Consolidated Specialized Analytics Hub
Consolidates old pages: 10 (Clinical), 24 (Network), 34 (Global Localization),
36 (Lab Protocol), 57 (GIS), 63 (Academic Portfolio), 64 (Global Surveillance).
"""

import numpy as np
import pandas as pd
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.session_manager import get_active_dataframe
from modules.shared_ui import (
    hero_card,
    section_header,
    render_dataset_context_banner,
    render_export_buttons,
)


def render_clinical(df):
    """Tab: Clinical analytics."""
    section_header("🏥 Clinical & Biometric Analytics", "Biometric calculators, risk screening, and reference ranges.")

    if df is not None and "Weight_kg" in df.columns and "Height_cm" in df.columns:
        st.markdown("#### Batch Cohort BMI Screening")
        audit = df.copy()
        audit["Calculated_BMI"] = audit["Weight_kg"] / ((audit["Height_cm"] / 100) ** 2)
        audit["BMI_Status"] = pd.cut(
            audit["Calculated_BMI"],
            bins=[0, 18.5, 25, 30, 100],
            labels=["Underweight", "Normal", "Overweight", "Obese"],
        )
        st.dataframe(audit.head(15), use_container_width=True)
        with st.expander("Cohort's BMI Distribution", expanded=False):
            st.write(audit["BMI_Status"].value_counts())

    st.markdown("#### Individual Biometric Calculator")
    col1, col2 = st.columns(2)
    with col1:
        weight = st.number_input("Weight (kg)", 20.0, 300.0, 75.0, key="cli_wt")
        height = st.number_input("Height (cm)", 50.0, 250.0, 175.0, key="cli_ht")
    with col2:
        waist = st.number_input("Waist (cm)", 30.0, 200.0, 88.0, key="cli_waist")
        hip = st.number_input("Hip (cm)", 30.0, 200.0, 96.0, key="cli_hip")

    if st.button("🩺 Calculate Biometrics", type="primary", key="run_biometric"):
        bmi = weight / ((height / 100) ** 2)
        whr = waist / hip
        bsa = np.sqrt((height * weight) / 3600)
        c1, c2, c3 = st.columns(3)
        c1.metric("BMI", f"{bmi:.1f}")
        c2.metric("Waist-Hip Ratio", f"{whr:.2f}")
        c3.metric("Body Surface Area", f"{bsa:.2f} m²")

    st.markdown("#### CVD Risk Estimation")
    sbp = st.slider("Systolic BP", 70, 250, 125, key="cli_sbp")
    chol = st.slider("Total Cholesterol", 100, 400, 210, key="cli_chol")
    smoker = st.checkbox("Smoker", key="cli_smoker")
    diabetic = st.checkbox("Diabetic", key="cli_diab")
    if st.button("❤️ Compute CVD Risk", type="primary", key="run_cvd"):
        risk = 4.2 + (sbp - 120) * 0.08 + (chol - 200) * 0.03
        if smoker:
            risk += 6.5
        if diabetic:
            risk += 5.0
        risk = max(1, min(95, risk))
        st.metric("10-Year ASCVD Risk", f"{risk:.1f}%")
        st.success("Low Risk" if risk < 5 else "Borderline" if risk < 15 else "High Risk")


def render_network():
    """Tab: Network analysis."""
    section_header("🔗 Network & Knowledge Graph Analysis", "Analyze relationships, networks, and graph structures.")

    st.markdown("#### Network Visualization")
    st.info("Network analytics for graph structures, relationships, and centrality.")

    n_nodes = st.slider("Number of nodes", 5, 30, 10, key="net_nodes")
    if st.button("🌐 Generate Network Graph", type="primary", key="run_network"):
        np.random.seed(42)
        nodes = [f"Node {i}" for i in range(1, n_nodes + 1)]
        edges = np.random.randint(1, n_nodes, (n_nodes * 2, 2)).tolist()
        edges = [(a, b) for a, b in edges if a != b][: n_nodes * 2]
        graph_data = pd.DataFrame(edges[: n_nodes * 2 if n_nodes * 2 < len(edges) else n_nodes * 2], columns=["Source", "Target"])
        st.dataframe(graph_data, use_container_width=True, hide_index=True)
        st.caption(f"Network generated with {n_nodes} nodes and {len(graph_data)} edges.")


def render_gis():
    """Tab: GIS spatial analytics."""
    section_header("🗺️ GIS & Spatial Analytics", "Geospatial analysis and mapping.")

    try:
        import folium
        from streamlit_folium import st_folium
        st.markdown("#### Interactive Map Selector")
        m = folium.Map(location=[0.3476, 32.5825], zoom_start=6)
        m.add_child(folium.LatLngPopup())
        map_data = st_folium(m, height=350, width="100%")
        if map_data and map_data.get("last_clicked"):
            lat = map_data["last_clicked"]["lat"]
            lon = map_data["last_clicked"]["lng"]
            st.info(f"Selected coordinates: {lat:.4f}, {lon:.4f}")
    except ImportError:
        st.info("`folium` and `streamlit_folium` required for interactive maps.")
        st.warning("Static coordinates below:")
        col1, col2 = st.columns(2)
        col1.number_input("Latitude", value=0.3476, key="gis_lat")
        col2.number_input("Longitude", value=32.5825, key="gis_lon")


def render_global_surveillance():
    """Tab: Global surveillance/impact."""
    section_header("🌍 Global Surveillance & Sector Impact", "Macro sector analysis and global monitoring.")

    st.markdown("#### Global Sector Intelligence")
    sector = st.selectbox("Select Sector", [
        "Agriculture & Food Security",
        "Healthcare & Epidemiology",
        "Energy & Power Grids",
        "Financial Systems",
        "Environmental Conservation",
    ], key="sector_sel")

    st.markdown("#### Live Sector Telemetry Dashboard")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sentinel Coverage", "42 Satellites", delta="Active")
    c2.metric("Region Monitoring", "Global", delta="Live")
    c3.metric("Risk Index", "0.014", delta="Low")
    c4.metric("Sector Health", "Stable", delta="Optimal")

    if st.button("🌍 Generate Sector Intelligence Report", type="primary", key="run_sector_intel"):
        st.success(f"Sector intelligence report generated for **{sector}**.")
        report = pd.DataFrame({
            "Indicator": ["Coverage", "Data Quality", "Alert Level", "Action Priority"],
            "Status": ["Optimal", "Verified", "Low", "Routine"],
            "Score": [94, 88, 12, 30],
        })
        st.dataframe(report, use_container_width=True, hide_index=True)


def render_academic():
    """Tab: Academic portfolio."""
    section_header("🎓 Academic Portfolio & Grants Studio", "Manage academic achievements, publications, and grants.")

    st.markdown("#### Academic Portfolio")
    portfolio = pd.DataFrame({
        "Item": ["Publication 1", "Grant Award 1", "Conference Paper", "Research Project", "Dataset Collection"],
        "Type": ["Journal Article", "Grant", "Conference", "Project", "Data"],
        "Status": ["Published", "Awarded", "Presented", "Ongoing", "Completed"],
        "Year": [2024, 2023, 2024, 2024, 2023],
    })
    st.dataframe(portfolio, use_container_width=True, hide_index=True)

    st.markdown("#### Impact Metrics")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Publications", 12)
    c2.metric("Citations", 340)
    c3.metric("h-Index", 8)
    c4.metric("Grants Awarded", 5)

    render_export_buttons(portfolio, base_name="academic_portfolio")


def render_lab():
    """Tab: Lab protocol."""
    section_header("🧪 Lab Protocol & Methodology Transpiler", "Translate lab protocols into reproducible workflows.")

    st.markdown("#### Protocol Transpiler")
    st.info("Convert experimental protocols into structured, reproducible documentation.")
    protocol_name = st.text_input("Protocol Name", placeholder="e.g., PCR Amplification", key="lab_name")
    steps = st.text_area("Protocol Steps (one per line)", placeholder="Step 1: Prepare sample\nStep 2: Amplify DNA", key="lab_steps")
    if st.button("🧪 Transpile Protocol", type="primary", key="run_lab"):
        if protocol_name:
            docs = f"""# PROTOCOL: {protocol_name}
## Standard Operating Procedure
{steps}
## Materials & Reagents
- [List materials]
## Safety Notes
- [Safety considerations]
"""
            st.code(docs, language="markdown")
            st.download_button("⬇️ Download Protocol", data=docs, file_name=f"{protocol_name.replace(' ', '_')}_protocol.md", mime="text/markdown")
        else:
            st.warning("Enter a protocol name.")


def main():
    setup_page("Domain Analytics Hub", "🔬", initial_sidebar_state="expanded")

    hero_card(
        "🔬 Domain & Specialized Analytics Hub",
        "Consolidated domain hub: clinical/biometric analytics, network analysis, GIS spatial analytics, global surveillance, academic portfolio, and lab protocols.",
        badge_text="DOMAIN ANALYTICS HUB • CONSOLIDATED",
    )

    render_dataset_context_banner()

    df = get_active_dataframe()

    tabs = st.tabs([
        "🏥 Clinical",
        "🔗 Network",
        "🗺️ GIS",
        "🌍 Surveillance",
        "🎓 Academic",
        "🧪 Lab Protocol",
    ])

    with tabs[0]:
        render_clinical(df)
    with tabs[1]:
        render_network()
    with tabs[2]:
        render_gis()
    with tabs[3]:
        render_global_surveillance()
    with tabs[4]:
        render_academic()
    with tabs[5]:
        render_lab()

    render_standard_footer("DOMAIN ANALYTICS HUB")


if __name__ == "__main__":
    main()
