"""NEMA-AGORA Phase 50 — Governance Review Workspace."""
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

st.set_page_config(page_title="NEMA-AGORA Review Workspace",page_icon="⌕",layout="wide")
st.title("NEMA-AGORA — Governance Review Workspace")
st.caption("Phase 50-v1 • authenticated, read-only case investigation")
st.info("Engineering/research evidence only. Governance mutations remain outside this read-only workspace.")
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
    snapshot=build_integrity_snapshot(reconciliation=reconciliation,closure=derived["closure"],resolutions=resolutions,
        evidence_rows=derived["evidence"],attestations=attestations)
    decisions=lr.list(500); bindings=pr.list(500)
    life=evaluate_lifecycle(attestations,decisions,reconciliation_fingerprint=snapshot["provenance"]["reconciliation_fingerprint"],
        evidence_registry_fingerprint=snapshot["integrity"]["registry_fingerprint"],provenance_fingerprint=snapshot["provenance_fingerprint"],
        integrity_valid=snapshot["integrity"]["valid"],provenance_complete=snapshot["provenance"]["complete"])
    prov=evaluate_provenance(bindings,decisions,attestations,reconciliation_fingerprint=snapshot["provenance"]["reconciliation_fingerprint"],
        evidence_registry_fingerprint=snapshot["integrity"]["registry_fingerprint"],provenance_fingerprint=snapshot["provenance_fingerprint"])
    rec=reconcile(attestations=attestations,lifecycle_items=life["items"],bindings=bindings,provenance_result=prov,current_snapshot=life["current_snapshot"])
    book=build_casebook(reconciliation_result=rec,attestations=attestations,lifecycle_items=life["items"],
        lifecycle_decisions=decisions,bindings=bindings,current_snapshot=life["current_snapshot"])
    queue=build_review_queue(cases=book["cases"],current_snapshot=life["current_snapshot"])
except Exception as exc:
    st.error(f"Review workspace failed closed: {exc}"); st.stop()
case_ids=[str(x["case_id"]) for x in queue["queue"]]
if not case_ids:
    st.success("No governance review cases are currently queued.")
    st.caption("The workspace is read-only and will not create a case.")
    st.stop()
selected=st.selectbox("Select review case",case_ids,format_func=lambda x: f"{x} — {queue['queue'][case_ids.index(x)].get('code')}")
workspace=build_workspace(queue_result=queue,casebook=book,attestations=attestations,lifecycle_items=life["items"],
    lifecycle_decisions=decisions,bindings=bindings,provenance_result=prov,current_snapshot=life["current_snapshot"],case_id=selected)
case=workspace["case"]
c1,c2,c3,c4=st.columns(4)
c1.metric("Queue position",case["queue_context"].get("queue_position","—"))
c2.metric("Severity",case["queue_context"].get("severity","—"))
c3.metric("Age (days)",case["queue_context"].get("age_days",0))
c4.metric("Dependency",str(case["queue_context"].get("dependency",False)))
st.subheader(f"Case {case['case_id']}")
st.write("**Finding:**",case["finding"])
st.write("**Required action:** HUMAN_REVIEW_REQUIRED")
st.subheader("Accountable artifacts"); st.json(case["queue_context"].get("accountable_artifacts",{}))
st.subheader("Lifecycle evidence"); st.json({"items":case["lifecycle_items"],"decisions":case["lifecycle_decisions"]})
st.subheader("Provenance"); st.json(case["provenance_bindings"])
st.subheader("Exact current snapshot"); st.json(case["current_snapshot"])
st.subheader("Human review context"); st.json(case["review_context"])
st.code(workspace["workspace_fingerprint"])
st.caption(workspace["notice"])
