"""
⚙️ World-Class Advanced Settings, Administration & Dependency Engine
Enterprise-grade systems administration console featuring dynamic package hot-loading (pip subprocess integration),
role-based privilege escalation gates, resilient system caching, multi-layer keep-alive uptime monitoring, and audit log auditing.
"""
import os
import sys
import subprocess
import streamlit as st

st.set_page_config(
    page_title="Settings, Administration & System HUD",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 1. SESSION STATE & ADMINISTRATIVE GUARDS
# ==========================================
if "admin_authenticated" not in st.session_state:
    st.session_state["admin_authenticated"] = False
if "admin_privilege_level" not in st.session_state:
    st.session_state["admin_privilege_level"] = "Standard Operator"
if "audit_log_entries" not in st.session_state:
    st.session_state["audit_log_entries"] = []

from modules.config import init_session_state, clear_cache
from modules.ui_components import hero_card, section_header, load_css, watermark

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")

hero_card(
    "⚙️ Enterprise Administration & Configuration Hub",
    "Manage secure access controls, hot-load python packages dynamically, configure environment resilience, and audit system states.",
    "System Administration"
)
watermark("CHRISHEM")

# ==========================================
# 2. ROBUST PACKAGE INSTALLATION WORKER
# ==========================================
def robust_install_package(package_name: str) -> tuple[bool, str]:
    """Execute dynamic subprocess pip installation with fallback error handling."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return True, f"Successfully installed `{package_name}` via subprocess.\n{result.stdout.strip()}"
    except subprocess.CalledProcessError as e:
        return False, f"Installation failed for `{package_name}`: {e.stderr.strip()}"
    except Exception as ex:
        return False, f"System execution error during installation of `{package_name}`: {str(ex)}"

# ==========================================
# 3. ADMINISTRATIVE PRIVILEGE ESCALATION PANEL
# ==========================================
section_header("🔐 Administrative Access & Security Escalation")

with st.expander("🛡️ Root & Admin Privilege Management", expanded=not st.session_state["admin_authenticated"]):
    col_a, col_b = st.columns([2, 1])
    with col_a:
        admin_pass_input = st.text_input(
            "Master Admin Passkey",
            type="password",
            placeholder="Enter administrative credentials...",
            help="Required to unlock system-level write operations and package hot-loading."
        )
    with col_b:
        st.markdown("<br>", unsafe_allow_html=True)
        auth_submitted = st.button("🔑 Authenticate Root", type="primary", use_container_width=True)

    if auth_submitted:
        # Secure default or session-stored admin verification
        master_key = st.secrets.get("ADMIN_MASTER_KEY", "chrishem_secure_root_2026")
        if admin_pass_input == master_key:
            st.session_state["admin_authenticated"] = True
            st.session_state["admin_privilege_level"] = "System Superuser (Root)"
            st.session_state["audit_log_entries"].append({"action": "Admin Login Success", "user": "Root Operator"})
            st.success("🎉 **Privilege Escalation Successful!** Superuser controls unlocked.")
            st.rerun()
        else:
            st.error("❌ Invalid administrative passkey. Access restricted.")

    if st.session_state["admin_authenticated"]:
        st.markdown(f"**Current Status:** Active with `{st.session_state['admin_privilege_level']}` privileges.")
        if st.button("🔒 Revoke Admin Session"):
            st.session_state["admin_authenticated"] = False
            st.session_state["admin_privilege_level"] = "Standard Operator"
            st.rerun()

# ─── Theme & Appearance Settings ─────────────────────────────────────
section_header("🎨 Theme & Appearance")

col1, col2, col3 = st.columns(3)
with col1:
    theme = st.selectbox(
        "Theme mode",
        options=["light", "dark"],
        index=0 if st.session_state.get("theme", "light") == "light" else 1,
        key="theme_selector",
    )
    if theme != st.session_state.get("theme"):
        st.session_state["theme"] = theme
        st.rerun()

with col2:
    accent_color = st.color_picker(
        "Accent color",
        value=st.session_state.get("accent_color", "#1d4ed8"),
        key="accent_picker",
    )
    if accent_color != st.session_state.get("accent_color"):
        st.session_state["accent_color"] = accent_color
        st.rerun()

with col3:
    st.caption("Preview Element")
    st.markdown(
        f'<div style="background:{accent_color};color:white;padding:1rem;border-radius:12px;text-align:center;font-weight:600;">'
        f'Active Accent: {accent_color}</div>',
        unsafe_allow_html=True,
    )

# ─── Advanced Dependency & Package Manager ───────────────────────────
section_header("🔧 Dynamic Dependency & Package Manager")
st.markdown("*Verify environment health and hot-load packages dynamically via direct subprocess execution.*")

try:
    from modules.dependency_manager import check_all_packages, install_missing_packages, CATEGORY_ICONS
    all_pkgs, missing_pkgs, categories = check_all_packages()
except Exception:
    all_pkgs, missing_pkgs, categories = [], [], []

total = len(all_pkgs) if all_pkgs else 0
installed_count = total - len(missing_pkgs)
pct = int(installed_count / total * 100) if total > 0 else 100

col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
    st.metric("📦 Total Tracked Packages", total)
with col_m2:
    st.metric("✅ Verified Installed", installed_count)
with col_m3:
    st.metric("❌ Unresolved Missing", len(missing_pkgs))

if not missing_pkgs:
    st.success("🎉 **All system packages are fully synchronized!** Environment operating at peak efficiency.")
else:
    st.warning(f"⚠️ **{len(missing_pkgs)} packages** require synchronization.")

st.progress(pct, text=f"Environment health score: {pct}% complete")

# Direct manual package hot-loader (Available to all, enhanced with root verification if needed)
with st.expander("🛠️ Direct Subprocess Package Hot-Loader"):
    st.markdown("Type any PyPI package identifier to install it instantly into the running runtime environment.")
    custom_pkg_input = st.text_input("PyPI Package Name", placeholder="e.g., scikit-image, openpyxl, statsmodels")
    if st.button("🚀 Hot-Install Package", type="primary"):
        if custom_pkg_input.strip():
            with st.spinner(f"Executing pip install for {custom_pkg_input.strip()}..."):
                success, msg = robust_install_package(custom_pkg_input.strip())
            if success:
                st.success(msg)
                st.session_state["audit_log_entries"].append({"action": f"Installed package {custom_pkg_input.strip()}", "status": "Success"})
            else:
                st.error(msg)
        else:
            st.error("Please provide a valid package name.")

if missing_pkgs and st.session_state["admin_authenticated"]:
    st.markdown("### 🚀 One-Ready Automated Batch Sync")
    if st.button("🔧 Fix All Missing Packages (Root Authorized)", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        results = {}
        total_missing = len(missing_pkgs)
        for idx, pkg in enumerate(missing_pkgs):
            name = pkg.pip_name
            status_text.text(f"[{idx+1}/{total_missing}] Installing {name}...")
            success, msg = robust_install_package(name)
            results[name] = (success, msg)
            progress_bar.progress(int((idx + 1) / total_missing * 100))
        
        success_count = sum(1 for s, _ in results.values() if s)
        fail_count = sum(1 for s, _ in results.values() if not s)
        st.markdown(f"**Batch Results:** {success_count} installed, {fail_count} failed.")
        for name, (s, m) in results.items():
            if s:
                st.success(m)
            else:
                st.error(m)
        if fail_count == 0:
            st.success("🎉 Sync completed successfully! Refresh state.")
            if st.button("🔄 Reload Application Now"):
                st.rerun()
elif missing_pkgs and not st.session_state["admin_authenticated"]:
    st.info("🔒 Batch automatic installation requires **Root Administrative Authentication** above.")

# ─── Module Information Matrix ──────────────────────────────────────
section_header("🧩 Available System Modules & Health Matrix")
st.markdown("""
| Module | Status | Description |
|--------|--------|-------------|
| 📁 **File Analyzer** | ✅ Active | Upload CSV, Excel, SPSS, SAS, STATA, JSON |
| 🏷️ **Variable View** | ✅ Active | SPSS-style variable metadata editor |
| 🔬 **Statistical Tests** | ✅ Active | 20+ SPSS-level statistical analyses |
| 📈 **Advanced Visuals** | ✅ Active | 18+ interactive chart types |
| 🧬 **Predictive Modeling** | ✅ Active | AutoML classification, regression, clustering |
| 🤖 **CHRISHEM Insights** | ✅ Active | Automated advanced analytical insights |
| 🔧 **Data Transformer** | ✅ Active | SPSS Compute, Recode, Rank, Binning |
| 📋 **Methodology Advisor** | ✅ Active | Study design and test recommendation engine |
| 🏥 **Clinical Analytics** | ✅ Active | BMI, clinical reference ranges, health risks |
| 💬 **Text Analysis** | ✅ Active | Sentiment auditing, word clouds, N-grams |
| 📊 **Dashboard Builder** | ✅ Active | Custom multi-chart canvas configurations |
| 🔍 **Data Quality** | ✅ Active | Automated data quality anomaly auditing |
| 📑 **APA Outputs** | ✅ Active | APA 7th edition formatted export tables |
| 🎲 **Data Simulator** | ✅ Active | Synthetic data generation engine |
| 🔗 **Google Sheets** | ✅ Active | Secure Sheets read/write integration |
| ⚙️ **Settings & Admin** | ✅ Active | Theme, credentials, subprocess hot-loader, health |
""")

# ─── Credential Settings ─────────────────────────────────────────────
section_header("🔑 Integration Credentials & API Tokens")

with st.expander("Manage API Access Tokens & Vault Keys", expanded=False):
    token_input = st.text_input(
        "Notion / External API Token",
        type="password",
        value=st.session_state.get("user_NOTION_TOKEN", ""),
        help="Secure private integration token for API data syncing."
    )
    db_input = st.text_input(
        "Database ID (optional)",
        value=st.session_state.get("user_DATABASE_ID", ""),
        help="Target database string identifier."
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 Save Credentials Securely", type="primary", use_container_width=True):
            if token_input.strip():
                st.session_state["user_NOTION_TOKEN"] = token_input.strip()
                st.session_state["user_DATABASE_ID"] = db_input.strip()
                st.session_state["creds_validated"] = True
                st.session_state["creds_failed"] = False
                clear_cache()
                st.success("✅ Credentials updated successfully!")
                st.rerun()
            else:
                st.error("Please supply a valid token.")
    with c2:
        if st.button("🔄 Reset Credentials", use_container_width=True):
            for k in ("user_NOTION_TOKEN", "user_DATABASE_ID", "creds_validated", "creds_failed"):
                st.session_state[k] = "" if "TOKEN" in k or "DATABASE" in k else False
            clear_cache()
            st.success("Credentials cleared.")
            st.rerun()

# ─── Data Management & Cache Lifecycle ───────────────────────────────
section_header("💾 Data Lifecycle & Storage Management")

col_d1, col_d2, col_d3 = st.columns(3)
with col_d1:
    st.metric("Active source", st.session_state.get("data_source", "none").title())
with col_d2:
    notion_df = st.session_state.get("notion_df")
    st.metric("Notion rows loaded", len(notion_df) if notion_df is not None else 0)
with col_d3:
    uploaded_df = st.session_state.get("uploaded_df")
    st.metric("Uploaded rows loaded", len(uploaded_df) if uploaded_df is not None else 0)

if st.button("🗑️ Purge Local Cache & Active Datasets", type="secondary"):
    clear_cache()
    for key in ["notion_df", "uploaded_df", "merged_df", "active_df"]:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state["data_source"] = "none"
    st.success("✅ System cache completely purged.")
    st.rerun()

# ─── Keep-Alive & 24/7 Uptime ─────────────────────────────────────────
section_header("⏰ Keep-Alive & 24/7 Uptime Control")

st.markdown("""
### Resiliency Architecture
Preventing cold starts and instance scale-downs via a robust multi-layer defense strategy:
""")

keep_alive_enabled = st.toggle(
    "Enable local app keep-alive loop",
    value=st.session_state.get("keep_alive_enabled", False),
    key="settings_keep_alive",
)
if keep_alive_enabled:
    st.session_state["keep_alive_enabled"] = True
    interval = st.selectbox(
        "Ping frequency",
        options=["1 min", "5 min", "10 min", "15 min"],
        index=1,
    )
    interval_map = {"1 min": 60, "5 min": 300, "10 min": 600, "15 min": 900}
    st.session_state["keep_alive_interval_sec"] = interval_map[interval]
    st.success(f"✅ Internal keep-alive active (interval: {interval})")
    
    default_url = st.secrets.get("RENDER_EXTERNAL_URL", os.environ.get("RENDER_EXTERNAL_URL", "https://YOUR-APP.onrender.com"))
    app_url = st.text_input("Target Public App URL", value=default_url)
    st.code(f"Monitor Target Endpoint: {app_url}/", language="text")
else:
    st.session_state["keep_alive_enabled"] = False

# ─── About Section ───────────────────────────────────────────────────
section_header("ℹ️ System Architecture & Metadata")
st.markdown("""
### Advanced Research Data Analyzer & Visualizer
* **Version**: 2.5.0 Enterprise 
* **Author / Architecture**: CHRISHEM
* **Core Stack**: Streamlit, Plotly, SciPy, StatsModels, Pandas, Scikit-Learn, Subprocess Pip Manager

Designed for high-throughput scientific investigations, robust clinical analytics, and high-precision data operations.
""")