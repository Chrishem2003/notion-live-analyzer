"""NEMA-AGORA Phase 108 — persistent reconciliation history demo."""
from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from nema_agora.api_governance_drift_review_reconciliation import reconcile_drift_reviews
from nema_agora.api_governance_drift_reconciliation_history import build_reconciliation_snapshot
from nema_agora.api_governance_drift_reconciliation_history_registry import (
    GovernanceDriftReconciliationHistoryRegistry,
)

st.set_page_config(page_title="NEMA-AGORA Phase 108", layout="wide")
st.title("NEMA-AGORA — Persistent Reconciliation History")
st.caption("Phase 108 • append-only SQLite demonstration")
st.warning(
    "Synthetic demonstration only. This is not an official NEMA system or integration. "
    "History integrity is not an environmental or regulatory conclusion."
)

# Use an isolated temporary database for each page session/demo; no real operational
# evidence is written and no long-lived deployment path is assumed.
if "phase108_demo_dir" not in st.session_state:
    st.session_state["phase108_demo_dir"] = tempfile.mkdtemp(prefix="nema_agora_phase108_")
registry = GovernanceDriftReconciliationHistoryRegistry(
    Path(st.session_state["phase108_demo_dir"]) / "synthetic_history.db"
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
history = registry.reconcile_history()
a, b, c = st.columns(3)
a.metric("Persisted demo snapshots", registry.count())
b.metric("History state", history["state"])
c.metric("Integrity findings", len(history["findings"]))
st.subheader("Stored snapshot history")
st.dataframe(
    [
        {
            "sequence": item["sequence"],
            "captured_at": item["captured_at"],
            "state": item["state"],
            "snapshot_id": item["snapshot_id"],
            "snapshot_fingerprint": item["snapshot_fingerprint"],
        }
        for item in records
    ],
    use_container_width=True,
)
if history["findings"]:
    st.dataframe(history["findings"], use_container_width=True)
else:
    st.success("The synthetic persisted history is contiguous and fingerprint-linked.")
st.caption("The demo database is temporary and synthetic; it is not a production retention strategy.")
