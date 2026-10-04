"""NEMA-AGORA Phase 16 — Model Governance & Admission Gate."""
from __future__ import annotations

import json
import pandas as pd
import streamlit as st

from nema_agora.access import has_permission
from nema_agora.admission import ModelCandidate
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.service import NemaAgoraService
from nema_agora.storage import NemaAgoraRepository

st.set_page_config(page_title="NEMA-AGORA Model Governance", page_icon="🛡️", layout="wide")
st.title("🛡️ NEMA-AGORA — Model Governance")
st.caption("Phase 16 • benchmark governance • evidence binding • controlled-shadow admission")

st.warning(
    "Independent student-led prototype. Admission means eligibility for controlled shadow evaluation only; "
    "it is not NEMA endorsement, regulatory approval, environmental truth, enforcement authority, emergency response, or production approval."
)

mode=mode_from_secrets(st.secrets)
principal=principal_from_streamlit_user(st.user,st.secrets) if mode=="persistent" else None
db_path=database_path_from_secrets(st.secrets) if mode=="persistent" else None
service=NemaAgoraService(NemaAgoraRepository(db_path)) if principal and principal.is_authorised and db_path else None

if not service:
    st.info("Authenticate in persistent mode to use model governance.")
    st.stop()
if not has_permission(principal.role,"intelligence:admit_model"):
    st.error("Only coordinator/admin roles may make model-admission decisions.")
    st.stop()

st.subheader("1. Select comparison evidence")
history=service.list_comparison_runs(principal,limit=100)
if not history:
    st.info("No persisted comparison runs exist yet. Complete Phase 15 comparison first.")
    st.stop()

labels=[f'{x["run_id"]} • {x["dataset_version"]} • {x["created_at"]}' for x in history]
idx=st.selectbox("Comparison run",range(len(history)),format_func=lambda i: labels[i])
selected=history[idx]["result"]
dataset=selected.get("dataset",{})

st.write(f"**Dataset:** {dataset.get('dataset_version','')}  •  **Manifest SHA-256:** {dataset.get('manifest_hash','')}  •  **Cases:** {dataset.get('cases',0)}")
st.caption("The admission gate binds the selected comparison run to its exact dataset version, manifest hash, provider, model version and adapter.")

st.subheader("2. Candidate metadata")
candidate_provider=st.text_input("Provider",value=(selected.get("adapters") or [{}])[0].get("provider",""))
candidate_version=st.text_input("Model version",value=(selected.get("adapters") or [{}])[0].get("model_version",""))
candidate_adapter=st.text_input("Adapter name",value=(selected.get("adapters") or [{}])[0].get("adapter",""))
intended_use=st.text_input("Intended use",value="Advisory evidence classification and reviewer decision support")
data_handling=st.text_input("Data handling",value="Synthetic or explicitly permissioned pilot records only")
retention=st.text_input("Retention policy",value="Controlled project retention under approved governance")
location=st.text_input("Processing location",value="Local / explicitly documented deployment")
failure=st.text_input("Failure behaviour",value="Fail closed; preserve human review")

candidate=ModelCandidate(
    provider=candidate_provider,model_version=candidate_version,adapter_name=candidate_adapter,
    intended_use=intended_use,data_handling=data_handling,retention_policy=retention,
    processing_location=location,failure_behaviour=failure,
)

st.subheader("3. Annotation governance evidence")
annotation_version=dataset.get("dataset_version","")
try:
    ann=service.annotation_readiness(principal,annotation_version)
except Exception as exc:
    st.error(f"Could not read annotation readiness: {exc}")
    st.stop()

c1,c2,c3,c4=st.columns(4)
c1.metric("Double-annotated",ann.get("double_annotated_cases",0))
c2.metric("Annotators",len(ann.get("annotators",[])))
c3.metric("Min category κ",f'{ann.get("minimum_category_kappa",0):.2f}')
c4.metric("Unresolved",len(ann.get("unresolved_disagreements",[])))
st.dataframe(pd.DataFrame([{"gate":k,"passed":v} for k,v in ann.get("gates",{}).items()]),use_container_width=True,hide_index=True)

st.subheader("4. Admission decision")
approver=st.text_input("Approver identity",value=principal.subject_key)
rationale=st.text_area("Decision rationale",height=120,placeholder="Document the evidence reviewed and why controlled shadow evaluation is justified.")

if st.button("Evaluate & record admission",type="primary",use_container_width=True):
    try:
        decision=service.evaluate_model_admission(
            candidate=candidate,dataset=dataset,annotation_readiness=ann,
            comparison=selected,comparison_run_id=history[idx]["run_id"],
            principal=principal,approver_id=approver,rationale=rationale,
        )
        if decision["decision"]=="ADMITTED_FOR_CONTROLLED_SHADOW":
            st.success("ADMITTED_FOR_CONTROLLED_SHADOW")
        else:
            st.error("NOT_ADMITTED")
        st.dataframe(pd.DataFrame([{"gate":k,"passed":v} for k,v in decision["gates"].items()]),use_container_width=True,hide_index=True)
        st.json(decision)
        st.download_button("Download admission record",json.dumps(decision,indent=2),file_name=f'{decision["admission_id"]}.json',mime="application/json")
    except (ValueError,PermissionError,KeyError) as exc:
        st.error(f"Admission evaluation rejected: {exc}")

st.divider()
st.subheader("Admission history")
rows=service.list_model_admissions(principal,limit=50)
if rows:
    st.dataframe(pd.DataFrame([{
        "admission_id":x["admission_id"],"decision":x["decision"],
        "provider":x["provider"],"model_version":x["model_version"],
        "dataset_version":x["dataset_version"],"comparison_run_id":x["comparison_run_id"],
        "approver_id":x["approver_id"],"created_at":x["created_at"],
    } for x in rows]),use_container_width=True,hide_index=True)
else:
    st.info("No admission decisions have been recorded.")

st.info(
    "Safety boundary: even an admitted candidate remains advisory. It cannot change observation status, "
    "declare environmental truth or illegality, trigger enforcement/emergency response, submit official reports, "
    "or claim NEMA authorization."
)
