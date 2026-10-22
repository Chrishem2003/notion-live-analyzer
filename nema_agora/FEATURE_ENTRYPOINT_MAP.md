# NEMA-AGORA Feature-to-Entrypoint Map (Batch 1)

**Candidate:** PR #52 — `integration/nema-agora-current-main`  
**Purpose:** classify the 82 modules with no detected runtime importer without deleting them or claiming they are live features.  
**Evidence basis:** static import inventory and the current `pages/18_NEMA_AGORA.py`, `api_server.py`, and `Dockerfile.api`. Names below are triage categories, not a substitute for reading each module's public contract.

## Current user-facing path

| User journey | Current entrypoint / service | Current assessment |
|---|---|---|
| Capture an observation | `pages/18_NEMA_AGORA.py` → `nema_agora.core`, `service`, `storage` | Implemented in the pilot code; hosted persistence still needs verification |
| Quality checks and human review | Streamlit page → quality, access, workflow and service modules | Partially surfaced in the page; verify each role and direct service call |
| Spatial change / evidence | Streamlit page → `spatial_temporal_change`, `spatial_temporal_quality`, `spatial_change_detection`, `spatial_workspace_bundle` | Advisory code path exists; no proof of live imagery acquisition or validated classification |
| Metrics, controlled export, governance and backups | Streamlit page → reporting / governance / backup and release-readiness functions | Repository contracts exist; hosted authorization, persistence, retention and restore remain release gates |
| External spatial API | `nema_agora.fastapi_authenticated_routes`, `fastapi_spatial_evidence_app`, related API modules | **Not served** by the current API container |
| Main platform API | `Dockerfile.api` → `uvicorn api_server:app` | Existing CHRISHEM API surface; does not import `nema_agora` |

## Recommended service boundary

**Do not mount the NEMA API directly into the existing platform API in this batch.** Its current shared-key service-to-service authentication is not interchangeable with the NEMA pilot's OIDC identity and server-side role-binding model. Blindly mounting routers risks creating inconsistent authorization, unclear route ownership, and a false impression that spatial API security has been verified.

For the current pilot:
1. Keep the existing Streamlit journey as the user-facing NEMA entrypoint.
2. Keep NEMA FastAPI modules unexposed until their authentication dependencies, role checks, input validation, audit behavior, rate limits, error handling and persistence semantics are traced and tested.
3. If API access is needed, prefer a separately deployed NEMA API with its own explicit configuration and authentication boundary, or a deliberately designed router integration only after a security review. Do not create a second service or deploy it without an approved target and acceptance tests.
4. Keep all Earth Engine/Sentinel-2 behavior labelled as adapter-dependent or experimental until a controlled live-source test and independent validation pass.

## Triage of the 82 no-runtime-importer modules

All 82 modules below are referenced by tests, but none has a detected runtime importer in the scanned package/page graph. Categories are provisional based on module names and must be confirmed by inspecting each module's exports, dependencies, side effects, tests and deployment contract.

### A. Governance, audit, lifecycle, reconciliation and review API contracts (28)

- `nema_agora.api_audit_casebook`
- `nema_agora.api_audit_lifecycle`
- `nema_agora.api_audit_lifecycle_reconciliation`
- `nema_agora.api_audit_reconciliation`
- `nema_agora.api_governance_drift`
- `nema_agora.api_governance_drift_human_review`
- `nema_agora.api_governance_drift_reconciliation_history_registry`
- `nema_agora.api_governance_drift_reconciliation_monitor`
- `nema_agora.api_governance_drift_recovery_authorization_registry`
- `nema_agora.api_governance_drift_recovery_authorization_retention_decision_reconciliation`
- `nema_agora.api_governance_drift_recovery_authorization_retention_registry`
- `nema_agora.api_governance_drift_recovery_authorization_retention_registry_decision_reconciliation`
- `nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_decision_continuity_registry_phase156`
- `nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_decision_continuity_registry_review_reconciliation_phase159`
- `nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_reconciliation_phase154`
- `nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_reconciliation_phase146`
- `nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_reconciliation_phase138`
- `nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_registry_phase140`
- `nema_agora.api_governance_drift_recovery_authorization_retention_registry_registry`
- `nema_agora.api_governance_drift_recovery_decision_reconciliation`
- `nema_agora.api_governance_drift_recovery_review_reconciliation`
- `nema_agora.api_governance_drift_registry`
- `nema_agora.api_governance_drift_review_queue`
- `nema_agora.api_governance_drift_review_reconciliation`
- `nema_agora.api_governance_health`
- `nema_agora.api_governance_observatory`
- `nema_agora.api_governance_review_queue`
- `nema_agora.api_human_review_reconciliation`

**Decision:** do not expose every module as an endpoint just because its name starts with `api_`. First identify which functions are stable contracts, which overlap, and which require a shared governance/service layer.

### B. Standalone API and spatial/data provider boundaries (12)

- `nema_agora.fastapi_authenticated_routes`
- `nema_agora.fastapi_spatial_evidence_app`
- `nema_agora.gee_boundary`
- `nema_agora.earth_engine`
- `nema_agora.sentinel2`
- `nema_agora.sentinel2_acquisition`
- `nema_agora.raster_processing`
- `nema_agora.spectral_indices`
- `nema_agora.spatial_evidence_api`
- `nema_agora.spatial_evidence_http`
- `nema_agora.spatial_evidence_integration`
- `nema_agora.spatial_map_layers`

**Decision:** treat as provider/standalone boundaries until their callers, credentials, deployment configuration and real-source tests are confirmed. Earth Engine-related code is not proof of an authenticated live Google Earth Engine connection.

### C. Governance and evidence domain libraries (17)

- `nema_agora.attestation_lifecycle`
- `nema_agora.audit_recovery`
- `nema_agora.case_pipeline`
- `nema_agora.closure_evidence`
- `nema_agora.decision_receipt`
- `nema_agora.decision_receipt_reconciliation`
- `nema_agora.evidence`
- `nema_agora.evidence_export`
- `nema_agora.evidence_graph`
- `nema_agora.evidence_integrity`
- `nema_agora.evidence_observatory`
- `nema_agora.evidence_pack`
- `nema_agora.evidence_synthesis`
- `nema_agora.governance_decision_execution`
- `nema_agora.governance_evidence_casebook`
- `nema_agora.governance_evidence_reconciliation`
- `nema_agora.governance_review_decision`

**Decision:** retain human authority over review and decisions. Receipts, reconciliation and audit should remain evidence records—not autonomous enforcement or a way to bypass role checks.

### D. Review workspaces, provenance, operations, readiness, publication and spatial review (25)

- `nema_agora.governance_review_queue`
- `nema_agora.governance_review_workspace`
- `nema_agora.governance_traceability`
- `nema_agora.lifecycle_provenance`
- `nema_agora.operations_metrics`
- `nema_agora.outcomes`
- `nema_agora.pilot_acceptance`
- `nema_agora.pilot_readiness`
- `nema_agora.platform_capability_registry`
- `nema_agora.publication_control`
- `nema_agora.deployment`
- `nema_agora.recovery`
- `nema_agora.reporting`
- `nema_agora.research_dossier`
- `nema_agora.reviewer_workspace`
- `nema_agora.spatial_change_map`
- `nema_agora.spatial_change_review_audit`
- `nema_agora.spatial_change_review_queue`
- `nema_agora.spatial_change_scoring`
- `nema_agora.spatial_command_center`
- `nema_agora.spatial_evidence_longitudinal`
- `nema_agora.spatial_intelligence`
- `nema_agora.spatial_review_audit_registry`
- `nema_agora.spatial_review_casebook`
- `nema_agora.spatial_review_reconciliation`

**Decision:** these are candidates for UI/service integration only after checking their contracts against the current Streamlit page and avoiding duplicate workflow implementations. Metrics must distinguish synthetic/demo records from real observations and must not imply validated environmental outcomes without evidence.

## Prioritized next steps

1. **Contract map:** for each module, record public functions/classes, imported dependencies, side effects, matching tests, authorization requirements, persistence behavior and intended entrypoint.
2. **Group overlap:** identify repeated phase-numbered governance implementations by public contract and behavior; add equivalence/regression tests before any consolidation.
3. **Reachability tests:** for each feature selected for the pilot, test the whole path from page/API to permission check, service, storage and actor-attributed audit.
4. **Spatial validation:** distinguish mock/injected provider tests from authenticated live imagery acquisition, CRS/geometry checks, index computation, uncertainty and field validation.
5. **Release gates:** verify deployed navigation, OIDC, role-deny cases, durable write/read/audit, backup/restore/retention and data governance before merge or production.

## Non-claims

This map does not prove that any no-runtime-importer module is dead code, does not certify API security, and does not claim live imagery, live environmental monitoring, official NEMA integration or production readiness.
