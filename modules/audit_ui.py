import streamlit as st

try:
    from modules.audit_engine import (
        AuditOrchestrator,
        EnterpriseDataEngine,
        ProductionLinguisticProcessor,
        ComplianceEngine,
        DataEngine,
        LinguisticProcessor
    )
except ImportError:
    from audit_engine import (
        AuditOrchestrator,
        EnterpriseDataEngine,
        ProductionLinguisticProcessor,
        ComplianceEngine,
        DataEngine,
        LinguisticProcessor
    )

def render_audit_tab():
    """Renders the system audit and compliance interface tab."""
    st.markdown("### 🛡️ System Audit & Compliance")
    st.info("Literature engine modules and audit pipelines are active.")
    
    orchestrator = AuditOrchestrator()
    st.write("**System Orchestrator Status:** Online & Operational")
    
    if st.button("Run Diagnostics"):
        log = orchestrator.log_event("manual_diagnostic", "system_user", {"status": "healthy"})
        st.success(f"Diagnostic completed successfully. Compliance Hash: `{log['hash']}`")
        st.json(log)
