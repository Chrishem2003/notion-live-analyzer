"""NEMA-AGORA Phase 31 — Research & Award Dossier."""
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.evidence_graph import build_evidence_graph
from nema_agora.evidence_synthesis import build_evidence_synthesis
from nema_agora.provenance import ProvenanceStore
from nema_agora.research_dossier import build_dossier, serialise_dossier, validate_dossier

st.set_page_config(page_title="NEMA-AGORA Research Dossier",page_icon="🏆",layout="wide")
st.title("🏆 NEMA-AGORA — Research & Award Dossier")
st.caption("Phase 31-v1 — evidence → narrative → human review")
st.warning("This dossier is research/engineering documentation only. It does not establish environmental truth, environmental impact, NEMA authorization, regulatory status, production approval, enforcement, emergency response, or autonomous authority.")

if mode_from_secrets(st.secrets)!="persistent":
    st.info("Persistent authenticated mode is required."); st.stop()
principal=principal_from_streamlit_user(st.user,st.secrets)
if not principal or not principal.is_authorised or not has_permission(principal.role,"intelligence:evidence"):
    st.error("Authenticated evidence access is required."); st.stop()
db=database_path_from_secrets(st.secrets)
if not db: st.error("Persistent database path is required."); st.stop()

records=ProvenanceStore(db).list(limit=1000)
sources=[str(r["provenance_id"]) for r in records[:50]]
domains={k:{"count":len(records) if k in ("ENGINEERING","REPRODUCIBILITY") else 0,"source_ids":sources if k in ("ENGINEERING","REPRODUCIBILITY") else [],"limitations":["Evidence is bounded by recorded artifacts."]} for k in ("ENGINEERING","WORKFLOW_OUTCOMES","HUMAN_GOVERNANCE","REPRODUCIBILITY","ACCESSIBILITY","FIELD_EVALUATION")}
synthesis=build_evidence_synthesis(evidence_domains=domains,global_limitations=("Evidence volume and representativeness constrain generalisation.","Human review is required before publication or interpretation."))
graph=build_evidence_graph(provenance_records=records,synthesis=synthesis.to_dict())
dossier=build_dossier(synthesis=synthesis.to_dict(),graph=graph.to_dict())
validation=validate_dossier(dossier)
a,b,c=st.columns(3)
a.metric("Claims",dossier.claim_count); b.metric("Linked claims",dossier.linked_claim_count); c.metric("Status",dossier.review_status)
for section in dossier.sections:
    with st.expander(section.section_id+" — "+section.title,expanded=section.section_id=="SEC-01"):
        st.write(section.content)
        if section.evidence_refs: st.write({"evidence_refs":list(section.evidence_refs)})
        st.write({"limitations":list(section.limitations)})
st.subheader("Publication control")
st.write({"valid":validation["valid"],"errors":validation["errors"],"dossier_id":dossier.dossier_id})
st.download_button("Download dossier JSON",serialise_dossier(dossier),"nema_agora_phase31_dossier.json","application/json")
st.caption(dossier.decision_notice)
