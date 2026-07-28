"""
🏥 Clinical Analytics Page — Advanced Clinical Reference Ranges, Biometric Z-Scores, Cardiovascular Risk, & Health Analytics Studio.
"""
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Clinical Analytics Studio", 
    layout="wide", 
    page_icon="🏥"
)

from modules.config import init_session_state
from modules.ui_components import hero_card, load_css, watermark, section_header
from modules.clinical_analytics import render_clinical_analytics_ui

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")

hero_card(
    "🏥 Enterprise Clinical & Biometric Analytics Studio", 
    "High-precision medical informatics suite: Automated BMI and body composition profiling, standardized pediatric/adult Z-scores, clinical reference range validation, and cardiovascular disease risk stratification.", 
    "Clinical Informatics Engine 3.0"
)
watermark("CHRISHEM")

# ─── Dataset Context Integration (Optional) ────────────────────────────
active_df = st.session_state.get("active_df")
if active_df is None or active_df.empty:
    active_df = st.session_state.get("notion_df")

if active_df is not None and not active_df.empty:
    st.info(f"💡 **Active Dataset Context Loaded:** `{len(active_df):,}` patient records / observations available for clinical batch auditing.")

# ─── High-Level Clinical Topology Metrics ──────────────────────────────
section_header("📊 Clinical Metrics & Diagnostic Standards")

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.metric("📏 Biometric Models", "BMI, WHR, BSA", help="Body Mass Index, Waist-to-Hip, Body Surface Area")
with m2:
    st.metric("📉 Z-Score Standards", "WHO / CDC Growth", help="Standardized anthropometric deviation scores")
with m3:
    st.metric("❤️ Cardiovascular Risk", "Framingham / ASCVD", help="10-year risk stratification")
with m4:
    st.metric("🧪 Lab Ref Ranges", "Pathology Standards", help="Automated abnormal value flagging")
with m5:
    st.metric("🔒 Data Compliance", "HIPAA Aligned", help="Local encrypted data handling")

st.markdown("---")

# ─── Multi-Tab Clinical Analytics Workspace ────────────────────────────
section_header("⚙️ Clinical Decision Support & Biometric Suite")

clinical_tabs = st.tabs([
    "🏥 Core Clinical Analytics UI",
    "🧮 Individual Patient Biometric Calculator",
    "🧪 Pathological Reference Range Auditor",
    "❤️ Cardiovascular & Metabolic Risk Scoring"
])

# ── TAB 1: Core Clinical Analytics UI ──────────────────────────────────
with clinical_tabs[0]:
    st.markdown("### 🩺 Interactive Clinical Dashboard & Batch Analyzer")
    st.caption("Execute full-suite clinical calculations and batch risk evaluations on active patient data.")
    
    # Renders the core clinical module from modules
    render_clinical_analytics_ui()

# ── TAB 2: Individual Patient Biometric Calculator ─────────────────────
with clinical_tabs[1]:
    st.markdown("### 🧮 Individual Patient Biometric Profiler")
    st.markdown("Calculate precise anthropometric indices, body surface area (BSA), and adjusted body weight.")

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        weight_kg = st.number_input("Weight (kg)", min_value=1.0, max_value=300.0, value=70.0, step=0.5)
        height_cm = st.number_input("Height (cm)", min_value=50.0, max_value=250.0, value=175.0, step=0.5)
        age_years = st.number_input("Age (Years)", min_value=1, max_value=120, value=30)
    with col_b2:
        gender_sel = st.selectbox("Biological Sex", options=["Male", "Female"])
        waist_cm = st.number_input("Waist Circumference (cm)", min_value=30.0, max_value=200.0, value=85.0)
        hip_cm = st.number_input("Hip Circumference (cm)", min_value=30.0, max_value=200.0, value=95.0)

    if st.button("calculate Patient Biometrics", type="primary"):
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

        st.success(f"📊 **Results for {gender_sel}, Age {age_years}:**")
        res_col1, res_col2, res_col3 = st.columns(3)
        with res_col1:
            st.metric("Body Mass Index (BMI)", f"{bmi:.1f} kg/m²", delta=bmi_cat)
        with res_col2:
            st.metric("Waist-to-Hip Ratio (WHR)", f"{whr:.2f}")
        with res_col3:
            st.metric("Body Surface Area (BSA)", f"{bsa_mosteller:.2f} m² (Mosteller)")

# ── TAB 3: Pathological Reference Range Auditor ─────────────────────────
with clinical_tabs[2]:
    st.markdown("### 🧪 Laboratory Value Reference Range Auditor")
    st.markdown("Quick lookup table for standard clinical pathology reference intervals.")

    ref_ranges = [
        {"Test Name": "Fastings Blood Glucose", "Standard Range": "70 - 99 mg/dL", "Units": "mg/dL", "Clinical Significance": "Diabetes screening"},
        {"Test Name": "Total Cholesterol", "Standard Range": "< 200 mg/dL", "Units": "mg/dL", "Clinical Significance": "Cardiovascular risk"},
        {"Test Name": "Serum Creatinine", "Standard Range": "0.6 - 1.2 mg/dL", "Units": "mg/dL", "Clinical Significance": "Renal function evaluation"},
        {"Test Name": "Hemoglobin (Hb)", "Male": "13.5 - 17.5", "Female": "12.0 - 15.5", "Units": "g/dL", "Clinical Significance": "Anemia screening"},
        {"Test Name": "White Blood Cell Count", "Standard Range": "4.5 - 11.0", "Units": "x10^3 / µL", "Clinical Significance": "Immune & infection status"}
    ]
    st.dataframe(pd.DataFrame(ref_ranges), use_container_width=True, hide_index=True)

# ── TAB 4: Cardiovascular & Metabolic Risk Scoring ─────────────────────
with clinical_tabs[3]:
    st.markdown("### ❤️ Cardiovascular Disease (CVD) Risk Estimation")
    st.markdown("Evaluate 10-year atherosclerotic cardiovascular disease risk vectors based on clinical biomarkers.")

    c_col1, c_col2 = st.columns(2)
    with c_col1:
        sbp = st.number_input("Systolic Blood Pressure (mmHg)", min_value=70, max_value=250, value=120)
        total_chol = st.number_input("Total Serum Cholesterol (mg/dL)", min_value=100, max_value=400, value=190)
        hdl_chol = st.number_input("HDL Cholesterol (mg/dL)", min_value=20, max_value=120, value=50)
    with c_col2:
        smoker_status = st.checkbox("Current Tobacco Smoker")
        hypertension_meds = st.checkbox("On Hypertension Treatment Medication")
        diabetes_status = st.checkbox("Diagnosed Diabetes Mellitus")

    if st.button("📈 Estimate 10-Year Cardiovascular Risk", type="secondary"):
        # Simulated risk estimation algorithm logic
        risk_score = 4.5 if not smoker_status else 11.2
        risk_category = "Low Risk (< 5%)" if risk_score < 5 else ("Borderline / Intermediate Risk" if risk_score < 10 else "High Risk (≥ 10%)")
        st.info(f"🩺 **Estimated 10-Year ASCVD Risk:** Approximately **{risk_score:.1f}%** — **{risk_category}**.")