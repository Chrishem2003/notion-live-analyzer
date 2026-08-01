

import streamlit as st

# --- 1. PAGE CONFIGURATION ----------------------------------------------
st.set_page_config(
    page_title="Energy Grids & Infrastructure Resiliency",
    page_icon="?",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- 2. HIGH-CONTRAST & ULTRA-LEGIBLE COLOR STYLING -----------------------
st.markdown(
    """
    <style>
    /* --- GLOBAL SIDEBAR DARK THEMING OVERRIDE --- */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #1e293b !important;
    }
    
    /* Force all sidebar text, links, and headers to high-contrast off-white */
    [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    /* Target navigation links and text explicitly */
    [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarHeader"] {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    /* Navigation item hover state */
    [data-testid="stSidebarNavLink"]:hover,
    [data-testid="stSidebarNav"] a:hover {
        background-color: #1e293b !important;
        border-radius: 8px !important;
    }

    /* Currently selected navigation item active state */
    [data-testid="stSidebarNavLink"][aria-current="page"],
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }

    /* Custom form inputs inside sidebar */
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: #38bdf8 !important;
        font-weight: 700 !important;
    }
    /* Global Background & Base Font */
    .stApp {
        background-color: #060b13 !important;
        color: #ffffff !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Typography Overrides */
    h1, h2, h3, h4 {
        color: #00f2fe !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em;
    }
    
    /* Custom High-Contrast Card Containers */
    .card-container {
        background: #111c2e;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    }
    
    /* Metric Styling */
    div[data-testid="stMetricValue"] {
        color: #00f2fe !important;
        font-size: 2rem !important;
        font-weight: 900 !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #cbd5e1 !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        font-size: 0.8rem !important;
        letter-spacing: 0.05em;
    }
    
    /* Alert / Status Card Custom Styling */
    .status-card-success {
        background: linear-gradient(135deg, #022c22 0%, #064e3b 100%);
        border: 1px solid #10b981;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        color: #ecfdf5 !important;
        font-weight: 600;
        font-size: 0.95rem;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        box-shadow: 0 4px 14px rgba(16, 185, 129, 0.2);
    }
    
    /* High-Visibility Badges */
    .badge-primary {
        background: #172554;
        color: #93c5fd;
        border: 1px solid #1d4ed8;
        padding: 0.25rem 0.65rem;
        border-radius: 6px;
        font-size: 0.7rem;
        font-family: monospace;
        letter-spacing: 0.05em;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- 3. HERO HEADER SECTION ---------------------------------------------
st.markdown(
    """
<div style='background: linear-gradient(135deg, #0b1e36 0%, #061527 100%); border: 2px solid #00f2fe; padding: 1.5rem; border-radius: 14px; margin-bottom: 1.5rem;'>
    <span class='badge-primary'>INFRASTRUCTURE TELEMETRY & SIMULATION</span>
    <h1 style='font-size: 2.2rem; margin: 0.5rem 0 0.2rem 0; color: #00f2fe;'>? Energy Grids & Infrastructure Resiliency</h1>
    <p style='color: #cbd5e1; margin: 0; font-size: 0.98rem;'>
        Cascading Grid Failure Simulation, Reservoir Strain Analysis, and Intermittent Renewable Limits Monitoring.
    </p>
</div>
""",
    unsafe_allow_html=True,
)

# --- 4. METRICS & STATUS CARDS ------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.markdown("<div class='card-container'>", unsafe_allow_html=True)
    st.metric(
        label="Power Grid Cascade Risk",
        value="0.012",
        delta="Stable",
        delta_color="normal"
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div class='card-container'>", unsafe_allow_html=True)
    st.metric(
        label="Municipal Water Reservoir Level",
        value="68.5%",
        delta="Capacity Optimum",
        delta_color="normal"
    )
    st.markdown("</div>", unsafe_allow_html=True)

# --- 5. HIGH-VISIBILITY STATUS ALERT -----------------------------------
st.markdown(
    """
<div class='status-card-success'>
    <span style='font-size: 1.4rem;'>?</span>
    <div>
        <strong style='color: #34d399;'>Renewable Grid Penetration Threshold Safe:</strong><br>
        Current load operating at <span style='color: #ffffff; font-weight: 800;'>32%</span> / Maximum tolerance threshold is <span style='color: #ffffff; font-weight: 800;'>45%</span>.
    </div>
</div>
""",
    unsafe_allow_html=True,
)

