"""NEMA-AGORA Phase 19 - Human Review & Re-evaluation."""
from __future__ import annotations
import pandas as pd
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.review_governance import REVIEW_DECISIONS
from nema_agora.service import NemaAgoraService
from nema_agora.storage import NemaAgoraRepository

st.set_page_config(page_title="NEMA-AGORA Human Review", page_icon="🧑‍⚖️", layout="wide")
st.title("🧑‍⚖️ NEMA-AGORA - Human Review & Re-evaluation")
st.caption("Phase 19 - human judgement closes the controlled-shadow evidence loop")
st.warning("Human review evaluates advisory model usefulness and safety. It does not establish environmental truth, regulatory status, enforcement priority, emergency response, production approval, or NEMA authorization.")

mode = mode_from_secrets(st.secrets)
principal = principal_from_streamlit_user(st.user, st.secrets) if mode == "persistent" else None
db_path = database_path_from_secrets(st.secrets) if mode == "persistent" else None
service = NemaAgoraService(NemaAgoraRepository(db_path)) if principal and principal.is_authorised and db_path else None
if not service:
    st.info("Authenticate in persistent mode to use human review.")
    st.stop()
if not has_permission(principal.role, "intelligence:review_shadow"):
    st.error("Your role cannot review controlled-shadow evidence.")
    st.stop()

admissions = [x for x in service.list_model_admissions(principal, limit=100) if x["decision"] == "ADMITTED_FOR_CONTROLLED_SHADOW"]
if not admissions:
    st.info("No admitted model is available for human review.")
    st.stop()
selected = st.selectbox("Admission", [x["admission_id"] for x in admissions])
runs = service.list_controlled_shadow_runs(principal, admission_id=selected, limit=500)
reviews = service.list_shadow_reviews(principal, admission_id=selected, limit=500)
reevaluation = service.build_reevaluation(principal, admission_id=selected, limit=500)

st.subheader("Re-evaluation signal")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Shadow runs", reevaluation["runs_observed"])
c2.metric("Human reviewed", reevaluation["reviewed_runs"])
c3.metric("Correction rate", f"{reevaluation['correction_rate']*100:.1f}%")
c4.metric("Unsafe rate", f"{reevaluation['unsafe_rate']*100:.1f}%")
st.info(f"Governance recommendation: **{reevaluation['recommendation']}**")
for alert in reevaluation["alerts"]:
    st.warning(alert)

st.subheader("Pending / recent shadow runs")
reviewed_ids = {x["run_id"] for x in reviews}
pending = [x for x in runs if x["run_id"] not in reviewed_ids]
if pending:
    selected_run_id = st.selectbox("Run to review", [x["run_id"] for x in pending])
    run = next(x for x in pending if x["run_id"] == selected_run_id)
    st.json({"run_id": run["run_id"], "case_id": run["case_id"], "model_version": run["model_version"],
             "status": run["status"], "latency_ms": run["latency_ms"], "output": run["output"]})
    decision = st.selectbox("Human judgement", list(REVIEW_DECISIONS))
    corrected = st.text_input("Corrected category (optional)")
    notes = st.text_area("Review notes", max_chars=1500)
    if st.button("Record human review"):
        service.record_shadow_review(principal, run=run, decision=decision, corrected_category=corrected or None, notes=notes)
        st.success("Human review recorded in the governed evidence ledger.")
        st.rerun()
else:
    st.info("No unreviewed shadow runs are currently available.")

st.subheader("Recent human reviews")
if reviews:
    st.dataframe(pd.DataFrame(reviews), use_container_width=True, hide_index=True)

if has_permission(principal.role, "intelligence:govern_shadow"):
    st.subheader("Explicit governance decision")
    action = st.selectbox("Lifecycle action", ["RETAIN", "REVIEW", "SUSPEND", "RE_ADMIT_REQUIRED"])
    rationale = st.text_area("Governance rationale", max_chars=1500)
    if st.button("Record governance decision"):
        admission = next(x for x in admissions if x["admission_id"] == selected)
        service.record_lifecycle_decision(principal, admission=admission, action=action, rationale=rationale, evidence_snapshot=reevaluation)
        st.success("Human governance decision recorded. The system does not autonomously change model status.")
        st.rerun()

lifecycle = service.list_lifecycle_decisions(principal, admission_id=selected, limit=100)
if lifecycle:
    st.subheader("Governance decision history")
    st.dataframe(pd.DataFrame(lifecycle), use_container_width=True, hide_index=True)

st.caption("Phase 19 is a human-governed re-evaluation loop. Recommendations are not autonomous suspension, regulatory determination, or production decisions.")
