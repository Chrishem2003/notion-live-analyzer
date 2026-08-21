import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

"""
🔬 Domain & Specialized Analytics Hub — Consolidated Specialized Analytics Hub (Production Grade)
Clinical & biometric calculators with honest risk scoring, robust correlation-based network analysis, 
GIS mapping with cached reverse-geocoding and automatic column mapping, World Bank Open Data API 
integration with error boundaries, a secure academic portfolio with fail-safe h-index calculation, 
and standardized SOP generation.
"""

import re
import json
import datetime
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

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False


# ==============================================================================
# Clinical & Biometric Studio
# ==============================================================================
def render_clinical(df):
    section_header("🏥 Clinical, Biometric & Cardiovascular Screening Studio", "Batch biometric screening, dynamic column mapping, anthropometric calculations, and an honestly-labeled cardiovascular risk factor score.")

    if df is not None:
        cols_lower = {c.lower(): c for c in df.columns}
        wt_col = next((cols_lower[k] for k in ["weight_kg", "weight", "wt", "wt_kg"] if k in cols_lower), None)
        ht_col = next((cols_lower[k] for k in ["height_cm", "height", "ht", "ht_cm"] if k in cols_lower), None)

        if wt_col and ht_col:
            st.markdown(f"#### Batch Cohort BMI Screening & Stratification (Mapped: `{wt_col}}`, `{ht_col}}`)")
            audit = df.copy()
            
            # Safe numeric conversion
            audit[wt_col] = pd.to_numeric(audit[wt_col], errors="coerce")
            audit[ht_col] = pd.to_numeric(audit[ht_col], errors="coerce")
            
            # Convert height to meters if values look like centimeters (> 3.0)
            ht_vals = audit[ht_col]
            ht_meters = np.where(ht_vals > 3.0, ht_vals / 100.0, ht_vals)

            audit["Calculated_BMI"] = audit[wt_col] / (ht_meters ** 2)
            audit["BMI_Status"] = pd.cut(
                audit["Calculated_BMI"],
                bins=[0, 18.5, 25.0, 30.0, 100.0],
                labels=["Underweight", "Normal", "Overweight", "Obese"],
            )
            st.dataframe(audit.head(15), use_container_width=True)

            c1, c2 = st.columns(2)
            with c1:
                with st.expander("📊 Cohort BMI Distribution Counts", expanded=True):
                    st.write(audit["BMI_Status"].value_counts())
            with c2:
                if PLOTLY_AVAILABLE:
                    fig = px.histogram(audit.dropna(subset=["Calculated_BMI"]), x="Calculated_BMI", color="BMI_Status", template="plotly_dark", height=280)
                    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=20, b=0))
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("ℹ️ Active dataset loaded, but standard weight/height columns were not automatically detected. You can still use the individual biometric calculator below.")

    st.markdown("#### Individual Anthropometric & Biometric Calculator")
    col1, col2 = st.columns(2)
    with col1:
        weight = st.number_input("Weight (kg)", 20.0, 300.0, 75.0, key="cli_wt_prod")
        height = st.number_input("Height (cm)", 50.0, 250.0, 175.0, key="cli_ht_prod")
    with col2:
        waist = st.number_input("Waist Circumference (cm)", 30.0, 200.0, 88.0, key="cli_waist_prod")
        hip = st.number_input("Hip Circumference (cm)", 30.0, 200.0, 96.0, key="cli_hip_prod")

    if st.button("🩺 Execute Comprehensive Biometric Calculation", type="primary", key="run_biometric_prod"):
        bmi = weight / ((height / 100.0) ** 2)
        whr = waist / hip if hip > 0 else 0.0
        bsa_mosteller = np.sqrt((height * weight) / 3600.0)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Body Mass Index (BMI)", f"{bmi:.1f}}", delta="Normal" if 18.5 <= bmi < 25 else "Out of Optimal Range")
        c2.metric("Waist-Hip Ratio (WHR)", f"{whr:.2f}}", delta="Optimal" if whr < 0.9 else "Elevated Risk")
        c3.metric("Body Surface Area (Mosteller)", f"{bsa_mosteller:.2f}} m²", delta="√((cm·kg)/3600)")

    st.markdown("---")
    st.markdown("#### Illustrative Cardiovascular Risk Factor Score")
    st.warning(
        "⚠️ **This is NOT the validated ACC/AHA Pooled Cohort Equations and does not produce a clinical ASCVD risk percentage.** "
        "It is a transparent, additive screening heuristic for educational illustration. "
        "For certified clinical evaluations, use the official "
        "[ACC/AHA ASCVD Risk Estimator Plus](https://tools.acc.org/ascvd-risk-estimator-plus/)."
    )
    col_a, col_b = st.columns(2)
    with col_a:
        sbp = st.slider("Systolic Blood Pressure (mmHg)", 70, 250, 125, key="cli_sbp_prod")
        chol = st.slider("Total Serum Cholesterol (mg/dL)", 100, 400, 210, key="cli_chol_prod")
        age = st.slider("Age (years)", 20, 90, 50, key="cli_age_prod")
    with col_b:
        smoker = st.checkbox("Current Tobacco Smoker", key="cli_smoker_prod")
        diabetic = st.checkbox("Diagnosed Diabetic Condition", key="cli_diab_prod")
        htn_treated = st.checkbox("On Blood Pressure Medication", key="cli_htn_prod")

    if st.button("📋 Compute Illustrative Risk Factor Score", type="primary", key="run_cvd_prod"):
        points = 0.0
        points += max(0.0, float(age - 40)) * 0.5
        points += max(0.0, float(sbp - 120)) * (0.3 if htn_treated else 0.2)
        points += max(0.0, float(chol - 200)) * 0.15
        points += 15.0 if smoker else 0.0
        points += 12.0 if diabetic else 0.0
        score = min(100.0, points)

        st.metric("Illustrative Risk Factor Score", f"{score:.1f}} / 100")
        if score < 20:
            st.success("🟢 Low illustrative risk-factor burden")
        elif score < 45:
            st.warning("🟡 Moderate illustrative risk-factor burden")
        else:
            st.error("🔴 High illustrative risk-factor burden — consult a qualified clinician for professional assessment.")
        st.caption("Score formulation: age contributes 0.5 pts/year over 40; SBP contributes 0.2–0.3 pts/mmHg over 120; cholesterol contributes 0.15 pts/mg·dL over 200; smoking +15; diabetes +12. Capped at 100.")


# ==============================================================================
# Advanced Network Analytics Studio
# ==============================================================================
def render_network(df):
    section_header("🔗 Network Analytics — Correlation Graph & Network Topology", "Builds a real topological network graph derived from numeric column relationships in your loaded dataset.")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist() if df is not None else []

    if df is None or len(numeric_cols) < 2:
        st.info("ℹ️ Load a dataset with at least 2 numeric columns via Data Studio to construct a real correlation network.")
        return

    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        threshold = st.slider("Correlation threshold for edge inclusion (|r| ≥)", 0.1, 0.95, 0.40, 0.05, key="net_thresh_prod")
    with col_t2:
        layout_type = st.selectbox("Graph Layout", ["Spring (Fruchterman-Reingold)", "Circular", "Kamada-Kawai"], key="net_layout_prod")

    if st.button("🌐 Build Advanced Network Graph", type="primary", key="run_network_prod"):
        corr = df[numeric_cols].corr().abs()
        edges = []
        for i, c1 in enumerate(numeric_cols):
            for c2 in numeric_cols[i + 1:]:
                r = corr.loc[c1, c2]
                if pd.notnull(r) and r >= threshold:
                    edges.append({"Source Node": c1, "Target Node": c2, "|Correlation|": round(float(r), 3)})

        if not edges:
            st.info(f"No variable pairs exceed |r| ≥ {threshold}}. Try decreasing the correlation threshold.")
            return

        edges_df = pd.DataFrame(edges).sort_values("|Correlation|", ascending=False)
        
        # Build NetworkX Graph for Advanced Topology Metrics
        if NETWORKX_AVAILABLE:
            G = nx.Graph()
            for _, row in edges_df.iterrows():
                G.add_edge(row["Source Node"], row["Target Node"], weight=row["|Correlation|"])
            
            degree_dict = dict(G.degree())
            betweenness_dict = nx.betweenness_centrality(G)
            eigenvector_dict = nx.eigenvector_centrality(G, max_iter=500) if len(G) > 2 else {n: 1.0 for n in G.nodes()}
            
            metrics_df = pd.DataFrame({
                "Variable": list(G.nodes()),
                "Degree": [degree_dict[n] for n in G.nodes()],
                "Betweenness Centrality": [round(betweenness_dict[n], 4) for n in G.nodes()],
                "Eigenvector Centrality": [round(eigenvector_dict[n], 4) for n in G.nodes()]
            }).sort_values("Degree", ascending=False)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Active Network Nodes", len(G.nodes()))
            c2.metric("Connected Edges", len(G.edges()))
            max_possible = len(numeric_cols) * (len(numeric_cols) - 1) / 2
            c3.metric("Network Density", f"{len(G.edges()) / max_possible:.3f}}" if max_possible > 0 else "n/a")
            c4.metric("Avg Clustering Coeff.", f"{nx.average_clustering(G):.3f}}")

            st.markdown("#### Topological Node Centrality Metrics")
            st.dataframe(metrics_df, use_container_width=True, hide_index=True)

            if PLOTLY_AVAILABLE:
                # Layout selection
                if layout_type == "Circular":
                    pos = nx.circular_layout(G)
                elif layout_type == "Kamada-Kawai":
                    pos = nx.kamada_kawai_layout(G)
                else:
                    pos = nx.spring_layout(G, seed=42)

                edge_x, edge_y = [], []
                for edge in G.edges():
                    x0, y0 = pos[edge[0]]
                    x1, y1 = pos[edge[1]]
                    edge_x.extend([x0, x1, None])
                    edge_y.extend([y0, y1, None])

                edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.5, color="#475569"), hoverinfo="none", mode="lines")

                node_x, node_y, node_text, node_size = [], [], [], []
                for node in G.nodes():
                    x, y = pos[node]
                    node_x.append(x)
                    node_y.append(y)
                    node_text.append(f"<b>{node}}</b><br>Degree: {degree_dict[node]}}<br>Betweenness: {betweenness_dict[node]:.3f}}")
                    node_size.append(15 + degree_dict[node] * 5)

                node_trace = go.Scatter(
                    x=node_x, y=node_y, mode="markers+text", text=[n for n in G.nodes()],
                    textposition="top center", hoverinfo="text", hovertext=node_text,
                    marker=dict(showscale=True, colorscale="Viridis", size=node_size,
                                color=[betweenness_dict[n] for n in G.nodes()],
                                colorbar=dict(thickness=15, title="Betweenness", xpad=10))
                )

                fig = go.Figure(data=[edge_trace, node_trace],
                               layout=go.Layout(
                                   title="Correlation Network Graph",
                                   template="plotly_dark",
                                   showlegend=False,
                                   hovermode="closest",
                                   margin=dict(b=20, l=5, r=5, t=40),
                                   xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                   yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                   paper_bgcolor="rgba(0,0,0,0)",
                                   plot_bgcolor="rgba(0,0,0,0)",
                               ))
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Significant Correlation Edges")
        st.dataframe(edges_df, use_container_width=True, hide_index=True)
        render_export_buttons(edges_df, base_name="correlation_network_edges")


# ==============================================================================
# GIS & Spatial Analytics Mapping
# ==============================================================================
@st.cache_data(ttl=3600, show_spinner=False)
def cached_reverse_geocode(lat: float, lon: float):
    if not REQUESTS_AVAILABLE:
        return None, "`requests` package not available in environment."
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json"},
            headers={"User-Agent": "ChrishemProductionPlatform-DomainHub/2.0 (contact@researcher.edu)"},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("display_name"), None
    except Exception as e:
        return None, str(e)


def render_gis():
    section_header("🗺️ GIS & Spatial Analytics Mapping", "Interactive spatial selection with cached reverse-geocoding via OpenStreetMap Nominatim.")

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
            st.success(f"📍 Selected Coordinates: Latitude {lat:.4f}}, Longitude {lon:.4f}}")
            if REQUESTS_AVAILABLE:
                with st.spinner("Reverse-geocoding location..."):
                    place, err = cached_reverse_geocode(round(lat, 4), round(lon, 4))
                if place:
                    st.info(f"📜 **Resolved Location:** {place}}")
                elif err:
                    st.caption(f"Reverse-geocoding notice: {err}}")
    except ImportError:
        st.info("ℹ️ `folium` and `streamlit_folium` packages required for full interactive map rendering. Using high-precision manual coordinate interface:")
        col1, col2 = st.columns(2)
        lat = col1.number_input("Latitude", value=0.3476, format="%.4f", key="gis_lat_prod")
        lon = col2.number_input("Longitude", value=32.5825, format="%.4f", key="gis_lon_prod")
        if st.button("📍 Reverse-Geocode Coordinate", key="gis_manual_geocode_prod"):
            place, err = cached_reverse_geocode(round(lat, 4), round(lon, 4))
            if place:
                st.success(f"📜 {place}}")
            else:
                st.error(f"Geocoding failed: {err}}")


# ==============================================================================
# World Bank Open Data Integration
# ==============================================================================
@st.cache_data(ttl=86400, show_spinner=False)
def _cached_country_list():
    try:
        from modules.world_data_connector import fetch_country_list
        return fetch_country_list()
    except Exception:
        # Fallback dataset if external module fails
        return pd.DataFrame([
            {"name": "Uganda", "iso3": "UGA"},
            {"name": "Kenya", "iso3": "KEN"},
            {"name": "United States", "iso3": "USA"},
            {"name": "United Kingdom", "iso3": "GBR"}
        ])


@st.cache_data(ttl=86400, show_spinner=False)
def _cached_indicator_series(country_iso3: str, indicator_code: str):
    from modules.world_data_connector import fetch_indicator_series
    return fetch_indicator_series([country_iso3], indicator_code)


def render_global_surveillance():
    section_header(
        "🌐 Sector Indicator Monitor (World Bank Open Data API)",
        "Real macroeconomic, health, and environmental indicator data pulled directly from the World "
        "Bank API — covering all ~217 real countries/economies.",
    )

    SECTOR_INDICATORS = {
        "Healthcare & Mortality": {
            "Life Expectancy at Birth": "SP.DYN.LE00.IN",
            "Current Health Expenditure (% of GDP)": "SH.XPD.CHEX.GD.ZS",
            "Under-5 Mortality Rate (per 1,000)": "SH.DYN.MORT",
        },
        "Economic Growth & Trade": {
            "GDP Growth (Annual %)": "NY.GDP.MKTP.KD.ZG",
            "Inflation, Consumer Prices (Annual %)": "FP.CPI.TOTL.ZG",
            "R&D Expenditure (% of GDP)": "GB.XPD.RSDV.GD.ZS",
        },
        "Environment & Energy": {
            "CO2 Emissions (Metric Tons per Capita)": "EN.ATM.CO2E.PC",
            "Renewable Energy Output (% Total)": "EG.FEC.RNEW.ZS",
        }
    }

    if not REQUESTS_AVAILABLE:
        st.error("The `requests` package isn't available in this environment.")
        return

    try:
        country_df = _cached_country_list()
    except Exception as e:
        st.error(f"Could not reach the World Bank API for the country list: {e}}")
        return

    col1, col2 = st.columns(2)
    with col1:
        sector = st.selectbox("Select Strategic Sector Focus", list(SECTOR_INDICATORS.keys()), key="sector_sel_prod")
        indicator_label = st.selectbox("Indicator", list(SECTOR_INDICATORS[sector].keys()), key="sector_ind_prod")
    with col2:
        default_idx = int(country_df.index[country_df["name"] == "Uganda"][0]) if "Uganda" in country_df["name"].values else 0
        country_name = st.selectbox("Country / Economy", country_df["name"].tolist(), index=default_idx, key="sector_country_prod")

    indicator_code = SECTOR_INDICATORS[sector][indicator_label]
    country_iso3 = country_df.loc[country_df["name"] == country_name, "iso3"].iloc[0]

    if st.button("🌐 Fetch Live Sector Indicator Data", type="primary", key="run_sector_intel_prod"):
        with st.spinner(f"Querying World Bank API for {indicator_label}} ({country_name}})..."):
            try:
                series_df = _cached_indicator_series(country_iso3, indicator_code)
            except Exception as e:
                st.error(f"🚫 Live data retrieval failed: {e}}")
                return

        if series_df is None or series_df.empty:
            st.warning("No data points available for this country/indicator combination.")
        else:
            latest = series_df.iloc[-1]
            c1, c2, c3 = st.columns(3)
            c1.metric(indicator_label, f"{latest['value']:.2f}}", delta=f"as of {int(latest['year'])}}")
            c2.metric("Data Points Retrieved", len(series_df))
            c3.metric("Data Source", "World Bank Open Data API")

            if PLOTLY_AVAILABLE:
                fig = px.line(series_df, x="year", y="value", markers=True, template="plotly_dark", height=350,
                              title=f"{indicator_label}} — {country_name}}")
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig, use_container_width=True)

            st.dataframe(series_df, use_container_width=True, hide_index=True)
            render_export_buttons(series_df, base_name=f"worldbank_{indicator_code}}_{country_iso3}}")


# ==============================================================================
# Academic Portfolio & SOP Generators
# ==============================================================================
def _compute_h_index(citation_counts: list) -> int:
    try:
        clean_counts = sorted([int(c) for c in citation_counts if pd.notnull(c) and not np.isnan(c)], reverse=True)
        h = 0
        for i, c in enumerate(clean_counts, 1):
            if c >= i:
                h = i
            else:
                break
        return h
    except Exception:
        return 0


def render_academic():
    section_header("🎓 Academic Portfolio & Grant Management Studio", "Dynamic editable portfolio where citation totals, grant budgets, and h-index are computed directly from your entries.")

    if "academic_pubs_prod" not in st.session_state:
        st.session_state["academic_pubs_prod"] = pd.DataFrame({
            "Title": ["Automated Multi-Omics Pipeline Architecture", "Predictive Biomarker Discovery in Clinical Cohorts"],
            "Venue": ["Journal of Biomedical Informatics", "Nature Communications"],
            "Year": [2024, 2026],
            "Citations": [42, 15],
        })
    if "academic_grants_prod" not in st.session_state:
        st.session_state["academic_grants_prod"] = pd.DataFrame({
            "Grant Title": ["Translational Bioinformatics Grant"],
            "Funder": ["National Science Foundation"],
            "Amount (USD)": [150000.0],
        })

    st.markdown("#### Publications Library")
    pubs = st.data_editor(st.session_state["academic_pubs_prod"], num_rows="dynamic", use_container_width=True, key="pubs_editor_prod")
    st.session_state["academic_pubs_prod"] = pubs

    st.markdown("#### Research Grants")
    grants = st.data_editor(st.session_state["academic_grants_prod"], num_rows="dynamic", use_container_width=True, key="grants_editor_prod")
    st.session_state["academic_grants_prod"] = grants

    valid_pubs = pubs.dropna(subset=["Title"]) if not pubs.empty else pd.DataFrame(columns=["Title", "Venue", "Year", "Citations"])
    citations = valid_pubs["Citations"].dropna().tolist() if "Citations" in valid_pubs.columns else []
    
    total_citations = sum(int(c) for c in citations if pd.notnull(c) and str(c).isdigit()) if citations else 0
    h_index = _compute_h_index(citations)
    
    total_grant_amount = pd.to_numeric(grants["Amount (USD)"], errors="coerce").fillna(0).sum() if "Amount (USD)" in grants.columns and not grants.empty else 0.0

    st.markdown("#### Scholarly Impact Metrics (Computed Live)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Publications", len(valid_pubs))
    c2.metric("Total Citations", total_citations)
    c3.metric("Computed h-Index", h_index)
    c4.metric("Total Grant Funding", f"${total_grant_amount:,.0f}}")

    if not valid_pubs.empty:
        render_export_buttons(valid_pubs, base_name="academic_portfolio_publications")


def render_lab():
    section_header("🧪 Lab Protocol & Methodology Transpiler", "Convert raw experimental notes into standardized, reproducible Standard Operating Procedures (SOPs).")

    st.markdown("#### Laboratory Protocol Authoring Engine")
    protocol_name = st.text_input("Protocol Title", value="High-Throughput PCR & DNA Amplification Protocol", key="lab_name_prod")
    steps = st.text_area("Raw Experimental Steps (one per line)", value="Step 1: Aliquot master mix into PCR strip tubes.\nStep 2: Add template DNA under sterile laminar flow hood.\nStep 3: Execute thermal cycler amplification profile.", key="lab_steps_prod")

    col1, col2 = st.columns(2)
    with col1:
        safety_notes = st.text_input("Safety & Biosafety Level", value="BSL-2 Standard Precautions, PPE Required", key="lab_safety_prod")
    with col2:
        author = st.text_input("Lead Investigator / Author", value="Dr. Chris Kula", key="lab_author_prod")

    if st.button("🧪 Transpile Standard Operating Procedure (SOP)", type="primary", key="run_lab_prod"):
        if protocol_name.strip():
            sop_doc = f"""# STANDARD OPERATING PROCEDURE (SOP)
**Protocol Title:** {protocol_name}
**Lead Investigator:** {author or '[Not specified]'}
**Biosafety Classification:** {safety_notes}
**Timestamp:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

## 1. Objective & Scope
Standardized protocol generated for reproducible laboratory execution and compliance.

## 2. Step-by-Step Procedure
{steps}

## 3. Required Reagents & Equipment
- Thermal Cycler Unit
- Sterile Pipette Tips & Microcentrifuge Tubes
- Taq DNA Polymerase Master Mix

## 4. Safety, Biosafety & Waste Management
- Dispose of all biohazard waste in designated autoclave containers according to institutional protocol.
"""
            st.code(sop_doc, language="markdown")
            st.download_button("⬇️ Download Formatted SOP Document (.md)", data=sop_doc, file_name=f"{protocol_name.lower().replace(' ', '_')}}_sop.md", mime="text/markdown")
        else:
            st.warning("⚠️ Please provide a valid protocol title.")


def render_field_surveillance():
    section_header(
        "🧬 Genomic & Clinical Field Surveillance",
        "Colistin-resistance gene (mcr) surveillance and a postpartum health cohort (PPWR/DRA), backed "
        "by persistent storage.",
    )

    try:
        from modules.legacy_research_data import (
            get_mcr_surveillance_df, add_mcr_sample, get_ppwr_df, add_ppwr_entry,
        )
    except ImportError:
        st.info("ℹ️ Persistent storage module (`modules.legacy_research_data`) is not loaded in this session context.")
        return

    sub_mcr, sub_ppwr = st.tabs(["🦠 mcr Gene Resistance Surveillance", "🤰 PPWR / DRA Clinical Cohort"])

    with sub_mcr:
        gis_df = get_mcr_surveillance_df()
        st.dataframe(gis_df, use_container_width=True, hide_index=True)

        if PLOTLY_AVAILABLE and not gis_df.empty:
            fig = px.scatter_mapbox(
                gis_df, lat="latitude", lon="longitude", color="mcr_variant", size="colistin_mic",
                hover_name="sample_id", hover_data=["sample_type", "source_location", "colistin_mic"],
                zoom=11, height=420, title="mcr Gene Distribution — Arua Region Field Samples",
            )
            fig.update_layout(mapbox_style="carto-darkmatter", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        elif not gis_df.empty:
            st.map(gis_df[["latitude", "longitude"]])

        render_export_buttons(gis_df, base_name="mcr_gene_surveillance")

        with st.expander("➕ Log a new field sample"):
            with st.form("mcr_add_form"):
                c1, c2 = st.columns(2)
                with c1:
                    sample_id = st.text_input("Sample ID (unique)", value="")
                    sample_type = st.text_input("Sample Type", value="Poultry Cecal")
                    source_location = st.text_input("Source Location", value="")
                    isolation_date = st.date_input("Isolation Date", value=datetime.date.today())
                with c2:
                    lat = st.number_input("Latitude", value=3.03, format="%.4f")
                    lon = st.number_input("Longitude", value=30.91, format="%.4f")
                    mcr_variant = st.text_input("mcr Variant (or 'Negative')", value="Negative")
                    colistin_mic = st.number_input("Colistin MIC", value=0.5, min_value=0.0)
                notes = st.text_area("Notes", value="")
                if st.form_submit_button("Add Real Field Sample"):
                    if not sample_id.strip():
                        st.warning("Sample ID is required.")
                    else:
                        try:
                            add_mcr_sample(sample_id.strip(), sample_type, source_location, lat, lon,
                                          mcr_variant, colistin_mic, isolation_date, notes)
                            st.success(f"Sample {sample_id}} recorded.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Could not save (duplicate Sample ID?): {e}}")

    with sub_ppwr:
        ppwr_df = get_ppwr_df()
        col_p1, col_p2 = st.columns([1, 2])

        with col_p1:
            st.markdown("#### ➕ Log Participant Data")
            with st.form("ppwr_add_form"):
                age = st.number_input("Age", 18, 50, 26)
                months = st.number_input("Months Postpartum", 1, 48, 6)
                dra = st.number_input("DRA Gap (cm)", 0.0, 10.0, 2.5)
                ppwr = st.number_input("PPWR (kg)", 0.0, 30.0, 4.5)
                if st.form_submit_button("Record Entry"):
                    add_ppwr_entry(age, months, dra, ppwr)
                    st.success("Entry added.")
                    st.rerun()

        with col_p2:
            st.dataframe(ppwr_df, use_container_width=True, hide_index=True)
            if PLOTLY_AVAILABLE and not ppwr_df.empty:
                fig = px.scatter(
                    ppwr_df, x="dra_gap_cm", y="ppwr_kg", size="months_postpartum", color="participant_age",
                    title="Diastasis Recti Gap (cm) vs Postpartum Weight Retention (kg)",
                )
                fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
            render_export_buttons(ppwr_df, base_name="ppwr_cohort")


# ==============================================================================
# Main Execution Orchestrator
# ==============================================================================
def main():
    try:
        from modules.subscription import require_active_subscription
        require_active_subscription(hub_id="domain")
    except ImportError:
        pass

    setup_page("Domain Analytics Hub", "🔬", initial_sidebar_state="expanded")

    try:
        from modules.user_preferences import render_readability_fix, render_accent_color_css
        render_readability_fix()
        render_accent_color_css()
    except ImportError:
        pass

    hero_card(
        "🔬 Domain & Specialized Analytics Hub — Production Suite",
        "Consolidated domain hub featuring robust biometric screening, correlation-driven network analytics, cached GIS reverse-geocoding, live World Bank sector data, and an editable academic portfolio.",
        badge_text="DOMAIN ANALYTICS HUB • PRODUCTION TIER",
    )

    render_dataset_context_banner()

    df = get_active_dataframe()

    tabs = st.tabs([
        "🏥 Clinical & Biometric",
        "🔗 Network Analysis",
        "🗺️ GIS & Spatial",
        "🌐 Sector Indicators",
        "🎓 Academic Portfolio",
        "🧪 Lab Protocols",
        "🧬 Field Surveillance (mcr/PPWR)",
    ])

    with tabs[0]:
        render_clinical(df)
    with tabs[1]:
        render_network(df)
    with tabs[2]:
        render_gis()
    with tabs[3]:
        render_global_surveillance()
    with tabs[4]:
        render_academic()
    with tabs[5]:
        render_lab()
    with tabs[6]:
        render_field_surveillance()

    render_standard_footer("DOMAIN ANALYTICS HUB")


if __name__ == "__main__":
    main()
