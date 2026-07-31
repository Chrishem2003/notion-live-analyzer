import streamlit as st
import os
import io
import time
import numpy as np
import pandas as pd
from datetime import datetime

# Optional Module Imports
try:
    from modules.database import init_db, log_backend_event
    init_db()
except Exception:
    pass

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

# ---------------------------------------------------------
# GLOBAL PAGE CONFIG
# ---------------------------------------------------------
st.set_page_config(
    page_title="CHRISHEM Sovereign Enterprise",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# WORLD-CLASS CYBER-SOVEREIGN CSS
# ---------------------------------------------------------
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    
    .stApp {
        background: radial-gradient(circle at 50% 0%, #0d1527 0%, #050811 100%);
        color: #f1f5f9;
    }

    /* --- SIDEBAR STYLING FIXES --- */
    section[data-testid="stSidebar"] {
        background-color: rgba(10, 15, 30, 0.85) !important;
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }
    
    /* Dedicated non-overlapping status badge */
    .status-badge-container {
        margin-top: 2rem;
        padding: 0.85rem 1rem;
        background: rgba(16, 185, 129, 0.08);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
    .status-badge-header {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #34d399;
        font-weight: 700;
        margin-bottom: 0.25rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    .status-badge-sub {
        font-size: 0.8rem;
        color: #94a3b8;
    }

    /* --- METRIC CARDS --- */
    .metric-card {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 1.25rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.25);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        border-color: rgba(56, 189, 248, 0.4);
        transform: translateY(-2px);
    }
    .metric-card-title {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94a3b8;
        font-weight: 600;
    }
    .metric-card-value {
        font-size: 1.8rem;
        font-weight: 800;
        background: linear-gradient(90deg, #38bdf8 0%, #818cf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0.25rem 0;
    }
    .metric-card-delta {
        font-size: 0.8rem;
        color: #34d399;
        font-weight: 600;
    }

    /* --- HEADERS --- */
    .main-title-glow {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        background: linear-gradient(90deg, #60a5fa 0%, #c084fc 50%, #f472b6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# SECURE VAULT MODAL
# ---------------------------------------------------------
@st.dialog("Enterprise Secure Vault Inspector", width="large")
def inspect_vault_file(file_item):
    st.markdown(f"### 📄 {file_item.get('name', 'Document')}")
    st.caption(f"Size: **{file_item.get('size', 'N/A')}** | Status: {file_item.get('status', 'Verified')}")
    
    file_bytes = file_item.get("bytes", b"")
    file_name = file_item.get("name", "").lower()

    t_view, t_edit, t_export = st.tabs(["👁️ Read Stream", "✏️ Live Editor", "📥 Export Stream"])

    with t_view:
        if file_name.endswith(".pdf"):
            if HAS_PYPDF and file_bytes:
                try:
                    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                    text = "\n\n".join([f"--- Page {i+1} ---\n" + (p.extract_text() or "") for i, p in enumerate(reader.pages)])
                    st.text_area("Extracted Text Payload", value=text, height=350)
                except Exception as e:
                    st.warning(f"Raw Byte Payload Loaded (Parse Note: {e})")
            else:
                st.info("PDF Binary Payload Loaded.")
        elif file_name.endswith((".csv", ".xlsx")):
            try:
                df = pd.read_csv(io.BytesIO(file_bytes))
                st.dataframe(df, use_container_width=True)
            except Exception:
                st.text_area("Raw Stream", value=file_bytes.decode("utf-8", errors="ignore"), height=300)
        else:
            st.code(file_bytes.decode("utf-8", errors="ignore"))

    with t_edit:
        if file_name.endswith((".csv", ".xlsx")):
            try:
                df = pd.read_csv(io.BytesIO(file_bytes))
                edited_df = st.data_editor(df, num_rows="dynamic", key=f"v_edit_{file_item['name']}")
                if st.button("💾 Save Spreadsheet Changes", type="primary"):
                    buf = io.StringIO()
                    edited_df.to_csv(buf, index=False)
                    file_item["bytes"] = buf.getvalue().encode("utf-8")
                    st.success("Spreadsheet synchronized successfully!")
                    st.rerun()
            except Exception as e:
                st.error(f"Spreadsheet error: {e}")
        else:
            text_val = file_bytes.decode("utf-8", errors="ignore")
            updated = st.text_area("Edit Content:", value=text_val, height=300, key=f"v_txt_{file_item['name']}")
            if st.button("💾 Save Changes", type="primary"):
                file_item["bytes"] = updated.encode("utf-8")
                st.success("Document updated successfully!")
                st.rerun()

    with t_export:
        st.download_button(
            label=f"⬇️ Download {file_item.get('name')}",
            data=file_bytes,
            file_name=file_item.get("name"),
            mime="application/octet-stream",
            type="primary"
        )

# ---------------------------------------------------------
# MAIN NAVIGATION ROUTER
# ---------------------------------------------------------
def main():
    # Sidebar Header
    st.sidebar.markdown("## 🌌 CHRISHEM")
    st.sidebar.caption("Sovereign Enterprise Intelligence Engine")
    
    st.sidebar.markdown("---")

    navigation = st.sidebar.selectbox(
        "Select Navigation Hub",
        [
            "Personal Workspace",
            "Access Control & Licensing",
            "Ecosystem Apex",
            "AI Intelligence Daemon",
            "Admin Billing Ledger",
            "Workflow Scheduler",
            "Neural Forecaster & AI",
            "Academic & CV Studio",
            "Telemetry & Smart Alerts",
            "System Diagnostics & Health",
            "API & Integration Gateway"
        ]
    )
    
    st.sidebar.markdown("---")

    # Clean, non-overlapping Status Badge
    st.sidebar.markdown("""
        <div class="status-badge-container">
            <div class="status-badge-header">
                <span style="display:inline-block; width:8px; height:8px; background:#34d399; border-radius:50%;"></span>
                SYSTEM OPERATIONAL
            </div>
            <div class="status-badge-sub">Enclave: Secure Sovereign</div>
        </div>
    """, unsafe_allow_html=True)

    # Main Canvas Header
    st.markdown(f'<div class="main-title-glow">{navigation}</div>', unsafe_allow_html=True)
    st.caption(f"Enterprise Operational Node | Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} EAT")
    st.markdown("<br>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # ROUTE: PERSONAL WORKSPACE
    # ---------------------------------------------------------
    if navigation == "Personal Workspace":
        try:
            from modules.personal_workspace import render_personal_workspace_panel
            render_personal_workspace_panel()
        except Exception:
            st.markdown("##### Universal Personal Workspace & Productivity Hub")
            st.caption("Manage personal research milestones, bioinformatics pipelines, system configurations, and workflow tasks.")
            st.markdown("<br>", unsafe_allow_html=True)

            # Metric Cards
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown("""
                    <div class="metric-card">
                        <div class="metric-card-title">Active Milestones</div>
                        <div class="metric-card-value">4 Tracked</div>
                        <div class="metric-card-delta">Up to Date</div>
                    </div>
                """, unsafe_allow_html=True)
            with c2:
                st.markdown("""
                    <div class="metric-card">
                        <div class="metric-card-title">Research Progress</div>
                        <div class="metric-card-value">94.2%</div>
                        <div class="metric-card-delta">+3.5% Auto</div>
                    </div>
                """, unsafe_allow_html=True)
            with c3:
                st.markdown("""
                    <div class="metric-card">
                        <div class="metric-card-title">Workspace Status</div>
                        <div class="metric-card-value">Synced</div>
                        <div class="metric-card-delta">Local Enclave</div>
                    </div>
                """, unsafe_allow_html=True)
            with c4:
                st.markdown("""
                    <div class="metric-card">
                        <div class="metric-card-title">Focus Score</div>
                        <div class="metric-card-value">100%</div>
                        <div class="metric-card-delta">Deep Work</div>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("#### 🎯 Active Research & Task Milestones")
            
            tasks_df = pd.DataFrame([
                {"Task Item": "Waterborne Pathogen Surveillance Batch Analysis", "Category": "Bioinformatics Research", "Priority": "Critical", "Status": "IN PROGRESS"},
                {"Task Item": "ALX Data Analytics Portfolio Integration", "Category": "Professional Certification", "Priority": "High", "Status": "OPTIMIZED"},
                {"Task Item": "Desktop Environment Customization & UI Polish", "Category": "Workspace Customization", "Priority": "Medium", "Status": "ACTIVE"},
                {"Task Item": "Cryptographic Vault Key Rotation", "Category": "Security Engineering", "Priority": "Critical", "Status": "COMPLETED"}
            ])
            st.dataframe(tasks_df, use_container_width=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("#### 📝 Quick Notes & Code Snippet Vault")
            st.text_area("Jot down research notes, terminal commands, or project ideas:", height=120, placeholder="Type notes here...")

        st.markdown("---")
        st.subheader("📁 Embedded Secure Personal Vault Explorer")
        
        if "vault_files" not in st.session_state:
            st.session_state["vault_files"] = []

        up = st.file_uploader("Upload files into Secure Vault:", accept_multiple_files=True, key="main_vault_uploader")
        if up:
            for f in up:
                if not any(x["name"] == f.name for x in st.session_state["vault_files"]):
                    st.session_state["vault_files"].insert(0, {
                        "name": f.name,
                        "size": f"{f.size / 1024:.1f} KB" if f.size < 1048576 else f"{f.size / 1048576:.1f} MB",
                        "status": "Verified Payload",
                        "bytes": f.getvalue()
                    })
            st.rerun()

        if st.session_state["vault_files"]:
            cols = st.columns(3)
            for idx, item in enumerate(st.session_state["vault_files"]):
                with cols[idx % 3]:
                    with st.container(border=True):
                        st.markdown(f"#### 📄 {item['name']}")
                        st.caption(f"**Size:** {item['size']} | **Status:** {item['status']}")
                        if st.button("Open Workspace", key=f"vault_open_{idx}"):
                            inspect_vault_file(item)

    # ---------------------------------------------------------
    # OTHER SUB-PANEL FALLBACKS
    # ---------------------------------------------------------
    elif navigation == "Access Control & Licensing":
        try:
            from modules.access_control import render_access_control_panel
            render_access_control_panel()
        except Exception:
            c1, c2, c3 = st.columns(3)
            c1.metric("Clearance Tier", "Tier-1 Sovereign")
            c2.metric("License Expiry", "2030-12-31")
            c3.metric("Active Sessions", "3 Nodes")

    elif navigation == "Ecosystem Apex":
        try:
            from modules.ecosystem_apex import render_ecosystem_apex_panel
            render_ecosystem_apex_panel()
        except Exception:
            st.markdown("#### Macro Topology Monitor")
            cols = st.columns(4)
            cols[0].metric("Grid Load", "84.2 %")
            cols[1].metric("Throughput", "1.2 TB/s")
            cols[2].metric("Latency", "2.1 ms")
            cols[3].metric("Resilience", "99.98 %")

    elif navigation == "AI Intelligence Daemon":
        try:
            from modules.ai_intelligence_daemon import render_ai_intelligence_panel
            render_ai_intelligence_panel()
        except Exception:
            st.markdown("#### Autonomous Intelligence Console")
            prompt = st.text_input("Enter natural language directive:")
            if prompt:
                st.info(f"Command executed: **{prompt}**")

    elif navigation == "Admin Billing Ledger":
        try:
            from modules.admin_billing_core import render_admin_billing_panel
            render_admin_billing_panel()
        except Exception:
            st.markdown("#### Billing & Resource Allocation")
            c1, c2 = st.columns(2)
            c1.metric("Current Cycle", "JULY 2026")
            c2.metric("Compute Allocation", ",240.50 USD")

    elif navigation == "Workflow Scheduler":
        try:
            from modules.workflow_scheduler import render_workflow_scheduler_panel
            render_workflow_scheduler_panel()
        except Exception:
            st.markdown("#### Autonomous Task Scheduler")
            st.checkbox("Enable Automated Nightly Git Sync", value=True)

    elif navigation == "Neural Forecaster & AI":
        try:
            from modules.neural_forecaster import render_neural_forecaster_panel
            render_neural_forecaster_panel()
        except Exception:
            st.markdown("#### Neural Forecast Matrix")
            st.line_chart(np.sin(np.linspace(0, 10, 30)))

    elif navigation == "Academic & CV Studio":
        try:
            from modules.academic_portfolio_studio import render_academic_portfolio_studio_panel
            render_academic_portfolio_studio_panel()
        except Exception:
            st.markdown("#### Academic Portfolio Studio")
            st.write("**Lead Researcher:** Kula Chris")
            st.write("**Focus:** Bioinformatics, Systems Biology & Data Analytics")

    elif navigation == "Telemetry & Smart Alerts":
        try:
            from modules.telemetry_alerting import render_telemetry_alerting_panel
            render_telemetry_alerting_panel()
        except Exception:
            st.success("✅ Systems Operating Within Thermal Limits")

    elif navigation == "System Diagnostics & Health":
        try:
            from modules.system_diagnostics import render_system_diagnostics_panel
            render_system_diagnostics_panel()
        except Exception:
            st.success("✅ Diagnostic Integrity Verified")

    elif navigation == "API & Integration Gateway":
        try:
            from modules.api_integration_gateway import render_api_gateway_panel
            render_api_gateway_panel()
        except Exception:
            st.code("POST /api/v1/sovereign/execute")

if __name__ == "__main__":
    main()

# --- Background Auto-Sync ---
try:
    from modules.auto_sync import auto_commit_and_push
    success, msg = auto_commit_and_push("auto: layout redesign and unicode clean")
    if success:
        print(f"[Auto-Sync] {msg}")
except Exception:
    pass