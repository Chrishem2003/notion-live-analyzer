"""NEMA-AGORA Phase 15 — Controlled Model Comparison Laboratory."""
from __future__ import annotations
import json
import pandas as pd
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.comparison import FrozenCase, compare_models, freeze_dataset, serialise_comparison
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.service import NemaAgoraService
from nema_agora.shadow import DeterministicShadowAdapter
from nema_agora.storage import NemaAgoraRepository

st.set_page_config(page_title="NEMA-AGORA Model Comparison", page_icon="🔬", layout="wide")
st.title("🔬 NEMA-AGORA — Controlled Model Comparison")
st.caption("Phase 15 • frozen benchmark • side-by-side evidence • regression controls")

st.warning("Independent student-led prototype. This laboratory compares advisory model outputs; it is not an official NEMA evaluation or reporting system.")

mode=mode_from_secrets(st.secrets)
principal=principal_from_streamlit_user(st.user,st.secrets) if mode=="persistent" else None
db_path=database_path_from_secrets(st.secrets) if mode=="persistent" else None
service=NemaAgoraService(NemaAgoraRepository(db_path)) if principal and principal.is_authorised and db_path else None
if not principal or not principal.is_authorised or not service:
    st.info("Authenticate in persistent mode to use controlled model comparison.")
    st.stop()
if not has_permission(principal.role,"intelligence:comparison"):
    st.error("Your role is not permitted to run controlled model comparison.")
    st.stop()

with st.expander("Phase 15 control contract",expanded=True):
    st.markdown(
        "- Freeze the human-labelled benchmark before comparison.\n"
        "- Record a SHA-256 manifest so the case set is reproducible.\n"
        "- Give every adapter the same case record.\n"
        "- Reject unsafe, malformed or cross-case outputs.\n"
        "- Record failures as failures; never turn errors into guesses.\n"
        "- Keep results separate from live observation workflow.\n"
        "- Human review remains mandatory."
    )

version=st.text_input("Dataset version",value="phase15-human-v1",max_chars=80)
dataset_text=st.text_area(
    "Human-labelled benchmark JSON",
    value=st.session_state.get("nema_agora_cmp_dataset","[]"),
    height=300,
    help="Use synthetic or explicitly permissioned records. Do not paste personal or confidential information.",
)

if st.button("Freeze benchmark",use_container_width=True):
    try:
        raw=json.loads(dataset_text)
        if not isinstance(raw,list) or not raw: raise ValueError("Dataset must be a non-empty JSON list.")
        cases=[FrozenCase(str(x["case_id"]),dict(x["record"]),str(x["expected_category"]),
                          bool(x["expected_duplicate"]),x.get("expected_summary_faithful"),
                          str(x.get("slice_name","all"))) for x in raw]
        manifest=freeze_dataset(cases,version)
        st.session_state["nema_agora_cmp_cases"]=cases
        st.session_state["nema_agora_cmp_manifest"]=manifest
        st.session_state["nema_agora_cmp_dataset"]=dataset_text
        st.success(f"Frozen {manifest.cases} cases. Manifest SHA-256: {manifest.manifest_hash}")
    except (ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
        st.error(f"Benchmark rejected: {exc}")

cases=st.session_state.get("nema_agora_cmp_cases",[])
manifest=st.session_state.get("nema_agora_cmp_manifest")
if not cases or manifest is None:
    st.info("Freeze a labelled benchmark before running a comparison.")
    st.stop()

a,b,c=st.columns(3)
a.metric("Frozen cases",manifest.cases)
b.metric("Dataset version",manifest.dataset_version)
c.metric("Manifest",manifest.manifest_hash[:12]+"…")

st.info("Enabled adapter in this build: local deterministic baseline. No external AI provider is silently connected. A future provider must implement the provider-neutral contract and be explicitly approved before comparison.")

if st.button("Run controlled comparison",type="primary",use_container_width=True):
    with st.spinner("Running every adapter on the identical frozen benchmark…"):
        result=compare_models(cases,{"deterministic-baseline":DeterministicShadowAdapter()},
                             dataset=manifest,baseline_adapter="deterministic-baseline")
    st.session_state["nema_agora_cmp_result"]=result
    try:
        service.record_comparison_run(result,principal)
        st.success(f"Comparison completed and persisted: {result.run_id}")
    except (ValueError,PermissionError,KeyError) as exc:
        st.error(f"Comparison completed but persistence failed: {exc}")

result=st.session_state.get("nema_agora_cmp_result")
if result:
    st.divider()
    st.subheader("Scoreboard")
    st.dataframe(pd.DataFrame([m.to_dict() for m in result.adapters]),use_container_width=True,hide_index=True)
    st.write(f"Run: **{result.run_id}** • Readiness: **{result.readiness}**")
    st.caption("Readiness is an engineering review gate only. It is not model approval or environmental validation.")

    tabs=st.tabs(["Disagreement","Regression","Slices","Per-case audit"])
    with tabs[0]:
        if result.model_disagreement: st.dataframe(pd.DataFrame(result.model_disagreement),use_container_width=True,hide_index=True)
        else: st.success("No model-to-model disagreement was observed in this run.")
    with tabs[1]:
        if result.regression: st.dataframe(pd.DataFrame(result.regression),use_container_width=True,hide_index=True)
        else: st.info("No second adapter is present, so baseline regression is not applicable.")
    with tabs[2]:
        st.dataframe(pd.DataFrame(result.slice_results),use_container_width=True,hide_index=True)
    with tabs[3]:
        st.dataframe(pd.DataFrame(result.case_results),use_container_width=True,hide_index=True)

    st.warning(result.safety_notice)
    st.download_button("Download reproducible comparison JSON",data=serialise_comparison(result),
                       file_name=f"{result.run_id}.json",mime="application/json",use_container_width=True)

st.divider()
st.subheader("Persisted comparison history")
try:
    history=service.list_comparison_runs(principal,limit=25)
    if history:
        st.dataframe(pd.DataFrame([{
            "run_id":x["run_id"],"dataset_version":x["dataset_version"],
            "manifest_hash":x["manifest_hash"],"created_at":x["created_at"],
            "actor_id":x["actor_id"],"readiness":x["result"].get("readiness")
        } for x in history]),use_container_width=True,hide_index=True)
    else: st.info("No comparison runs yet.")
except (ValueError,PermissionError,KeyError) as exc:
    st.error(str(exc))
