"""NEMA-AGORA Phase 21 - Controlled Field Evaluation Laboratory."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.field_eval import scenario_catalog, scenario_fingerprint, summarise_results
from nema_agora.service import NemaAgoraService
from nema_agora.storage import NemaAgoraRepository

st.set_page_config(page_title="NEMA-AGORA Field Evaluation", page_icon="🧪", layout="wide")
st.title("🧪 NEMA-AGORA — Controlled Field Evaluation Laboratory")
st.caption("Phase 21-v2 — real observation → quality → intelligence → reviewer-support execution")
st.warning(
    "Scenarios are synthetic or explicitly consented test cases. Results measure software "
    "behaviour only; they do not establish environmental truth, regulatory status, NEMA "
    "authorization, enforcement, emergency response, or production approval."
)

mode = mode_from_secrets(st.secrets)
principal = principal_from_streamlit_user(st.user, st.secrets) if mode == "persistent" else None
db_path = database_path_from_secrets(st.secrets) if mode == "persistent" else None
service = NemaAgoraService(NemaAgoraRepository(db_path)) if principal and principal.is_authorised and db_path else None

if not service:
    st.info("Authenticate in persistent mode to run field-evaluation evidence.")
    st.stop()
if not has_permission(principal.role, "intelligence:field_eval"):
    st.error("Your role cannot run field evaluation.")
    st.stop()

scenarios = scenario_catalog()
st.metric("Scenario set fingerprint", scenario_fingerprint(scenarios))
st.write("The suite now executes the real pipeline rather than accepting manually entered observed outputs.")

if st.button("▶️ Run all six controlled scenarios"):
    with st.spinner("Executing the controlled synthetic field suite..."):
        summary = service.run_controlled_field_evaluation(principal)
    st.success(f"Phase 21 suite completed: {summary['status']}")
    st.metric("Pass rate", f"{summary['pass_rate'] * 100:.1f}%")
    st.json(summary)

st.subheader("Individual scenario review")
selected = st.selectbox("Scenario", [s.scenario_id + " — " + s.name for s in scenarios])
scenario = next(s for s in scenarios if s.scenario_id == selected.split(" — ")[0])
st.write(scenario.description)
st.json(
    {
        "expected_quality": scenario.expected_quality,
        "required_quality_flags": list(scenario.expected_flags),
        "human_review_required": scenario.expected_human_review,
        "safety_contract_required": scenario.expected_safety_contract,
    }
)

results = service.list_field_evaluations(principal, limit=500)
if results:
    passed = sum(bool(row["passed"]) for row in results)
    summary = summarise_results(
        [
            type("R", (), {"passed": bool(row["passed"]), "scenario_id": row["scenario_id"]})()
            for row in results
        ]
    )
    st.subheader("Evaluation summary")
    st.metric("Stored evaluations", len(results))
    st.metric("Stored pass rate", f"{summary['pass_rate'] * 100:.1f}%")
    st.info("Status: " + summary["status"])
    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
else:
    st.info("No Phase 21 evaluation results are stored yet. Run the six-scenario suite above.")
