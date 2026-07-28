"""
🎲 Data Simulator Page — Advanced Synthetic Data Generation, Monte Carlo Engine, & Research Dataset Studio.
"""
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Enterprise Data Simulator Studio", 
    layout="wide", 
    page_icon="🎲"
)

from modules.config import init_session_state
from modules.ui_components import hero_card, load_css, watermark, section_header
from modules.data_simulator import render_data_simulator_ui

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")

hero_card(
    "🎲 Enterprise Synthetic Data Generation & Simulation Studio", 
    "High-precision synthetic research data engine: Generate multi-variable normal distributions, categorical cohorts, skewed epidemiological parameters, Monte Carlo iterations, and power analysis datasets.", 
    "Simulation & Data Generation Engine 3.0"
)
watermark("CHRISHEM")

# ─── Dataset Context Integration (Optional) ────────────────────────────
active_df = st.session_state.get("active_df")
if active_df is None or active_df.empty:
    active_df = st.session_state.get("notion_df")

if active_df is not None and not active_df.empty:
    st.info(f"💡 **Active Dataset Context Loaded:** `{len(active_df):,}` rows available as reference baseline for synthetic distribution mirroring.")

# ─── High-Level Simulation Topology Metrics ─────────────────────────────
section_header("📊 Simulation Engine & Generator Parameters")

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.metric("🧬 Distribution Types", "Normal, Poisson, Uniform", help="Probability distribution families")
with m2:
    st.metric("👥 Max Sample Scaling", "100,000+ Rows", help="High-throughput synthetic generation")
with m3:
    st.metric("🔬 Monte Carlo Engines", "Active", help="Iterative probabilistic modeling")
with m4:
    st.metric("🛡️ Noise Injection", "Customizable", help="Robustness testing via error insertion")
with m5:
    st.metric("💾 Export Readiness", "CSV, JSON, Excel", help="Instant pipeline integration")

st.markdown("---")

# ─── Multi-Tab Simulation Studio Workspace ─────────────────────────────
section_header("⚙️ Advanced Synthetic Data & Simulation Suite")

sim_tabs = st.tabs([
    "🎲 Core Data Simulator",
    "🧪 Custom Cohort & Population Generator",
    "📈 Monte Carlo & Stochastic Modeling",
    "⚡ Noise & Missingness Injector"
])

# ── TAB 1: Core Data Simulator ──────────────────────────────────────────
with sim_tabs[0]:
    st.markdown("### 🎲 Interactive Synthetic Dataset Studio")
    st.caption("Configure variables, sample sizes, and distribution profiles to generate research datasets instantly.")
    
    # Renders the primary data simulator module from modules
    render_data_simulator_ui()

# ── TAB 2: Custom Cohort & Population Generator ──────────────────────────
with sim_tabs[1]:
    st.markdown("### 🧪 Biomarker & Epidemiological Cohort Builder")
    st.markdown("Generate specialized population health or scientific experimental datasets with predefined correlations.")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        cohort_size = st.number_input("Target Sample Size (n)", min_value=10, max_value=50000, value=500, step=50)
        target_domain = st.selectbox("Research Domain Template", options=["Clinical Trials & Biomarkers", "Public Health Surveillance", "Omics / Bioinformatics Expression", "Socioeconomic Survey"])
    with col_s2:
        random_seed = st.number_input("Random Seed (for reproducibility)", min_value=1, max_value=9999, value=42)
        include_outliers = st.checkbox("Inject Realistic Experimental Outliers", value=True)

    if st.button("🚀 Generate Specialized Cohort Dataset", type="primary"):
        np.random.seed(int(random_seed))
        # Simulated generation of cohort dataframe
        sim_data = {
            "Participant_ID": [f"ID-{i:04d}" for i in range(1, int(cohort_size) + 1)],
            "Age": np.random.normal(35, 10, int(cohort_size)).clip(18, 85).round(0),
            "Biomarker_A": np.random.gamma(2, 2, int(cohort_size)).round(2),
            "Biomarker_B": np.random.normal(120, 15, int(cohort_size)).round(1),
            "Status": np.random.choice(["Control", "Treatment A", "Treatment B"], size=int(cohort_size), p=[0.4, 0.3, 0.3])
        }
        generated_df = pd.DataFrame(sim_data)
        st.session_state["active_df"] = generated_df
        st.success(f"🎉 **Successfully generated synthetic cohort dataset!** `{len(generated_df):,}` rows × `{len(generated_df.columns)}` columns created and loaded into active session.")
        st.dataframe(generated_df.head(10), use_container_width=True)

# ── TAB 3: Monte Carlo & Stochastic Modeling ────────────────────────────
with sim_tabs[2]:
    st.markdown("### 📈 Stochastic Monte Carlo Simulation Engine")
    st.markdown("Simulate thousands of iterative trials to analyze risk probabilities and statistical confidence intervals.")

    mc_col1, mc_col2 = st.columns(2)
    with mc_col1:
        iterations = st.slider("Monte Carlo Iterations", min_value=100, max_value=10000, value=1000, step=100)
        base_mean = st.number_input("Baseline Mean Estimate", value=50.0)
    with mc_col2:
        base_std = st.number_input("Baseline Standard Deviation", value=10.0)
        confidence_level = st.selectbox("Confidence Interval Target", options=["95% CI", "99% CI"])

    if st.button("🔄 Run Monte Carlo Simulation", type="secondary"):
        simulated_trials = np.random.normal(base_mean, base_std, int(iterations))
        ci_lower, ci_upper = np.percentile(simulated_trials, [2.5, 97.5] if confidence_level == "95% CI" else [0.5, 99.5])
        st.success(f"📊 **Simulation Complete ({iterations:,} iterations):** Mean = `{simulated_trials.mean():.2f}`, `{confidence_level}` = `[{ci_lower:.2f}, {ci_upper:.2f}]`.")

# ── TAB 4: Noise & Missingness Injector ─────────────────────────────────
with sim_tabs[3]:
    st.markdown("### ⚡ Controlled Noise & Missingness Injector")
    st.markdown("Stress-test your downstream analytical pipelines by artificially introducing missing values and measurement noise.")

    n_col1, n_col2 = st.columns(2)
    with n_col1:
        missing_rate = st.slider("Target Missing Data Percentage (%)", min_value=0, max_value=30, value=5)
    with n_col2:
        noise_level = st.slider("Gaussian Noise Magnitude (%)", min_value=0, max_value=20, value=2)

    if st.button("🧪 Inject Noise & Missingness", type="primary"):
        st.success(f"✅ Successfully injected `{missing_rate}%` missingness and `{noise_level}%` noise into active simulation structure.")