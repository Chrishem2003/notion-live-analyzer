"""NEMA-AGORA Phase 49 — Governance Review Queue."""
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.closure_evidence import reconcile_with_evidence
from nema_agora.governance_attestation import GovernanceAttestationRegistry, build_integrity_snapshot
from nema_agora.governance_exception_resolution import GovernanceExceptionResolver
from nema_agora.attestation_lifecycle import AttestationLifecycleRegistry, evaluate_lifecycle
from nema_agora.lifecycle_provenance import LifecycleProvenanceRegistry, evaluate_provenance
from nema_agora.governance_evidence_reconciliation import reconcile
from nema_agora.governance_evidence_casebook import build_casebook
from nema_agora.governance_review_queue import build_review_queue
st.set_page_config(page_title="NEMA-AGORA Review Queue",page_icon="☷",layout="wide")
st.title("NEMA-AGORA — Governance Review Queue")
st.caption("Phase 49-v1 • deterministic, read-only prioritization for human review")
st.info("Engineering/research evidence only. This queue does not authorize NEMA integration, regulatory action, enforcement, emergency response, production or autonomous decisions.")
if mode_from_secrets(st.secrets)!="persistent": st.warning("Persistent authenticated mode is required."); st.stop()
principal=principal_from_streamlit_user(st.user,st.secrets)
if not principal or not principal.is_authorised or principal.role not in {"reviewer","coordinator","admin"} or not has_permission(principal.role,"audit:read"): st.error("Authorized reviewer, coordinator, or admin access is required."); st.stop()
db=database_path_from_secrets(st.secrets)
try:
    ar=GovernanceAttestationRegistry(db); lr=AttestationLifecycleRegistry(db); pr=LifecycleProvenanceRegistry(db)
    derived=reconcile_with_evidence(db)
    reconciliation={"reconciliation_fingerprint":derived["closure"]["reconciliation_fingerprint"],"exceptions":[{"code":x["exception_code"],"decision_kind":x["decision_kind"],"artifact_id":x["artifact_id"],"severity":x.get("severity"),"detail":x.get("detail")} for x in derived["closure"]["results"]]}
    resolutions=GovernanceExceptionResolver(db).list_resolutions(limit=500); attestations=ar.list(500)
    snapshot=build_integrity_snapshot(reconciliation=reconciliation,closure=derived["closure"],resolutions=resolutions,evidence_rows=derived["evidence"],attestations=attestations)
    decisions=lr.list(500); bindings=pr.list(500)
    life=evaluate_lifecycle(attestations,decisions,reconciliation_fingerprint=snapshot["provenance"]["reconciliation_fingerprint"],evidence_registry_fingerprint=snapshot["integrity"]["registry_fingerprint"],provenance_fingerprint=snapshot["provenance_fingerprint"],integrity_valid=snapshot["integrity"]["valid"],provenance_complete=snapshot["provenance"]["complete"])
    prov=evaluate_provenance(bindings,decisions,attestations,reconciliation_fingerprint=snapshot["provenance"]["reconciliation_fingerprint"],evidence_registry_fingerprint=snapshot["integrity"]["registry_fingerprint"],provenance_fingerprint=snapshot["provenance_fingerprint"])
    rec=reconcile(attestations=attestations,lifecycle_items=life["items"],bindings=bindings,provenance_result=prov,current_snapshot=life["current_snapshot"])
    book=build_casebook(reconciliation_result=rec,attestations=attestations,lifecycle_items=life["items"],lifecycle_decisions=decisions,bindings=bindings,current_snapshot=life["current_snapshot"])
    queue=build_review_queue(cases=book["cases"],current_snapshot=life["current_snapshot"])
except Exception as exc: st.error(f"Review queue failed closed: {exc}"); st.stop()
st.metric("Review cases",queue["queue_count"])
if queue["queue_count"]: st.warning("Human review is required; queue order is advisory.")
else: st.success("No review cases are currently generated.")
st.dataframe(queue["queue"] or [{"status":"EMPTY"}],use_container_width=True,hide_index=True)
st.subheader("Queue fingerprint"); st.code(queue["queue_fingerprint"])
st.caption(queue["notice"])
