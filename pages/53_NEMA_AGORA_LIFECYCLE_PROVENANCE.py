"""NEMA-AGORA Phase 45 — Lifecycle Provenance & Accountability."""
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.closure_evidence import reconcile_with_evidence
from nema_agora.governance_attestation import build_integrity_snapshot
from nema_agora.governance_exception_resolution import GovernanceExceptionResolver
from nema_agora.attestation_lifecycle import AttestationLifecycleRegistry
from nema_agora.governance_attestation import GovernanceAttestationRegistry
from nema_agora.lifecycle_provenance import LifecycleProvenanceRegistry, evaluate_provenance, validate_supersession_chain

st.set_page_config(page_title="NEMA-AGORA Lifecycle Provenance",page_icon="🔗",layout="wide")
st.title("NEMA-AGORA — Lifecycle Provenance & Accountability")
st.caption("Phase 45-v1 • exact decision-to-snapshot binding • reviewer/attester accountability • supersession validation")
st.info("This is a research/engineering evidence control. It does not establish NEMA authorization, environmental truth, regulatory status, production approval, enforcement or emergency authority.")

if mode_from_secrets(st.secrets)!="persistent":
    st.warning("Persistent authenticated mode is required."); st.stop()
principal=principal_from_streamlit_user(st.user,st.secrets)
if not principal or not principal.is_authorised or principal.role not in {"reviewer","coordinator","admin"} or not has_permission(principal.role,"audit:read"):
    st.error("Authorized reviewer, coordinator, or admin access is required."); st.stop()

db=database_path_from_secrets(st.secrets)
lr=AttestationLifecycleRegistry(db)
ar=GovernanceAttestationRegistry(db)
pr=LifecycleProvenanceRegistry(db)
decisions=lr.list(500); attestations=ar.list(500); bindings=pr.list(500)
try:
    derived=reconcile_with_evidence(db)
    reconciliation={"reconciliation_fingerprint":derived["closure"]["reconciliation_fingerprint"],"exceptions":[{"code":x["exception_code"],"decision_kind":x["decision_kind"],"artifact_id":x["artifact_id"],"severity":x.get("severity"),"detail":x.get("detail")} for x in derived["closure"]["results"]]}
    resolutions=GovernanceExceptionResolver(db).list_resolutions(limit=500)
    snapshot=build_integrity_snapshot(reconciliation=reconciliation,closure=derived["closure"],resolutions=resolutions,evidence_rows=derived["evidence"],attestations=attestations)
    current=snapshot["integrity"]["registry_fingerprint"]
    current_reconciliation=snapshot["provenance"]["reconciliation_fingerprint"]
    current_provenance=snapshot["provenance_fingerprint"]
except Exception as exc:
    st.error(f"Current governance snapshot failed closed: {exc}"); st.stop()

st.subheader("Binding coverage")
st.metric("Lifecycle decisions",len(decisions))
st.metric("Provenance bindings",len(bindings))
st.metric("Attestations",len(attestations))

if bindings:
    result=evaluate_provenance(bindings,decisions,attestations,
        reconciliation_fingerprint=current_reconciliation,
        evidence_registry_fingerprint=current,
        provenance_fingerprint=current_provenance)
    chain=validate_supersession_chain(bindings,attestations)
    a,b,c=st.columns(3)
    a.metric("Valid bindings",result["valid_count"])
    b.metric("Stale bindings",result["stale_count"])
    c.metric("Supersession chain","VALID" if chain["valid"] else "FAILED")
    if result["failure_count"]: st.error("Provenance failures detected; lifecycle evidence must be reviewed.")
    if not chain["valid"]: st.error("Supersession chain failure detected.")
    st.dataframe(result["bindings"],use_container_width=True)
else:
    st.warning("No provenance bindings exist yet. Phase 45 is fail-closed until lifecycle decisions are explicitly bound to an exact snapshot.")

st.subheader("Accountability chain")
st.code("Attestation → Lifecycle Decision → Reviewer Identity → Exact Snapshot → Supersession Chain → Current Governance State")
st.warning("Bindings are append-only. A changed snapshot makes an old binding stale; the system does not silently repair or reinterpret historical decisions.")
