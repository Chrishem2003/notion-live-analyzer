"""NEMA-AGORA Phase 27 — Deployment Health & Demonstration Control."""
import streamlit as st

from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.demo import build_demo_dataset, serialise_demo_dataset, validate_demo_dataset
from nema_agora.deployment import health_summary
from nema_agora.provenance import ProvenanceStore
from nema_agora.recovery import run_recovery_smoke
from nema_agora.reproducibility import build_runtime_manifest, manifest_fingerprint

st.set_page_config(page_title="NEMA-AGORA Deployment Health", page_icon="🛡️", layout="wide")
st.title("🛡️ NEMA-AGORA — Deployment Health & Demo Control")
st.warning(
    "Engineering/deployment evidence only. This page does not establish environmental truth, "
    "NEMA authorization, regulatory status, production approval, enforcement, or emergency response."
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

summary = health_summary()
st.metric("Deployment health", "HEALTHY" if summary["healthy"] else "CONTROL REQUIRED")
for check in summary["checks"]:
    st.write(("✅ " if check["ok"] else "❌ ") + check["name"] + " — " + check["detail"])

st.subheader("Non-destructive recovery smoke test")
recovery = run_recovery_smoke()
st.metric("Isolated recovery", "HEALTHY" if recovery["healthy"] else "CONTROL REQUIRED")
for name, ok in recovery["checks"].items():
    st.write(("✅ " if ok else "❌ ") + name)
st.caption(recovery["decision_notice"])

demo = build_demo_dataset()
st.subheader("Synthetic demonstration dataset")
st.json(validate_demo_dataset(demo))
st.download_button(
    "Download synthetic demo dataset",
    serialise_demo_dataset(demo),
    file_name=f"nema_agora_{demo.dataset_id}_{demo.version}.json",
    mime="application/json",
)

database_path = database_path_from_secrets(st.secrets)
if database_path is None:
    st.info("No explicit persistent database path is configured.")
    records = []
else:
    records = ProvenanceStore(str(database_path)).list(limit=1000)

policies = {
    str(r["event_type"]): str(r["policy_version"])
    for r in records
    if r.get("event_type") and r.get("policy_version")
}
datasets = {
    str(r["dataset_version"]): str(r["dataset_hash"])
    for r in records
    if r.get("dataset_version") and r.get("dataset_hash")
}

try:
    manifest = build_runtime_manifest(
        policy_versions=policies,
        dataset_bindings=datasets,
        configuration={"mode": "persistent", "official_integration_enabled": False},
        dependencies={"python": "runtime"},
    )
except RuntimeError as exc:
    st.error(str(exc))
    st.caption("Fail-closed: no fabricated Git revision is accepted.")
else:
    st.subheader("Runtime deployment manifest")
    st.json(manifest.to_dict())
    st.code(manifest_fingerprint(manifest))
    st.download_button(
        "Download runtime manifest",
        manifest_fingerprint(manifest),
        file_name=f"{manifest.manifest_id}.sha256",
        mime="text/plain",
    )

st.caption(summary["decision_notice"])
