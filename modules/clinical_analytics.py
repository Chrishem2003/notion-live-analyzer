"""
Clinical & Health Analytics  BMI calculator, clinical reference ranges,
Z-scores, growth percentiles, and health indicator analysis.
"""
from typing import Dict, List, Any, Optional, Tuple, Union
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, date


# ─── BMI Calculator ────────────────────────────────────────────────

def calculate_bmi(weight_kg: float, height_cm: float) -> Dict[str, Any]:
    """Calculate BMI and provide clinical interpretation."""
    if height_cm <= 0 or weight_kg <= 0:
        return {"error": "Height and weight must be positive values"}

    height_m = height_cm / 100
    bmi = weight_kg / (height_m ** 2)

    # WHO Classification
    if bmi < 16.0:
        category = "Severe Thinness"
        risk = "Very high health risk"
        color = "#e74c3c"
    elif bmi < 17.0:
        category = "Moderate Thinness"
        risk = "High health risk"
        color = "#e67e22"
    elif bmi < 18.5:
        category = "Mild Thinness"
        risk = "Moderate health risk"
        color = "#f1c40f"
    elif bmi < 25.0:
        category = "Normal Range"
        risk = "Low health risk"
        color = "#2ecc71"
    elif bmi < 30.0:
        category = "Overweight (Pre-obese)"
        risk = "Moderate health risk"
        color = "#e67e22"
    elif bmi < 35.0:
        category = "Obese Class I"
        risk = "High health risk"
        color = "#e74c3c"
    elif bmi < 40.0:
        category = "Obese Class II"
        risk = "Very high health risk"
        color = "#c0392b"
    else:
        category = "Obese Class III (Severe)"
        risk = "Extremely high health risk"
        color = "#8e44ad"

    # Ideal weight range (BMI 18.5-24.9)
    ideal_min = 18.5 * (height_m ** 2)
    ideal_max = 24.9 * (height_m ** 2)

    return {
        "bmi": round(bmi, 1),
        "category": category,
        "risk": risk,
        "color": color,
        "weight_kg": weight_kg,
        "height_cm": height_cm,
        "ideal_weight_min": round(ideal_min, 1),
        "ideal_weight_max": round(ideal_max, 1),
        "weight_to_ideal": round(weight_kg - ideal_max, 1) if weight_kg > ideal_max else 0,
        "weight_to_gain": round(ideal_min - weight_kg, 1) if weight_kg < ideal_min else 0,
    }


def calculate_bmi_for_age(
    weight_kg: float,
    height_cm: float,
    age_years: float,
    sex: str = "male",
) -> Dict[str, Any]:
    """Calculate BMI percentile for age (simplified CDC-like reference)."""
    bmi_result = calculate_bmi(weight_kg, height_cm)
    if "error" in bmi_result:
        return bmi_result

    bmi = bmi_result["bmi"]

    # Simplified percentile estimation (log-normal distribution)
    # Mean and SD vary by age and sex  using simplified reference tables
    if sex.lower() == "male":
        if age_years < 18:
            mean_bmi = 15.5 + age_years * 0.45
            sd_bmi = 1.2 + age_years * 0.08
        else:
            mean_bmi = 22.5 + (age_years - 18) * 0.05
            sd_bmi = 2.5
    else:  # female
        if age_years < 18:
            mean_bmi = 15.0 + age_years * 0.50
            sd_bmi = 1.3 + age_years * 0.09
        else:
            mean_bmi = 21.5 + (age_years - 18) * 0.06
            sd_bmi = 2.8

    # Z-score
    z_score = (bmi - mean_bmi) / sd_bmi if sd_bmi > 0 else 0

    # Approximate percentile (using normal CDF approximation)
    percentile = round(float(normal_cdf(z_score) * 100), 1)

    # Weight status based on percentile
    if percentile < 5:
        status = "Underweight"
    elif percentile < 85:
        status = "Normal weight"
    elif percentile < 95:
        status = "Overweight"
    else:
        status = "Obese"

    bmi_result["z_score"] = round(z_score, 2)
    bmi_result["percentile"] = percentile
    bmi_result["age_years"] = age_years
    bmi_result["sex"] = sex
    bmi_result["status_for_age"] = status

    return bmi_result


def normal_cdf(x: float) -> float:
    """Standard normal CDF approximation."""
    return 0.5 * (1 + np.sign(x) * np.sqrt(1 - np.exp(-2 * x**2 / np.pi)))


# ─── Clinical Reference Ranges ──────────────────────────────────────

CLINICAL_REFERENCE_RANGES = {
    "Blood Pressure (Systolic)": {"unit": "mmHg", "normal": [90, 120], "flag_low": 90, "flag_high": 140},
    "Blood Pressure (Diastolic)": {"unit": "mmHg", "normal": [60, 80], "flag_low": 60, "flag_high": 90},
    "Heart Rate (Resting)": {"unit": "bpm", "normal": [60, 100], "flag_low": 50, "flag_high": 120},
    "Body Temperature": {"unit": "°C", "normal": [36.1, 37.2], "flag_low": 35.0, "flag_high": 38.0},
    "Respiratory Rate": {"unit": "breaths/min", "normal": [12, 20], "flag_low": 8, "flag_high": 25},
    "Blood Glucose (Fasting)": {"unit": "mmol/L", "normal": [3.9, 5.6], "flag_low": 3.5, "flag_high": 7.0},
    "Blood Glucose (Random)": {"unit": "mmol/L", "normal": [3.9, 7.8], "flag_low": 3.5, "flag_high": 11.1},
    "HbA1c": {"unit": "%", "normal": [4.0, 5.6], "flag_low": 3.5, "flag_high": 6.5},
    "Total Cholesterol": {"unit": "mmol/L", "normal": [3.0, 5.2], "flag_low": 2.5, "flag_high": 6.2},
    "HDL Cholesterol": {"unit": "mmol/L", "normal": [1.0, 2.5], "flag_low": 0.5, "flag_high": 3.0},
    "LDL Cholesterol": {"unit": "mmol/L", "normal": [0.0, 3.4], "flag_low": 0.0, "flag_high": 4.1},
    "Triglycerides": {"unit": "mmol/L", "normal": [0.0, 1.7], "flag_low": 0.0, "flag_high": 2.3},
    "Hemoglobin (Male)": {"unit": "g/dL", "normal": [13.5, 17.5], "flag_low": 11.0, "flag_high": 19.0},
    "Hemoglobin (Female)": {"unit": "g/dL", "normal": [12.0, 15.5], "flag_low": 10.0, "flag_high": 17.0},
    "White Blood Cell Count": {"unit": "×10⁹/L", "normal": [4.0, 11.0], "flag_low": 3.0, "flag_high": 15.0},
    "Platelet Count": {"unit": "×10⁹/L", "normal": [150, 450], "flag_low": 100, "flag_high": 600},
    "Sodium": {"unit": "mmol/L", "normal": [135, 145], "flag_low": 130, "flag_high": 150},
    "Potassium": {"unit": "mmol/L", "normal": [3.5, 5.0], "flag_low": 3.0, "flag_high": 5.5},
    "Calcium (Total)": {"unit": "mmol/L", "normal": [2.2, 2.6], "flag_low": 2.0, "flag_high": 2.8},
    "Creatinine": {"unit": "µmol/L", "normal": [60, 110], "flag_low": 40, "flag_high": 130},
    "eGFR": {"unit": "mL/min/1.73m²", "normal": [90, 120], "flag_low": 60, "flag_high": 150},
    "ALT": {"unit": "U/L", "normal": [10, 40], "flag_low": 5, "flag_high": 60},
    "AST": {"unit": "U/L", "normal": [10, 40], "flag_low": 5, "flag_high": 60},
    "TSH": {"unit": "mIU/L", "normal": [0.4, 4.0], "flag_low": 0.1, "flag_high": 10.0},
    "Vitamin D (25-OH)": {"unit": "nmol/L", "normal": [50, 125], "flag_low": 25, "flag_high": 200},
    "Vitamin B12": {"unit": "pmol/L", "normal": [145, 700], "flag_low": 100, "flag_high": 900},
    "Iron (Serum)": {"unit": "µg/dL", "normal": [60, 170], "flag_low": 40, "flag_high": 200},
    "Ferritin": {"unit": "ng/mL", "normal": [20, 250], "flag_low": 10, "flag_high": 500},
}


def interpret_clinical_value(
    test_name: str,
    value: float,
    sex: str = "unspecified",
) -> Dict[str, Any]:
    """Interpret a clinical laboratory value against reference ranges."""
    if test_name not in CLINICAL_REFERENCE_RANGES:
        # Try to match partial name
        matches = [k for k in CLINICAL_REFERENCE_RANGES if test_name.lower() in k.lower()]
        if matches:
            test_name = matches[0]
        else:
            return {"error": f"Unknown test: {test_name}", "test": test_name}

    ref = CLINICAL_REFERENCE_RANGES[test_name]
    normal_low, normal_high = ref["normal"]
    flag_low = ref.get("flag_low", normal_low)
    flag_high = ref.get("flag_high", normal_high)
    unit = ref["unit"]

    if value < flag_low:
        status = "⬇️ Critically Low"
        severity = "critical"
    elif value < normal_low:
        status = "↓ Low"
        severity = "moderate"
    elif value <= normal_high:
        status = "✅ Normal"
        severity = "normal"
    elif value <= flag_high:
        status = "↑ High"
        severity = "moderate"
    else:
        status = "⬆️ Critically High"
        severity = "critical"

    # Deviation
    if value < normal_low:
        deviation_pct = round((normal_low - value) / normal_low * 100, 1)
    elif value > normal_high:
        deviation_pct = round((value - normal_high) / normal_high * 100, 1)
    else:
        deviation_pct = 0

    return {
        "test": test_name,
        "value": value,
        "unit": unit,
        "normal_range": f"{normal_low}–{normal_high} {unit}",
        "status": status,
        "severity": severity,
        "deviation_pct": deviation_pct,
        "flag_low": flag_low,
        "flag_high": flag_high,
    }


def interpret_multiple_values(results: List[Dict[str, Any]]) -> pd.DataFrame:
    """Interpret multiple clinical values and return a DataFrame."""
    rows = []
    for r in results:
        interp = interpret_clinical_value(r.get("test", ""), r.get("value", 0), r.get("sex", "unspecified"))
        if "error" not in interp:
            rows.append(interp)
    return pd.DataFrame(rows)


# ─── Z-Score Calculator ────────────────────────────────────────────

def calculate_z_score(value: float, mean: float, sd: float) -> float:
    """Calculate Z-score for a given value."""
    if sd == 0:
        return 0
    return (value - mean) / sd


def calculate_percentile_from_z(z_score: float) -> float:
    """Convert Z-score to percentile."""
    return round(float(normal_cdf(z_score) * 100), 1)


# ─── Health Risk Assessment ────────────────────────────────────────

def assess_cardiovascular_risk(
    age: int,
    sex: str,
    systolic_bp: float,
    total_cholesterol: float,
    hdl_cholesterol: float,
    smoker: bool,
    diabetic: bool,
    hypertensive: bool,
) -> Dict[str, Any]:
    """
    Simplified cardiovascular risk assessment (based on Framingham-like model).
    """
    risk_score = 0

    # Age points
    if sex.lower() == "male":
        if age >= 30: risk_score += 1
        if age >= 40: risk_score += 1
        if age >= 50: risk_score += 2
        if age >= 60: risk_score += 2
        if age >= 70: risk_score += 2
    else:
        if age >= 40: risk_score += 1
        if age >= 50: risk_score += 2
        if age >= 60: risk_score += 2
        if age >= 70: risk_score += 3

    # Blood pressure
    if systolic_bp > 140: risk_score += 2
    elif systolic_bp > 130: risk_score += 1

    # Cholesterol
    total_hdl_ratio = total_cholesterol / hdl_cholesterol if hdl_cholesterol > 0 else 10
    if total_hdl_ratio > 5: risk_score += 2
    elif total_hdl_ratio > 4: risk_score += 1

    # Risk factors
    if smoker: risk_score += 2
    if diabetic: risk_score += 2
    if hypertensive: risk_score += 1

    # Risk category
    if risk_score <= 3:
        category = "Low Risk"
        recommendation = "Maintain healthy lifestyle. Regular check-ups."
    elif risk_score <= 6:
        category = "Moderate Risk"
        recommendation = "Consider lifestyle modifications. Monitor blood pressure and cholesterol."
    elif risk_score <= 9:
        category = "High Risk"
        recommendation = "Consult healthcare provider. Consider medication and significant lifestyle changes."
    else:
        category = "Very High Risk"
        recommendation = "Urgent medical consultation required. Immediate intervention recommended."

    return {
        "risk_score": risk_score,
        "category": category,
        "recommendation": recommendation,
        "total_hdl_ratio": round(total_hdl_ratio, 1),
        "risk_factors": {
            "age": age,
            "sex": sex,
            "systolic_bp": systolic_bp,
            "total_cholesterol": total_cholesterol,
            "hdl_cholesterol": hdl_cholesterol,
            "smoker": smoker,
            "diabetic": diabetic,
            "hypertensive": hypertensive,
        }
    }


# ─── UI ─────────────────────────────────────────────────────────────

def render_clinical_analytics_ui():
    """Render the clinical analytics UI."""
    st.markdown("## 🏥 Clinical & Health Analytics")
    st.markdown("*BMI calculator, clinical reference ranges, Z-scores, and health risk assessment*")

    tab1, tab2, tab3, tab4 = st.tabs([
        "⚖️ BMI Calculator", "🔬 Clinical Reference", "📊 Z-Score Calculator", "❤️ Health Risk"
    ])

    with tab1:
        st.subheader("⚖️ BMI Calculator")
        st.caption("Calculate Body Mass Index and get WHO classification")

        col1, col2 = st.columns(2)
        with col1:
            weight = st.number_input("Weight (kg)", min_value=1.0, max_value=500.0, value=70.0, step=0.1, key="bmi_weight")
            height = st.number_input("Height (cm)", min_value=30.0, max_value=250.0, value=170.0, step=0.1, key="bmi_height")
        with col2:
            use_age = st.checkbox("Calculate BMI-for-age percentile", key="bmi_age_use")
            if use_age:
                age = st.number_input("Age (years)", min_value=0.0, max_value=120.0, value=30.0, step=0.5, key="bmi_age")
                sex = st.selectbox("Sex", options=["male", "female"], key="bmi_sex")

        if weight > 0 and height > 0:
            if use_age:
                result = calculate_bmi_for_age(weight, height, age, sex)
            else:
                result = calculate_bmi(weight, height)

            if "error" in result:
                st.error(result["error"])
            else:
                bmi_val = result["bmi"]
                category = result["category"]
                color = result.get("color", "#2ecc71")

                # Gauge-like display
                st.markdown(f"""
                <div style="text-align:center;padding:1.5rem;background:{color}20;border-radius:18px;border:2px solid {color};">
                    <div style="font-size:3rem;font-weight:900;color:{color};">{bmi_val}</div>
                    <div style="font-size:1.2rem;font-weight:700;color:{color};">{category}</div>
                </div>
                """, unsafe_allow_html=True)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Ideal Weight Range", f"{result.get('ideal_weight_min', 0):.0f}–{result.get('ideal_weight_max', 0):.0f} kg")
                with col2:
                    if result.get("weight_to_ideal", 0) > 0:
                        st.metric("Weight to Lose", f"{result['weight_to_ideal']:.1f} kg", delta=-result['weight_to_ideal'])
                    elif result.get("weight_to_gain", 0) > 0:
                        st.metric("Weight to Gain", f"{result['weight_to_gain']:.1f} kg", delta=result['weight_to_gain'])
                    else:
                        st.metric("Weight Status", "✅ Healthy")
                with col3:
                    st.metric("Health Risk", result.get("risk", "N/A"))

                if "percentile" in result:
                    z = result.get("z_score", 0)
                    pct = result.get("percentile", 50)
                    status = result.get("status_for_age", "")
                    st.info(f"**BMI-for-age**: Z-score = {z:.2f}, Percentile = {pct:.1f}%  **{status}**")

        # BMI Category reference
        with st.expander("📖 WHO BMI Classification Reference"):
            bmi_ref = pd.DataFrame({
                "Category": ["Severe Thinness", "Moderate Thinness", "Mild Thinness", "Normal Range",
                              "Overweight", "Obese Class I", "Obese Class II", "Obese Class III"],
                "BMI Range": ["< 16.0", "16.0–16.9", "17.0–18.4", "18.5–24.9",
                              "25.0–29.9", "30.0–34.9", "35.0–39.9", "≥ 40.0"],
                "Risk": ["Very High", "High", "Moderate", "Low", "Moderate", "High", "Very High", "Extremely High"],
            })
            st.dataframe(bmi_ref, use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("🔬 Clinical Laboratory Reference Ranges")
        st.caption("Interpret lab values against clinical reference ranges")

        search = st.text_input("🔍 Search test name", placeholder="e.g., glucose, cholesterol, hemoglobin", key="clin_search")

        filtered_tests = {
            k: v for k, v in CLINICAL_REFERENCE_RANGES.items()
            if not search or search.lower() in k.lower()
        }

        if filtered_tests:
            test_name = st.selectbox("Select a test", options=list(filtered_tests.keys()), key="clin_test")
            value = st.number_input("Enter value", value=0.0, step=0.1, key="clin_value",
                                    help=f"Normal range: {filtered_tests[test_name]['normal'][0]}–{filtered_tests[test_name]['normal'][1]} {filtered_tests[test_name]['unit']}")

            if value != 0 and st.button("🔍 Interpret", type="primary"):
                result = interpret_clinical_value(test_name, value)
                if "error" not in result:
                    status_color = "#2ecc71" if result["severity"] == "normal" else "#e67e22" if result["severity"] == "moderate" else "#e74c3c"
                    st.markdown(f"""
                    <div style="padding:1rem;border-radius:12px;border:2px solid {status_color};background:{status_color}15;">
                        <h3 style="color:{status_color};">{result['status']}</h3>
                        <p><strong>{result['test']}</strong>: {result['value']} {result['unit']}</p>
                        <p><strong>Normal Range:</strong> {result['normal_range']}</p>
                        <p><strong>Deviation:</strong> {result['deviation_pct']}% from normal</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error(result["error"])

        # Reference table
        with st.expander("📋 Complete Reference Range Table"):
            ref_rows = []
            for name, ref in CLINICAL_REFERENCE_RANGES.items():
                ref_rows.append({
                    "Test": name,
                    "Normal Range": f"{ref['normal'][0]}–{ref['normal'][1]} {ref['unit']}",
                    "Critical Low": f"< {ref.get('flag_low', ref['normal'][0])}",
                    "Critical High": f"> {ref.get('flag_high', ref['normal'][1])}",
                })
            ref_df = pd.DataFrame(ref_rows)
            st.dataframe(ref_df, use_container_width=True, hide_index=True)

    with tab3:
        st.subheader("📊 Z-Score & Percentile Calculator")
        st.caption("Calculate Z-scores and percentiles for any measurement")

        col1, col2, col3 = st.columns(3)
        with col1:
            z_value = st.number_input("Raw value (x)", value=100.0, step=1.0, key="z_x")
        with col2:
            z_mean = st.number_input("Population mean (μ)", value=100.0, step=1.0, key="z_mean")
        with col3:
            z_sd = st.number_input("Standard deviation (σ)", value=15.0, min_value=0.01, step=1.0, key="z_sd")

        if st.button("📊 Calculate Z-Score", type="primary"):
            z = calculate_z_score(z_value, z_mean, z_sd)
            pct = calculate_percentile_from_z(z)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Z-Score", f"{z:.2f}")
            with col2:
                st.metric("Percentile", f"{pct:.1f}%")
            with col3:
                status = "Above average" if z > 0 else "Below average" if z < 0 else "Average"
                st.metric("Interpretation", status)

            # Visual
            import plotly.graph_objects as go
            import numpy as np

            x_range = np.linspace(-4, 4, 200)
            y_range = np.exp(-x_range**2 / 2) / np.sqrt(2 * np.pi)

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=x_range, y=y_range, mode='lines', fill='tozeroy',
                                     name='Normal Distribution', line=dict(color='#1d4ed8')))
            fig.add_vline(x=z, line_color='red', line_dash='dash', annotation_text=f'z = {z:.2f}')

            fig.update_layout(title='Standard Normal Distribution', height=300,
                              xaxis_title='Z-Score', yaxis_title='Density',
                              showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        # Z-score interpretation guide
        with st.expander("📖 Z-Score Interpretation Guide"):
            st.markdown("""
            | Z-Score Range | Percentile Range | Interpretation |
            |--------------|-----------------|----------------|
            | +2.0 to +3.0 | 97.7–99.9% | Significantly above average |
            | +1.0 to +2.0 | 84.1–97.7% | Above average |
            | -1.0 to +1.0 | 15.9–84.1% | Average range |
            | -2.0 to -1.0 | 2.3–15.9% | Below average |
            | -3.0 to -2.0 | 0.1–2.3% | Significantly below average |
            """)

    with tab4:
        st.subheader("❤️ Cardiovascular Risk Assessment")
        st.caption("Simplified risk assessment based on key health indicators")

        col1, col2 = st.columns(2)
        with col1:
            cv_age = st.number_input("Age", min_value=18, max_value=120, value=45, step=1, key="cv_age")
            cv_sex = st.selectbox("Sex", options=["male", "female"], key="cv_sex")
            cv_sbp = st.number_input("Systolic Blood Pressure (mmHg)", min_value=80, max_value=250, value=130, step=1, key="cv_sbp")
            cv_tc = st.number_input("Total Cholesterol (mmol/L)", min_value=1.0, max_value=15.0, value=5.2, step=0.1, key="cv_tc")
        with col2:
            cv_hdl = st.number_input("HDL Cholesterol (mmol/L)", min_value=0.1, max_value=5.0, value=1.3, step=0.1, key="cv_hdl")
            cv_smoker = st.checkbox("Smoker", key="cv_smoker")
            cv_diabetic = st.checkbox("Diabetic", key="cv_diabetic")
            cv_htn = st.checkbox("Hypertensive (diagnosed)", key="cv_htn")

        if st.button("🫀 Assess Cardiovascular Risk", type="primary"):
            risk = assess_cardiovascular_risk(
                cv_age, cv_sex, cv_sbp, cv_tc, cv_hdl,
                cv_smoker, cv_diabetic, cv_htn
            )

            risk_color = "#2ecc71" if risk["category"] == "Low Risk" else \
                         "#e67e22" if risk["category"] == "Moderate Risk" else \
                         "#e74c3c" if risk["category"] == "High Risk" else "#8e44ad"

            st.markdown(f"""
            <div style="padding:1.5rem;border-radius:18px;border:2px solid {risk_color};background:{risk_color}15;text-align:center;">
                <h2 style="color:{risk_color};">Score: {risk['risk_score']}</h2>
                <h3 style="color:{risk_color};">{risk['category']}</h3>
                <p style="font-size:1.1rem;">{risk['recommendation']}</p>
                <p><strong>Total/HDL Ratio:</strong> {risk['total_hdl_ratio']}</p>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("📋 Risk Factor Details"):
                for factor, value in risk.get("risk_factors", {}).items():
                    st.markdown(f"- **{factor.replace('_', ' ').title()}**: {value}")

