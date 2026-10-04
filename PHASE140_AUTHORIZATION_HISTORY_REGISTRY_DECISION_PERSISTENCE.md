# Phase 140 — Authorization History Registry Decision Persistence

## Purpose
Phase 140 persists Phase 139 authorization-history decision-continuity snapshots as append-only SQLite evidence.

## Registry guarantees
- First snapshot must be sequence `1` with no predecessor.
- Each subsequent snapshot must be exactly the next sequence.
- Each subsequent snapshot must reference the exact prior snapshot fingerprint.
- Snapshot fingerprints and sequences are unique.
- SQLite triggers block UPDATE and DELETE.
- Stored records retain the registry policy version.
- Reconciliation delegates to the Phase 139 continuity validator.

## Governance boundary
The registry is evidence storage, not authority. It cannot execute decisions, repair evidence, enforce environmental rules, dispatch emergencies, or create environmental/regulatory conclusions.

## Files
- `nema_agora/api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_registry_phase140.py`
- `tests/nema_agora/test_api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_registry_phase140.py`

## Next phase
Phase 141 should monitor registry integrity, including policy, count, sequence, predecessor, snapshot, and execution-boundary health.
