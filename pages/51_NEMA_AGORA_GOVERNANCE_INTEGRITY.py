"""NEMA-AGORA Phase 43 — Governance Evidence Integrity & Attestation."""
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.closure_evidence import reconcile_with_evidence
from nema_agora.governance_attestation import (
    GovernanceAttestationRegistry, build_integrity_snapshot, ATTESTED, PENDING, CONTROL_REQUIRED,
)

st.set_page_config(page_title="NEMA-AGORA Governance Integrity",page_icon="◎",layout="wide")
st.title("NEMA-AGORA — Governance Evidence Integrity & Attestation")
st.caption("Phase 43-v1 • integrity verification, provenance completeness, explicit human attestation")
st.info("Authenticated governance surface. Integrity is verified against the current derived evidence snapshot; attestation is never inferred and never mutates source records.")

if mode_from_secrets(st.secrets)!="persistent":
    st.warning("Persistent authenticated mode is required."); st.stop()
principal=principal_from_streamlit_user(st.user,st.secrets)
if not principal or not principal.is_authorised or principal.role not in {"reviewer","coordinator","admin"} or not has_permission(principal.role,"audit:read"):
    st.error("Authorized reviewer, coordinator, or admin access is required."); st.stop()

db=database_path_from_secrets(st.secrets)
registry=GovernanceAttestationRegistry(db)
try:
    derived=reconcile_with_evidence(db)
    reconciliation={"reconciliation_fingerprint":derived["closure"]["reconciliation_fingerprint"],
        "exceptions":[{"code":x["exception_code"],"decision_kind":x["decision_kind"],"artifact_id":x["artifact_id"],
                       "severity":x.get("severity"),"detail":x.get("detail")} for x in derived["closure"]["results"]]}
    snapshot=build_integrity_snapshot(reconciliation=reconciliation,closure=derived["closure"],
        resolutions=[],evidence_rows=derived["evidence"],attestations=registry.list())
    # Phase 42 returns evidence plus closure, but current resolutions are not exposed.
    # For provenance completeness we recover the resolution events from the authoritative registry.
    from nema_agora.governance_exception_resolution import GovernanceExceptionResolver
    resolutions=GovernanceExceptionResolver(db).list_resolutions(limit=500)
    snapshot=build_integrity_snapshot(reconciliation=reconciliation,closure=derived["closure"],
        resolutions=resolutions,evidence_rows=derived["evidence"],attestations=registry.list())
except Exception as exc:
    st.error(f"Phase 43 integrity evaluation failed closed: {exc}"); st.stop()

integrity=snapshot["integrity"]; provenance=snapshot["provenance"]
if snapshot["overall_state"]==ATTESTED: st.success("CURRENT ATTESTATION — exact reconciliation, evidence and provenance snapshot is attested.")
elif snapshot["overall_state"]==CONTROL_REQUIRED: st.error("CONTROL REQUIRED — integrity or provenance completeness failed.")
else: st.warning("PENDING HUMAN ATTESTATION — the current snapshot is not attested.")

c=st.columns(6)
for col,label,value in zip(c,["Integrity","Provenance","Attested","Evidence rows","Integrity errors","Missing provenance"],
    ["PASS" if integrity["valid"] else "FAIL","COMPLETE" if provenance["complete"] else "INCOMPLETE",
     snapshot["active_attestation_count"],integrity["row_count"],integrity["error_count"],
     sum(len(x["missing"]) for x in provenance["items"])]):
    col.metric(label,value)

st.subheader("Evidence integrity")
st.dataframe(integrity["errors"] if integrity["errors"] else [{"status":"VALID","registry_fingerprint":integrity["registry_fingerprint"]}],
             use_container_width=True,hide_index=True)
st.subheader("Provenance completeness")
st.dataframe(provenance["items"] if provenance["items"] else [{"status":"NO_CURRENT_EXCEPTIONS"}],
             use_container_width=True,hide_index=True)
st.subheader("Attestation history")
st.dataframe(snapshot["attestations"] if snapshot["attestations"] else [{"status":"NO_ATTESTATIONS"}],
             use_container_width=True,hide_index=True)

if has_permission(principal.role,"intelligence:attest"):
    st.subheader("Human attestation")
    st.caption("Only the authenticated coordinator/admin principal can create an attestation. The attestation binds the exact current reconciliation, evidence-registry and provenance fingerprints.")
    if integrity["valid"] and provenance["complete"]:
        reason=st.text_area("Attestation rationale",max_chars=2000)
        if st.button("Record ATTESTED",type="primary"):
            try:
                registry.attest(actor_id=principal.subject_key,role=principal.role,
                    reconciliation_fingerprint=snapshot["provenance"]["reconciliation_fingerprint"],
                    evidence_registry_fingerprint=integrity["registry_fingerprint"],
                    provenance_fingerprint=snapshot["provenance_fingerprint"],reason=reason)
                st.success("ATTESTED record appended. Re-run the page to verify the exact snapshot is active.")
            except Exception as exc: st.error(f"Attestation rejected: {exc}")
    else:
        st.error("Attestation disabled because integrity/provenance gates are not satisfied.")
else:
    st.info("Read-only for this role. Coordinator/admin is required for human attestation.")

st.subheader("Governance boundaries")
st.markdown("Attestation is governance evidence only. It does not mean NEMA approval, regulatory authorization, environmental truth, production approval, enforcement authority, emergency response authorization, or autonomous decision authority.")
st.caption(snapshot["notice"])
