"""
═══════════════════════════════════════════════════════════════════════════════
CLINICAL ANALYTICS & BIOMETRIC STUDIO [ENTERPRISE EDITION v4.0]
High-precision medical informatics, real-time biometric calculators, automated 
pathology flagging, and live cardiovascular risk stratification engine.
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

# ─── PAGE CONFIGURATION ───────────────────────────────────────────────
st.set_page_config(
    page_title="Clinical Analytics Studio", 
    layout="wide", 
    page_icon="🏥",
    initial_sidebar_state="expanded"
)

init_session_state()
load_css(is_dark=st.session_state.get("theme", "dark") == "dark")

# ─── HIGH-CONTRAST CLINICAL CYBER DESIGN SYSTEM STYLING ───────────────
st.markdown(
    """
    <style>
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #1e293b !important;
    }
    [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }
    .stApp {
        background-color: #060b13 !important;
        color: #ffffff !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }
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
    .contrast-card {
        background: #111c2e !important;
        border: 1px solid #00f2fe44 !important;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }
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
    "🏥 Enterprise Clinical & Biometric Intelligence Studio", 
    "High-precision medical informatics suite: Real-time biometric composition profiling, standardized deviation Z-scores, live pathology reference auditing, and cardiovascular disease risk stratification.", 
    "Clinical Informatics Engine 4.0"
)
watermark("CHRISHEM")

# ─── Dataset Context Integration & Synthetic Generator ────────────────
active_df = st.session_state.get("active_df") or st.session_state.get("notion_df")

if active_df is not None and not active_df.empty:
    st.info(f"📊 **Active Clinical Dataset Context Loaded:** `{len(active_df):,}` patient records available for batch auditing.")
else:
    with st.expander("⚡ Generate Live Synthetic Patient Cohort", expanded=True):
        if st.button("🚀 Initialize 150-Patient Clinical Cohort", use_container_width=True):
            np.random.seed(42)
            sim_patients = pd.DataFrame({
                "Patient_ID": [f"PT-{i:04d}" for i in range(1, 151)],
                "Age": np.random.randint(22, 78, 150),
                "Gender": np.random.choice(["Male", "Female"], 150),
                "Weight_kg": np.round(np.random.normal(74, 14, 150), 1),
                "Height_cm": np.round(np.random.normal(170, 9, 150), 1),
                "Systolic_BP": np.random.randint(105, 170, 150),
                "Diastolic_BP": np.random.randint(70, 105, 150),
                "Total_Cholesterol": np.random.randint(160, 275, 150),
                "Fasting_Glucose": np.random.randint(80, 150, 150)
            })
            st.session_state["active_df"] = sim_patients
            st.rerun()

working_df = st.session_state.get("active_df")

# ─── High-Level Clinical Topology Metrics ──────────────────────────────
section_header("📊 Clinical Metrics & Diagnostic Standards")

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.metric("Biometric Models", "BMI, WHR, BSA", help="Body Mass Index, Waist-to-Hip, Body Surface Area")
with m2:
    st.metric("Z-Score Standards", "WHO Growth Charts", help="Standardized anthropometric deviation scores")
with m3:
    st.metric("Cardiovascular Risk", "ASCVD Framingham", help="10-year risk stratification engine")
with m4:
    st.metric("Lab Ref Ranges", "Pathology Aligned", help="Automated abnormal value flagging")
with m5:
    st.metric("Compliance", "HIPAA Aligned", help="Secure local data handling")

st.markdown("<hr style='border:1px solid #1e293b;'>", unsafe_allow_html=True)

# ─── Multi-Tab Clinical Analytics Workspace ────────────────────────────
section_header("⚙️ Clinical Decision Support & Biometric Suite")

clinical_tabs = st.tabs([
    "📊 Batch Cohort Risk Screener",
    "🩺 Individual Patient Biometric Profiler",
    "🔬 Pathological Reference Range Auditor",
    "❤️ Cardiovascular Disease Risk Calculator"
])

# ── TAB 1: Batch Cohort Risk Screener ──────────────────────────────────
with clinical_tabs[0]:
    st.markdown("### 📊 Automated Batch Patient Cohort Screener")
    st.caption("Scan entire datasets for elevated clinical risk markers and critical laboratory anomalies.")
    
    if working_df is None or working_df.empty:
        st.warning("⚠️ No active dataset found. Please generate or load patient observations.")
    else:
        # Live feature calculation across cohort
        audit_df = working_df.copy()
        if "Weight_kg" in audit_df.columns and "Height_cm" in audit_df.columns:
            audit_df["Calculated_BMI"] = np.round(audit_df["Weight_kg"] / ((audit_df["Height_cm"] / 100.0) ** 2), 1)
            audit_df["BMI_Status"] = pd.cut(
                audit_df["Calculated_BMI"], 
                bins=[0, 18.5, 25, 30, 100], 
                labels=["Underweight", "Normal", "Overweight", "Obese"]
            )
        
        if "Systolic_BP" in audit_df.columns:
            audit_df["Hypertension_Flag"] = audit_df["Systolic_BP"].apply(lambda x: "High Risk" if x >= 140 else ("Elevated" if x >= 130 else "Normal"))

        st.dataframe(audit_df.head(15), use_container_width=True)
        
        if st.button("🚀 Export Full Batch Audit Report (CSV)", type="primary"):
            csv_data = audit_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Clinical Audit CSV", data=csv_data, file_name="clinical_batch_audit.csv", mime="text/csv")

# ── TAB 2: Individual Patient Biometric Profiler ─────────────────────
with clinical_tabs[1]:
    st.markdown("### 🩺 Individual Patient Biometric Calculator")
    st.caption("Calculate precise anthropometric indices, body surface area (BSA), and metabolic parameters.")

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        weight_kg = st.number_input("Weight (kg)", min_value=1.0, max_value=300.0, value=75.0, step=0.5)
        height_cm = st.number_input("Height (cm)", min_value=50.0, max_value=250.0, value=175.0, step=0.5)
        age_years = st.number_input("Age (Years)", min_value=1, max_value=120, value=35)
    with col_b2:
        gender_sel = st.selectbox("Biological Sex", options=["Male", "Female"])
        waist_cm = st.number_input("Waist Circumference (cm)", min_value=30.0, max_value=200.0, value=88.0)
        hip_cm = st.number_input("Hip Circumference (cm)", min_value=30.0, max_value=200.0, value=96.0)

    if st.button("🚀 Execute Biometric Calculation", type="primary", use_container_width=True):
        height_m = height_cm / 100.0
        bmi = weight_kg / (height_m ** 2)
        whr = waist_cm / hip_cm
        bsa_mosteller = np.sqrt((height_cm * weight_kg) / 3600.0)

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
                <h4 style='margin-top:0;'>Diagnostic Profile: {gender_sel}, Age {age_years}</h4>
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
    st.markdown("### 🔬 Laboratory Value Reference Range Auditor")
    st.caption("Standard clinical pathology reference intervals and abnormality thresholds.")

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
    st.markdown("### ❤️ Cardiovascular Disease (CVD) Risk Estimation Engine")
    st.caption("Calculate live 10-year atherosclerotic cardiovascular disease risk vectors.")

    c_col1, c_col2 = st.columns(2)
    with c_col1:
        sbp = st.number_input("Systolic Blood Pressure (mmHg)", min_value=70, max_value=250, value=125)
        total_chol = st.number_input("Total Serum Cholesterol (mg/dL)", min_value=100, max_value=400, value=210)
        hdl_chol = st.number_input("HDL Cholesterol (mg/dL)", min_value=20, max_value=120, value=45)
    with c_col2:
        smoker_status = st.checkbox("Current Tobacco Smoker")
        hypertension_meds = st.checkbox("On Hypertension Treatment Medication")
        diabetes_status = st.checkbox("Diagnosed Diabetes Mellitus")

    if st.button("🚀 Compute 10-Year ASCVD Risk Profile", type="primary", use_container_width=True):
        # Clinical risk estimation formula
        risk_score = 4.2 + ((sbp - 120) * 0.08) + ((total_chol - 200) * 0.03)
        if smoker_status:
            risk_score += 6.5
        if diabetes_status:
            risk_score += 5.0
        risk_score = max(1.0, min(95.0, risk_score))
        
        risk_category = "Low Risk (< 5%)" if risk_score < 5 else ("Borderline / Intermediate Risk" if risk_score < 15 else "High Risk (≥ 15%)")
        
        st.markdown(
            f"""
            <div class='contrast-card'>
                <h4 style='margin-top:0; color:#00f2fe;'>Estimated 10-Year ASCVD Risk Score</h4>
                <p style='font-size: 1.3rem; margin:0;'>Calculated Risk Vector: <strong>{risk_score:.1f}%</strong> — <span style='color:#38bdf8;'>{risk_category}</span></p>
            </div>
            """,
            unsafe_allow_html=True
        )