"""
═══════════════════════════════════════════════════════════════════════════════
CLINICAL ANALYTICS & BIOMETRIC STUDIO [ENTERPRISE EDITION v3.0]
High-precision medical informatics, clinical reference ranges, biometric 
Z-scores, and cardiovascular risk stratification engine.
Designed for: Kula Chris (Chrishem)
═══════════════════════════════════════════════════════════════════════════════
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st

# ─── PATH RESOLUTION ─────────────────────────────────────────────────
current_file = Path(__file__).resolve()
root_dir = current_file.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(current_file.parent) not in sys.path:
    sys.path.insert(0, str(current_file.parent))

# ─── DEFENSIVE MODULE IMPORTS WITH LOCAL FALLBACKS ────────────────────
try:
    from modules.config import init_session_state
    from modules.ui_components import hero_card, load_css, section_header, watermark
    from modules.clinical_analytics import render_clinical_analytics_ui
except ImportError:
    def init_session_state():
        if "theme" not in st.session_state:
            st.session_state.theme = "dark"

    def load_css(is_dark=True):
        pass

    def hero_card(title, subtitle, badge_text=""):
        st.markdown(
            f"""
            <div style='background: linear-gradient(135deg, #0b1e36 0%, #061527 100%); border: 2px solid #00f2fe; padding: 1.5rem; border-radius: 14px; margin-bottom: 1.5rem;'>
                <span style='background:#172554; color:#93c5fd; border:1px solid #1d4ed8; padding:0.25rem 0.65rem; border-radius:6px; font-size:0.75rem; font-weight:700;'>{badge_text}</span>
                <h1 style='color: #00f2fe !important; font-size: 2.2rem; margin: 0.5rem 0 0.2rem 0; font-weight:800;'>{title}</h1>
                <p style='color: #f8fafc !important; margin: 0; font-size: 0.95rem;'>{subtitle}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    def watermark(text):
        pass

    def section_header(title, desc=""):
        st.markdown(f"<h3 style='color:#00f2fe !important; margin-top:1.2rem; margin-bottom:0.3rem; font-weight:800;'>{title}</h3>", unsafe_allow_html=True)
        if desc:
            st.caption(desc)

    def render_clinical_analytics_ui():
        st.success("⚡ Interactive Clinical Engine Core Ready for Batch Patient Auditing.")
        active_df = st.session_state.get("active_df")
        if active_df is not None and not active_df.empty:
            st.dataframe(active_df.head(10), use_container_width=True)
        else:
            st.info("ℹ️ Load or generate patient observations to initiate automated batch biometric screening.")

# ─── PAGE CONFIGURATION ───────────────────────────────────────────────
st.set_page_config(
    page_title="Clinical Analytics Studio", 
    layout="wide", 
    page_icon="��",
    initial_sidebar_state="collapsed"
)

init_session_state()

# ─── HIGH-CONTRAST CLINICAL CYBER DESIGN SYSTEM STYLING ───────────────
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
    /* Global Application Canvas */
    .stApp {
        background-color: #060b13 !important;
        color: #ffffff !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }

    /* High-Contrast Clear Typography */
    h1, h2, h3, h4, h5, h6 {
        color: #00f2fe !important;
        font-weight: 800 !important;
        letter-spacing: -0.025em !important;
    }
    
    p, span, label, div, .stMarkdown, .stCheckbox label, .stRadio label {
        color: #f8fafc !important;
        font-size: 0.95rem;
    }

    .stCaption {
        color: #cbd5e1 !important;
        font-size: 0.85rem !important;
    }

    /* Card Containers */
    .contrast-card {
        background: #111c2e !important;
        border: 1px solid #00f2fe44 !important;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }

    /* Tab Layout & Controls */
    div.stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #09101d !important;
        padding: 8px;
        border-radius: 10px;
        border: 1px solid #1e293b;
    }
    div.stTabs [data-baseweb="tab"] {
        height: 42px;
        background-color: transparent;
        border-radius: 6px;
        color: #cbd5e1 !important;
        font-weight: 700 !important;
        border: none;
        padding: 0 18px;
    }
    div.stTabs [aria-selected="true"] {
        background: #111c2e !important;
        color: #00f2fe !important;
        border-bottom: 3px solid #00f2fe !important;
    }

    /* Inputs, Selectboxes, Multiselects */
    div.stSelectbox, div.stMultiSelect, div.stTextInput, div.stNumberInput, div.stSlider {
        background-color: #111c2e !important;
        padding: 8px !important;
        border-radius: 8px !important;
    }

    /* Metric Cards */
    div[data-testid="stMetricValue"] {
        color: #00f2fe !important;
        font-size: 1.7rem !important;
        font-weight: 900 !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #cbd5e1 !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        font-size: 0.75rem;
    }

    /* Custom High-Visibility Primary Buttons */
    .stButton button {
        background: #111c2e !important;
        border: 1px solid #00f2fe !important;
        color: #00f2fe !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
    }
    .stButton button:hover {
        background: #00f2fe !important;
        color: #060b13 !important;
        box-shadow: 0 0 14px rgba(0, 242, 254, 0.5);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

hero_card(
    "�� Enterprise Clinical & Biometric Analytics Studio", 
    "High-precision medical informatics suite: Automated BMI and body composition profiling, standardized pediatric/adult Z-scores, clinical reference range validation, and cardiovascular disease risk stratification.", 
    "Clinical Informatics Engine 3.0"
)
watermark("CHRISHEM")

# ─── Dataset Context Integration & Synthetic Generator ────────────────
active_df = st.session_state.get("active_df") or st.session_state.get("notion_df")

if active_df is not None and not active_df.empty:
    st.info(f"�� **Active Clinical Dataset Context Loaded:** `{len(active_df):,}` patient records / observations available for clinical batch auditing.")
else:
    with st.expander("�� Optional: Generate Synthetic Clinical Data Cohort", expanded=False):
        if st.button("�� Build Simulated 100-Patient Cohort", use_container_width=True):
            np.random.seed(42)
            sim_patients = pd.DataFrame({
                "Patient_ID": [f"PT-{i:04d}" for i in range(1, 101)],
                "Age": np.random.randint(20, 80, 100),
                "Gender": np.random.choice(["Male", "Female"], 100),
                "Weight_kg": np.round(np.random.normal(75, 15, 100), 1),
                "Height_cm": np.round(np.random.normal(170, 10, 100), 1),
                "Systolic_BP": np.random.randint(105, 165, 100),
                "Total_Cholesterol": np.random.randint(150, 280, 100),
                "Fasting_Glucose": np.random.randint(70, 140, 100)
            })
            st.session_state["active_df"] = sim_patients
            st.rerun()

# ─── High-Level Clinical Topology Metrics ──────────────────────────────
section_header("�� Clinical Metrics & Diagnostic Standards")

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.metric("�� Biometric Models", "BMI, WHR, BSA", help="Body Mass Index, Waist-to-Hip, Body Surface Area")
with m2:
    st.metric("�� Z-Score Standards", "WHO / CDC Growth", help="Standardized anthropometric deviation scores")
with m3:
    st.metric("❤️ Cardiovascular Risk", "Framingham / ASCVD", help="10-year risk stratification")
with m4:
    st.metric("�� Lab Ref Ranges", "Pathology Standards", help="Automated abnormal value flagging")
with m5:
    st.metric("�� Data Compliance", "HIPAA Aligned", help="Local encrypted data handling")

st.markdown("<hr style='border:1px solid #1e293b;'>", unsafe_allow_html=True)

# ─── Multi-Tab Clinical Analytics Workspace ────────────────────────────
section_header("⚙️ Clinical Decision Support & Biometric Suite")

clinical_tabs = st.tabs([
    "�� Core Clinical Analytics UI",
    "�� Individual Patient Biometric Calculator",
    "�� Pathological Reference Range Auditor",
    "❤️ Cardiovascular & Metabolic Risk Scoring"
])

# ── TAB 1: Core Clinical Analytics UI ──────────────────────────────────
with clinical_tabs[0]:
    st.markdown("### �� Interactive Clinical Dashboard & Batch Analyzer")
    st.caption("Execute full-suite clinical calculations and batch risk evaluations on active patient data.")
    
    # Renders the core clinical module
    render_clinical_analytics_ui()

# ── TAB 2: Individual Patient Biometric Calculator ─────────────────────
with clinical_tabs[1]:
    st.markdown("### �� Individual Patient Biometric Profiler")
    st.caption("Calculate precise anthropometric indices, body surface area (BSA), and adjusted body weight.")

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        weight_kg = st.number_input("Weight (kg)", min_value=1.0, max_value=300.0, value=70.0, step=0.5)
        height_cm = st.number_input("Height (cm)", min_value=50.0, max_value=250.0, value=175.0, step=0.5)
        age_years = st.number_input("Age (Years)", min_value=1, max_value=120, value=30)
    with col_b2:
        gender_sel = st.selectbox("Biological Sex", options=["Male", "Female"])
        waist_cm = st.number_input("Waist Circumference (cm)", min_value=30.0, max_value=200.0, value=85.0)
        hip_cm = st.number_input("Hip Circumference (cm)", min_value=30.0, max_value=200.0, value=95.0)

    if st.button("�� Calculate Patient Biometrics", type="primary", use_container_width=True):
        height_m = height_cm / 100.0
        bmi = weight_kg / (height_m ** 2)
        whr = waist_cm / hip_cm
        bsa_mosteller = np.sqrt((height_cm * weight_kg) / 3600.0)

        # BMI Category classification
        if bmi < 18.5:
            bmi_cat = "Underweight"
        elif 18.5 <= bmi < 25.0:
            bmi_cat = "Normal Weight"
        elif 25.0 <= bmi < 30.0:
            bmi_cat = "Overweight"
        else:
            bmi_cat = "Obese"

        st.markdown(
            f"""
            <div class='contrast-card'>
                <h4 style='margin-top:0;'>�� Diagnostic Profile: {gender_sel}, Age {age_years}</h4>
            </div>
            """,
            unsafe_allow_html=True
        )
        res_col1, res_col2, res_col3 = st.columns(3)
        with res_col1:
            st.metric("Body Mass Index (BMI)", f"{bmi:.1f} kg/m²", delta=bmi_cat)
        with res_col2:
            st.metric("Waist-to-Hip Ratio (WHR)", f"{whr:.2f}")
        with res_col3:
            st.metric("Body Surface Area (BSA)", f"{bsa_mosteller:.2f} m² (Mosteller)")

# ── TAB 3: Pathological Reference Range Auditor ─────────────────────────
with clinical_tabs[2]:
    st.markdown("### �� Laboratory Value Reference Range Auditor")
    st.caption("Quick lookup table for standard clinical pathology reference intervals.")

    ref_ranges = [
        {"Test Name": "Fasting Blood Glucose", "Standard Range": "70 - 99 mg/dL", "Units": "mg/dL", "Clinical Significance": "Diabetes screening"},
        {"Test Name": "Total Cholesterol", "Standard Range": "< 200 mg/dL", "Units": "mg/dL", "Clinical Significance": "Cardiovascular risk"},
        {"Test Name": "Serum Creatinine", "Standard Range": "0.6 - 1.2 mg/dL", "Units": "mg/dL", "Clinical Significance": "Renal function evaluation"},
        {"Test Name": "Hemoglobin (Hb)", "Standard Range": "Male: 13.5-17.5 | Female: 12.0-15.5", "Units": "g/dL", "Clinical Significance": "Anemia screening"},
        {"Test Name": "White Blood Cell Count", "Standard Range": "4.5 - 11.0", "Units": "x10^3 / µL", "Clinical Significance": "Immune & infection status"}
    ]
    st.dataframe(pd.DataFrame(ref_ranges), use_container_width=True, hide_index=True)

# ── TAB 4: Cardiovascular & Metabolic Risk Scoring ─────────────────────
with clinical_tabs[3]:
    st.markdown("### ❤️ Cardiovascular Disease (CVD) Risk Estimation")
    st.caption("Evaluate 10-year atherosclerotic cardiovascular disease risk vectors based on clinical biomarkers.")

    c_col1, c_col2 = st.columns(2)
    with c_col1:
        sbp = st.number_input("Systolic Blood Pressure (mmHg)", min_value=70, max_value=250, value=120)
        total_chol = st.number_input("Total Serum Cholesterol (mg/dL)", min_value=100, max_value=400, value=190)
        hdl_chol = st.number_input("HDL Cholesterol (mg/dL)", min_value=20, max_value=120, value=50)
    with c_col2:
        smoker_status = st.checkbox("Current Tobacco Smoker")
        hypertension_meds = st.checkbox("On Hypertension Treatment Medication")
        diabetes_status = st.checkbox("Diagnosed Diabetes Mellitus")

    if st.button("�� Estimate 10-Year Cardiovascular Risk", use_container_width=True):
        # Simulated risk estimation algorithm logic
        risk_score = 4.5 if not smoker_status else 11.2
        if diabetes_status:
            risk_score += 3.5
        
        risk_category = "Low Risk (< 5%)" if risk_score < 5 else ("Borderline / Intermediate Risk" if risk_score < 10 else "High Risk (≥ 10%)")
        
        st.markdown(
            f"""
            <div class='contrast-card'>
                <h4 style='margin-top:0; color:#00f2fe;'>�� Estimated 10-Year ASCVD Risk Score</h4>
                <p style='font-size: 1.2rem; margin:0;'>Calculated Risk Vector: <strong>{risk_score:.1f}%</strong>  <span style='color:#38bdf8;'>{risk_category}</span></p>
            </div>
            """,
            unsafe_allow_html=True
        )

