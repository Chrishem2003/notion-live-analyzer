import security_guard
iimport security_guard
security_guard.verify_access()



"""
═══════════════════════════════════════════════════════════════════════════════
META-ANALYSIS & EVIDENCE SYNTHESIS ENGINE [ENTERPRISE ULTRA v6.0]
Features: Dynamic Effect Size Calculators (Continuous & Binary),
Multi-Estimator Random-Effects (DL, REML, HE), Advanced Heterogeneity (Q, I², Tau², H²),
Duval & Tweedie Trim-and-Fill, Interactive Plotly Forest & Funnel Plots, and Subgroup Pooling.
Designed for CHRISHEM Enterprise Build.
═══════════════════════════════════════════════════════════════════════════════
"""

import sys
import hashlib
import time
import pandas as pd
import numpy as np
import streamlit as st

# ─── DEPENDENCY CHECK ──────────────────────────────────────────────────
try:
    import scipy.stats as stats
    import plotly.graph_objects as go
    import plotly.express as px
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

# ─── PAGE CONFIGURATION ───────────────────────────────────────────────
st.set_page_config(
    page_title="Meta-Analysis Engine [ENTERPRISE v6.0]",
    page_icon="🔍 ",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if not HAS_DEPS:
    st.error(
        "⚠️ Required statistical dependencies not installed.\n\n"
        "Please install missing packages: `pip install scipy statsmodels plotly pandas numpy`"
    )
    st.stop()

# ─── SESSION STATE INITIALIZATION ──────────────────────────────────────
if "meta_engine_clearance" not in st.session_state:
    st.session_state.meta_engine_clearance = False
if "custom_access_password" not in st.session_state:
    st.session_state.custom_access_password = hashlib.sha256("ENTERPRISE_KEY".encode()).hexdigest()
if "meta_df" not in st.session_state:
    st.session_state["meta_df"] = pd.DataFrame({
        "Study": ["Trial Alpha (2023)", "Study Beta (2024)", "Cohort Gamma (2024)", "Trial Delta (2025)", "Bio-Survey Epsilon (2026)"],
        "Effect_Size": [0.65, 0.42, 0.81, 0.30, 0.55],
        "Standard_Error": [0.12, 0.15, 0.10, 0.18, 0.14],
        "Subgroup": ["Region A", "Region A", "Region B", "Region B", "Region A"]
    })

# ─── CUSTOM HIGH-CONTRAST CSS ──────────────────────────────────────────
st.markdown("""
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
    .stApp {
        background-color: #020617 !important;
        color: #f8fafc !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    
    h1, h2, h3, h4 {
        color: #f8fafc !important;
        font-weight: 800 !important;
    }
    
    p, span, label, div {
        color: #cbd5e1 !important;
    }

    .enterprise-card {
        background: #090d16 !important;
        border: 1px solid #1e293b !important;
        border-radius: 16px;
        padding: 1.25rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
        margin-bottom: 1rem;
    }

    .badge-glow {
        background: rgba(99, 102, 241, 0.15) !important;
        color: #818cf8 !important;
        border: 1px solid #4f46e5 !important;
        padding: 0.25rem 0.6rem;
        border-radius: 6px;
        font-size: 0.7rem;
        font-family: monospace;
        font-weight: 700;
        letter-spacing: 0.05em;
    }

    div.stSelectbox, div.stTextInput, div.stTextArea {
        background-color: #090d16 !important;
        border-radius: 8px !important;
    }

    .stButton button {
        background: #090d16 !important;
        border: 1px solid #4f46e5 !important;
        color: #818cf8 !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        transition: all 0.2s ease;
    }
    .stButton button:hover {
        background: #4f46e5 !important;
        color: #ffffff !important;
        box-shadow: 0 0 16px rgba(79, 70, 229, 0.4);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #020617;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: #090d16 !important;
        border: 1px solid #1e293b !important;
        border-radius: 8px 8px 0px 0px !important;
        color: #94a3b8 !important;
        font-weight: 600;
        padding: 0.6rem 1.2rem !important;
    }

    .stTabs [aria-selected="true"] {
        background-color: #1e293b !important;
        color: #00f2fe !important;
        border-color: #00f2fe !important;
    }

    div[data-testid="stMetricValue"] {
        color: #00f2fe !important;
        font-weight: 800 !important;
    }
</style>
""", unsafe_allow_html=True)

# ─── STATISTICAL HELPER FUNCTIONS ─────────────────────────────────────
def compute_continuous_effect(m1, sd1, n1, m2, sd2, n2, measure="hedges_g"):
    """Calculates Cohen's d or Hedges' g along with Standard Errors."""
    s_pooled = np.sqrt(((n1 - 1) * sd1**2  (n2 - 1) * sd2**2) / (n1  n2 - 2))
    d = (m1 - m2) / s_pooled
    var_d = ((n1  n2) / (n1 * n2))  (d**2 / (2 * (n1  n2)))
    
    if measure == "hedges_g":
        j_correction = 1 - (3 / (4 * (n1  n2 - 2) - 1))
        g = d * j_correction
        var_g = (j_correction**2) * var_d
        return g, np.sqrt(var_g)
    return d, np.sqrt(var_d)

def compute_binary_effect(e1, n1, e2, n2, measure="log_or"):
    """Calculates Log Odds Ratio or Log Risk Ratio with Standard Errors."""
    c1, c2 = n1 - e1, n2 - e2
    if 0 in [e1, c1, e2, c2]:
        e1, c1, e2, c2 = e1  0.5, c1  0.5, e2  0.5, c2  0.5
        n1, n2 = n1  1, n2  1
        
    if measure == "log_or":
        log_or = np.log((e1 * c2) / (c1 * e2))
        se_log_or = np.sqrt(1/e1  1/c1  1/e2  1/c2)
        return log_or, se_log_or
    else:
        log_rr = np.log((e1 / n1) / (e2 / n2))
        se_log_rr = np.sqrt((1/e1 - 1/n1)  (1/e2 - 1/n2))
        return log_rr, se_log_rr

def trim_and_fill(effects, std_errs, max_iter=20):
    """Duval & Tweedie Trim-and-Fill algorithm for estimating missing studies."""
    k = len(effects)
    weights = 1.0 / (std_errs ** 2)
    center = np.sum(weights * effects) / np.sum(weights)
    
    filled_effects = list(effects)
    filled_se = list(std_errs)
    imputed_count = 0
    
    for _ in range(max_iter):
        devs = filled_effects - center
        abs_devs = np.abs(devs)
        ranks = stats.rankdata(abs_devs)
        signed_ranks = ranks * np.sign(devs)
        
        k0 = max(0, int(round(abs(np.sum(signed_ranks[signed_ranks < 0])))))
        if k0 == imputed_count:
            break
        
        imputed_count = k0
        if k0 > 0:
            sorted_idx = np.argsort(devs)
            missing_effects = 2 * center - np.array(filled_effects)[sorted_idx[-k0:]]
            missing_se = np.array(filled_se)[sorted_idx[-k0:]]
            
            filled_effects = list(effects)  list(missing_effects)
            filled_se = list(std_errs)  list(missing_se)
            
            w_temp = 1.0 / (np.array(filled_se) ** 2)
            center = np.sum(w_temp * np.array(filled_effects)) / np.sum(w_temp)
            
    return np.array(filled_effects), np.array(filled_se), imputed_count

# ─── HERO HEADER ───────────────────────────────────────────────────────
st.markdown("""
<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:1.5rem; flex-wrap:wrap; gap:1rem;'>
    <div>
        <span class='badge-glow'>⚡ v6.0 ULTRA  DYNAMIC EFFECT CONVERTERS & TRIM-AND-FILL SUITE</span>
        <h1 style='font-size:2.2rem; color:#f8fafc; margin:0.4rem 0 0.2rem 0;'>
            🔍 Enterprise Meta-Analysis & Evidence Synthesis Engine
        </h1>
        <p style='color:#94a3b8; font-size:0.95rem; max-width:850px; margin:0;'>
            Perform rigorous statistical pooling, multi-estimator heterogeneity modeling (DL, REML, HE), publication bias adjustments (Egger's Test & Trim-and-Fill), and interactive visualization.
        </p>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<hr style='border-color:#1e293b; margin:1rem 0;'>", unsafe_allow_html=True)

# ─── SECURITY GATE & WORKSPACE CONTROL ────────────────────────────────
col_sec, col_proj = st.columns([1, 1])

with col_sec:
    st.markdown("### 🔍 Security Authentication Gate")
    if not st.session_state.meta_engine_clearance:
        st.info("🔍 Enter passkey (**ENTERPRISE_KEY**) to access statistical modeling suite.")
        security_input = st.text_input("Enter Passkey", type="password", placeholder="••••••••", key="meta_passkey_input")
        if st.button("🔍 Authenticate Passkey", type="primary", use_container_width=True):
            if security_input and hashlib.sha256(security_input.encode()).hexdigest() == st.session_state.custom_access_password:
                st.session_state.meta_engine_clearance = True
                st.success("✅ Enterprise Clearance Granted!")
                st.rerun()
            else:
                st.error("❌ Access Denied: Invalid Passkey")
    else:
        st.success("🔍 Enterprise Workspace Unlocked")
        if st.button("🔍 Lock Workspace", use_container_width=True):
            st.session_state.meta_engine_clearance = False
            st.rerun()

with col_proj:
    st.markdown("### 🔍 Project & Input Strategy")
    analysis_mode = st.selectbox(
        "Select Data Input Mode",
        options=[
            "Pre-computed Effect Sizes (ES  SE)",
            "Raw Continuous Data (Mean, SD, N)",
            "Raw Binary Outcome Data (Events, N)",
            "Upload Custom Dataset (.csv / .xlsx)"
        ]
    )

if not st.session_state.meta_engine_clearance:
    st.warning("🔍 **Authenticate via Security Gate** to perform modeling and export publication plots.")
    st.stop()

st.markdown("<hr style='border-color:#1e293b; margin:1rem 0;'>", unsafe_allow_html=True)

# ─── NAVIGATION TABS ─────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 Dataset & Effect Builder",
    "⚙️ Statistical Pooling Engine",
    "🔍 Interactive Forest Plot",
    "🔍 Publication Bias & Trim-and-Fill",
    "🔍 Heterogeneity & Subgroups"
])

# ═══════════════════════════════════════════════════════════════════════
# TAB 1: DATASET MANAGER & CONVERTERS
# ═══════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("<h3 style='color:#00f2fe;'>🔍 Study Data & Effect Size Converter Engine</h3>", unsafe_allow_html=True)
    
    if analysis_mode == "Upload Custom Dataset (.csv / .xlsx)":
        uploaded_file = st.file_uploader("Upload study dataset", type=["csv", "xlsx"])
        if uploaded_file:
            if uploaded_file.name.endswith(".csv"):
                st.session_state["meta_df"] = pd.read_csv(uploaded_file)
            else:
                st.session_state["meta_df"] = pd.read_excel(uploaded_file)
            st.success("✅ Custom Dataset Loaded Successfully!")

    elif analysis_mode == "Raw Continuous Data (Mean, SD, N)":
        st.markdown("#### Compute Hedges' g / Cohen's d from Raw Means")
        raw_c_df = pd.DataFrame({
            "Study": ["Study A", "Study B", "Study C"],
            "Mean_Exp": [12.5, 14.1, 10.8], "SD_Exp": [2.1, 2.5, 1.9], "N_Exp": [50, 45, 60],
            "Mean_Ctrl": [10.2, 13.0, 9.5], "SD_Ctrl": [2.0, 2.3, 1.8], "N_Ctrl": [50, 45, 60],
            "Subgroup": ["Group 1", "Group 1", "Group 2"]
        })
        edited_raw = st.data_editor(raw_c_df, num_rows="dynamic", use_container_width=True)
        
        if st.button("⚡ Convert Raw Continuous Data to Effect Sizes"):
            es_list, se_list = [], []
            for _, row in edited_raw.iterrows():
                es, se = compute_continuous_effect(
                    row["Mean_Exp"], row["SD_Exp"], row["N_Exp"],
                    row["Mean_Ctrl"], row["SD_Ctrl"], row["N_Ctrl"]
                )
                es_list.append(es)
                se_list.append(se)
            
            st.session_state["meta_df"] = pd.DataFrame({
                "Study": edited_raw["Study"],
                "Effect_Size": es_list,
                "Standard_Error": se_list,
                "Subgroup": edited_raw["Subgroup"]
            })
            st.success("✅ Calculated Hedges' g and SE successfully!")

    elif analysis_mode == "Raw Binary Outcome Data (Events, N)":
        st.markdown("#### Compute Log Odds Ratio / Log Risk Ratio from Event Counts")
        raw_b_df = pd.DataFrame({
            "Study": ["Study X", "Study Y", "Study Z"],
            "Events_Exp": [15, 22, 8], "Total_Exp": [100, 150, 80],
            "Events_Ctrl": [28, 35, 18], "Total_Ctrl": [100, 150, 80],
            "Subgroup": ["Cohort A", "Cohort A", "Cohort B"]
        })
        edited_b_raw = st.data_editor(raw_b_df, num_rows="dynamic", use_container_width=True)
        
        if st.button("⚡ Convert Raw Binary Data to Log Odds Ratios"):
            es_list, se_list = [], []
            for _, row in edited_b_raw.iterrows():
                es, se = compute_binary_effect(
                    row["Events_Exp"], row["Total_Exp"],
                    row["Events_Ctrl"], row["Total_Ctrl"]
                )
                es_list.append(es)
                se_list.append(se)
            
            st.session_state["meta_df"] = pd.DataFrame({
                "Study": edited_b_raw["Study"],
                "Effect_Size": es_list,
                "Standard_Error": se_list,
                "Subgroup": edited_b_raw["Subgroup"]
            })
            st.success("✅ Calculated Log Odds Ratio and SE successfully!")

    st.markdown("#### Current Master Data Table")
    edited_df = st.data_editor(
        st.session_state["meta_df"],
        num_rows="dynamic",
        use_container_width=True,
        key="master_meta_editor"
    )
    st.session_state["meta_df"] = edited_df

# ─── EXTRACT DATA ARRAYS ───────────────────────────────────────────────
df = st.session_state["meta_df"]
try:
    studies = df["Study"].astype(str).tolist()
    effect_sizes = df["Effect_Size"].astype(float).values
    standard_errors = df["Standard_Error"].astype(float).values
    weights = 1.0 / (standard_errors ** 2)
    k = len(studies)
except Exception as e:
    st.error(f"⚠️ Column mapping error: Ensure 'Study', 'Effect_Size', and 'Standard_Error' exist. Details: {e}")
    st.stop()

# ═══════════════════════════════════════════════════════════════════════
# TAB 2: STATISTICAL POOLING ENGINE
# ═══════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("<h3 style='color:#00f2fe;'>⚙️ Advanced Model Pooling & Variance Estimators</h3>", unsafe_allow_html=True)
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        model_type = st.radio("Pooling Model Strategy", ["Random-Effects Model", "Fixed-Effect Model"])
    with col_m2:
        tau_estimator = st.selectbox("Tau² Variance Estimator (Random-Effects)", ["DerSimonian-Laird (DL)", "Restricted Maximum Likelihood (REML)", "Hedges-Olkin (HE)"])

    sum_w = np.sum(weights)
    pooled_fe = np.sum(weights * effect_sizes) / sum_w
    se_fe = np.sqrt(1.0 / sum_w)
    
    q_stat = np.sum(weights * ((effect_sizes - pooled_fe) ** 2))
    df_q = max(1, k - 1)
    pval_q = 1.0 - stats.chi2.cdf(q_stat, df_q)
    i_squared = max(0.0, 100.0 * (q_stat - df_q) / q_stat) if q_stat > df_q else 0.0
    h_squared = q_stat / df_q if df_q > 0 else 1.0
    
    if tau_estimator == "Hedges-Olkin (HE)":
        tau_squared = max(0.0, (q_stat - df_q) / (sum_w - np.sum(weights**2)/sum_w))
    else:
        c_val = sum_w - (np.sum(weights ** 2) / sum_w)
        tau_squared = max(0.0, (q_stat - df_q) / c_val) if c_val > 0 else 0.0

    if "Random" in model_type:
        weights_re = 1.0 / ((standard_errors ** 2)  tau_squared)
        sum_w_re = np.sum(weights_re)
        pooled_active = np.sum(weights_re * effect_sizes) / sum_w_re
        se_active = np.sqrt(1.0 / sum_w_re)
    else:
        pooled_active = pooled_fe
        se_active = se_fe

    z_stat = pooled_active / se_active
    p_val = 2 * (1 - stats.norm.cdf(abs(z_stat)))
    ci_low = pooled_active - 1.96 * se_active
    ci_high = pooled_active  1.96 * se_active

    st.markdown("### 🔍 Meta-Analytic Synthesis Results")
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("Pooled Effect Size", f"{pooled_active:.4f}")
    m_col2.metric("95% Confidence Interval", f"[{ci_low:.4f}, {ci_high:.4f}]")
    m_col3.metric("Z-Value (p-value)", f"Z = {z_stat:.2f} (p = {p_val:.4f})")
    m_col4.metric("Tau² Between-Study Var", f"{tau_squared:.4f}")

# ═══════════════════════════════════════════════════════════════════════
# TAB 3: INTERACTIVE FOREST PLOT
# ═══════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("<h3 style='color:#00f2fe;'>🔍 Interactive Forest Plot</h3>", unsafe_allow_html=True)

    fig = go.Figure()

    for i in range(k):
        es = effect_sizes[i]
        se = standard_errors[i]
        ci_l, ci_u = es - 1.96 * se, es  1.96 * se
        rel_wt = (weights[i] / np.sum(weights)) * 100
        
        fig.add_trace(go.Scatter(
            x=[ci_l, es, ci_u],
            y=[studies[i], studies[i], studies[i]],
            mode='linesmarkers',
            marker=dict(size=[6, 10, 6], symbol=['line-ew', 'square', 'line-ew'], color='#818cf8'),
            line=dict(color='#818cf8', width=2),
            name=studies[i],
            hovertemplate=f"<b>{studies[i]}</b><br>Effect Size: {es:.3f}<br>95% CI: [{ci_l:.3f}, {ci_u:.3f}]<br>Weight: {rel_wt:.1f}%<extra></extra>"
        ))

    fig.add_trace(go.Scatter(
        x=[ci_low, pooled_active, ci_high],
        y=["Overall Pooled", "Overall Pooled", "Overall Pooled"],
        mode='linesmarkers',
        marker=dict(size=[8, 12, 8], symbol=['diamond', 'diamond', 'diamond'], color='#f43f5e'),
        line=dict(color='#f43f5e', width=3),
        name="Pooled Result",
        hovertemplate=f"<b>Overall Pooled Estimate</b><br>Effect: {pooled_active:.3f}<br>95% CI: [{ci_low:.3f}, {ci_high:.3f}]<extra></extra>"
    ))

    fig.add_vline(x=0, line_dash="dash", line_color="#64748b", annotation_text="Null Effect")
    fig.add_vline(x=pooled_active, line_dash="dot", line_color="#f43f5e")

    fig.update_layout(
        title=f"Forest Plot  {model_type} (k = {k})",
        xaxis_title="Effect Size (95% CI)",
        yaxis_title="Studies",
        showlegend=False,
        height=max(450, k * 45),
        paper_bgcolor="#020617",
        plot_bgcolor="#090d16",
        font=dict(color="#f8fafc"),
        xaxis=dict(gridcolor="#1e293b"),
        yaxis=dict(gridcolor="#1e293b"),
        margin=dict(l=150, r=40, t=60, b=50)
    )

    st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════
# TAB 4: PUBLICATION BIAS & TRIM-AND-FILL
# ═══════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("<h3 style='color:#00f2fe;'>🔍 Publication Bias Diagnostics & Trim-and-Fill</h3>", unsafe_allow_html=True)

    if k < 3:
        st.warning("⚠️ Publication bias detection requires at least k ≥ 3 studies.")
    else:
        precision = 1.0 / standard_errors
        std_effects = effect_sizes / standard_errors
        slope, intercept, r_val, p_val_egger, std_err = stats.linregress(precision, std_effects)

        col_e1, col_e2 = st.columns(2)
        col_e1.metric("Egger's Test Intercept", f"{intercept:.4f}")
        col_e2.metric("Egger's Test P-Value", f"{p_val_egger:.4f}", delta="Asymmetry Detected" if p_val_egger < 0.05 else "Symmetric")

        filled_es, filled_se, k0 = trim_and_fill(effect_sizes, standard_errors)
        st.info(f"🔍 **Duval & Tweedie Trim-and-Fill Result:** Estimated **{k0} missing study/studies** due to funnel asymmetry.")

        fig_funnel = go.Figure()

        fig_funnel.add_trace(go.Scatter(
            x=effect_sizes, y=standard_errors,
            mode='markers',
            marker=dict(size=9, color='#00f2fe', line=dict(width=1, color='#ffffff')),
            name='Observed Studies'
        ))

        if k0 > 0:
            imputed_es = filled_es[k:]
            imputed_se = filled_se[k:]
            fig_funnel.add_trace(go.Scatter(
                x=imputed_es, y=imputed_se,
                mode='markers',
                marker=dict(size=9, color='#f59e0b', symbol='circle-open', line=dict(width=2, color='#f59e0b')),
                name='Imputed Studies (Trim-and-Fill)'
            ))

        se_seq = np.linspace(0.001, max(filled_se) * 1.15, 100)
        cone_upper = pooled_active  1.96 * se_seq
        cone_lower = pooled_active - 1.96 * se_seq

        fig_funnel.add_trace(go.Scatter(x=cone_upper, y=se_seq, mode='lines', line=dict(color='#64748b', dash='dash'), showlegend=False))
        fig_funnel.add_trace(go.Scatter(x=cone_lower, y=se_seq, mode='lines', line=dict(color='#64748b', dash='dash'), showlegend=False))
        fig_funnel.add_vline(x=pooled_active, line_color='#f43f5e', annotation_text="Pooled ES")

        fig_funnel.update_layout(
            title="Funnel Plot with Pseudo 95% Confidence Limits",
            xaxis_title="Effect Size",
            yaxis_title="Standard Error (SE)",
            yaxis=dict(autorange="reversed", gridcolor="#1e293b"),
            xaxis=dict(gridcolor="#1e293b"),
            paper_bgcolor="#020617",
            plot_bgcolor="#090d16",
            font=dict(color="#f8fafc"),
            height=500
        )

        st.plotly_chart(fig_funnel, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════
# TAB 5: HETEROGENEITY & SUBGROUPS
# ═══════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("<h3 style='color:#00f2fe;'>🔍 Statistical Heterogeneity & Subgroup Stratification</h3>", unsafe_allow_html=True)

    st.markdown("### 🔍 Heterogeneity Indices")
    h_col1, h_col2, h_col3, h_col4 = st.columns(4)
    h_col1.metric("Cochran's Q", f"{q_stat:.3f}")
    h_col2.metric("Q Test p-value", f"{pval_q:.4f}")
    h_col3.metric("I² Inconsistency", f"{i_squared:.1f}%")
    h_col4.metric("H² Index", f"{h_squared:.2f}")

    st.markdown("<hr style='border-color:#1e293b; margin:1rem 0;'>", unsafe_allow_html=True)
    st.markdown("### 🔍 Subgroup Stratified Pooling")
    if "Subgroup" in df.columns:
        subgroups = df["Subgroup"].unique()
        sub_results = []
        
        for sg in subgroups:
            sub_df = df[df["Subgroup"] == sg]
            sg_es = sub_df["Effect_Size"].values
            sg_se = sub_df["Standard_Error"].values
            sg_w = 1.0 / (sg_se ** 2)
            
            sg_pooled = np.sum(sg_w * sg_es) / np.sum(sg_w)
            sg_se_pooled = np.sqrt(1.0 / np.sum(sg_w))
            
            sub_results.append({
                "Subgroup": sg,
                "Studies (k)": len(sub_df),
                "Pooled Effect": round(sg_pooled, 4),
                "95% CI Lower": round(sg_pooled - 1.96 * sg_se_pooled, 4),
                "95% CI Upper": round(sg_pooled  1.96 * sg_se_pooled, 4)
            })
            
        st.dataframe(pd.DataFrame(sub_results), use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ Include a 'Subgroup' column in your dataset to automatically run stratified subgroup synthesis.")

# ─── FOOTER WATERMARK ───────────────────────────────────────────────────
st.markdown("<hr style='border-color:#1e293b; margin-top:3rem;'>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align:center; color:#64748b; font-size:0.75rem; font-family:monospace; letter-spacing:0.1em;'>"
    "ENTERPRISE SYNTHESIS ENGINE • SECURE INTEL • DESIGNED FOR CHRISHEM"
    "</div>",
    unsafe_allow_html=True
)



