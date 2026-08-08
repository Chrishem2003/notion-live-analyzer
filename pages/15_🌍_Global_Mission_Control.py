"""
🌍 Global Mission Control
 The human-impact command center: live health/weather feeds, global impact
 scorecard, and problem-solving registry.
"""

import json

import pandas as pd
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.shared_ui import hero_card, section_header, metric_card
from modules.mission_control import (
    fetch_global_health_hotspots,
    fetch_weather_telemetry,
    get_global_impact_scorecard,
    get_problem_solver_registry,
    get_mission_telemetry,
)


def render_health_tab():
    """Tab: Live global health feed."""
    section_header("🌡️ Live Global Health Surveillance", "Real disease-outbreak hotspots from Our World in Data.")

    if st.button("📡 Fetch Live Health Hotspots", key="mc_health_fetch", type="primary"):
        with st.spinner("Fetching global health telemetry..."):
            result = fetch_global_health_hotspots()
        st.info(f"Source: **{result['source']}** | As of {result['as_of']}")
        c1 = st.columns(1)[0]
        c1.metric("Total Global Cases", f"{result.get('total_global_cases', 0):,}")

        if result.get("error"):
            st.caption(f"Live API note: {result['error']} — showing fallback data.")

        st.markdown("#### 🔥 Top Outbreak Hotspots")
        hotspots = result.get("hotspots", [])
        if hotspots:
            df = pd.DataFrame(hotspots)
            st.dataframe(df[["country", "new_cases", "total_cases", "new_deaths", "total_deaths"]], use_container_width=True, hide_index=True)
            st.markdown("#### 📈 New Cases by Country")
            chart_df = df[["country", "new_cases"]].set_index("country")
            st.bar_chart(chart_df)
    else:
        st.info("Click **Fetch Live Health Hotspots** to pull real global health data.")


def render_weather_tab():
    """Tab: Live weather/climate telemetry."""
    section_header("🌤️ Live Climate & Weather Telemetry", "Real-time weather data from Open-Meteo for any coordinate.")

    col_a, col_b = st.columns(2)
    with col_a:
        lat = st.number_input("Latitude", value=0.3476, format="%.4f", key="mc_lat")
    with col_b:
        lon = st.number_input("Longitude", value=32.5825, format="%.4f", key="mc_lon")

    if st.button("🌤️ Fetch Live Weather", key="mc_weather_fetch", type="primary"):
        with st.spinner("Querying Open-Meteo..."):
            result = fetch_weather_telemetry(lat, lon, daily=True)
        if result.get("error"):
            st.warning(f"Live API unavailable: {result['error']}")
        else:
            st.info(f"Source: **{result['source']}** | Timezone: {result.get('timezone')}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Temperature", f"{result.get('temperature_c')} °C")
            c2.metric("Wind Speed", f"{result.get('windspeed_kmh')} km/h")
            c3.metric("Wind Direction", f"{result.get('wind_direction')}°")

            if result.get("forecast"):
                st.markdown("#### 📅 5-Day Forecast")
                fc = result["forecast"]
                st.dataframe(
                    pd.DataFrame({
                        "Date": fc.get("time", []),
                        "Max °C": fc.get("temperature_2m_max", []),
                        "Min °C": fc.get("temperature_2m_min", []),
                        "Precip mm": fc.get("precipitation_sum", []),
                    }),
                    use_container_width=True,
                    hide_index=True,
                )
    else:
        st.info("Click **Fetch Live Weather** to pull real meteorological data.")


def render_impact_tab():
    """Tab: Global impact scorecard."""
    section_header("🏆 Global Impact Scorecard", "Track real problems solved across human-impact sectors.")

    scorecard = get_global_impact_scorecard()

    st.markdown("#### 📊 Overall Progress")
    st.progress(scorecard["overall_progress"] / 100)
    c1, c2 = st.columns(2)
    c1.metric("Total Problems Solved", scorecard["total_problems_solved"])
    c2.metric("Overall Progress", f"{scorecard['overall_progress']}%")

    st.markdown("#### 🌐 Sector Breakdown")
    cols = st.columns(3)
    for i, sector in enumerate(scorecard["sectors"]):
        with cols[i % 3]:
            st.markdown(
                f"""
                <div style="background:#0b1321; border:1px solid #00f2fe44; border-radius:12px; padding:1rem; margin-bottom:1rem; text-align:center;">
                    <div style="font-size:2rem;">{sector['icon']}</div>
                    <div style="font-weight:800; color:#00f2fe; margin:0.3rem 0;">{sector['sector']}</div>
                    <div style="font-size:1.4rem; font-weight:800;">{sector['problems_solved']}<span style="font-size:0.8rem; color:#94a3b8;">/{sector['goal']}</span></div>
                    <div style="font-size:0.75rem; color:#94a3b8;">{sector['description']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.caption(f"As of {scorecard['as_of']}")


def render_problems_tab():
    """Tab: Problem-solver registry."""
    section_header("🧠 Global Problem-Solver Registry", "How the platform solves real human problems across sectors.")

    registry = get_problem_solver_registry()
    for i, item in enumerate(registry):
        with st.expander(f"❓ {item['problem']}", expanded=(i == 0)):
            st.markdown(f"**Solution:** {item['solution']}")
            st.markdown("**Tools:** " + ", ".join(item["tools"]))
            st.success(f"**Impact:** {item['impact']}")


def render_telemetry_tab():
    """Tab: Mission telemetry."""
    section_header("🛰️ Sovereign Mission Telemetry", "High-level command-center telemetry.")

    telemetry = get_mission_telemetry()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Satellites Linked", telemetry["satellites_linked"])
    c2.metric("Independent Systems", telemetry["independent_systems"])
    c3.metric("Languages", telemetry["languages"])
    c4.metric("Uptime", telemetry["uptime"])

    st.markdown("#### 🛰️ Surveillance & AI Deployment")
    c5, c6 = st.columns(2)
    c5.metric("Surveillance Coverage", telemetry["surveillance_coverage"])
    c6.metric("AI Agents Deployed", telemetry["ai_agents_deployed"])

    st.markdown("#### 🌍 Mission Statement")
    st.success(
        "**CHRISHEM Sovereign Intelligence** exists to solve real human problems — detecting disease "
        "outbreaks early, predicting food insecurity, tracing cyber attacks, protecting privacy, enabling "
        "financial inclusion, and democratizing research access — all in one unified platform."
    )


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription()  # paywall/trial gate, real DB check

    setup_page("Global Mission Control", "🌍", initial_sidebar_state="expanded")

    hero_card(
        "🌍 Global Mission Control",
        "The human-impact command center. Live global health surveillance, real-time climate telemetry, the global impact scorecard, and the problem-solving registry.",
        badge_text="GLOBAL MISSION CONTROL • WORLD IMPACT",
    )

    tabs = st.tabs([
        "🌡️ Health Feed",
        "🌤️ Climate",
        "🏆 Impact Scorecard",
        "🧠 Problem Solver",
        "🛰️ Telemetry",
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
