import os
import sys
import streamlit as st

st.set_page_config(page_title="Settings & Configuration", layout="wide", page_icon="⚙️")

from modules.config import init_session_state, clear_cache
from modules.ui_components import hero_card, section_header, load_css, watermark

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")
hero_card("⚙️ Settings & Configuration", "Manage your preferences, credentials, dependencies, and data lifecycle.", "Configuration")
watermark("CHRISHEM")

# ─── Theme Settings ──────────────────────────────────────────────────
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

# ─── Dependency Manager ─────────────────────────────────────────────
section_header("🔧 Dependency Manager")
st.markdown("*Check, verify, and manage required application packages dynamically.*")

from modules.dependency_manager import check_all_packages, install_missing_packages, install_package, CATEGORY_ICONS

all_pkgs, missing_pkgs, categories = check_all_packages()

total = len(all_pkgs)
installed_count = total - len(missing_pkgs)
pct = int(installed_count / total * 100) if total > 0 else 0

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📦 Total Tracked", total)
with col2:
    st.metric("✅ Installed", installed_count)
with col3:
    st.metric("❌ Missing", len(missing_pkgs))

if len(missing_pkgs) == 0:
    st.success("🎉 **All packages are installed!** System environment is fully operational.")
else:
    st.warning(f"⚠️ **{len(missing_pkgs)} packages** missing — click 'Fix All' below to sync dependencies.")

st.progress(pct, text=f"Environment health: {pct}% complete")

from modules.dependency_manager import get_package_summary
summary = get_package_summary()

for cat in categories:
    cat_data = summary[cat]
    icon = CATEGORY_ICONS.get(cat, "📦")
    with st.expander(
        f"{icon} **{cat}** — {cat_data['installed']}/{cat_data['total']} installed",
        expanded=cat_data["missing"] > 0 and cat_data["missing"] < cat_data["total"],
    ):
        cols = st.columns(2)
        with cols[0]:
            st.markdown("**✅ Installed:**")
            for name in cat_data["installed_names"]:
                pkg = next((p for p in all_pkgs if p.pip_name == name), None)
                version = f" v{pkg.installed_version}" if pkg and pkg.installed_version else ""
                st.markdown(f"- ✅ {name}{version}")
        with cols[1]:
            if cat_data["missing_names"]:
                st.markdown("**❌ Missing:**")
                for name in cat_data["missing_names"]:
                    pkg = next((p for p in all_pkgs if p.pip_name == name), None)
                    desc = f" — {pkg.description}" if pkg else ""
                    st.markdown(f"- ❌ {name}{desc}")
            else:
                st.markdown("**✅ All operational!**")

if missing_pkgs:
    st.markdown("---")
    st.markdown("### 🚀 One-Click Environment Sync")
    missing_names = [p.pip_name for p in missing_pkgs]
    st.markdown(f"Target packages: `{', '.join(missing_names)}`")

    col1, col2 = st.columns([1, 3])
    with col1:
        fix_clicked = st.button("🔧 Fix All Missing Packages", type="primary", use_container_width=True)

    if fix_clicked:
        progress_bar = st.progress(0)
        status_text = st.empty()

        def progress_cb(current, total, msg):
            progress_bar.progress(int(current / total * 100))
            status_text.text(f"[{current}/{total}] {msg}")

        with st.spinner("Synchronizing environment packages..."):
            results = install_missing_packages(missing_names, progress_cb)

        success_count = sum(1 for s, _ in results.values() if s)
        fail_count = sum(1 for s, _ in results.values() if not s)

        st.markdown(f"**{success_count} installed**, **{fail_count} failed**")
        for name, (success, msg) in results.items():
            if success:
                st.success(msg)
            else:
                st.error(msg)

        if fail_count == 0:
            st.success("🎉 **Sync complete!** Refresh app state.")
            if st.button("🔄 Refresh App Now", type="primary"):
                st.rerun()

    with st.expander("🛠️ Install Individual Package"):
        pkg_names = sorted([p.pip_name for p in missing_pkgs])
        selected_pkg = st.selectbox("Select target package", options=pkg_names)
        if st.button(f"📥 Install {selected_pkg}"):
            with st.spinner(f"Installing {selected_pkg}..."):
                success, message = install_package(selected_pkg)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

st.markdown("---")

# ─── Module Information Matrix ──────────────────────────────────────
section_header("🧩 Available System Modules")
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
| ⚙️ **Settings** | ✅ Active | Theme, credentials, dependencies, and health |
""")

# ─── Credential Settings ─────────────────────────────────────────────
section_header("🔑 Integration Credentials")

with st.expander("Manage API Access Tokens", expanded=False):
    token_input = st.text_input(
        "Notion API Token",
        type="password",
        value=st.session_state.get("user_NOTION_TOKEN", ""),
        help="Secure private integration token for Notion DB syncing."
    )
    db_input = st.text_input(
        "Database ID (optional)",
        value=st.session_state.get("user_DATABASE_ID", ""),
        help="Target database string identifier."
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 Save Credentials", type="primary", use_container_width=True):
            if token_input.strip():
                st.session_state["user_NOTION_TOKEN"] = token_input.strip()
                st.session_state["user_DATABASE_ID"] = db_input.strip()
                st.session_state["creds_validated"] = True
                st.session_state["creds_failed"] = False
                clear_cache()
                st.success("✅ Credentials updated successfully!")
                st.rerun()
            else:
                st.error("Please supply a valid API Token.")
    with c2:
        if st.button("🔄 Reset Credentials", use_container_width=True):
            for k in ("user_NOTION_TOKEN", "user_DATABASE_ID", "creds_validated", "creds_failed"):
                st.session_state[k] = "" if "TOKEN" in k or "DATABASE" in k else False
            clear_cache()
            st.success("Credentials cleared.")
            st.rerun()

# ─── Data Management & Cache Lifecycle ───────────────────────────────
section_header("💾 Data Lifecycle & Storage")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Active source", st.session_state.get("data_source", "none").title())
with col2:
    notion_df = st.session_state.get("notion_df")
    st.metric("Notion rows loaded", len(notion_df) if notion_df is not None else 0)
with col3:
    uploaded_df = st.session_state.get("uploaded_df")
    st.metric("Uploaded rows loaded", len(uploaded_df) if uploaded_df is not None else 0)

if st.button("🗑️ Purge Local Cache & Active Datasets", type="secondary"):
    clear_cache()
    for key in ["notion_df", "uploaded_df", "merged_df", "active_df"]:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state["data_source"] = "none"
    st.success("✅ System cache completely cleared.")
    st.rerun()

# ─── Keep-Alive & 24/7 Uptime ─────────────────────────────────────────
section_header("⏰ Keep-Alive & 24/7 Uptime Control")

st.markdown("""
### Resiliency Architecture
Preventing cold starts and platform scale-downs on free instance infrastructure via a **5-layer defensive strategy**:

| Layer | Component | Status |
|-------|-----------|--------|
| **1** 🖥️ | **Client-side JS Ping** — Active browser connection loop | Configurable below |
| **2** ⚙️ | **Server Threading** — Automated background loop worker | Configurable below |
| **3** 📡 | **Streamlit Heartbeat** — Native socket connection keep-alive | ✅ Active |
| **4** ⏲️ | **External Cron Worker** — Automated REST ping hooks | Recommended |
| **5** 🔄 | **Auto-Watchdog** — State drift and crash self-recovery | ✅ Active |
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

    st.info(
        "💡 **For bulletproof 24/7 hosting uptime**, pair this with an external cron monitor:\n\n"
        "- **UptimeRobot** (uptimerobot.com) — Free Tier (5-min interval)\n"
        "- **cron-job.org** — Free Tier (Flexible intervals)\n\n"
        "Point your monitor to the public endpoint URL below."
    )
    
    default_url = st.secrets.get("RENDER_EXTERNAL_URL", os.environ.get("RENDER_EXTERNAL_URL", "https://YOUR-APP.onrender.com"))
    app_url = st.text_input("Target Public App URL", value=default_url)
    st.code(f"Monitor Target Endpoint: {app_url}/", language="text")
else:
    st.session_state["keep_alive_enabled"] = False

# ─── About Section ───────────────────────────────────────────────────
section_header("ℹ️ System Architecture & Metadata")
st.markdown("""
### Advanced Research Data Analyzer & Visualizer
* **Version**: 2.0.0 
* **Author / Architecture**: CHRISHEM
* **Core Stack**: Streamlit, Plotly, SciPy, StatsModels, Pandas, Scikit-Learn

Designed for high-throughput scientific investigations, robust clinical analytics, and high-precision data operations.
""")