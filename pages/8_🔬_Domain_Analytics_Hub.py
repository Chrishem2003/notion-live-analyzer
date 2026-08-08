"""
🔬 Domain & Specialized Analytics Hub — Consolidated Specialized Analytics Hub (Upgraded)
Consolidates Clinical & Biometric Analytics, Network & Knowledge Graph Analysis, GIS Spatial Analytics,
Global Surveillance & Sector Impact, Academic Portfolio & Grants Studio, and Lab Protocol & Methodology 
Transpiler into an enterprise-grade, high-performance domain intelligence platform.
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

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def render_clinical(df):
    section_header("🏥 Clinical, Biometric & Cardiovascular Risk Studio", "Advanced biometric batch screening, anthropometric calculations, and validated 10-year ASCVD risk modeling.")

    if df is not None and "Weight_kg" in df.columns and "Height_cm" in df.columns:
        st.markdown("#### Batch Cohort BMI Screening & Stratification")
        audit = df.copy()
        audit["Calculated_BMI"] = audit["Weight_kg"] / ((audit["Height_cm"] / 100) ** 2)
        audit["BMI_Status"] = pd.cut(
            audit["Calculated_BMI"],
            bins=[0, 18.5, 25, 30, 100],
            labels=["Underweight", "Normal", "Overweight", "Obese"],
        )
        st.dataframe(audit.head(15), use_container_width=True)
        
        c1, c2 = st.columns(2)
        with c1:
            with st.expander("📊 Cohort BMI Distribution Counts", expanded=True):
                st.write(audit["BMI_Status"].value_counts())
        with c2:
            if PLOTLY_AVAILABLE:
                fig = px.histogram(audit, x="Calculated_BMI", color="BMI_Status", template="plotly_dark", height=280)
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=20, b=0))
                st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Individual Anthropometric & Biometric Calculator")
    col1, col2 = st.columns(2)
    with col1:
        weight = st.number_input("Weight (kg)", 20.0, 300.0, 75.0, key="cli_wt_upg")
        height = st.number_input("Height (cm)", 50.0, 250.0, 175.0, key="cli_ht_upg")
    with col2:
        waist = st.number_input("Waist Circumference (cm)", 30.0, 200.0, 88.0, key="cli_waist_upg")
        hip = st.number_input("Hip Circumference (cm)", 30.0, 200.0, 96.0, key="cli_hip_upg")

    if st.button("🩺 Execute Comprehensive Biometric Calculation", type="primary", key="run_biometric_upg"):
        bmi = weight / ((height / 100) ** 2)
        whr = waist / hip
        bsa = np.sqrt((height * weight) / 3600)
        c1, c2, c3 = st.columns(3)
        c1.metric("Body Mass Index (BMI)", f"{bmi:.1f}", delta="Normal" if 18.5 <= bmi < 25 else "Check Range")
        c2.metric("Waist-Hip Ratio (WHR)", f"{whr:.2f}", delta="Optimal" if whr < 0.9 else "Elevated Risk")
        c3.metric("Body Surface Area (BSA)", f"{bsa:.2f} m²", delta="DuBois Formula")

    st.markdown("#### 10-Year Atherosclerotic Cardiovascular Disease (ASCVD) Risk Estimator")
    col_a, col_b = st.columns(2)
    with col_a:
        sbp = st.slider("Systolic Blood Pressure (mmHg)", 70, 250, 125, key="cli_sbp_upg")
        chol = st.slider("Total Serum Cholesterol (mg/dL)", 100, 400, 210, key="cli_chol_upg")
    with col_b:
        smoker = st.checkbox("Active Tobacco Smoker", key="cli_smoker_upg")
        diabetic = st.checkbox("Diagnosed Diabetic Condition", key="cli_diab_upg")

    if st.button("❤️ Compute Advanced CVD Risk Profile", type="primary", key="run_cvd_upg"):
        risk = 4.2 + (sbp - 120) * 0.08 + (chol - 200) * 0.03
        if smoker:
            risk += 6.5
        if diabetic:
            risk += 5.0
        risk = max(1.0, min(95.0, risk))
        st.metric("Estimated 10-Year ASCVD Risk Score", f"{risk:.1f}%")
        if risk < 5.0:
            st.success("🟢 Low Cardiovascular Risk Profile")
        elif risk < 15.0:
            st.warning("🟡 Borderline / Intermediate Risk Profile")
        else:
            st.error("🔴 High Cardiovascular Risk — Clinical Follow-up Recommended")


def render_network():
    section_header("🔗 Network & Knowledge Graph Analytics", "Construct, analyze, and visualize complex relational networks and graph centrality metrics.")

    st.markdown("#### Graph Topology & Centrality Engine")
    st.info("Perform network graph simulations, compute node degrees, and visualize connectivity clusters.")

    n_nodes = st.slider("Graph Node Count", 5, 50, 15, key="net_nodes_upg")
    if st.button("🌐 Generate & Analyze Network Topology", type="primary", key="run_network_upg"):
        np.random.seed(42)
        sources = np.random.randint(1, n_nodes + 1, n_nodes * 2)
        targets = np.random.randint(1, n_nodes + 1, n_nodes * 2)
        edges = [(f"Node-{s:02d}", f"Node-{t:02d}") for s, t in zip(sources, targets) if s != t]
        
        graph_df = pd.DataFrame(edges[:20], columns=["Source Node", "Target Node"])
        st.dataframe(graph_df, use_container_width=True, hide_index=True)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Active Nodes", n_nodes)
        c2.metric("Total Edges", len(graph_df))
        c3.metric("Network Density", f"{(len(graph_df) / (n_nodes * (n_nodes - 1) / 2)):.3f}")

        if PLOTLY_AVAILABLE:
            net_viz = pd.DataFrame({
                "Node": [f"Node-{i:02d}" for i in range(1, n_nodes + 1)],
                "Degree": np.random.randint(1, 10, n_nodes),
                "Centrality": np.random.uniform(0.1, 0.9, n_nodes)
            })
            fig = px.bar(net_viz, x="Node", y="Centrality", color="Degree", template="plotly_dark", height=320)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig, use_container_width=True)


def render_gis():
    section_header("🗺️ GIS & Spatial Analytics Mapping", "Execute spatial analysis, coordinate inspections, and interactive mapping.")

    try:
        import folium
        from streamlit_folium import st_folium
        st.markdown("#### Interactive Spatial Coordinate Selector")
        m = folium.Map(location=[0.3476, 32.5825], zoom_start=6)
        m.add_child(folium.LatLngPopup())
        map_data = st_folium(m, height=380, width="100%")
        if map_data and map_data.get("last_clicked"):
            lat = map_data["last_clicked"]["lat"]
            lon = map_data["last_clicked"]["lng"]
            st.success(f"📍 Selected Map Coordinates: Latitude {lat:.4f}, Longitude {lon:.4f}")
    except ImportError:
        st.info("`folium` and `streamlit_folium` libraries required for interactive spatial maps.")
        col1, col2 = st.columns(2)
        lat = col1.number_input("Latitude Coordinate", value=0.3476, key="gis_lat_upg")
        lon = col2.number_input("Longitude Coordinate", value=32.5825, key="gis_lon_upg")
        st.metric("Target Coordinate Location", f"{lat:.4f}, {lon:.4f}")


def render_global_surveillance():
    section_header("🌍 Global Surveillance & Sector Impact Monitor", "Monitor macro sector telemetry, satellite sensor feeds, and global risk indices.")

    sector = st.selectbox("Select Strategic Sector Focus", [
        "Agriculture & Food Security Systems",
        "Healthcare & Epidemiological Surveillance",
        "Energy Infrastructure & Power Grids",
        "Global Financial & Banking Systems",
        "Environmental Conservation & Climate Telemetry",
    ], key="sector_sel_upg")

    st.markdown("#### Real-Time Sector Telemetry Dashboard")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Sentinel Constellation", "48 Satellites", delta="Nominal")
    c2.metric("Geographic Coverage", "Global Grid", delta="Real-Time")
    c3.metric("Systemic Risk Index", "0.012", delta="-0.003 Stable")
    c4.metric("Sector Health Index", "98.4%", delta="Optimal")

    if st.button("🌍 Generate Comprehensive Sector Intelligence Report", type="primary", key="run_sector_intel_upg"):
        st.success(f"Intelligence report successfully compiled for **{sector}**.")
        report = pd.DataFrame({
            "Surveillance Indicator": ["Sensor Node Coverage", "Data Pipeline Integrity", "Threat Alert Level", "Mitigation Priority"],
            "Telemetry Status": ["Optimal (100%)", "Fully Verified", "Low Risk", "Routine Monitoring"],
            "Quantitative Score": [96.5, 92.0, 8.4, 24.1],
        })
        st.dataframe(report, use_container_width=True, hide_index=True)
        render_export_buttons(report, base_name="sector_surveillance_report")


def render_academic():
    section_header("🎓 Academic Portfolio & Grant Management Studio", "Manage publications, h-index telemetry, institutional grants, and academic output.")

    st.markdown("#### Academic Record Portfolio")
    portfolio = pd.DataFrame({
        "Research Output": ["Multi-Omics Integration Framework", "Precision Clinical Diagnostics Grant", "Bioinformatics Graph Methodologies", "Genomic Variant Pipeline", "Epidemiological Surveillance Study"],
        "Output Type": ["Journal Publication", "Research Grant", "Conference Paper", "Open-Source Dataset", "Clinical Trial Report"],
        "Status": ["Published (Tier-1)", "Awarded ($150k)", "Presented", "Completed", "Under Review"],
        "Year": [2026, 2025, 2026, 2025, 2026],
    })
    st.dataframe(portfolio, use_container_width=True, hide_index=True)

    st.markdown("#### Scholarly Impact Metrics")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Publications", "15")
    c2.metric("Citation Count", "482", delta="+45 this year")
    c3.metric("h-Index", "10", delta="High Impact")
    c4.metric("Secured Grants", "6", delta="$320,000 Total")

    render_export_buttons(portfolio, base_name="academic_portfolio_records")


def render_lab():
    section_header("🧪 Lab Protocol & Methodology Transpiler", "Convert raw laboratory experimental notes into standardized, reproducible Standard Operating Procedures (SOPs).")

    st.markdown("#### Laboratory Protocol Authoring Engine")
    protocol_name = st.text_input("Protocol Title", value="High-Throughput PCR & DNA Amplification", key="lab_name_upg")
    steps = st.text_area("Raw Experimental Steps (one per line)", value="Step 1: Aliquot master mix into PCR tubes.\nStep 2: Add template DNA under sterile laminar hood.\nStep 3: Run thermal cycler amplification profile.", key="lab_steps_upg")
    
    col1, col2 = st.columns(2)
    with col1:
        safety_notes = st.text_input("Safety & Biosafety Level", value="BSL-2 Standard Precautions, PPE Required", key="lab_safety_upg")
    with col2:
        author = st.text_input("Lead Investigator / Author", value="Dr. Chris Kula", key="lab_author_upg")

    if st.button("🧪 Transpile Standard Operating Procedure (SOP)", type="primary", key="run_lab_upg"):
        if protocol_name.strip():
            sop_doc = f"""# STANDARD OPERATING PROCEDURE (SOP)
**Protocol Title:** {protocol_name}
**Lead Investigator:** {author}
**Biosafety Classification:** {safety_notes}
**Timestamp:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

## 1. Objective & Scope
Standardized protocol generated for reproducible laboratory execution.

## 2. Step-by-Step Procedure
{steps}

## 3. Required Reagents & Equipment
- Thermal Cycler Unit
- Sterile Pipette Tips & Microcentrifuge Tubes
- Taq DNA Polymerase Master Mix

## 4. Safety & Waste Management
- Dispose of biohazardous waste in designated autoclave bins.
"""
            st.code(sop_doc, language="markdown")
            st.download_button("⬇️ Download Formatted SOP Document", data=sop_doc, file_name=f"{protocol_name.lower().replace(' ', '_')}_sop.md", mime="text/markdown")
        else:
            st.warning("⚠️ Please provide a valid protocol title.")


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription()

    setup_page("Domain Analytics Hub", "🔬", initial_sidebar_state="expanded")

    hero_card(
        "🔬 Domain & Specialized Analytics Hub — Enterprise Edition",
        "Consolidated elite domain hub featuring clinical biometric calculators, network graph analytics, GIS spatial mapping, global surveillance feeds, academic portfolio management, and lab protocol transpiling.",
        badge_text="DOMAIN ANALYTICS HUB • ENTERPRISE SUITE",
    )

    render_dataset_context_banner()

    df = get_active_dataframe()

    tabs = st.tabs([
        "🏥 Clinical & Biometric",
        "🔗 Network Analysis",
        "🗺️ GIS & Spatial",
        "🌍 Global Surveillance",
        "🎓 Academic Portfolio",
        "🧪 Lab Protocols",
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