"""
🔬 Domain & Specialized Analytics Hub — Consolidated Specialized Analytics Hub (Premium)
Clinical & biometric calculators with an honestly-labeled risk score, a network analysis engine
derived from real correlations in your active dataset, GIS mapping with real reverse-geocoding,
sector data from the real World Bank Open Data API, and a genuine editable academic portfolio
with a computed h-index.

Changelog vs prior version — several of these were either fabricated data or mislabeled formulas,
which matters more here than most hubs since this one touches clinical and research contexts:
- FIXED (patient-safety issue): the "10-Year ASCVD Risk Estimator" used a made-up linear formula
  (`4.2 + (sbp-120)*0.08 + ...`) and presented the output as if it were the validated 2013 ACC/AHA
  Pooled Cohort Equations — it wasn't, and it never collected the HDL cholesterol or race inputs
  that equation actually requires. Rather than hardcoding a real clinical risk equation from
  memory (verifying the exact race/sex-specific coefficients to the precision a clinical tool
  needs isn't something to guess at), this has been renamed to an honestly-labeled "Illustrative
  Cardiovascular Risk Factor Score" — a transparent, non-clinical point-based screening heuristic
  — with a prominent disclaimer and a direct link to the real ACC/AHA ASCVD Risk Estimator Plus
  tool for actual clinical use.
- FIXED (mislabeled): "Body Surface Area (DuBois Formula)" actually computed the Mosteller
  formula (`sqrt((height×weight)/3600)`), not DuBois's. Label corrected.
- FIXED (was fake): "Network & Knowledge Graph Analytics" generated a fully random graph with
  `np.random.randint` node connections and called it "network analysis" — the edges meant
  nothing. It now builds a real correlation network from the numeric columns of your active
  dataset (edges = variable pairs above a correlation threshold you set), with genuine degree
  centrality computed from those real edges. If no dataset is loaded, it says so rather than
  showing a fake demo graph.
- ADDED: GIS tab now does real reverse-geocoding (via OpenStreetMap Nominatim, free/no key) on
  the coordinate you click, showing an actual place name instead of just raw lat/lon.
- FIXED (was fake): "Global Surveillance & Sector Impact Monitor" showed hardcoded fictional
  numbers ("48 Satellites", "Systemic Risk Index: 0.012") that never changed regardless of sector
  selection. It now pulls real indicator data for a country you choose from the World Bank Open
  Data API (free, no key) — actual health expenditure, electricity access, CO2 emissions, etc.,
  with a real historical trend chart.
- FIXED (was fake/generic): "Academic Portfolio" showed the same hardcoded fictional publications
  and citation counts to every user regardless of who they are. It's now an editable table where
  you enter your own publications and grants — citation totals, grant totals, and a genuinely
  computed h-index are all derived from what you actually enter, not fixed placeholder numbers.
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

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


def render_clinical(df):
    section_header("🏥 Clinical, Biometric & Cardiovascular Screening Studio", "Batch biometric screening, anthropometric calculations, and an honestly-labeled (non-clinical) cardiovascular risk factor score.")

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
        bsa_mosteller = np.sqrt((height * weight) / 3600)
        c1, c2, c3 = st.columns(3)
        c1.metric("Body Mass Index (BMI)", f"{bmi:.1f}", delta="Normal" if 18.5 <= bmi < 25 else "Check Range")
        c2.metric("Waist-Hip Ratio (WHR)", f"{whr:.2f}", delta="Optimal" if whr < 0.9 else "Elevated Risk")
        c3.metric("Body Surface Area (Mosteller)", f"{bsa_mosteller:.2f} m²", delta="√((cm·kg)/3600)")

    st.markdown("#### Illustrative Cardiovascular Risk Factor Score")
    st.warning(
        "⚠️ **This is NOT the validated ACC/AHA Pooled Cohort Equations and does not produce a real clinical ASCVD risk percentage.** "
        "It's a transparent, additive screening heuristic based on common risk factors, intended for illustration only. "
        "For an actual validated 10-year ASCVD risk estimate, use the official "
        "[ACC/AHA ASCVD Risk Estimator Plus](https://tools.acc.org/ascvd-risk-estimator-plus/) or consult a clinician."
    )
    col_a, col_b = st.columns(2)
    with col_a:
        sbp = st.slider("Systolic Blood Pressure (mmHg)", 70, 250, 125, key="cli_sbp_upg")
        chol = st.slider("Total Serum Cholesterol (mg/dL)", 100, 400, 210, key="cli_chol_upg")
        age = st.slider("Age (years)", 20, 90, 50, key="cli_age_upg")
    with col_b:
        smoker = st.checkbox("Current Tobacco Smoker", key="cli_smoker_upg")
        diabetic = st.checkbox("Diagnosed Diabetic Condition", key="cli_diab_upg")
        htn_treated = st.checkbox("On Blood Pressure Medication", key="cli_htn_upg")

    if st.button("📋 Compute Illustrative Risk Factor Score", type="primary", key="run_cvd_upg"):
        # Transparent additive point score — every term and its weight is visible here, no hidden "validated" claim.
        points = 0
        points += max(0, (age - 40)) * 0.5
        points += max(0, (sbp - 120)) * (0.3 if htn_treated else 0.2)
        points += max(0, (chol - 200)) * 0.15
        points += 15 if smoker else 0
        points += 12 if diabetic else 0
        score = min(100, points)

        st.metric("Illustrative Risk Factor Score", f"{score:.1f} / 100")
        if score < 20:
            st.success("🟢 Low illustrative risk-factor burden")
        elif score < 45:
            st.warning("🟡 Moderate illustrative risk-factor burden")
        else:
            st.error("🔴 High illustrative risk-factor burden — this score is not diagnostic; discuss real risk factors with a clinician.")
        st.caption("Score composition: age contributes 0.5 pts/year over 40; SBP contributes 0.2–0.3 pts/mmHg over 120 (higher weight if untreated); cholesterol contributes 0.15 pts/mg·dL over 200; smoking +15; diabetes +12. Capped at 100.")


def render_network(df):
    section_header("🔗 Network Analytics — Correlation Graph from Your Active Dataset", "Builds a real network from the numeric relationships in your loaded data — not a randomly generated demo graph.")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist() if df is not None else []

    if df is None or len(numeric_cols) < 2:
        st.info("ℹ️ Load a dataset with at least 2 numeric columns (via Data Studio) to build a real correlation network. A synthetic random graph wouldn't reflect anything about actual data, so none is shown here.")
        return

    threshold = st.slider("Correlation threshold for an edge (|r| ≥)", 0.1, 0.9, 0.4, 0.05, key="net_thresh")

    if st.button("🌐 Build Correlation Network", type="primary", key="run_network_upg"):
        corr = df[numeric_cols].corr().abs()
        edges = []
        for i, c1 in enumerate(numeric_cols):
            for c2 in numeric_cols[i + 1:]:
                r = corr.loc[c1, c2]
                if pd.notnull(r) and r >= threshold:
                    edges.append({"Source Node": c1, "Target Node": c2, "|Correlation|": round(float(r), 3)})

        if not edges:
            st.info(f"No variable pairs exceed |r| ≥ {threshold} — try lowering the threshold.")
            return

        edges_df = pd.DataFrame(edges).sort_values("|Correlation|", ascending=False)
        st.dataframe(edges_df, use_container_width=True, hide_index=True)

        degree = pd.Series(edges_df["Source Node"].tolist() + edges_df["Target Node"].tolist()).value_counts()
        c1, c2, c3 = st.columns(3)
        c1.metric("Active Nodes (Variables)", len(numeric_cols))
        c2.metric("Edges (above threshold)", len(edges_df))
        max_possible = len(numeric_cols) * (len(numeric_cols) - 1) / 2
        c3.metric("Network Density", f"{len(edges_df) / max_possible:.3f}" if max_possible else "n/a")

        if PLOTLY_AVAILABLE:
            deg_df = degree.reset_index()
            deg_df.columns = ["Variable", "Degree (Connections)"]
            fig = px.bar(deg_df, x="Variable", y="Degree (Connections)", template="plotly_dark", height=320, title="Real Degree Centrality (from correlation graph)")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

        render_export_buttons(edges_df, base_name="correlation_network_edges")


def reverse_geocode(lat: float, lon: float):
    if not REQUESTS_AVAILABLE:
        return None, "`requests` package not available."
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json"},
            headers={"User-Agent": "ChrishemPlatform-DomainAnalyticsHub/1.0"},
            timeout=6,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("display_name"), None
    except Exception as e:
        return None, str(e)


def render_gis():
    section_header("🗺️ GIS & Spatial Analytics Mapping", "Interactive coordinate selection with real reverse-geocoding (OpenStreetMap Nominatim) — no fabricated place data.")

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
            if REQUESTS_AVAILABLE:
                with st.spinner("Reverse-geocoding via OpenStreetMap..."):
                    place, err = reverse_geocode(lat, lon)
                if place:
                    st.info(f"📌 **Location:** {place}")
                elif err:
                    st.caption(f"Reverse-geocoding unavailable: {err}")
    except ImportError:
        st.info("`folium` and `streamlit_folium` libraries required for interactive spatial maps.")
        col1, col2 = st.columns(2)
        lat = col1.number_input("Latitude Coordinate", value=0.3476, key="gis_lat_upg")
        lon = col2.number_input("Longitude Coordinate", value=32.5825, key="gis_lon_upg")
        if st.button("📍 Reverse-Geocode This Coordinate", key="gis_manual_geocode"):
            place, err = reverse_geocode(lat, lon)
            if place:
                st.success(f"📌 {place}")
            else:
                st.error(f"Reverse-geocoding failed: {err}")


# ══════════════════════════════════════════════════════════════════════
# Real World Bank Open Data — replaces fabricated "satellite telemetry"
# ══════════════════════════════════════════════════════════════════════
SECTOR_INDICATORS = {
    "Agriculture & Food Security Systems": ("AG.LND.AGRI.ZS", "Agricultural land (% of land area)"),
    "Healthcare & Epidemiological Surveillance": ("SH.XPD.CHEX.GD.ZS", "Current health expenditure (% of GDP)"),
    "Energy Infrastructure & Power Grids": ("EG.ELC.ACCS.ZS", "Access to electricity (% of population)"),
    "Global Financial & Banking Systems": ("FS.AST.PRVT.GD.ZS", "Domestic credit to private sector (% of GDP)"),
    "Environmental Conservation & Climate Telemetry": ("EN.ATM.CO2E.PC", "CO2 emissions (metric tons per capita)"),
}
COMMON_COUNTRIES = {
    "Uganda": "UG", "Kenya": "KE", "Nigeria": "NG", "United States": "US", "United Kingdom": "GB",
    "India": "IN", "Brazil": "BR", "South Africa": "ZA", "Germany": "DE", "China": "CN",
}


def fetch_worldbank_series(country_code: str, indicator_code: str):
    if not REQUESTS_AVAILABLE:
        return None, "`requests` package not available."
    try:
        url = f"https://api.worldbank.org/v2/country/{country_code}/indicator/{indicator_code}"
        resp = requests.get(url, params={"format": "json", "per_page": 20}, timeout=8)
        resp.raise_for_status()
        payload = resp.json()
        if len(payload) < 2 or not payload[1]:
            return None, "No data returned for this country/indicator combination."
        records = [{"Year": int(r["date"]), "Value": r["value"]} for r in payload[1] if r["value"] is not None]
        if not records:
            return None, "Indicator has no non-null values for this country."
        return pd.DataFrame(records).sort_values("Year"), None
    except Exception as e:
        return None, str(e)


def render_global_surveillance():
    section_header("🌍 Sector Indicator Monitor (World Bank Open Data)", "Real economic/health/environmental indicator data — replaces the previous hardcoded 'satellite telemetry' numbers.")

    col1, col2 = st.columns(2)
    with col1:
        sector = st.selectbox("Select Strategic Sector Focus", list(SECTOR_INDICATORS.keys()), key="sector_sel_upg")
    with col2:
        country_name = st.selectbox("Country", list(COMMON_COUNTRIES.keys()), key="sector_country_upg")

    indicator_code, indicator_label = SECTOR_INDICATORS[sector]
    country_code = COMMON_COUNTRIES[country_name]

    if st.button("🌍 Fetch Real Sector Indicator Data", type="primary", key="run_sector_intel_upg"):
        with st.spinner(f"Querying World Bank Open Data for {indicator_label} ({country_name})..."):
            series_df, error = fetch_worldbank_series(country_code, indicator_code)

        if error:
            st.error(f"🚫 Live data unavailable: {error}")
        else:
            latest = series_df.iloc[-1]
            c1, c2, c3 = st.columns(3)
            c1.metric(indicator_label, f"{latest['Value']:.2f}", delta=f"as of {int(latest['Year'])}")
            c2.metric("Years of Data Retrieved", len(series_df))
            c3.metric("Source", "World Bank Open Data")

            if PLOTLY_AVAILABLE:
                fig = px.line(series_df, x="Year", y="Value", markers=True, template="plotly_dark", height=350, title=f"{indicator_label} — {country_name}")
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig, use_container_width=True)

            st.dataframe(series_df, use_container_width=True, hide_index=True)
            render_export_buttons(series_df, base_name=f"worldbank_{indicator_code}_{country_code}")


def _compute_h_index(citation_counts: list) -> int:
    counts_sorted = sorted([c for c in citation_counts if pd.notnull(c)], reverse=True)
    h = 0
    for i, c in enumerate(counts_sorted, 1):
        if c >= i:
            h = i
        else:
            break
    return h


def render_academic():
    section_header("🎓 Academic Portfolio & Grant Management Studio", "Enter your own publications and grants — every summary metric below (including h-index) is computed from what you actually enter, not placeholder data.")

    if "academic_pubs" not in st.session_state:
        st.session_state["academic_pubs"] = pd.DataFrame({
            "Title": pd.Series(dtype="str"), "Venue": pd.Series(dtype="str"),
            "Year": pd.Series(dtype="Int64"), "Citations": pd.Series(dtype="Int64"),
        })
    if "academic_grants" not in st.session_state:
        st.session_state["academic_grants"] = pd.DataFrame({
            "Grant Title": pd.Series(dtype="str"), "Funder": pd.Series(dtype="str"), "Amount (USD)": pd.Series(dtype="float"),
        })

    st.markdown("#### Your Publications")
    pubs = st.data_editor(st.session_state["academic_pubs"], num_rows="dynamic", use_container_width=True, key="pubs_editor")
    st.session_state["academic_pubs"] = pubs

    st.markdown("#### Your Grants")
    grants = st.data_editor(st.session_state["academic_grants"], num_rows="dynamic", use_container_width=True, key="grants_editor")
    st.session_state["academic_grants"] = grants

    valid_pubs = pubs.dropna(subset=["Title"])
    citations = valid_pubs["Citations"].dropna().tolist() if "Citations" in valid_pubs else []
    total_citations = sum(c for c in citations if pd.notnull(c))
    h_index = _compute_h_index(citations)
    total_grant_amount = grants["Amount (USD)"].dropna().sum() if "Amount (USD)" in grants else 0

    st.markdown("#### Scholarly Impact Metrics (computed from your entries above)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Publications", len(valid_pubs))
    c2.metric("Total Citations", int(total_citations))
    c3.metric("h-Index (computed)", h_index)
    c4.metric("Total Grant Funding", f"${total_grant_amount:,.0f}")

    if len(valid_pubs):
        render_export_buttons(valid_pubs, base_name="academic_portfolio_publications")


def render_lab():
    section_header("🧪 Lab Protocol & Methodology Transpiler", "Convert raw laboratory experimental notes into standardized, reproducible Standard Operating Procedures (SOPs).")

    st.markdown("#### Laboratory Protocol Authoring Engine")
    protocol_name = st.text_input("Protocol Title", value="High-Throughput PCR & DNA Amplification", key="lab_name_upg")
    steps = st.text_area("Raw Experimental Steps (one per line)", value="Step 1: Aliquot master mix into PCR tubes.\nStep 2: Add template DNA under sterile laminar hood.\nStep 3: Run thermal cycler amplification profile.", key="lab_steps_upg")

    col1, col2 = st.columns(2)
    with col1:
        safety_notes = st.text_input("Safety & Biosafety Level", value="BSL-2 Standard Precautions, PPE Required", key="lab_safety_upg")
    with col2:
        author = st.text_input("Lead Investigator / Author", value="", key="lab_author_upg")

    if st.button("🧪 Transpile Standard Operating Procedure (SOP)", type="primary", key="run_lab_upg"):
        if protocol_name.strip():
            sop_doc = f"""# STANDARD OPERATING PROCEDURE (SOP)
**Protocol Title:** {protocol_name}
**Lead Investigator:** {author or '[Not specified]'}
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
        "🔬 Domain & Specialized Analytics Hub — Premium Edition",
        "Consolidated domain hub featuring clinical biometric calculators with honest risk-score labeling, real correlation-derived network analytics, GIS mapping with real reverse-geocoding, live World Bank sector data, and a genuine editable academic portfolio.",
        badge_text="DOMAIN ANALYTICS HUB • PREMIUM SUITE",
    )

    render_dataset_context_banner()

    df = get_active_dataframe()

    tabs = st.tabs([
        "🏥 Clinical & Biometric",
        "🔗 Network Analysis",
        "🗺️ GIS & Spatial",
        "🌍 Sector Indicators",
        "🎓 Academic Portfolio",
        "🧪 Lab Protocols",
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

    render_standard_footer("DOMAIN ANALYTICS HUB")


if __name__ == "__main__":
    main()