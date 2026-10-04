"""NEMA-AGORA Phase 25 — Deployment & Reproducibility."""
import json
import sys

import streamlit as st

from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.provenance import ProvenanceStore
from nema_agora.reproducibility import build_manifest, manifest_fingerprint, validate_manifest

st.set_page_config(page_title="NEMA-AGORA Reproducibility", page_icon="🧬", layout="wide")
st.title("🧬 NEMA-AGORA — Deployment & Reproducibility")
st.caption("A non-secret deployment identity and reproducibility manifest.")

st.warning("This manifest is engineering/research evidence. It is not environmental truth, NEMA authorization, regulatory status, production approval, or environmental impact.")

if mode_from_secrets(st.secrets) != "persistent":
    st.info("Persistent authenticated mode is required.")
    st.stop()

principal = principal_from_streamlit_user(st.user, st.secrets)
if not principal or not principal.is_authorised:
    st.error("Authenticated provisioned access is required.")
    st.stop()
if not has_permission(principal.role, "intelligence:reproducibility"):
    st.error("Your role cannot access reproducibility evidence.")
    st.stop()

db = database_path_from_secrets(st.secrets)
records = ProvenanceStore(db).list(limit=1000)
dataset_bindings = {}
policy_versions = {}
for row in records:
    event = str(row.get("event_type", ""))
    dataset = str(row.get("dataset_version", ""))
    data_hash = str(row.get("dataset_hash", ""))
    if dataset and data_hash:
        dataset_bindings.setdefault(dataset, data_hash)
    policy = str(row.get("policy_version", ""))
    if event and policy:
        policy_versions[event] = policy

configuration = {"mode": "persistent", "official_integration_enabled": False}
git_revision = st.text_input("Git revision", value="UNKNOWN")
manifest = build_manifest(
    git_revision=git_revision,
    policy_versions=policy_versions,
    dataset_bindings=dataset_bindings,
    configuration=configuration,
    dependencies={"python": sys.version.split()[0]},
)
validation = validate_manifest(manifest)

c1, c2, c3 = st.columns(3)
c1.metric("Manifest status", "VALID" if validation["valid"] else "INVALID")
c2.metric("Provenance records", len(records))
c3.metric("Secrets included", "NO" if not manifest.secret_values_included else "YES")

st.subheader("Deployment manifest")
st.json(manifest.to_dict())
st.subheader("Manifest fingerprint")
st.code(manifest_fingerprint(manifest))
st.download_button(
    "Download manifest JSON",
    data=json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False),
    file_name=f"{manifest.manifest_id}.json",
    mime="application/json",
)
st.caption(manifest.decision_notice)
