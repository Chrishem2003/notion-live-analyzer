"""NEMA-AGORA Phase 17 — Controlled Shadow Operations."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.service import NemaAgoraService
from nema_agora.storage import NemaAgoraRepository

st.set_page_config(page_title="NEMA-AGORA Controlled Shadow", page_icon="🧪", layout="wide")
st.title("🧪 NEMA-AGORA — Controlled Shadow Operations")
st.caption("Phase 17 • admitted-model execution ledger • human-review-only monitoring")

st.warning(
    "Controlled shadow execution is advisory only. It cannot alter observations, "
    "declare environmental truth, change official status, trigger enforcement or "
    "emergency response, submit official reports, or imply NEMA authorization."
)

mode = mode_from_secrets(st.secrets)
principal = principal_from_streamlit_user(st.user, st.secrets) if mode == "persistent" else None
db_path = database_path_from_secrets(st.secrets) if mode == "persistent" else None
service = NemaAgoraService(NemaAgoraRepository(db_path)) if principal and principal.is_authorised and db_path else None

if not service:
    st.info("Authenticate in persistent mode to inspect controlled-shadow operations.")
    st.stop()
if not has_permission(principal.role, "intelligence:controlled_shadow"):
    st.error("Your role cannot access controlled-shadow operations.")
    st.stop()

admissions = service.list_model_admissions(principal, limit=100)
admitted = [x for x in admissions if x["decision"] == "ADMITTED_FOR_CONTROLLED_SHADOW"]

c1, c2, c3 = st.columns(3)
c1.metric("Admitted models", len(admitted))
runs = service.list_controlled_shadow_runs(principal, limit=200)
c2.metric("Shadow runs", len(runs))
c3.metric("Shadow errors", sum(x["status"] == "SHADOW_ERROR" for x in runs))

st.subheader("Admitted candidates")
if admitted:
    st.dataframe(pd.DataFrame([{
        "admission_id": x["admission_id"],
        "provider": x["provider"],
        "model_version": x["model_version"],
        "adapter_name": x["adapter_name"],
        "dataset_version": x["dataset_version"],
        "approver_id": x["approver_id"],
        "created_at": x["created_at"],
    } for x in admitted]), use_container_width=True, hide_index=True)
else:
    st.info("No model is currently admitted for controlled shadow evaluation.")

st.subheader("Execution ledger")
if runs:
    st.dataframe(pd.DataFrame([{
        "run_id": x["run_id"],
        "admission_id": x["admission_id"],
        "case_id": x["case_id"],
        "provider": x["provider"],
        "model_version": x["model_version"],
        "adapter_name": x["adapter_name"],
        "status": x["status"],
        "latency_ms": x["latency_ms"],
        "human_review_required": x["human_review_required"],
        "occurred_at": x["occurred_at"],
    } for x in runs]), use_container_width=True, hide_index=True)
else:
    st.info("No controlled-shadow executions have been recorded.")

st.info(
    "Execution is intentionally not exposed as an arbitrary UI action. A future "
    "deployment adapter registry must bind a concrete adapter implementation to "
    "an admitted provider/model/version before execution is enabled."
)
