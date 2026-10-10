"""NEMA-AGORA Phase 23 — Community & Accessibility Laboratory."""
import pandas as pd
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.accessibility import AccessibilityStore, make_observation, summarise

st.set_page_config(page_title="NEMA-AGORA Accessibility", page_icon="♿", layout="wide")
st.title("♿ NEMA-AGORA — Community & Accessibility Laboratory")
st.warning("Controlled participation evidence only. Do not enter names, phone numbers, precise locations, health information, or other personal data.")

if mode_from_secrets(st.secrets) != "persistent":
    st.info("Persistent authenticated mode is required.")
    st.stop()
principal=principal_from_streamlit_user(st.user, st.secrets)
if not principal or not principal.is_authorised:
    st.error("Authenticated provisioned access is required.")
    st.stop()
if not has_permission(principal.role,"intelligence:field_eval"):
    st.error("Your role cannot access this laboratory.")
    st.stop()

scenario=st.text_input("Synthetic scenario ID","COMMUNITY-01")
channel=st.selectbox("Interaction channel",["WEB","LOW_BANDWIDTH","ASSISTED"])
outcome=st.selectbox("Outcome",["COMPLETED","PARTIAL","ABANDONED"])
expected=st.number_input("Expected workflow steps",1,50,5)
completed=st.number_input("Completed steps",0,int(expected),int(expected))
barrier=st.checkbox("Accessibility barrier encountered")
review=st.checkbox("Human review required",value=True)
notes=st.text_area("Non-identifying notes")

if st.button("Record participation observation"):
    row=make_observation(scenario_id=scenario,channel=channel,outcome=outcome,
        steps_completed=completed,steps_expected=expected,
        accessibility_barrier=barrier,review_required=review,notes=notes)
    AccessibilityStore(database_path_from_secrets(st.secrets)).save(row)
    st.success("Controlled observation recorded.")

rows=AccessibilityStore(database_path_from_secrets(st.secrets)).list()
if rows:
    from nema_agora.accessibility import AccessibilityObservation
    typed=[AccessibilityObservation(
        observation_id=x["observation_id"],scenario_id=x["scenario_id"],
        channel=x["channel"],outcome=x["outcome"],steps_completed=x["steps_completed"],
        steps_expected=x["steps_expected"],accessibility_barrier=bool(x["accessibility_barrier"]),
        review_required=bool(x["review_required"]),notes=x["notes"],
        created_at=x["created_at"],policy_version=x["policy_version"]) for x in rows]
    st.subheader("Participation evidence")
    st.json(summarise(typed))
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
else:
    st.info("No controlled observations recorded yet.")
