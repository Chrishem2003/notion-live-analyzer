# Phase 137 — Authorization History Registry Lifecycle Decision

## Purpose
Phase 137 creates the explicit human authorization boundary for lifecycle states produced by Phase 136. It records what a coordinator or administrator authorizes without executing that decision.

## Decisions
- `AUTHORIZE_AUTHORIZATION_HISTORY_REVIEW`: allowed only for `DEFERRED`.
- `AUTHORIZE_PRESERVATION`: allowed for `ACKNOWLEDGED` or `DEFERRED`.
- `AUTHORIZE_ESCALATION`: allowed only for `ESCALATED`.

## Governance boundary
Every decision:
- validates the Phase 136 lifecycle and binds its lifecycle, monitor, and review fingerprints;
- requires an identified human actor with `coordinator` or `admin` role;
- requires a timestamp and non-empty rationale;
- sets `human_authorized=True`;
- keeps `execution_gate_closed=True`;
- keeps `execution_permitted=False` and `execution_performed=False`;
- keeps `automatic_repair_performed=False`;
- contains no environmental, regulatory, enforcement, or emergency conclusion.

The module is a decision-record boundary, not an execution engine. Later phases may reconcile, retain, and audit these decisions, but must not silently turn authorization into automatic action.

## Files
- `nema_agora/api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_phase137.py`
- `tests/nema_agora/test_api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_phase137.py`

## Expected next phase
Phase 138 should reconcile Phase 136 lifecycle records against Phase 137 decisions, detecting orphan, duplicate, binding, state, and execution-gate violations.
