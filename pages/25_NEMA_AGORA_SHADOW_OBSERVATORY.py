"""NEMA-AGORA Phase 18 - Shadow Monitoring & Evidence Observatory."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.service import NemaAgoraService
from nema_agora.storage import NemaAgoraRepository

st.set_page_config(page_title="NEMA-AGORA Shadow Observatory", page_icon="📡", layout="wide")
st.title("📡 NEMA-AGORA - Shadow Monitoring & Evidence Observatory")
st.caption("Phase 18 - operational evidence - controlled shadow only")

st.warning(
    "This observatory measures the behaviour of an admitted advisory model in "
    "controlled shadow mode. It does not establish environmental truth, "
    "regulatory status, enforcement priority, emergency response, production "
    "approval, or NEMA authorization."
)

mode = mode_from_secrets(st.secrets)
principal = principal_from_streamlit_user(st.user, st.secrets) if mode == "persistent" else None
db_path = database_path_from_secrets(st.secrets) if mode == "persistent" else None
service = NemaAgoraService(NemaAgoraRepository(db_path)) if principal and principal.is_authorised and db_path else None

if not service:
    st.info("Authenticate in persistent mode to inspect the shadow evidence observatory.")
    st.stop()
if not has_permission(principal.role, "intelligence:monitor"):
    st.error("Your role cannot access the shadow observatory.")
    st.stop()

admissions = service.list_model_admissions(principal, limit=100)
admitted = [x for x in admissions if x["decision"] == "ADMITTED_FOR_CONTROLLED_SHADOW"]

if not admitted:
    st.info("No model is currently admitted for controlled shadow monitoring.")
    st.stop()

options = ["ALL ADMITTED MODELS"] + [x["admission_id"] for x in admitted]
selected = st.selectbox("Monitoring scope", options)
admission_id = None if selected == options[0] else selected

snapshot = service.build_shadow_monitoring_snapshot(principal, admission_id=admission_id, limit=500)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Runs", snapshot["total_runs"])
c2.metric("Success rate", f"{(1-snapshot['error_rate'])*100:.1f}%")
c3.metric("P95 latency", f"{snapshot['p95_latency_ms']:.0f} ms")
c4.metric("Unique cases", snapshot["unique_cases"])

status = snapshot["status"]
if status == "HEALTHY_WITHIN_SHADOW_POLICY":
    st.success(status)
elif status == "WATCH":
    st.warning(status)
else:
    st.error(status)

if snapshot["alerts"]:
    st.subheader("Active control signals")
    for alert in snapshot["alerts"]:
        st.warning(alert)
else:
    st.info("No active monitoring alerts under the Phase 18 policy.")

st.subheader("Evidence snapshot")
st.json(snapshot)

runs = service.list_controlled_shadow_runs(principal, admission_id=admission_id, limit=500)
if runs:
    st.subheader("Recent shadow evidence")
    st.dataframe(pd.DataFrame([{
        "run_id": x["run_id"], "admission_id": x["admission_id"], "case_id": x["case_id"],
        "model_version": x["model_version"], "status": x["status"], "latency_ms": x["latency_ms"],
        "human_review_required": x["human_review_required"], "occurred_at": x["occurred_at"],
    } for x in runs]), use_container_width=True, hide_index=True)

st.caption(
    "Phase 18 is evidence monitoring for a controlled shadow lane. A WATCH or "
    "CONTROL_REQUIRED state does not itself make a regulatory or environmental "
    "determination; it signals that human review and governance attention are required."
)
