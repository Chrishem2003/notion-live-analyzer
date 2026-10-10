"""NEMA-AGORA Phase 33 — Evidence Integrity Audit."""
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.evidence_graph import build_evidence_graph, build_research_report
from nema_agora.evidence_integrity import audit_evidence_integrity
from nema_agora.evidence_synthesis import build_evidence_synthesis
from nema_agora.provenance import ProvenanceStore

st.set_page_config(page_title="NEMA-AGORA Evidence Integrity",page_icon="🔎",layout="wide")
st.title("🔎 NEMA-AGORA — Evidence Integrity Audit")
st.caption("Phase 33-v1 — detect broken lineage, duplicate IDs and content tampering")
st.warning("Integrity checks assess artifact consistency only; they do not establish environmental truth/impact, NEMA authorization, regulatory status, or production approval.")
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
 "limitations":["Evidence is bounded by recorded artifacts."]}
 for k in ("ENGINEERING","WORKFLOW_OUTCOMES","HUMAN_GOVERNANCE","REPRODUCIBILITY","ACCESSIBILITY","FIELD_EVALUATION")}
synthesis=build_evidence_synthesis(evidence_domains=domains,global_limitations=("Evidence volume and representativeness constrain generalisation.",))
graph=build_evidence_graph(provenance_records=records,synthesis=synthesis.to_dict())
report=build_research_report(synthesis=synthesis.to_dict(),graph=graph)
result=audit_evidence_integrity(provenance_records=records,graph=graph,report=report)
st.metric("Integrity status","VALID" if result["valid"] else "CONTROL REQUIRED")
st.json(result)
st.download_button("Download integrity audit JSON",__import__("json").dumps(result,sort_keys=True,indent=2),"nema_agora_phase33_integrity.json","application/json")
