"""NEMA-AGORA Phase 46 — Governance Evidence Observatory."""
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.closure_evidence import reconcile_with_evidence
from nema_agora.governance_attestation import GovernanceAttestationRegistry, build_integrity_snapshot
from nema_agora.governance_exception_resolution import GovernanceExceptionResolver
from nema_agora.attestation_lifecycle import AttestationLifecycleRegistry, evaluate_lifecycle
from nema_agora.lifecycle_provenance import LifecycleProvenanceRegistry, evaluate_provenance, validate_supersession_chain
from nema_agora.evidence_observatory import build_observatory

st.set_page_config(page_title="NEMA-AGORA Evidence Observatory",page_icon="◎",layout="wide")
st.title("NEMA-AGORA — Governance Evidence Observatory")
st.caption("Phase 46-v1 • read-only evidence coverage across integrity, attestation, lifecycle and provenance")
st.info("Research/engineering evidence surface only. It does not establish NEMA authorization, regulatory status, environmental truth, production approval, enforcement or emergency authority.")

if mode_from_secrets(st.secrets)!="persistent":
    st.warning("Persistent authenticated mode is required."); st.stop()
principal=principal_from_streamlit_user(st.user,st.secrets)
if not principal or not principal.is_authorised or principal.role not in {"reviewer","coordinator","admin"} or not has_permission(principal.role,"audit:read"):
    st.error("Authorized reviewer, coordinator, or admin access is required."); st.stop()

db=database_path_from_secrets(st.secrets)
try:
    ar=GovernanceAttestationRegistry(db); lr=AttestationLifecycleRegistry(db); pr=LifecycleProvenanceRegistry(db)
    derived=reconcile_with_evidence(db)
    reconciliation={"reconciliation_fingerprint":derived["closure"]["reconciliation_fingerprint"],
        "exceptions":[{"code":x["exception_code"],"decision_kind":x["decision_kind"],"artifact_id":x["artifact_id"],
        "severity":x.get("severity"),"detail":x.get("detail")} for x in derived["closure"]["results"]]}
    resolutions=GovernanceExceptionResolver(db).list_resolutions(limit=500)
    attestations=ar.list(500)
    snapshot=build_integrity_snapshot(reconciliation=reconciliation,closure=derived["closure"],resolutions=resolutions,evidence_rows=derived["evidence"],attestations=attestations)
    decisions=lr.list(500); bindings=pr.list(500)
    life=evaluate_lifecycle(attestations,decisions,
        reconciliation_fingerprint=snapshot["provenance"]["reconciliation_fingerprint"],
        evidence_registry_fingerprint=snapshot["integrity"]["registry_fingerprint"],
        provenance_fingerprint=snapshot["provenance_fingerprint"],
        integrity_valid=snapshot["integrity"]["valid"],provenance_complete=snapshot["provenance"]["complete"])
    prov=evaluate_provenance(bindings,decisions,attestations,
        reconciliation_fingerprint=snapshot["provenance"]["reconciliation_fingerprint"],
        evidence_registry_fingerprint=snapshot["integrity"]["registry_fingerprint"],
        provenance_fingerprint=snapshot["provenance_fingerprint"])
    chain=validate_supersession_chain(bindings,attestations)
    obs=build_observatory(attestations=attestations,lifecycle_items=life["items"],provenance_result=prov,
        integrity_valid=snapshot["integrity"]["valid"],provenance_complete=snapshot["provenance"]["complete"])
except Exception as exc:
    st.error(f"Observatory failed closed: {exc}"); st.stop()

if obs["overall_state"]=="CONTROL_REQUIRED": st.error("CONTROL REQUIRED — evidence coverage cannot support a clean governance interpretation.")
elif obs["overall_state"]=="READY_FOR_HUMAN_REVIEW": st.warning("READY FOR HUMAN REVIEW — evidence coverage has explicit gaps.")
else: st.success("EVIDENCE COVERAGE OK — this is not production or regulatory approval.")

st.metric("Overall state",obs["overall_state"])
c=st.columns(6)
for col,label,key in zip(c,["Attestations","Attested","Active","Stale","Control required","Provenance failures"],["attestations","attested","active","stale","control_required","provenance_failures"]):
    col.metric(label,obs["coverage"][key])
st.subheader("Coverage gaps")
st.dataframe([{"gap":x} for x in obs["gaps"]] or [{"gap":"NONE"}],use_container_width=True,hide_index=True)
st.subheader("Supersession chain")
st.metric("Chain status","VALID" if chain["valid"] else "FAILED")
if not chain["valid"]: st.dataframe(chain["failures"],use_container_width=True,hide_index=True)
st.subheader("Lifecycle evidence")
st.dataframe(life["items"] or [{"status":"NO_ATTESTATIONS"}],use_container_width=True,hide_index=True)
st.subheader("Provenance evidence")
st.dataframe(prov["bindings"] or [{"status":"NO_BINDINGS"}],use_container_width=True,hide_index=True)
st.caption(obs["notice"])
