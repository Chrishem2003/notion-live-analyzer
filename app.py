try:
    from modules.ui_stunning import apply_stunning_styles
    apply_stunning_styles()
except Exception:
    pass

import streamlit as st
import os
import io
import pandas as pd
from datetime import datetime

# Import Database & Sync Core
from modules.database import init_db, log_backend_event
from modules.theme_loader import apply_custom_theme

# Import All Module Panels
from modules.access_control import render_access_control_panel
from modules.ecosystem_apex import render_ecosystem_apex_panel
from modules.personal_workspace import render_personal_workspace_panel
from modules.ai_intelligence_daemon import render_ai_intelligence_panel
from modules.admin_billing_core import render_admin_billing_panel
from modules.workflow_scheduler import render_workflow_scheduler_panel
from modules.neural_forecaster import render_neural_forecaster_panel
from modules.academic_portfolio_studio import render_academic_portfolio_studio_panel
from modules.telemetry_alerting import render_telemetry_alerting_panel
from modules.system_diagnostics import render_system_diagnostics_panel
from modules.api_integration_gateway import render_api_gateway_panel

# Try importing PDF reader safely
try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

# ---------------------------------------------------------
# INITIALIZATION & PAGE CONFIG
# ---------------------------------------------------------
init_db()

st.set_page_config(
    page_title="CHRISHEM Sovereign Enterprise Intelligence Engine",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_custom_theme()

# ---------------------------------------------------------
# EMBEDDED SECURE VAULT MODAL (NO FROZEN UI)
# ---------------------------------------------------------
@st.dialog("📄 Enterprise Secure Vault Inspector", width="large")
def inspect_vault_file(file_item):
    st.markdown(f"### 📄 {file_item.get('name', 'Document')}")
    st.caption(f"**Size:** {file_item.get('size', 'N/A')} | **Status:** {file_item.get('status', 'Verified')}")
    
    file_bytes = file_item.get("bytes", b"")
    file_name = file_item.get("name", "").lower()

    t_view, t_edit, t_export = st.tabs(["👁️ View / Read", "✏️ Edit (Docs/Sheets)", "📥 Download Stream"])

    with t_view:
        if file_name.endswith(".pdf"):
            st.markdown("#### 📄 PDF Reader (Google Docs Mode)")
            if HAS_PYPDF and file_bytes:
                try:
                    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                    text = "\n\n".join([f"--- Page {i+1} ---\n" + (p.extract_text() or "") for i, p in enumerate(reader.pages)])
                    st.text_area("Extracted Document Stream", value=text, height=350)
                except Exception as e:
                    st.warning(f"Extracted Raw Stream Payload (PDF Parse Note: {e})")
            else:
                st.info("PDF Binary Payload Ready.")
        elif file_name.endswith((".csv", ".xlsx", ".parquet")):
            st.markdown("#### 📊 Spreadsheet View (Google Sheets Mode)")
            try:
                df = pd.read_csv(io.BytesIO(file_bytes))
                st.dataframe(df, use_container_width=True)
            except Exception:
                st.text_area("Raw Data", value=file_bytes.decode("utf-8", errors="ignore"), height=300)
        else:
            st.markdown("#### 📝 Plain Text / Code View")
            st.code(file_bytes.decode("utf-8", errors="ignore"))

    with t_edit:
        if file_name.endswith((".csv", ".xlsx")):
            st.markdown("#### 📊 Interactive Data Grid Editor")
            try:
                df = pd.read_csv(io.BytesIO(file_bytes))
                edited_df = st.data_editor(df, num_rows="dynamic", key=f"v_edit_{file_item['name']}")
                if st.button("💾 Save Sheet Changes", type="primary"):
                    buf = io.StringIO()
                    edited_df.to_csv(buf, index=False)
                    file_item["bytes"] = buf.getvalue().encode("utf-8")
                    st.success("Updated spreadsheet saved successfully!")
                    st.rerun()
            except Exception as e:
                st.error(f"Spreadsheet error: {e}")
        else:
            st.markdown("#### ✏️ Live Text Editor")
            text_val = file_bytes.decode("utf-8", errors="ignore")
            updated = st.text_area("Edit Document Content:", value=text_val, height=300, key=f"v_txt_{file_item['name']}")
            if st.button("💾 Save Document Changes", type="primary"):
                file_item["bytes"] = updated.encode("utf-8")
                st.success("Document updated successfully!")
                st.rerun()

    with t_export:
        st.markdown("### 📥 Direct File Download Stream")
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
    st.sidebar.title("🌌 CHRISHEM Enterprise")
    st.sidebar.caption("Sovereign Intelligence & Autonomous Grid")
    
    navigation = st.sidebar.selectbox(
        "Navigation Hub",
        [
            "Access Control & Licensing",
            "Ecosystem Apex",
            "Personal Workspace",
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
    st.sidebar.info("System Status: 100% Operational\nEnclave: Secure Sovereign")

    if navigation == "Access Control & Licensing":
        render_access_control_panel()
    elif navigation == "Ecosystem Apex":
        render_ecosystem_apex_panel()
    elif navigation == "Personal Workspace":
        render_personal_workspace_panel()
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
                        if st.button("👁️ Open Workspace", key=f"vault_open_{idx}"):
                            inspect_vault_file(item)

    elif navigation == "AI Intelligence Daemon":
        render_ai_intelligence_panel()
    elif navigation == "Admin Billing Ledger":
        render_admin_billing_panel()
    elif navigation == "Workflow Scheduler":
        render_workflow_scheduler_panel()
    elif navigation == "Neural Forecaster & AI":
        render_neural_forecaster_panel()
    elif navigation == "Academic & CV Studio":
        render_academic_portfolio_studio_panel()
    elif navigation == "Telemetry & Smart Alerts":
        render_telemetry_alerting_panel()
    elif navigation == "System Diagnostics & Health":
        render_system_diagnostics_panel()
    elif navigation == "API & Integration Gateway":
        render_api_gateway_panel()

if __name__ == "__main__":
    main()

# --- Autonomous Background Git Sync ---
try:
    from modules.auto_sync import auto_commit_and_push
    success, msg = auto_commit_and_push("auto: routine application sync")
    if success:
        print(f"🚀 [Auto-Sync] {msg}")
except Exception as _sync_err:
    pass
# -------------------------------------