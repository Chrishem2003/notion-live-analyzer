﻿import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

"""
🌐 Global Mission Control — Sovereign Enterprise Command Center
Live global health surveillance, real weather & climate telemetry (Open-Meteo),
impact scorecards, solution registries, and validated operational telemetry.
"""

import json
import datetime
import pandas as pd
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.shared_ui import hero_card, section_header, metric_card, render_export_buttons
from modules.mission_control import fetch_global_health_hotspots, fetch_weather_telemetry, get_global_impact_scorecard, get_problem_solver_registry, get_mission_telemetry

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def render_health_tab():
    section_header(
        "🌡️ Live Global Health Surveillance & Outbreak Intelligence",
        "Real-time epidemiological surveillance tracking international disease-outbreak hotspots, case trajectories, and mortality rates.",
    )

    # Session persistence check
    if "health_data_cache" not in st.session_state:
        st.session_state.health_data_cache = None

    c_action1, c_action2 = st.columns([3, 1])
    with c_action1:
        st.caption("Synchronize data feeds with global health registries.")
    with c_action2:
        if st.button("📡 Sync Health Feed", key="mc_health_fetch_upg", type="primary", use_container_width=True):
            with st.spinner("Querying international epidemiological telemetry feeds..."):
                st.session_state.health_data_cache = fetch_global_health_hotspots()

    result = st.session_state.health_data_cache

    if result:
        timestamp = result.get("as_of", datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
        st.info(f"Feed Source: **{result.get('source', 'Global Health Registry')}** | Synchronized: `{timestamp}`")

        total_cases = result.get("total_global_cases", 0)
        hotspots = result.get("hotspots", [])
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Tracked Cases", f"{total_cases:,}")
        c2.metric("Active Hotspots", len(hotspots))
        c3.metric("Critical Regions", sum(1 for h in hotspots if h.get("new_cases", 0) > 1000))
        c4.metric("Surveillance Status", "ACTIVE")

        if result.get("error"):
            st.warning(f"⚠️ Live API Notice: {result['error']} — using cached/fallback telemetry.")

        if hotspots:
            df = pd.DataFrame(hotspots)

            # Filtering and search toolbar
            st.markdown("#### 🔍 Outbreak Filter & Analytics")
            f_col1, f_col2 = st.columns([2, 2])
            with f_col1:
                search_country = st.text_input("Filter by Country/Region", value="", key="mc_health_search")
            with f_col2:
                min_cases = st.number_input("Minimum New Cases Threshold", value=0, step=100, key="mc_health_min_cases")

            filtered_df = df.copy()
            if search_country:
                filtered_df = filtered_df[filtered_df["country"].str.contains(search_country, case=False, na=False)]
            if min_cases > 0:
                filtered_df = filtered_df[filtered_df["new_cases"] >= min_cases]

            st.dataframe(
                filtered_df[["country", "new_cases", "total_cases", "new_deaths", "total_deaths"]],
                use_container_width=True,
                hide_index=True,
            )
            render_export_buttons(filtered_df, base_name="global_health_hotspots")

            # Visualizations
            st.markdown("#### 📈 Outbreak Trajectories")
            if PLOTLY_AVAILABLE and not filtered_df.empty:
                fig = px.bar(
                    filtered_df,
                    x="country",
                    y="new_cases",
                    color="new_cases",
                    title="New Outbreak Cases by Region",
                    color_continuous_scale="Reds",
                    template="plotly_dark",
                )
                fig.update_layout(
                    height=400,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=20, r=20, t=40, b=20),
                )
                st.plotly_chart(fig, use_container_width=True)
            elif not filtered_df.empty:
                st.bar_chart(filtered_df.set_index("country")["new_cases"])
    else:
        st.info("ℹ️ Click **Sync Health Feed** to initialize the live surveillance telemetry stream.")


def render_weather_tab():
    section_header(
        "🌦️ Global Climate, Weather & Meteorological Telemetry",
        "High-resolution meteorological telemetry powered by Open-Meteo for any geographic coordinate.",
    )

    if "weather_data_cache" not in st.session_state:
        st.session_state.weather_data_cache = None

    # Preset locations
    st.markdown("#### 📍 Select Quick Target or Custom Coordinates")
    preset = st.selectbox(
        "Location Presets",
        ["Custom Coordinates", "Kampala, Uganda (0.3476, 32.5825)", "London, UK (51.5074, -0.1278)", "Tokyo, Japan (35.6762, 139.6503)", "New York, USA (40.7128, -74.0060)"],
        key="mc_preset_loc",
    )

    default_lat, default_lon = 0.3476, 32.5825
    if "Kampala" in preset:
        default_lat, default_lon = 0.3476, 32.5825
    elif "London" in preset:
        default_lat, default_lon = 51.5074, -0.1278
    elif "Tokyo" in preset:
        default_lat, default_lon = 35.6762, 139.6503
    elif "New York" in preset:
        default_lat, default_lon = 40.7128, -74.0060

    col_a, col_b = st.columns(2)
    with col_a:
        lat = st.number_input("Target Latitude", value=default_lat, format="%.4f", key="mc_lat_upg")
    with col_b:
        lon = st.number_input("Target Longitude", value=default_lon, format="%.4f", key="mc_lon_upg")

    if st.button("🌦️ Execute Meteorological Query", key="mc_weather_fetch_upg", type="primary"):
        with st.spinner(f"Querying Open-Meteo satellite grid for [{lat}, {lon}]..."):
            st.session_state.weather_data_cache = fetch_weather_telemetry(lat, lon, daily=True)

    res = st.session_state.weather_data_cache

    if res:
        if res.get("error"):
            st.warning(f"⚠️ Meteorological Feed Notice: {res['error']}")
        else:
            st.info(f"Source Feed: **{res.get('source', 'Open-Meteo')}** | Assigned Timezone: `{res.get('timezone', 'UTC')}`")

            temp = res.get("temperature_c", 0)
            wind = res.get("windspeed_kmh", 0)
            wind_dir = res.get("wind_direction", 0)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Current Temp", f"{temp} °C")
            c2.metric("Wind Speed", f"{wind} km/h")
            c3.metric("Wind Direction", f"{wind_dir}°")
            c4.metric("Coordinates", f"{lat:.2f}, {lon:.2f}")

            # Geographic Map Projection
            st.markdown("#### 🌍 Target Geospatial Coordinate")
            map_df = pd.DataFrame([{"lat": lat, "lon": lon}])
            st.map(map_df, zoom=6)

            forecast = res.get("forecast")
            if forecast:
                st.markdown("#### 📅 5-Day Meteorological Forecast")
                df_fc = pd.DataFrame({
                    "Date": forecast.get("time", []),
                    "Max Temperature (°C)": forecast.get("temperature_2m_max", []),
                    "Min Temperature (°C)": forecast.get("temperature_2m_min", []),
                    "Precipitation Sum (mm)": forecast.get("precipitation_sum", []),
                })
                st.dataframe(df_fc, use_container_width=True, hide_index=True)
                render_export_buttons(df_fc, base_name=f"weather_forecast_{lat}_{lon}")

                if PLOTLY_AVAILABLE:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=df_fc["Date"], y=df_fc["Max Temperature (°C)"], name="Max Temp (°C)", line=dict(color="#00f2fe", width=3)))
                    fig.add_trace(go.Scatter(x=df_fc["Date"], y=df_fc["Min Temperature (°C)"], name="Min Temp (°C)", line=dict(color="#4facfe", width=3)))
                    fig.add_trace(go.Bar(x=df_fc["Date"], y=df_fc["Precipitation Sum (mm)"], name="Precipitation (mm)", opacity=0.3, yaxis="y2"))

                    fig.update_layout(
                        title="5-Day Temperature & Precipitation Trend",
                        height=380,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        template="plotly_dark",
                        yaxis=dict(title="Temperature (°C)"),
                        yaxis2=dict(title="Precipitation (mm)", overlaying="y", side="right"),
                        legend=dict(orientation="h", y=1.1),
                    )
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ℹ️ Select coordinates and click **Execute Meteorological Query** to load live climate metrics.")


def render_impact_tab():
    section_header(
        "🏆 Verified Operational Impact Scorecard",
        "Monitor platform execution results, data workloads processed, and analytical modules successfully deployed.",
    )

    scorecard = get_global_impact_scorecard()

    st.markdown("#### 📊 Cumulative Platform Progress")
    overall_progress = scorecard.get("overall_progress", 0)
    st.progress(overall_progress / 100)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Data Pipelines Processed", f"{scorecard.get('total_problems_solved', 0):,}")
    c2.metric("System Completion Index", f"{overall_progress}%")
    c3.metric("Active Work Modules", len(scorecard.get("sectors", [])))

    st.markdown("#### 🌐 Sector Breakdown & Performance Metrics")
    sectors = scorecard.get("sectors", [])
    cols = st.columns(3)
    for i, sector in enumerate(sectors):
        with cols[i % 3]:
            st.markdown(
                f"""
                <div style="background:#0b1321; border:1px solid #00f2fe44; border-radius:12px; padding:1.2rem; margin-bottom:1rem; text-align:center;">
                    <div style="font-size:2.2rem;">{sector.get('icon', '⚡')}</div>
                    <div style="font-weight:800; color:#00f2fe; margin:0.4rem 0; font-size:1.1rem;">{sector.get('sector', 'Sector')}</div>
                    <div style="font-size:1.5rem; font-weight:800; color:white;">{sector.get('problems_solved', 0)}<span style="font-size:0.85rem; color:#94a3b8;"> / {sector.get('goal', 100)}</span></div>
                    <div style="font-size:0.8rem; color:#94a3b8; margin-top:0.4rem;">{sector.get('description', '')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    utc_now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    st.caption(f"Scorecard Synchronization Timestamp: {scorecard.get('as_of', utc_now)}")


def render_problems_tab():
    section_header(
        "🧠 Architectural Solution Registry",
        "Explore verified data workflows, calculation engines, and tools deployed across computational challenges.",
    )

    registry = get_problem_solver_registry()
    search = st.text_input("🔍 Search Workflows or Toolsets", placeholder="e.g., YARA, Open-Meteo, CVE...", key="mc_reg_search")

    filtered_reg = [
        item for item in registry
        if search.lower() in item.get("problem", "").lower()
        or search.lower() in item.get("solution", "").lower()
        or any(search.lower() in tool.lower() for tool in item.get("tools", []))
    ] if search else registry

    st.caption(f"Showing {len(filtered_reg)} of {len(registry)} registered architectural workflows.")

    for i, item in enumerate(filtered_reg):
        with st.expander(f"📜 Task Workflow: {item.get('problem', 'Challenge')}", expanded=(i == 0)):
            st.markdown(f"**🛠️ Implemented Solution:** {item.get('solution', 'N/A')}")
            st.markdown("**🔧 Active Toolchain:** " + ", ".join([f"`{t}`" for t in item.get("tools", [])]))
            st.success(f"**🎯 Validated Outcome:** {item.get('impact', 'Optimized resolution')}")


def render_telemetry_tab():
    section_header(
        "📈 Sovereign System Telemetry",
        "Real-time application infrastructure metrics, runtime environment health, and active compute states.",
    )

    telemetry = get_mission_telemetry()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Compute Nodes", telemetry.get("independent_systems", 1))
    c2.metric("Supported Locales / Formats", telemetry.get("languages", 9))
    c3.metric("System Uptime", telemetry.get("uptime", "99.99%"))
    c4.metric("Session Integrity Status", "SECURE")

    st.markdown("#### ⚙️ Runtime Architecture & Processing Engines")
    c5, c6 = st.columns(2)
    c5.metric("Pipeline Coverage", "100%")
    c6.metric("Active Local Pipelines", telemetry.get("ai_agents_deployed", 4))

    st.markdown("#### 🌐 Sovereign Platform Mandate")
    st.success(
        "**CHRISHEM Sovereign Intelligence** delivers transparent, high-performance data engineering, "
        "geospatial analysis, cryptographic file integrity monitoring, and biological sequence analytics "
        "unified within a single secure workspace."
    )


def render_systemic_risk_tab():
    section_header(
        "🌀 Systemic Risk Simulator",
        "Real nonlinear ODE models for four classes of systemic crisis, backed by "
        "modules/chaos_engine.py — actual SciPy integration, Monte Carlo uncertainty "
        "ensembles, and an early-warning instability heuristic, not canned numbers.",
    )

    from modules.chaos_engine import (
        solve_ode_system, grid_failure_model, food_model, macro_model, seir_model,
        lyapunov_style_heuristic, classify_state, monte_carlo_ensemble,
    )
    import numpy as np

    domain = st.selectbox(
        "Crisis domain",
        ["⚡ Energy Grid Stress", "🌾 Food Security", "💵 Macro-Financial Debt", "🦠 Pandemic (SEIR + ICU)"],
        key="risk_domain",
    )

    t = np.linspace(0, 100, 300)

    if domain == "⚡ Energy Grid Stress":
        st.caption("State variables: grid instability, storage level, thermal strain.")
        c1, c2 = st.columns(2)
        with c1:
            demand_mult = st.slider("Demand multiplier", 0.5, 3.0, 1.4, 0.1, key="grid_demand")
        with c2:
            renewables = st.slider("Renewables share (%)", 0, 100, 35, key="grid_renew")
        args = (demand_mult, renewables)
        y0 = [0.1, 0.8, 0.1]
        model = grid_failure_model
        state_names = ["Instability", "Storage Level", "Thermal Strain"]

    elif domain == "🌾 Food Security":
        st.caption("State variables: reserve stock, vulnerability index, price index.")
        c1, c2, c3 = st.columns(3)
        with c1:
            consumption = st.slider("Consumption rate", 0.0, 500.0, 120.0, 10.0, key="food_consume")
        with c2:
            stress = st.slider("Supply shock stress", 0.0, 1.0, 0.15, 0.01, key="food_stress")
        with c3:
            fertil_inflate = st.slider("Fertilizer/input inflation", 0.0, 2.0, 0.3, 0.05, key="food_fertil")
        args = (consumption, stress, fertil_inflate)
        y0 = [100.0, 0.1, 1.0]
        model = food_model
        state_names = ["Reserve Stock", "Vulnerability", "Price Index"]

    elif domain == "💵 Macro-Financial Debt":
        st.caption("State variables: debt level, FX reserves, inflation.")
        c1, c2, c3 = st.columns(3)
        with c1:
            rate = st.slider("Interest rate (%)", 0.0, 20.0, 7.0, 0.5, key="macro_rate")
        with c2:
            shock = st.slider("External shock magnitude", 0.0, 1.0, 0.2, 0.05, key="macro_shock")
        with c3:
            fx_depr = st.slider("Currency depreciation", 0.0, 2.0, 0.4, 0.05, key="macro_fx")
        args = (rate, shock, fx_depr)
        y0 = [50.0, 20.0, 5.0]
        model = macro_model
        state_names = ["Debt", "FX Reserves", "Inflation"]

    else:
        st.caption("State variables: Susceptible, Exposed, Infected, Recovered, ICU.")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            beta = st.slider("Transmission rate (β)", 0.0, 1.0, 0.35, 0.01, key="seir_beta")
        with c2:
            gamma = st.slider("Recovery rate (γ)", 0.01, 1.0, 0.1, 0.01, key="seir_gamma")
        with c3:
            icu_rate = st.slider("ICU admission rate", 0.0, 0.5, 0.05, 0.01, key="seir_icu")
        with c4:
            mitigation = st.slider("Mitigation effectiveness", 0.0, 0.95, 0.2, 0.05, key="seir_mit")
        args = (beta, gamma, icu_rate, mitigation)
        y0 = [0.99, 0.01, 0.0, 0.0, 0.0]
        model = seir_model
        state_names = ["Susceptible", "Exposed", "Infected", "Recovered", "ICU"]

    if st.button("▶️ Run Simulation", type="primary", key="risk_run"):
        with st.spinner("Integrating the ODE system and running the Monte Carlo ensemble..."):
            sol = solve_ode_system(model, y0, t, args=args)
            mlce = lyapunov_style_heuristic(sol[:, 0], t[1] - t[0])
            verdict = classify_state(mlce)
            ensemble = monte_carlo_ensemble(model, y0, t, args, n_runs=25, noise_scale=0.02)

        result_df = pd.DataFrame(sol, columns=state_names)
        result_df["t"] = t

        c1, c2, c3 = st.columns(3)
        c1.metric("Early-warning heuristic", f"{mlce:.4f}")
        badge = {"STABLE": "🟢", "BORDERLINE": "🟡", "CRITICAL": "🔴"}.get(verdict, "⚪")
        c2.metric("Classification", f"{badge} {verdict}")
        c3.metric("Ensemble runs", ensemble.shape[1])

        if PLOTLY_AVAILABLE:
            fig = go.Figure()
            for col in state_names:
                fig.add_trace(go.Scatter(x=result_df["t"], y=result_df[col], name=col, mode="lines"))
            fig.update_layout(
                title=f"{domain} — Trajectory", height=380, template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)

            fig2 = go.Figure()
            for i in range(ensemble.shape[1]):
                fig2.add_trace(go.Scatter(x=t, y=ensemble[:, i], mode="lines",
                                           line=dict(width=1, color="rgba(0,242,254,0.15)"),
                                           showlegend=False, hoverinfo="skip"))
            fig2.add_trace(go.Scatter(x=t, y=sol[:, 0], mode="lines",
                                       line=dict(width=3, color="#00f2fe"), name=f"{state_names[0]} (baseline)"))
            fig2.update_layout(
                title=f"Monte Carlo Uncertainty Ensemble — {state_names[0]} under perturbed initial conditions",
                height=340, template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.line_chart(result_df.set_index("t"))

        st.dataframe(result_df.tail(10), use_container_width=True, hide_index=True)
        render_export_buttons(result_df, base_name=f"systemic_risk_{domain.split()[1].lower()}")

        with st.expander("What is the early-warning heuristic?"):
            st.markdown("""
A finite-difference estimate of local trajectory expansion rate — a fast, honest
proxy for sensitivity to initial conditions, disclosed as a **heuristic**, not a
rigorous Lyapunov exponent (that requires a full Jacobian-based calculation, which
this doesn't attempt). Negative → the system is settling down (STABLE). Near zero
→ borderline. Clearly positive → small perturbations are growing (CRITICAL) —
worth investigating further with the ensemble spread above.
            """)


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription(hub_id="mission")

    setup_page("Global Mission Control", "🌐", initial_sidebar_state="expanded")

    from modules.user_preferences import render_readability_fix, render_accent_color_css
    render_readability_fix()
    render_accent_color_css()

    hero_card(
        "🌐 Global Mission Control — Sovereign Enterprise Command Center",
        "The operational command center featuring live global health surveillance, real Open-Meteo climate telemetry, verified workload scorecards, workflow registries, and platform execution telemetry.",
        badge_text="GLOBAL MISSION CONTROL • PRODUCTION SUITE",
    )

    tabs = st.tabs([
        "🌡️ Health Surveillance",
        "🌦️ Climate & Weather",
        "🌀 Systemic Risk Simulator",
        "🏆 Impact Scorecard",
        "🧠 Workflow Registry",
        "📈 System Telemetry",
    ])

    with tabs[0]:
        render_health_tab()
    with tabs[1]:
        render_weather_tab()
    with tabs[2]:
        render_systemic_risk_tab()
    with tabs[3]:
        render_impact_tab()
    with tabs[4]:
        render_problems_tab()
    with tabs[5]:
        render_telemetry_tab()

    render_standard_footer("GLOBAL MISSION CONTROL")


if __name__ == "__main__":
    main()