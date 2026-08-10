"""
🌍 Global Mission Control — Sovereign Enterprise Command Center (Premium)
Live global health surveillance, real weather & climate telemetry (Open-Meteo), an impact
scorecard, a problem-solver registry, and mission telemetry.

Changelog vs prior version:
- ADDED transparency caveats on three tabs whose underlying data could not be verified. This
  page pulls from `modules/mission_control.py`, which was not provided alongside this file.
  The Health Surveillance and Weather tabs show real signs of being genuinely API-backed (explicit
  live-vs-fallback error handling, Open-Meteo attribution) and were left functionally as-is.
  The Impact Scorecard, Problem Solver Registry, and especially Mission Telemetry tabs
  ("Satellites Linked," "Independent Systems," "AI Agents Deployed") match — almost word for word
  — the exact fabricated-marketing-metrics pattern already confirmed and fixed in this same
  codebase's Domain Analytics Hub (which previously showed hardcoded "48 Satellites" and a static
  "Systemic Risk Index: 0.012" with zero basis in real data). A data-analytics SaaS platform
  literally operating satellites doesn't make sense as a real infrastructure claim. Since the
  source module wasn't available to inspect or rewrite, honest on-page disclaimers were added
  instead of silently presenting unverified — and, by strong pattern-match, likely fabricated —
  figures as validated fact. If these numbers *are* real (e.g., genuinely computed from logged
  platform usage), the fix is to wire `modules/mission_control.py` to real counters and this
  caveat can come out; if they're static, this caveat should stay until they're replaced.
"""

import json
import datetime
import pandas as pd
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.shared_ui import hero_card, section_header, metric_card, render_export_buttons
from modules.mission_control import (
    fetch_global_health_hotspots,
    fetch_weather_telemetry,
    get_global_impact_scorecard,
    get_problem_solver_registry,
    get_mission_telemetry,
)

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def render_health_tab():
    section_header("🌡️ Live Global Health Surveillance & Outbreak Intelligence", "Real-time epidemiological surveillance tracking international disease-outbreak hotspots, case trajectories, and mortality rates.")

    if st.button("📡 Initialize Live Health Surveillance Feed", key="mc_health_fetch_upg", type="primary"):
        with st.spinner("Querying international epidemiological telemetry feeds..."):
            result = fetch_global_health_hotspots()

        st.info(f"Feed Source: **{result.get('source', 'Global Health Registry')}** | Last Synchronized: `{result.get('as_of', datetime.datetime.utcnow().strftime('%Y-%m-%d'))}`")

        total_cases = result.get('total_global_cases', 0)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Global Tracked Cases", f"{total_cases:,}")
        c2.metric("Active Hotspot Regions", len(result.get("hotspots", [])))
        c3.metric("Surveillance Status", "ONLINE")

        if result.get("error"):
            st.warning(f"⚠️ Live API Notice: {result['error']} — displaying fallback telemetry cache.")

        hotspots = result.get("hotspots", [])
        if hotspots:
            df = pd.DataFrame(hotspots)
            st.markdown("#### 🔥 Top International Outbreak Hotspots")
            st.dataframe(df[["country", "new_cases", "total_cases", "new_deaths", "total_deaths"]], use_container_width=True, hide_index=True)
            render_export_buttons(df, base_name="global_health_hotspots")

            st.markdown("#### 📈 New Cases Trajectory by Country")
            if PLOTLY_AVAILABLE and "country" in df.columns and "new_cases" in df.columns:
                fig = px.bar(df, x="country", y="new_cases", title="New Outbreak Cases per Region", color="new_cases", color_continuous_scale="Reds")
                fig.update_layout(height=380, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.bar_chart(df[["country", "new_cases"]].set_index("country"))
    else:
        st.info("ℹ️ Click **Initialize Live Health Surveillance Feed** to pull live global health parameters.")


def render_weather_tab():
    section_header("🌤️ Global Climate, Weather & Meteorological Telemetry", "Real-time high-resolution meteorological telemetry powered by Open-Meteo for any global coordinate.")

    col_a, col_b = st.columns(2)
    with col_a:
        lat = st.number_input("Target Latitude", value=0.3476, format="%.4f", key="mc_lat_upg")
    with col_b:
        lon = st.number_input("Target Longitude", value=32.5825, format="%.4f", key="mc_lon_upg")

    if st.button("🌤️ Execute Meteorological Query", key="mc_weather_fetch_upg", type="primary"):
        with st.spinner(f"Querying Open-Meteo satellite grid for coordinates [{lat}, {lon}]..."):
            result = fetch_weather_telemetry(lat, lon, daily=True)

        if result.get("error"):
            st.warning(f"⚠️ Live Meteorological API Notice: {result['error']}")
        else:
            st.info(f"Source Feed: **{result.get('source', 'Open-Meteo')}** | Assigned Timezone: `{result.get('timezone', 'UTC')}`")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Current Temperature", f"{result.get('temperature_c', 0)} °C")
            c2.metric("Wind Speed", f"{result.get('windspeed_kmh', 0)} km/h")
            c3.metric("Wind Direction", f"{result.get('wind_direction', 0)}°")
            c4.metric("Coordinates", f"{lat}, {lon}")

            forecast = result.get("forecast")
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
                    fig.add_trace(go.Scatter(x=df_fc["Date"], y=df_fc["Max Temperature (°C)"], name="Max Temp", line=dict(color="#00f2fe", width=2)))
                    fig.add_trace(go.Scatter(x=df_fc["Date"], y=df_fc["Min Temperature (°C)"], name="Min Temp", line=dict(color="#4facfe", width=2)))
                    fig.update_layout(title="Temperature Trend Forecast", height=320, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ℹ️ Configure coordinates and click **Execute Meteorological Query** to load climate data.")


def render_impact_tab():
    section_header("🏆 Global Human-Impact Scorecard", "Measure and monitor real-world problems solved across humanitarian, ecological, and technological sectors.")
    st.caption("⚠️ **Unverified data source:** this comes from `modules/mission_control.get_global_impact_scorecard()`, which wasn't provided alongside this page and takes no real-usage input parameters — it could not be confirmed whether these figures reflect measured platform activity or static illustrative placeholders.")

    scorecard = get_global_impact_scorecard()

    st.markdown("#### 📊 Cumulative Sovereign Progress")
    overall_progress = scorecard.get("overall_progress", 0)
    st.progress(overall_progress / 100)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Problems Solved", f"{scorecard.get('total_problems_solved', 0):,}")
    c2.metric("Overall Progress Index", f"{overall_progress}%")
    c3.metric("Synchronized Sectors", len(scorecard.get("sectors", [])))

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
    st.caption(f"Scorecard Synchronization Timestamp: {scorecard.get('as_of', datetime.datetime.utcnow().isoformat())}")


def render_problems_tab():
    section_header("🧠 Global Problem-Solver Registry", "Explore architectural solutions, toolchains, and quantifiable impact metrics deployed across humanity's core challenges.")
    st.caption("⚠️ **Unverified data source:** same as the Impact Scorecard tab — sourced from an unseen module with no verification input. Treat the specific 'impact' figures below as illustrative unless you've confirmed how `modules/mission_control.py` computes them.")

    registry = get_problem_solver_registry()
    for i, item in enumerate(registry):
        with st.expander(f"❓ Problem: {item.get('problem', 'Challenge')}", expanded=(i == 0)):
            st.markdown(f"**🛠️ Engineered Solution:** {item.get('solution', 'N/A')}")
            st.markdown("**🔧 Deployed Module Toolchain:** " + ", ".join(item.get("tools", [])))
            st.success(f"**🎯 Quantifiable Impact:** {item.get('impact', 'Optimized resolution')}")


def render_telemetry_tab():
    section_header("🛰️ Sovereign Mission Command Telemetry", "High-level command-center infrastructure metrics and decentralized system health.")
    st.error(
        "⚠️ **Likely fabricated metrics:** figures like 'Satellites Linked' and 'Independent Systems' below match — almost verbatim — a pattern of hardcoded marketing numbers already found and fixed elsewhere in this codebase (Domain Analytics Hub previously showed a static '48 Satellites' and '0.012 Systemic Risk Index' with no real basis). A data-analytics platform operating satellites is not a plausible real infrastructure claim. This tab's source module wasn't available to rewrite — if you want this tab to show real numbers, wire it to actual measured platform telemetry (real user counts, real deployed integrations, real uptime) rather than these placeholder-style figures."
    )

    telemetry = get_mission_telemetry()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Satellites Linked", telemetry.get("satellites_linked", 0))
    c2.metric("Independent Systems", telemetry.get("independent_systems", 0))
    c3.metric("Supported Languages", telemetry.get("languages", 0))
    c4.metric("System Uptime", telemetry.get("uptime", "99.99%"))

    st.markdown("#### 🛰️ Surveillance Grid & Autonomous AI Deployment")
    c5, c6 = st.columns(2)
    c5.metric("Global Surveillance Coverage", telemetry.get("surveillance_coverage", "100%"))
    c6.metric("Active Autonomous Agents", telemetry.get("ai_agents_deployed", 0))

    st.markdown("#### 🌍 Sovereign Mission Mandate")
    st.success(
        "**CHRISHEM Sovereign Intelligence** exists to solve real human problems — detecting epidemiological "
        "outbreaks early, predicting food insecurity, tracing cyber attacks, protecting privacy, enabling "
        "financial inclusion, and democratizing advanced research access — unified within a single autonomous platform."
    )


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription()

    setup_page("Global Mission Control", "🌍", initial_sidebar_state="expanded")

    hero_card(
        "🌍 Global Mission Control — Sovereign Enterprise Command Center (Premium)",
        "The human-impact command center featuring live global health surveillance, real Open-Meteo climate telemetry, an impact scorecard, problem-solver registry, and mission telemetry — with honest data-provenance labeling where the source could not be verified.",
        badge_text="GLOBAL MISSION CONTROL • PREMIUM SUITE",
    )

    tabs = st.tabs([
        "🌡️ Health Surveillance",
        "🌤️ Climate & Weather",
        "🏆 Impact Scorecard",
        "🧠 Problem Solver",
        "🛰️ Mission Telemetry",
    ])

    with tabs[0]:
        render_health_tab()
    with tabs[1]:
        render_weather_tab()
    with tabs[2]:
        render_impact_tab()
    with tabs[3]:
        render_problems_tab()
    with tabs[4]:
        render_telemetry_tab()

    render_standard_footer("GLOBAL MISSION CONTROL")


if __name__ == "__main__":
    main()