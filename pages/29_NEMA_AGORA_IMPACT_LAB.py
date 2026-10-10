"""NEMA-AGORA Phase 22 — Impact Measurement Laboratory."""
import pandas as pd
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.impact import ImpactStore, make_observation, summarise_impact

st.set_page_config(page_title="NEMA-AGORA Impact Lab", page_icon="📊", layout="wide")
st.title("📊 NEMA-AGORA — Impact Measurement Laboratory")
st.warning("Controlled synthetic/consented evaluation only. Metrics describe system behaviour; they do not establish environmental impact, regulatory status, NEMA authorization, or production approval.")

if mode_from_secrets(st.secrets) != "persistent":
    st.info("Impact evidence requires persistent authenticated mode.")
    st.stop()

principal = principal_from_streamlit_user(st.user, st.secrets)
db_path = database_path_from_secrets(st.secrets)
if not principal or not principal.is_authorised:
    st.error("Authenticated provisioned access is required.")
    st.stop()
if not has_permission(principal.role, "intelligence:impact"):
    st.error("Your role cannot access the impact laboratory.")
    st.stop()

scenario_id = st.text_input("Scenario ID", "SCN-01")
condition = st.selectbox("Condition", ["BASELINE", "ASSISTED"])
review_seconds = st.number_input("Review time (seconds)", min_value=0.0, value=60.0)
evidence_complete = st.checkbox("Evidence complete")
duplicate_correct = st.checkbox("Duplicate handling correct")
reviewer_actions = st.number_input("Reviewer actions", min_value=0, value=3)
corrected = st.checkbox("Human correction required")
workflow_success = st.checkbox("End-to-end workflow succeeded", value=True)
notes = st.text_area("Notes")

if st.button("Record impact observation"):
    obs = make_observation(scenario_id=scenario_id, condition=condition,
        review_seconds=review_seconds, evidence_complete=evidence_complete,
        duplicate_correct=duplicate_correct, reviewer_actions=reviewer_actions,
        corrected=corrected, workflow_success=workflow_success, notes=notes)
    ImpactStore(db_path).save(obs)
    st.success("Controlled impact observation recorded.")

rows = ImpactStore(db_path).list()
if rows:
    from dataclasses import fields
    from nema_agora.impact import ImpactObservation
    observations = [ImpactObservation(
        observation_id=x["observation_id"], scenario_id=x["scenario_id"], condition=x["condition"],
        review_seconds=x["review_seconds"], evidence_complete=bool(x["evidence_complete"]),
        duplicate_correct=bool(x["duplicate_correct"]), reviewer_actions=x["reviewer_actions"],
        corrected=bool(x["corrected"]), workflow_success=bool(x["workflow_success"]),
        notes=x["notes"]) for x in rows]
    summary = summarise_impact(observations)
    st.subheader("Controlled comparison")
    st.json(summary.to_dict())
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.info("No controlled observations recorded yet.")
