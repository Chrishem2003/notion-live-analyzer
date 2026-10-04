"""NEMA-AGORA Phase 109 — read-only history integrity monitoring demo."""
from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from nema_agora.api_governance_drift_review_reconciliation import reconcile_drift_reviews
from nema_agora.api_governance_drift_reconciliation_history import build_reconciliation_snapshot
from nema_agora.api_governance_drift_reconciliation_history_registry import (
    GovernanceDriftReconciliationHistoryRegistry,
)
from nema_agora.api_governance_drift_reconciliation_monitor import monitor_registry

st.set_page_config(page_title="NEMA-AGORA Phase 109", layout="wide")
st.title("NEMA-AGORA — Reconciliation History Integrity Monitor")
st.caption("Phase 109 • read-only integrity monitoring • recovery evidence")
st.warning(
    "Synthetic demonstration only. This is not an official NEMA system or integration. "
    "Integrity findings are not environmental or regulatory conclusions; no automatic repair is performed."
)

if "phase109_demo_dir" not in st.session_state:
    st.session_state["phase109_demo_dir"] = tempfile.mkdtemp(prefix="nema_agora_phase109_")
registry = GovernanceDriftReconciliationHistoryRegistry(
    Path(st.session_state["phase109_demo_dir"]) / "synthetic_history.db"
)
if registry.count() == 0:
    reconciliation = reconcile_drift_reviews([], [], [], [])
    first = build_reconciliation_snapshot(
        reconciliation, captured_at="2026-10-04T12:00:00Z", sequence=1
    )
    registry.append(first)
    second = build_reconciliation_snapshot(
        reconciliation, captured_at="2026-10-04T13:00:00Z", sequence=2,
        previous_snapshot_fingerprint=first["snapshot_fingerprint"],
    )
    registry.append(second)

records = registry.list()
report = monitor_registry(registry, observed_at="2026-10-04T14:00:00Z")
a, b, c, d = st.columns(4)
a.metric("Registry rows", report["registry_record_count"])
b.metric("Monitor state", report["state"])
c.metric("Valid snapshots", report["valid_snapshot_count"])
d.metric("Integrity findings", len(report["findings"]))
st.subheader("Recovery review evidence")
st.write("Recommendation:", report["recovery_recommendation"])
st.write("Automatic repair performed:", report["automatic_repair_performed"])
st.write("Monitor fingerprint:")
st.code(report["monitor_fingerprint"])
if report["findings"]:
    st.dataframe(report["findings"], use_container_width=True)
else:
    st.success("The synthetic history passed the read-only integrity monitor.")
st.subheader("Persisted synthetic history")
st.dataframe(
    [
        {
            "sequence": item["sequence"],
            "captured_at": item["captured_at"],
            "snapshot_id": item["snapshot_id"],
            "snapshot_fingerprint": item["snapshot_fingerprint"],
            "registry_policy_version": item["registry_policy_version"],
        }
        for item in records
    ],
    use_container_width=True,
)
st.caption("This isolated temporary database is demo-only and is not a backup or production recovery mechanism.")
