"""NEMA-AGORA Phase 21 - Controlled Field Evaluation Laboratory."""
from __future__ import annotations
import pandas as pd
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.field_eval import scenario_catalog, scenario_fingerprint, evaluate_scenario, summarise_results
from nema_agora.service import NemaAgoraService
from nema_agora.storage import NemaAgoraRepository

st.set_page_config(page_title="NEMA-AGORA Field Evaluation",page_icon="🧪",layout="wide")
st.title("🧪 NEMA-AGORA — Controlled Field Evaluation Laboratory")
st.caption("Phase 21 — scenario-based system evaluation")
st.warning("Scenarios are synthetic or explicitly consented test cases. Results measure system behaviour only; they do not establish environmental truth, regulatory status, NEMA authorization, enforcement, emergency response, or production approval.")
mode=mode_from_secrets(st.secrets)
principal=principal_from_streamlit_user(st.user,st.secrets) if mode=="persistent" else None
db_path=database_path_from_secrets(st.secrets) if mode=="persistent" else None
service=NemaAgoraService(NemaAgoraRepository(db_path)) if principal and principal.is_authorised and db_path else None
if not service: st.info("Authenticate in persistent mode to run field-evaluation evidence."); st.stop()
if not has_permission(principal.role,"intelligence:field_eval"): st.error("Your role cannot run field evaluation."); st.stop()

scenarios=scenario_catalog()
st.metric("Scenario set fingerprint",scenario_fingerprint(scenarios))
selected=st.selectbox("Scenario",[s.scenario_id+" — "+s.name for s in scenarios])
scenario=next(s for s in scenarios if s.scenario_id==selected.split(" — ")[0])
st.write(scenario.description)
quality=st.selectbox("Observed quality status",["VALID","INCOMPLETE","DUPLICATE_SUSPECTED","NEEDS_REVIEW","CONTROLLED","ADJUDICATION_REQUIRED"])
review=st.checkbox("Human review required",value=True)
notes=st.text_area("Evaluation notes")
if st.button("Evaluate scenario"):
    result=service.record_field_evaluation(principal,scenario=scenario,observed={"quality_status":quality,"human_review_required":review},notes=notes)
    st.success("Controlled field-evaluation result recorded.")
    st.json(result)

results=service.list_field_evaluations(principal,limit=500)
summary=summarise_results([type("R",(),{"passed":bool(x["passed"]),"scenario_id":x["scenario_id"]})() for x in results])
st.subheader("Evaluation summary")
st.metric("Scenarios evaluated",summary["total_scenarios"])
st.metric("Pass rate",f"{summary['pass_rate']*100:.1f}%")
st.info("Status: "+summary["status"])
if results: st.dataframe(pd.DataFrame(results),use_container_width=True,hide_index=True)
