"""NEMA-AGORA Phase 27 — Award & Demonstration Evidence."""
import json
import streamlit as st

from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import mode_from_secrets
from nema_agora.evidence_pack import build_demo_evidence_pack
from nema_agora.reproducibility import current_git_revision

st.set_page_config(page_title="NEMA-AGORA Demo Evidence", page_icon="🏆", layout="wide")
st.title("🏆 NEMA-AGORA — Award & Demonstration Evidence")
st.warning(
    "Synthetic demonstration evidence for an independent student-led prototype. "
    "It is not NEMA authorization, environmental truth, regulatory evidence, or production approval."
)

if mode_from_secrets(st.secrets) != "persistent":
    st.info("Persistent authenticated mode is required.")
    st.stop()

principal = principal_from_streamlit_user(st.user, st.secrets)
if not principal or not principal.is_authorised or not has_permission(
    principal.role, "intelligence:reproducibility"
):
    st.error("Authenticated provisioned reproducibility access is required.")
    st.stop()

revision = current_git_revision()
if not revision:
    st.error("Git revision is unavailable; evidence generation is fail-closed.")
    st.stop()

pack = build_demo_evidence_pack(git_revision=revision)
st.metric("Evidence chain", "COMPLETE" if pack["records"] else "CONTROL REQUIRED")
st.write(" → ".join(pack["stage_order"]))
st.subheader("Demonstration safety boundary")
st.json(pack["safety"])
st.subheader("Dataset fingerprint")
st.code(pack["dataset"]["fingerprint"])
st.subheader("Reproducibility")
st.json(pack["reproducibility"])
st.subheader("End-to-end case evidence")
for item in pack["records"]:
    with st.expander(item["case_id"]):
        st.json(item)

st.download_button(
    "Download award/demo evidence pack",
    json.dumps(pack, ensure_ascii=False, indent=2),
    file_name="nema_agora_award_demo_evidence.json",
    mime="application/json",
)
st.caption(
    "Software behaviour on synthetic records only. It does not establish environmental "
    "impact, environmental truth, NEMA endorsement, regulatory status, enforcement authority, "
    "emergency response, or production suitability."
)
