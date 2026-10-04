"""NEMA-AGORA Phase 30 — Evidence and Governance Report."""
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.evidence_graph import build_evidence_graph, build_research_report, serialise_report, validate_graph
from nema_agora.provenance import ProvenanceStore
from nema_agora.evidence_synthesis import build_evidence_synthesis

st.set_page_config(page_title="NEMA-AGORA Evidence Report",page_icon="📚",layout="wide")
st.title("📚 NEMA-AGORA — Evidence & Governance Report")
st.caption("Phase 30-v1 — provenance graph → research report")
st.warning("Research/engineering evidence only. This report does not establish environmental truth, environmental impact, NEMA authorization, regulatory status, production approval, enforcement, emergency response, or autonomous authority.")

if mode_from_secrets(st.secrets)!="persistent":
    st.info("Persistent authenticated mode is required."); st.stop()
principal=principal_from_streamlit_user(st.user,st.secrets)
if not principal or not principal.is_authorised or not has_permission(principal.role,"intelligence:evidence"):
    st.error("Authenticated evidence access is required."); st.stop()
db=database_path_from_secrets(st.secrets)
if not db: st.error("Persistent database path is required."); st.stop()

records=ProvenanceStore(db).list(limit=1000)
domains={}
for r in records:
    event=str(r.get("event_type","UNKNOWN"))
    domains.setdefault("ENGINEERING",{"count":0,"source_ids":[],"limitations":["Repository provenance is engineering evidence, not field impact evidence."]})
    domains["ENGINEERING"]["count"]+=1
    if len(domains["ENGINEERING"]["source_ids"])<50: domains["ENGINEERING"]["source_ids"].append(str(r["provenance_id"]))
for key in ("WORKFLOW_OUTCOMES","HUMAN_GOVERNANCE","REPRODUCIBILITY","ACCESSIBILITY","FIELD_EVALUATION"):
    domains.setdefault(key,{"count":0,"source_ids":[],"limitations":["Evidence is bounded by available recorded artifacts and controlled evaluation design."]})
synthesis=build_evidence_synthesis(evidence_domains=domains,global_limitations=("Evidence volume and representativeness constrain generalisation.","Field use requires permission, consent and safeguards."))
graph=build_evidence_graph(provenance_records=records,synthesis=synthesis.to_dict())
report=build_research_report(synthesis=synthesis.to_dict(),graph=graph)
v=validate_graph(graph)
a,b,c=st.columns(3)
a.metric("Graph nodes",len(graph.nodes)); b.metric("Graph edges",len(graph.edges)); c.metric("Graph validity","VALID" if v["valid"] else "CONTROL REQUIRED")
st.subheader("Claim → Evidence → Limitation")
for claim in synthesis.claims:
    with st.expander(f"{claim.claim_id} — {claim.claim}"):
        st.write({"status":claim.support_status,"sources":list(claim.source_ids),"sample_size":claim.sample_size,"limitations":list(claim.limitations)})
st.subheader("Provenance lineage")
st.write({"records":len(records),"missing_parents":list(graph.missing_parents),"orphan_claims":list(graph.orphan_claims)})
st.code(report["report_id"])
st.download_button("Download research report JSON",serialise_report(report),"nema_agora_phase30_report.json","application/json")
st.caption(graph.decision_notice)
