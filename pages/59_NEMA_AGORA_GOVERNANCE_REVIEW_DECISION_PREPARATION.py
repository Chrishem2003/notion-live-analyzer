"""NEMA-AGORA Phase 51 — Governance Review Decision Preparation."""
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.closure_evidence import reconcile_with_evidence
from nema_agora.governance_exception_resolution import GovernanceExceptionResolver
from nema_agora.governance_attestation import GovernanceAttestationRegistry, build_integrity_snapshot
from nema_agora.attestation_lifecycle import AttestationLifecycleRegistry, evaluate_lifecycle
from nema_agora.lifecycle_provenance import LifecycleProvenanceRegistry, evaluate_provenance
from nema_agora.governance_evidence_reconciliation import reconcile
from nema_agora.governance_evidence_casebook import build_casebook
from nema_agora.governance_review_queue import build_review_queue
from nema_agora.governance_review_workspace import build_workspace
from nema_agora.governance_review_decision import prepare_review_decision

st.set_page_config(page_title="NEMA-AGORA Decision Preparation",page_icon="✓",layout="wide")
st.title("NEMA-AGORA — Governance Review Decision Preparation")
st.caption("Phase 51-v1 • evidence assembly only • no decision execution")
st.info("Preparation only: this surface assembles evidence for an authorized human reviewer. It does not make or record a governance decision.")
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
    resolutions=GovernanceExceptionResolver(db).list_resolutions(limit=500); attestations=ar.list(500)
    snapshot=build_integrity_snapshot(reconciliation=reconciliation,closure=derived["closure"],resolutions=resolutions,evidence_rows=derived["evidence"],attestations=attestations)
    decisions=lr.list(500); bindings=pr.list(500)
    life=evaluate_lifecycle(attestations,decisions,reconciliation_fingerprint=snapshot["provenance"]["reconciliation_fingerprint"],evidence_registry_fingerprint=snapshot["integrity"]["registry_fingerprint"],provenance_fingerprint=snapshot["provenance_fingerprint"],integrity_valid=snapshot["integrity"]["valid"],provenance_complete=snapshot["provenance"]["complete"])
    prov=evaluate_provenance(bindings,decisions,attestations,reconciliation_fingerprint=snapshot["provenance"]["reconciliation_fingerprint"],evidence_registry_fingerprint=snapshot["integrity"]["registry_fingerprint"],provenance_fingerprint=snapshot["provenance_fingerprint"])
    rec=reconcile(attestations=attestations,lifecycle_items=life["items"],bindings=bindings,provenance_result=prov,current_snapshot=life["current_snapshot"])
    book=build_casebook(reconciliation_result=rec,attestations=attestations,lifecycle_items=life["items"],lifecycle_decisions=decisions,bindings=bindings,current_snapshot=life["current_snapshot"])
    queue=build_review_queue(cases=book["cases"],current_snapshot=life["current_snapshot"])
except Exception as exc: st.error(f"Decision preparation failed closed: {exc}"); st.stop()
ids=[str(x["case_id"]) for x in queue["queue"]]
if not ids: st.success("No cases require preparation."); st.stop()
selected=st.selectbox("Case",ids)
workspace=build_workspace(queue_result=queue,casebook=book,attestations=attestations,lifecycle_items=life["items"],lifecycle_decisions=decisions,bindings=bindings,provenance_result=prov,current_snapshot=life["current_snapshot"],case_id=selected)
prepared=prepare_review_decision(workspace=workspace,current_snapshot=life["current_snapshot"],reviewer_actor_id=str(principal.actor_id))
if prepared["state"]!="READY_FOR_HUMAN_DECISION": st.error(prepared["reason"]); st.stop()
st.metric("Status","NOT_DECIDED")
st.subheader("Decision preparation package")
st.json(prepared["package"])
st.subheader("Package fingerprint")
st.code(prepared["package_fingerprint"])
st.warning("No approve/reject/revoke/supersede control exists here. Use the existing human-governed workflow when an authorized decision is actually required.")
st.caption(prepared["notice"])
