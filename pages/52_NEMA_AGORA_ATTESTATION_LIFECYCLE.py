"""NEMA-AGORA Phase 44 — Attestation Lifecycle Governance."""
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.closure_evidence import reconcile_with_evidence
from nema_agora.governance_attestation import GovernanceAttestationRegistry, build_integrity_snapshot
from nema_agora.governance_exception_resolution import GovernanceExceptionResolver
from nema_agora.attestation_lifecycle import (
    AttestationLifecycleRegistry, evaluate_lifecycle, APPROVE, REJECT, REVOKE, SUPERSEDE,
    ACTIVE, CONTROL_REQUIRED_STATE,
)

st.set_page_config(page_title="NEMA-AGORA Attestation Lifecycle", page_icon="◎", layout="wide")
st.title("NEMA-AGORA — Attestation Lifecycle Governance")
st.caption("Phase 44-v1 • second-person review, explicit lifecycle decisions, expiry, revocation, supersession")
st.info("This surface governs human attestations; it never infers approval. Lifecycle decisions are append-only, human-authorized and bound to the current integrity snapshot.")

if mode_from_secrets(st.secrets) != "persistent":
    st.warning("Persistent authenticated mode is required."); st.stop()
principal = principal_from_streamlit_user(st.user, st.secrets)
if (not principal or not principal.is_authorised or principal.role not in {"coordinator", "admin"}
        or not has_permission(principal.role, "audit:read")):
    st.error("Authorized coordinator or admin access is required."); st.stop()

db = database_path_from_secrets(st.secrets)
attestation_registry = GovernanceAttestationRegistry(db)
lifecycle_registry = AttestationLifecycleRegistry(db)

try:
    derived = reconcile_with_evidence(db)
    reconciliation = {
        "reconciliation_fingerprint": derived["closure"]["reconciliation_fingerprint"],
        "exceptions": [
            {"code": x["exception_code"], "decision_kind": x["decision_kind"],
             "artifact_id": x["artifact_id"], "severity": x.get("severity"), "detail": x.get("detail")}
            for x in derived["closure"]["results"]
        ],
    }
    resolutions = GovernanceExceptionResolver(db).list_resolutions(limit=500)
    attestations = attestation_registry.list(limit=500)
    snapshot = build_integrity_snapshot(
        reconciliation=reconciliation, closure=derived["closure"], resolutions=resolutions,
        evidence_rows=derived["evidence"], attestations=attestations,
    )
    lifecycle = evaluate_lifecycle(
        snapshot["attestations"], lifecycle_registry.list(limit=500),
        reconciliation_fingerprint=reconciliation["reconciliation_fingerprint"],
        evidence_registry_fingerprint=snapshot["integrity"]["registry_fingerprint"],
        provenance_fingerprint=snapshot["provenance_fingerprint"],
        integrity_valid=snapshot["integrity"]["valid"],
        provenance_complete=snapshot["provenance"]["complete"],
    )
except Exception as exc:
    st.error(f"Phase 44 lifecycle evaluation failed closed: {exc}"); st.stop()

c = st.columns(5)
c[0].metric("Integrity", "VALID" if snapshot["integrity"]["valid"] else "FAILED")
c[1].metric("Provenance", "COMPLETE" if snapshot["provenance"]["complete"] else "INCOMPLETE")
c[2].metric("Attestations", snapshot["attestation_count"])
c[3].metric("Active", lifecycle["active_count"])
c[4].metric("Conflicts", lifecycle["conflict_count"])

if lifecycle["overall_state"] == ACTIVE:
    st.success("CURRENT LIFECYCLE — an exact attestation has passed second-person review and is active.")
elif lifecycle["overall_state"] == CONTROL_REQUIRED_STATE:
    st.error("CONTROL REQUIRED — integrity/provenance failed or lifecycle conflict exists.")
else:
    st.warning("PENDING LIFECYCLE REVIEW — no current attestation is active.")

st.subheader("Current attestation lifecycle")
rows = lifecycle["items"]
if rows:
    st.dataframe([{
        "attestation_id": x["attestation_id"], "attester": x.get("actor_id"),
        "attestation": x.get("effective_state"), "lifecycle": x.get("lifecycle_state"),
        "reviewer": (x.get("latest_decision") or {}).get("actor_id"),
        "expires_at": (x.get("latest_decision") or {}).get("expires_at"),
    } for x in rows], use_container_width=True)
else:
    st.info("No attestation records are available.")

st.subheader("Human lifecycle decision")
if not has_permission(principal.role, "intelligence:attestation_lifecycle"):
    st.warning("Your role is authenticated but lacks the lifecycle decision permission."); st.stop()

eligible = [x for x in rows if x.get("effective_state") == "ATTESTED"]
if not eligible:
    st.info("No current exact attestation is eligible for lifecycle review."); st.stop()

selected_id = st.selectbox("Attestation", [x["attestation_id"] for x in eligible])
selected = next(x for x in eligible if x["attestation_id"] == selected_id)
st.caption("Attested by " + str(selected.get("actor_id")) + ". A second person is required for approval/rejection.")

decision_label = st.selectbox("Decision", ["APPROVE", "REJECT", "REVOKE", "SUPERSEDE"])
decision = {"APPROVE": APPROVE, "REJECT": REJECT, "REVOKE": REVOKE, "SUPERSEDE": SUPERSEDE}[decision_label]
rationale = st.text_area("Decision rationale", max_chars=2000)
expires_at = None
superseding_id = None
if decision == APPROVE:
    expires_at = st.text_input("Expiry (ISO-8601 UTC)", placeholder="2026-12-31T23:59:59+00:00").strip() or None
elif decision == SUPERSEDE:
    superseding_id = st.text_input("Replacement attestation ID").strip() or None

if st.button("Record human lifecycle decision", type="primary"):
    try:
        row = lifecycle_registry.decide(
            attestation_id=selected_id, decision=decision, actor_id=principal.actor_id,
            role=principal.role, attester_actor_id=selected.get("actor_id"),
            rationale=rationale, expires_at=expires_at,
            superseding_attestation_id=superseding_id,
        )
        st.success("Recorded immutable lifecycle decision " + row["decision_id"] + ".")
        st.rerun()
    except Exception as exc:
        st.error("Decision rejected: " + str(exc))

st.subheader("Immutable lifecycle decision ledger")
st.dataframe(lifecycle_registry.list(limit=500), use_container_width=True)
st.warning("Governance boundary: lifecycle states are research/engineering governance evidence only. They do not authorize NEMA integration, regulatory action, enforcement, emergency response, official reporting, production deployment, or autonomous decisions.")
