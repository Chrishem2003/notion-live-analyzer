"""NEMA-AGORA Phase 47 — Governance Evidence Reconciliation."""
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.closure_evidence import reconcile_with_evidence
from nema_agora.governance_attestation import GovernanceAttestationRegistry, build_integrity_snapshot
from nema_agora.governance_exception_resolution import GovernanceExceptionResolver
from nema_agora.attestation_lifecycle import AttestationLifecycleRegistry, evaluate_lifecycle
from nema_agora.lifecycle_provenance import LifecycleProvenanceRegistry, evaluate_provenance, validate_supersession_chain
from nema_agora.governance_evidence_reconciliation import reconcile

st.set_page_config(page_title="NEMA-AGORA Evidence Reconciliation",page_icon="◇",layout="wide")
st.title("NEMA-AGORA — Governance Evidence Reconciliation")
st.caption("Phase 47-v1 • deterministic, read-only, fail-closed cross-layer consistency control")
st.info("Engineering/research evidence only. This surface does not authorize NEMA integration, reporting, enforcement, emergency response, production or regulatory decisions.")
if mode_from_secrets(st.secrets)!="persistent": st.warning("Persistent authenticated mode is required."); st.stop()
principal=principal_from_streamlit_user(st.user,st.secrets)
if not principal or not principal.is_authorised or principal.role not in {"reviewer","coordinator","admin"} or not has_permission(principal.role,"audit:read"):
    st.error("Authorized reviewer, coordinator, or admin access is required."); st.stop()
db=database_path_from_secrets(st.secrets)
try:
    ar=GovernanceAttestationRegistry(db); lr=AttestationLifecycleRegistry(db); pr=LifecycleProvenanceRegistry(db)
    derived=reconcile_with_evidence(db)
    reconciliation={"reconciliation_fingerprint":derived["closure"]["reconciliation_fingerprint"],
        "exceptions":[{"code":x["exception_code"],"decision_kind":x["decision_kind"],"artifact_id":x["artifact_id"],"severity":x.get("severity"),"detail":x.get("detail")} for x in derived["closure"]["results"]]}
    resolutions=GovernanceExceptionResolver(db).list_resolutions(limit=500)
    attestations=ar.list(500)
    snapshot=build_integrity_snapshot(reconciliation=reconciliation,closure=derived["closure"],resolutions=resolutions,evidence_rows=derived["evidence"],attestations=attestations)
    decisions=lr.list(500); bindings=pr.list(500)
    life=evaluate_lifecycle(attestations,decisions,reconciliation_fingerprint=snapshot["provenance"]["reconciliation_fingerprint"],evidence_registry_fingerprint=snapshot["integrity"]["registry_fingerprint"],provenance_fingerprint=snapshot["provenance_fingerprint"],integrity_valid=snapshot["integrity"]["valid"],provenance_complete=snapshot["provenance"]["complete"])
    prov=evaluate_provenance(bindings,decisions,attestations,reconciliation_fingerprint=snapshot["provenance"]["reconciliation_fingerprint"],evidence_registry_fingerprint=snapshot["integrity"]["registry_fingerprint"],provenance_fingerprint=snapshot["provenance_fingerprint"])
    result=reconcile(attestations=attestations,lifecycle_items=life["items"],bindings=bindings,provenance_result=prov,current_snapshot=life["current_snapshot"])
except Exception as exc: st.error(f"Reconciliation failed closed: {exc}"); st.stop()
if result["state"]=="CONTROL_REQUIRED": st.error("CONTROL REQUIRED — cross-layer evidence is inconsistent and requires human investigation.")
else: st.success("RECONCILED — supplied evidence layers are internally consistent under Phase 47.")
st.metric("Finding count",result["finding_count"])
st.dataframe(result["findings"] or [{"code":"NONE"}],use_container_width=True,hide_index=True)
st.subheader("Current snapshot")
st.json(result["reconciliation_fingerprint"])
st.json(result["policy_version"])
st.caption("The reconciler is read-only. It never repairs, deletes, mutates, approves, rejects or authorizes governance records.")
