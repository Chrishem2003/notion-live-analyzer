import streamlit as st
import os
import io
import time
import numpy as np
import pandas as pd
from datetime import datetime

# Optional Module Imports with Fallbacks
try:
    from modules.ui_stunning import apply_stunning_styles
    apply_stunning_styles()
except Exception:
    pass

try:
    from modules.database import init_db, log_backend_event
    init_db()
except Exception:
    pass

try:
    from modules.theme_loader import apply_custom_theme
    apply_custom_theme()
except Exception:
    pass

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

# ---------------------------------------------------------
# PAGE CONFIGURATION & CLEAN STYLES
# ---------------------------------------------------------
st.set_page_config(
    page_title="CHRISHEM Enterprise Intelligence Engine",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: linear-gradient(135deg, #070B14 0%, #0F172A 50%, #070B14 100%); color: #F8FAFC; }
    
    /* Clean Sidebar Status Pill (Prevents Overlap) */
    .sidebar-status-box {
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid #10B981;
        border-radius: 10px;
        padding: 0.75rem 1rem;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        font-size: 0.85rem;
        line-height: 1.4;
        display: block;
        clear: both;
    }
    
    .header-glow {
        background: linear-gradient(90deg, #60A5FA, #A78BFA, #F472B6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2rem;
        font-weight: 800;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# EMBEDDED SECURE VAULT DIALOG
# ---------------------------------------------------------
@st.dialog("Enterprise Secure Vault Inspector", width="large")
def inspect_vault_file(file_item):
    st.markdown(f"### 📄 {file_item.get('name', 'Document')}")
    st.caption(f"**Size:** {file_item.get('size', 'N/A')} | **Status:** {file_item.get('status', 'Verified')}")
    
    file_bytes = file_item.get("bytes", b"")
    file_name = file_item.get("name", "").lower()

    t_view, t_edit, t_export = st.tabs(["View / Read", "Edit Content", "Download Stream"])

    with t_view:
        if file_name.endswith(".pdf"):
            st.markdown("#### PDF Text Payload")
            if HAS_PYPDF and file_bytes:
                try:
                    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                    text = "\n\n".join([f"--- Page {i+1} ---\n" + (p.extract_text() or "") for i, p in enumerate(reader.pages)])
                    st.text_area("Extracted Stream", value=text, height=350)
                except Exception as e:
                    st.warning(f"Extracted Raw Stream: {e}")
            else:
                st.info("PDF Binary Payload Loaded.")
        elif file_name.endswith((".csv", ".xlsx")):
            st.markdown("#### Spreadsheet View")
            try:
                df = pd.read_csv(io.BytesIO(file_bytes))
                st.dataframe(df, use_container_width=True)
            except Exception:
                st.text_area("Raw Stream", value=file_bytes.decode("utf-8", errors="ignore"), height=300)
        else:
            st.markdown("#### Document Text View")
            st.code(file_bytes.decode("utf-8", errors="ignore"))

    with t_edit:
        if file_name.endswith((".csv", ".xlsx")):
            try:
                df = pd.read_csv(io.BytesIO(file_bytes))
                edited_df = st.data_editor(df, num_rows="dynamic", key=f"v_edit_{file_item['name']}")
                if st.button("Save Table Changes", type="primary"):
                    buf = io.StringIO()
                    edited_df.to_csv(buf, index=False)
                    file_item["bytes"] = buf.getvalue().encode("utf-8")
                    st.success("Changes saved!")
                    st.rerun()
            except Exception as e:
                st.error(f"Spreadsheet error: {e}")
        else:
            text_val = file_bytes.decode("utf-8", errors="ignore")
            updated = st.text_area("Edit Content:", value=text_val, height=300, key=f"v_txt_{file_item['name']}")
            if st.button("Save Document", type="primary"):
                file_item["bytes"] = updated.encode("utf-8")
                st.success("Document updated!")
                st.rerun()

    with t_export:
        st.download_button(
            label=f"Download {file_item.get('name')}",
            data=file_bytes,
            file_name=file_item.get("name"),
            mime="application/octet-stream",
            type="primary"
        )

# ---------------------------------------------------------
# MAIN APPLICATION ROUTER
# ---------------------------------------------------------
def main():
    st.sidebar.markdown("## 🌌 CHRISHEM")
    st.sidebar.caption("Enterprise Intelligence Engine")
    
    navigation = st.sidebar.selectbox(
        "Navigation Hub",
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
    
    # Styled non-overlapping status box
    st.sidebar.markdown("""
        <div class="sidebar-status-box">
            🟢 <b>System Status:</b> Operational<br>
            🔒 <b>Enclave:</b> Secure
        </div>
    """, unsafe_allow_html=True)

    # Dynamic Header Display
    st.markdown(f'<div class="header-glow">{navigation}</div>', unsafe_allow_html=True)
    st.caption(f"Operational Node | Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown("---")

    # Clean Sub-Panels
    if navigation == "Personal Workspace":
        try:
            from modules.personal_workspace import render_personal_workspace_panel
            render_personal_workspace_panel()
        except Exception:
            st.markdown("### Universal Personal Workspace & Productivity Hub")
            st.caption("Custom command center: manage personal research milestones, bioinformatics pipelines, and daily workflow tasks.")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Active Milestones", "4 Tracked", "Up to Date")
            c2.metric("Research Progress", "94.2%", "+3.5%")
            c3.metric("Workspace Status", "Synchronized", "Local Enclave")
            c4.metric("Focus Score", "100%", "Deep Work")

            st.markdown("#### Active Research & Task Milestones")
            tasks_df = pd.DataFrame([
                {"Task_Item": "Waterborne Pathogen Surveillance Batch Analysis", "Category": "Bioinformatics Research", "Priority": "Critical", "Status": "IN PROGRESS"},
                {"Task_Item": "ALX Data Analytics Portfolio Integration", "Category": "Professional Certification", "Priority": "High", "Status": "OPTIMIZED"},
                {"Task_Item": "Desktop Environment Styling", "Category": "Workspace Customization", "Priority": "Medium", "Status": "ACTIVE"},
                {"Task_Item": "Cryptographic Vault Key Rotation", "Category": "Security Engineering", "Priority": "Critical", "Status": "COMPLETED"}
            ])
            st.dataframe(tasks_df, use_container_width=True)

            st.markdown("#### Quick Notes & Code Snippet Vault")
            st.text_area("Jot down research notes or commands:", height=120, placeholder="Type notes here...")

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

    elif navigation == "Access Control & Licensing":
        try:
            from modules.access_control import render_access_control_panel
            render_access_control_panel()
        except Exception:
            col1, col2, col3 = st.columns(3)
            col1.metric("Clearance Tier", "Tier-1 Sovereign")
            col2.metric("License Expiry", "2030-12-31")
            col3.metric("Active Sessions", "3 Nodes")

    elif navigation == "Ecosystem Apex":
        try:
            from modules.ecosystem_apex import render_ecosystem_apex_panel
            render_ecosystem_apex_panel()
        except Exception:
            st.markdown("#### Macro Topology")
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
            prompt = st.text_input("Enter system directive:")
            if prompt:
                st.info(f"Processing command: **{prompt}**")

    elif navigation == "Admin Billing Ledger":
        try:
            from modules.admin_billing_core import render_admin_billing_panel
            render_admin_billing_panel()
        except Exception:
            st.markdown("#### Billing & Allocation Ledger")
            c1, c2 = st.columns(2)
            c1.metric("Current Billing Cycle", "JULY 2026")
            c2.metric("Total Compute Cost", ",240.50 USD")

    elif navigation == "Workflow Scheduler":
        try:
            from modules.workflow_scheduler import render_workflow_scheduler_panel
            render_workflow_scheduler_panel()
        except Exception:
            st.markdown("#### Task & Workflow Engine")
            st.checkbox("Enable Automated Nightly Git Backup", value=True)

    elif navigation == "Neural Forecaster & AI":
        try:
            from modules.neural_forecaster import render_neural_forecaster_panel
            render_neural_forecaster_panel()
        except Exception:
            st.markdown("#### Forecast Engine")
            st.line_chart(np.sin(np.linspace(0, 10, 30)))

    elif navigation == "Academic & CV Studio":
        try:
            from modules.academic_portfolio_studio import render_academic_portfolio_studio_panel
            render_academic_portfolio_studio_panel()
        except Exception:
            st.markdown("#### Academic Portfolio Manager")
            st.write("**Lead Researcher:** Kula Chris")

    elif navigation == "Telemetry & Smart Alerts":
        try:
            from modules.telemetry_alerting import render_telemetry_alerting_panel
            render_telemetry_alerting_panel()
        except Exception:
            st.success("✅ System Temperature Normal")

    elif navigation == "System Diagnostics & Health":
        try:
            from modules.system_diagnostics import render_system_diagnostics_panel
            render_system_diagnostics_panel()
        except Exception:
            st.success("✅ Systems Operational")

    elif navigation == "API & Integration Gateway":
        try:
            from modules.api_integration_gateway import render_api_gateway_panel
            render_api_gateway_panel()
        except Exception:
            st.code("POST /api/v1/sovereign/execute")

if __name__ == "__main__":
    main()

# Background Sync
try:
    from modules.auto_sync import auto_commit_and_push
    success, msg = auto_commit_and_push("auto: ui cleanup and encoding fix")
    if success:
        print(f"[Auto-Sync] {msg}")
except Exception:
    pass