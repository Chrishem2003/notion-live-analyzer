"""NEMA-AGORA Phase 32 — Publication Control."""
import hashlib
import json
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.audit_events import AuditEventCapture
from nema_agora.audit_ledger import AuditLedger
from nema_agora.evidence_graph import build_evidence_graph, build_research_report, validate_graph
from nema_agora.evidence_synthesis import build_evidence_synthesis
from nema_agora.provenance import ProvenanceStore
from nema_agora.publication_control import evaluate_publication_gate, serialise_publication_decision, validate_publication_decision

st.set_page_config(page_title="NEMA-AGORA Publication Control",page_icon="🛡️",layout="wide")
st.title("🛡️ NEMA-AGORA — Evaluation & Publication Control")
st.caption("Phase 32-v1 — fail-closed review gate")
st.warning("Approval here means human-reviewed documentation readiness only. It is not NEMA authorization, regulatory approval, environmental truth/impact, production approval, enforcement or emergency-response authority.")
if mode_from_secrets(st.secrets)!="persistent":
    st.info("Persistent authenticated mode is required."); st.stop()
principal=principal_from_streamlit_user(st.user,st.secrets)
if not principal or not principal.is_authorised or not has_permission(principal.role,"intelligence:evidence"):
    st.error("Authenticated evidence access is required."); st.stop()
db=database_path_from_secrets(st.secrets)
if not db: st.error("Persistent database path is required."); st.stop()
records=ProvenanceStore(db).list(limit=1000)
sources=[str(r["provenance_id"]) for r in records[:50]]
domains={k:{"count":len(records) if k in ("ENGINEERING","REPRODUCIBILITY") else 0,
 "source_ids":sources if k in ("ENGINEERING","REPRODUCIBILITY") else [],
 "limitations":["Evidence is bounded by available recorded artifacts."]}
 for k in ("ENGINEERING","WORKFLOW_OUTCOMES","HUMAN_GOVERNANCE","REPRODUCIBILITY","ACCESSIBILITY","FIELD_EVALUATION")}
synthesis=build_evidence_synthesis(evidence_domains=domains,global_limitations=("Evidence volume and representativeness constrain generalisation.",))
graph=build_evidence_graph(provenance_records=records,synthesis=synthesis.to_dict())
report=build_research_report(synthesis=synthesis.to_dict(),graph=graph)
graph_validation=validate_graph(graph)
st.write({"report_id":report["report_id"],"graph_valid":graph_validation["valid"],"claims":len(synthesis.claims)})
with st.form("publication_review"):
    reviewer=st.text_input("Reviewer identity (authenticated principal)",value=principal.subject_key,disabled=True)
    rationale=st.text_area("Human review rationale",placeholder="Describe what was reviewed, limitations, and why publication is appropriate.")
    submitted=st.form_submit_button("Evaluate publication gates")
if submitted:
    decision=evaluate_publication_gate(report=report,graph_validation=graph_validation,
        reviewer_id=reviewer,rationale=rationale)
    validation=validate_publication_decision(decision)
    st.subheader(decision.status)
    st.write({"gates":decision.gates,"blockers":list(decision.blockers),"valid_decision":validation["valid"]})
    st.json(decision.to_dict())
    try:
        audit_material = json.dumps(
            {"report_id": report["report_id"], "status": decision.status,
             "gates": decision.gates, "blockers": list(decision.blockers)},
            sort_keys=True, separators=(",", ":"), default=str,
        )
        audit_event_id = "publication-" + hashlib.sha256(audit_material.encode("utf-8")).hexdigest()[:48]
        audit_result = AuditEventCapture(AuditLedger(db)).record(
            event_id=audit_event_id,
            event_type="PUBLICATION_GATE_DECIDED",
            actor_id=principal.subject_key,
            payload={
                "artifact_id": str(report["report_id"]),
                "status": decision.status,
                "decision": "APPROVE" if decision.status == "APPROVED_FOR_PUBLICATION" else "HUMAN_REVIEW_REQUIRED",
                "reason_code": "POLICY_GATE",
                "source_module": "publication_control",
                "recorded_by_role": principal.role,
                "policy_version": "phase36-v1",
            },
        )
        st.caption("Publication gate decision captured in the audit ledger (metadata only).")
        st.json({"audit_event_capture": audit_result})
    except Exception as audit_exc:
        st.warning(f"Decision evaluated, but audit event capture failed: {audit_exc}")
    st.download_button("Download publication decision JSON",serialise_publication_decision(decision),
        "nema_agora_phase32_publication_decision.json","application/json")
st.caption("This gate does not itself publish, upload or externally submit a report. Human review remains required.")
