st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)

"""
⚙️ Settings Page — Theme, credentials, dependencies, keep-alive, and data management.
"""
import os
import sys
import streamlit as st

st.set_page_config(page_title="Settings", layout="wide", page_icon="⚙️")

from modules.config import init_session_state, clear_cache
from modules.ui_components import hero_card, section_header, load_css, watermark

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")
hero_card("⚙️ Settings & Configuration", "Manage your preferences, credentials, dependencies, and data.", "Configuration")
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
    st.caption("Preview")
    st.markdown(
        f'<div style="background:{accent_color};color:white;padding:1rem;border-radius:12px;text-align:center;">'
        f'Accent Color: {accent_color}</div>',
        unsafe_allow_html=True,
    )

# ─── Dependency Manager ─────────────────────────────────────────────
section_header("🔧 Dependency Manager")
st.markdown("*Check, verify, and install all required Python packages with one click.*")

from modules.dependency_manager import check_all_packages, install_missing_packages, install_package, CATEGORY_ICONS, CATEGORY_ORDER

all_pkgs, missing_pkgs, categories = check_all_packages()

total = len(all_pkgs)
installed_count = total - len(missing_pkgs)
pct = int(installed_count / total * 100) if total > 0 else 0

# Overall status
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📦 Total Packages", total)
with col2:
    st.metric("✅ Installed", installed_count)
with col3:
    st.metric("❌ Missing", len(missing_pkgs))

if len(missing_pkgs) == 0:
    st.success("🎉 **All packages are installed!** The application is fully ready.")
else:
    st.warning(f"⚠️ **{len(missing_pkgs)} packages** missing — click 'Fix All' below to install them.")

st.progress(pct, text=f"{pct}% complete")

# Per-category expanders
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
                st.markdown("**✅ All installed!**")

# One-click fix button
if missing_pkgs:
    st.markdown("---")
    st.markdown("### 🚀 One-Click Fix")

    missing_names = [p.pip_name for p in missing_pkgs]
    st.markdown(f"Packages to install: `{', '.join(missing_names)}`")

    col1, col2 = st.columns([1, 3])
    with col1:
        fix_clicked = st.button("🔧 Fix All Missing Packages", type="primary", use_container_width=True)

    if fix_clicked:
        progress_bar = st.progress(0)
        status_text = st.empty()

        def progress_cb(current, total, msg):
            progress_bar.progress(int(current / total * 100))
            status_text.text(f"[{current}/{total}] {msg}")

        with st.spinner("Installing packages... This may take several minutes."):
            results = install_missing_packages(missing_names, progress_cb)

        success_count = sum(1 for s, _ in results.values() if s)
        fail_count = sum(1 for s, _ in results.values() if not s)

        st.markdown(f"**{success_count} succeeded**, **{fail_count} failed**")
        for name, (success, msg) in results.items():
            if success:
                st.success(msg)
            else:
                st.error(msg)

        if fail_count == 0:
            st.success("🎉 **All packages installed!** Refresh the app to apply changes.")
            if st.button("🔄 Refresh App Now", type="primary"):
                st.rerun()

    # Individual install
    with st.expander("🛠️ Install Individual Package"):
        pkg_names = sorted([p.pip_name for p in missing_pkgs])
        selected_pkg = st.selectbox("Select a package to install", options=pkg_names)
        if st.button(f"📥 Install {selected_pkg}"):
            with st.spinner(f"Installing {selected_pkg}..."):
                success, message = install_package(selected_pkg)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

st.markdown("---")

# ─── Module Information ─────────────────────────────────────────────
section_header("🧩 Available Modules")
st.markdown("""
| Module | Version | Description |
|--------|---------|-------------|
| 📁 **File Analyzer** | ✅ | Upload CSV, Excel, SPSS, SAS, STATA, JSON |
| 🏷️ **Variable View** | ✅ NEW | SPSS-style variable metadata editor |
| 🔬 **Statistical Tests** | ✅ | 20+ SPSS-level statistical analyses |
| 📈 **Advanced Visuals** | ✅ | 18+ interactive chart types |
| 🧬 **Predictive Modeling** | ✅ NEW | AutoML classification, regression, clustering |
| 🤖 **CHRISHEM Insights** | ✅ | Automated CHRISHEM-powered data analysis |
| 🔧 **Data Transformer** | ✅ NEW | SPSS Compute, Recode, Rank, Binning |
| 📋 **Methodology Advisor** | ✅ NEW | Study design and test recommendation |
| 🏥 **Clinical Analytics** | ✅ NEW | BMI, clinical ranges, health risk |
| 💬 **Text Analysis** | ✅ NEW | Sentiment, word clouds, N-grams |
| 📊 **Dashboard Builder** | ✅ NEW | Custom multi-chart dashboards |
| 🔍 **Data Quality** | ✅ NEW | Automated data quality audit |
| 📑 **APA Outputs** | ✅ NEW | APA 7th edition formatted results |
| 🎲 **Data Simulator** | ✅ NEW | Synthetic data generation |
| 🔗 **Google Sheets** | ✅ NEW | Sheets read/write integration |
| ⚙️ **Settings** | ✅ | Theme, credentials, dependencies, keep-alive |
""")

# ─── Credential Settings ─────────────────────────────────────────────
section_header("🔑 Notion Credentials")

with st.expander("Update Notion Credentials", expanded=False):
    from modules.ui_components import sidebar_card
    import requests

    token_input = st.text_input(
        "Notion API Token",
        type="password",
        value=st.session_state.get("user_NOTION_TOKEN", ""),
    )
    db_input = st.text_input(
        "Database ID (optional)",
        value=st.session_state.get("user_DATABASE_ID", ""),
    )

    if st.button("💾 Save Credentials", type="primary"):
        if token_input.strip():
            st.session_state["user_NOTION_TOKEN"] = token_input.strip()
            st.session_state["user_DATABASE_ID"] = db_input.strip()
            st.session_state["creds_validated"] = True
            st.session_state["creds_failed"] = False
            clear_cache()
            st.success("✅ Credentials saved! Redirecting to dashboard...")
            st.rerun()
        else:
            st.error("Please provide a Notion API Token.")

    if st.button("🔄 Reset All Credentials"):
        for k in ("user_NOTION_TOKEN", "user_DATABASE_ID", "creds_validated", "creds_failed"):
            st.session_state[k] = "" if "TOKEN" in k or "DATABASE" in k else False
        clear_cache()
        st.success("Credentials reset. You'll need to re-enter them.")
        st.rerun()

# ─── Data Management ─────────────────────────────────────────────────
section_header("💾 Data Management")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Current data source", st.session_state.get("data_source", "none").title())
with col2:
    notion_df = st.session_state.get("notion_df")
    st.metric("Notion rows", len(notion_df) if notion_df is not None else 0)
with col3:
    uploaded_df = st.session_state.get("uploaded_df")
    st.metric("Uploaded rows", len(uploaded_df) if uploaded_df is not None else 0)

if st.button("🗑️ Clear All Cached Data", type="secondary"):
    clear_cache()
    for key in ["notion_df", "uploaded_df", "merged_df", "active_df"]:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state["data_source"] = "none"
    st.success("✅ Cache cleared!")
    st.rerun()

# ─── Keep-Alive Settings ─────────────────────────────────────────────
section_header("⏰ Keep-Alive & 24/7 Uptime")

st.markdown("""
### Multi-Layer Keep-Alive System
This app uses **5 layers** to prevent sleep on free hosting plans:

| Layer | Description | Status |
|-------|-------------|--------|
| **1** 🖥️ | **Client-side JS** — Pings the app from your browser | ✅ Active when enabled |
| **2** ⚙️ | **Server-side thread** — Background self-ping from server | ✅ Active when enabled |
| **3** 📡 | **Streamlit heartbeat** — Built-in session keep-alive | ✅ Always active |
| **4** ⏲️ | **Render cron job** — Scheduled pings from Render | ✅ Configured in render.yaml |
| **5** 🔄 | **Auto-restart watchdog** — Detects stale state and recovers | ✅ Active |
""")

keep_alive_enabled = st.toggle(
    "Enable keep-alive system",
    value=st.session_state.get("keep_alive_enabled", False),
    key="settings_keep_alive",
)
if keep_alive_enabled:
    st.session_state["keep_alive_enabled"] = True
    interval = st.selectbox(
        "Ping interval",
        options=["1 min", "5 min", "10 min", "15 min"],
        index=1,
    )
    interval_map = {"1 min": 60, "5 min": 300, "10 min": 600, "15 min": 900}
    st.session_state["keep_alive_interval_sec"] = interval_map[interval]
    st.success(f"✅ Keep-alive enabled — will ping every {interval}")

    st.info(
        "💡 **For true 24/7 uptime**, also set up a free external monitor:\n\n"
        "- **UptimeRobot** (uptimerobot.com) — 50 monitors free, 5-min interval\n"
        "- **cron-job.org** — Unlimited free, 10-min interval\n"
        "- **Better Uptime** (betteruptime.com) — 10 monitors free\n\n"
        "Set the monitor to ping your app URL."
    )
    app_url = st.text_input(
        "Your app URL (for external monitors)",
        value=st.secrets.get("RENDER_EXTERNAL_URL", os.environ.get("RENDER_EXTERNAL_URL", "https://YOUR-APP.onrender.com")),
    )
    st.code(f"Ping URL: {app_url}/", language="text")
else:
    st.session_state["keep_alive_enabled"] = False

# ─── About Section ───────────────────────────────────────────────────
section_header("ℹ️ About")
st.markdown("""
### Advanced Research Data Analyzer & Visualizer
**Version**: 2.0.0 | **Author**: CHRISHEM

**Capabilities**:
- 🔗 **Notion API** — Live sync with all 20+ property types
- 📁 **File Upload** — CSV, Excel, SPSS (.sav), SAS, STATA, JSON, Parquet
- 🔬 **Statistical Tests** — 20+ SPSS-level analyses (t-test, ANOVA, correlation, regression, etc.)
- 📈 **Visualizations** — 18+ interactive chart types with auto-recommendation
- 🤖 **CHRISHEM Insights** — Automated profiling, outlier detection, smart recommendations
- 📄 **Report Generation** — Downloadable reports in Markdown, HTML, PDF
- ⏰ **24/7 Uptime** — 5-layer keep-alive system

**Built with**: Streamlit, Plotly, SciPy, StatsModels, Pandas, scikit-learn
""")

import os

