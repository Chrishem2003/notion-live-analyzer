import streamlit as st

st.set_page_config(
    page_title="Sovereign Intelligence Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("⚡ Sovereign Intelligence Platform")
st.subheader("Enterprise Institutional-Grade Decision Platform")

st.markdown("""
Welcome to the **Sovereign Engine**. Use the **sidebar menu on the left** to navigate across all specialized sector suites:

- 🧠 **ML Core:** Continuous-Time Neural ODEs & PINNs Physics Validation
- 📡 **Live Telemetry:** Real-time API Streams (Bond Yields, ICU Saturation, Satellite Feeds)
- 💰 **Financial Systems:** Sovereign Debt Restructuring & Capital Flight Analytics
- 🏥 **Healthcare Suite:** Pandemic Preparedness & ICU Triage Forecasting
- 🌾 **Food Security:** Grain Reserve Timers & Agricultural Shock Mapping
- ⚡ **Energy Grids:** Cascading Power Failure Simulations & Grid Load Analytics
- 🛡️ **Enterprise Security:** RBAC, Cryptographic Auditing & PDF Report Generation
""")

st.sidebar.success("Select a Sector Suite above to get started.")
