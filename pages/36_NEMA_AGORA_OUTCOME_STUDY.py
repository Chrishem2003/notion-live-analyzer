"""NEMA-AGORA Phase 28 — Controlled Outcome Study."""
import pandas as pd
import streamlit as st

from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.impact import ImpactObservation, ImpactStore
from nema_agora.outcomes import build_outcome_study, validate_outcome_study

st.set_page_config(page_title="NEMA-AGORA Outcome Study", page_icon="📊", layout="wide")
st.title("📊 NEMA-AGORA — Controlled Outcome Study")
st.caption("Phase 28-v1 — paired baseline vs assisted workflow evidence")
st.warning(
    "This laboratory measures software/workflow behaviour. It does not establish environmental "
    "impact, environmental truth, NEMA authorization, regulatory status, or production approval."
)

if mode_from_secrets(st.secrets) != "persistent":
    st.info("Persistent authenticated mode is required.")
    st.stop()
principal=principal_from_streamlit_user(st.user, st.secrets)
if not principal or not principal.is_authorised or not has_permission(principal.role,"intelligence:impact"):
    st.error("Authenticated impact-evidence access is required.")
    st.stop()

db_path=database_path_from_secrets(st.secrets)
if not db_path:
    st.error("Persistent database path is required.")
    st.stop()

rows=ImpactStore(db_path).list(limit=2000)
observations=[
    ImpactObservation(
        observation_id=str(r["observation_id"]), scenario_id=str(r["scenario_id"]),
        condition=str(r["condition"]), review_seconds=float(r["review_seconds"]),
        evidence_complete=bool(r["evidence_complete"]), duplicate_correct=bool(r["duplicate_correct"]),
        reviewer_actions=int(r["reviewer_actions"]), corrected=bool(r["corrected"]),
        workflow_success=bool(r["workflow_success"]), notes=str(r.get("notes","")),
    ) for r in rows
]
study=build_outcome_study(observations)
validation=validate_outcome_study(study,observations)
st.metric("Paired scenarios",study.sample_size)
st.metric("Study validity","VALID" if validation["valid"] else "CONTROL REQUIRED")
st.json({"metrics":study.metrics,"dataset_fingerprint":study.dataset_fingerprint,"policy_version":study.policy_version})
if study.pairs:
    st.dataframe(pd.DataFrame([p.to_dict() for p in study.pairs]),use_container_width=True,hide_index=True)
else:
    st.info("No matched BASELINE/ASSISTED scenario pairs are available yet.")
st.caption(study.decision_notice)
