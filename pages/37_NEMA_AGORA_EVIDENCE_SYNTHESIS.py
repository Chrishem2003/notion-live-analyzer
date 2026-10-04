"""NEMA-AGORA Phase 29 — Evidence Synthesis."""
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.accessibility import AccessibilityStore
from nema_agora.evidence_synthesis import build_evidence_synthesis, serialise_synthesis, validate_synthesis
from nema_agora.field_eval import FieldEvaluationStore
from nema_agora.impact import ImpactStore
from nema_agora.provenance import ProvenanceStore

st.set_page_config(page_title="NEMA-AGORA Evidence Synthesis",page_icon="🧭",layout="wide")
st.title("🧭 NEMA-AGORA — Evidence Synthesis")
st.caption("Phase 29-v1 — claim → evidence → limitation")
st.warning("This synthesis describes engineering/research evidence only. It does not establish environmental impact, environmental truth, regulatory status, NEMA authorization, or production approval.")

if mode_from_secrets(st.secrets)!="persistent":
    st.info("Persistent authenticated mode is required."); st.stop()
principal=principal_from_streamlit_user(st.user,st.secrets)
if not principal or not principal.is_authorised or not has_permission(principal.role,"intelligence:evidence"):
    st.error("Authenticated evidence access is required."); st.stop()
db_path=database_path_from_secrets(st.secrets)
if not db_path:
    st.error("Persistent database path is required."); st.stop()

impact=ImpactStore(db_path).list(limit=2000)
access=AccessibilityStore(db_path).list(limit=2000)
field=FieldEvaluationStore(db_path).list(limit=2000)
provenance=ProvenanceStore(db_path).list(limit=2000)

domains={
 "ENGINEERING":{"count":len(provenance),"sample_size":len(provenance),"source_ids":[str(x["provenance_id"]) for x in provenance[:50]],"limitations":["Engineering counts are repository/evidence records, not field outcomes."]},
 "WORKFLOW_OUTCOMES":{"count":len(impact),"sample_size":len(impact),"source_ids":[str(x["observation_id"]) for x in impact[:50]],"limitations":["Outcome observations measure software/workflow behaviour and may not represent real-world users."]},
 "HUMAN_GOVERNANCE":{"count":len(field),"sample_size":len(field),"source_ids":[str(x["evaluation_id"]) for x in field[:50]],"limitations":["Controlled scenarios do not establish effectiveness in operational environments."]},
 "REPRODUCIBILITY":{"count":len(provenance),"sample_size":len(provenance),"source_ids":[str(x["provenance_id"]) for x in provenance[:50]],"limitations":["Provenance records demonstrate traceability of recorded events only."]},
 "ACCESSIBILITY":{"count":len(access),"sample_size":len(access),"source_ids":[str(x["observation_id"]) for x in access[:50]],"limitations":["Accessibility evidence is aggregate and non-identifying; it is not demographic inference."]},
 "FIELD_EVALUATION":{"count":len(field),"sample_size":len(field),"source_ids":[str(x["evaluation_id"]) for x in field[:50]],"limitations":["Synthetic/controlled scenarios are not environmental truth or field impact evidence."]},
}
synthesis=build_evidence_synthesis(evidence_domains=domains,global_limitations=(
 "Evidence volume, selection, annotation quality and representativeness constrain generalisation.",
 "Real-user or field use requires appropriate permission, consent and institutional safeguards.",
 "No result here authorises autonomous enforcement, emergency response, official reporting or regulatory decisions.",
))
validation=validate_synthesis(synthesis)
c1,c2,c3=st.columns(3)
c1.metric("Evidence domains",len(synthesis.domains)); c2.metric("Claims",len(synthesis.claims)); c3.metric("Synthesis validity","VALID" if validation["valid"] else "CONTROL REQUIRED")
st.subheader("Claim → evidence → limitation")
for claim in synthesis.claims:
    with st.expander(f"{claim.claim_id} — {claim.claim}"):
        st.write({"status":claim.support_status,"domain":claim.evidence_domain,"evidence_type":claim.evidence_type,"sample_size":claim.sample_size,"source_ids":list(claim.source_ids),"limitations":list(claim.limitations)})
st.subheader("Domain coverage")
st.dataframe([{"domain":k,"count":v["count"],"sample_size":v["sample_size"],"sources":len(v["source_ids"]),"limitations":len(v["limitations"])} for k,v in synthesis.domains.items()],use_container_width=True,hide_index=True)
st.subheader("Reproducible artifact")
st.code(synthesis.evidence_fingerprint)
st.download_button("Download evidence synthesis JSON",serialise_synthesis(synthesis),"nema_agora_phase29_evidence_synthesis.json","application/json")
st.caption(synthesis.decision_notice)
