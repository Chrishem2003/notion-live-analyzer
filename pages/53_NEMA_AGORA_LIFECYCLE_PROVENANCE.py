"""NEMA-AGORA Phase 45 — Lifecycle Provenance & Accountability."""
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.attestation_lifecycle import AttestationLifecycleRegistry
from nema_agora.governance_attestation import GovernanceAttestationRegistry
from nema_agora.lifecycle_provenance import LifecycleProvenanceRegistry, evaluate_provenance, validate_supersession_chain

st.set_page_config(page_title="NEMA-AGORA Lifecycle Provenance",page_icon="🔗",layout="wide")
st.title("NEMA-AGORA — Lifecycle Provenance & Accountability")
st.caption("Phase 45-v1 • exact decision-to-snapshot binding • reviewer/attester accountability • supersession validation")
st.info("This is a research/engineering evidence control. It does not establish NEMA authorization, environmental truth, regulatory status, production approval, enforcement or emergency authority.")

if not has_permission("admin","audit:read"):
    st.error("Governance audit access is required."); st.stop()

db=st.secrets.get("NEMA_AGORA_DB_PATH","nema_agora.db")
lr=AttestationLifecycleRegistry(db)
ar=GovernanceAttestationRegistry(db)
pr=LifecycleProvenanceRegistry(db)
decisions=lr.list(500); attestations=ar.list(500); bindings=pr.list(500)

st.subheader("Binding coverage")
st.metric("Lifecycle decisions",len(decisions))
st.metric("Provenance bindings",len(bindings))
st.metric("Attestations",len(attestations))

if bindings:
    current=bindings[0]
    result=evaluate_provenance(bindings,decisions,attestations,
        reconciliation_fingerprint=current["reconciliation_fingerprint"],
        evidence_registry_fingerprint=current["evidence_registry_fingerprint"],
        provenance_fingerprint=current["provenance_fingerprint"])
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
