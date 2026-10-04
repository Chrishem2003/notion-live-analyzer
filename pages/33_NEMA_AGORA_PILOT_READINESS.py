"""NEMA-AGORA Phase 26 — controlled pilot readiness review."""
import streamlit as st

from nema_agora.auth import resolve_principal
from nema_agora.config import load_config
from nema_agora.access import require_permission
from nema_agora.service import NemaAgoraService
from nema_agora.storage import NemaAgoraRepository
from nema_agora.pilot_readiness import (
    PilotReadinessPolicy,
    evaluate_pilot_readiness,
    serialise_readiness,
)
from nema_agora.evidence import build_scorecard
from nema_agora.impact import ImpactStore
from nema_agora.accessibility import AccessibilityStore
from nema_agora.provenance import ProvenanceStore
from nema_agora.field_eval import FieldEvaluationStore
from nema_agora.review_governance import ReviewStore

st.set_page_config(page_title="NEMA-AGORA Pilot Readiness", page_icon="🛡️", layout="wide")
st.title("🛡️ NEMA-AGORA — Controlled Pilot Readiness")
st.caption("Phase 26 • evidence consolidation • human-governed gate")

config = load_config()
principal = resolve_principal(st)
if not principal.is_authorised:
    st.error("Authenticated, server-provisioned access is required.")
    st.stop()

try:
    require_permission(principal.role, "intelligence:pilot_readiness")
except PermissionError:
    st.error("Your role is not permitted to inspect pilot-readiness evidence.")
    st.stop()

repository = NemaAgoraRepository(config.database_path)
service = NemaAgoraService(repository)

st.info(
    "This workspace consolidates engineering evidence for a controlled pilot "
    "review. It cannot approve NEMA integration, regulatory action, emergency "
    "response, environmental truth, or production deployment."
)

admissions = service.list_model_admissions(principal, limit=1)
admission_id = admissions[0]["admission_id"] if admissions else None
shadow = service.build_shadow_monitoring_snapshot(
    principal, admission_id=admission_id
)

scorecard = build_scorecard(
    impact_count=len(ImpactStore(config.database_path).list()),
    accessibility_count=len(AccessibilityStore(config.database_path).list()),
    provenance_count=len(ProvenanceStore(config.database_path).list()),
    field_evaluation_count=len(FieldEvaluationStore(config.database_path).list()),
    human_governance_count=len(ReviewStore(config.database_path).list_reviews()),
)

manifest_id = st.text_input("Deployment manifest ID")
git_revision = st.text_input("Verified Git revision")
manifest = {"manifest_id": manifest_id, "git_revision": git_revision}

governance = {
    "human_review_required": True,
    "explicit_lifecycle_control": True,
    "autonomous_state_change_blocked": True,
}

result = evaluate_pilot_readiness(
    evidence_scorecard=scorecard.to_dict(),
    shadow_monitoring=shadow,
    reproducibility_manifest=manifest,
    human_governance=governance,
    policy=PilotReadinessPolicy(),
)

if result.decision == "READY_FOR_CONTROLLED_PILOT_REVIEW":
    st.success(result.decision)
else:
    st.warning(result.decision)

cols = st.columns(4)
cols[0].metric("Passed gates", sum(result.gates.values()))
cols[1].metric("Shadow runs", result.evidence["shadow_runs"])
cols[2].metric("Shadow error rate", f'{result.evidence["shadow_error_rate"]:.1%}')
cols[3].metric("Readiness ID", result.readiness_id[:12])

st.subheader("Gate review")
st.table([{"gate": key, "passed": value} for key, value in result.gates.items()])

if result.warnings:
    st.warning("\n".join(result.warnings))

st.subheader("Evidence snapshot")
st.json(result.evidence)

st.download_button(
    "Download readiness record",
    data=serialise_readiness(result),
    file_name="nema_agora_pilot_readiness.json",
    mime="application/json",
)

st.caption(result.decision_notice)
