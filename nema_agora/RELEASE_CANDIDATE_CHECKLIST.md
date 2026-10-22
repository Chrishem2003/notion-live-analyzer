# NEMA-AGORA Release Candidate

## Candidate under review

- Integration PR: [#52 — integrate NEMA-AGORA safely onto current main](https://github.com/Chrishem2003/notion-live-analyzer/pull/52)
- Branch: `integration/nema-agora-current-main`
- Last fully tested code commit: `73598d283c67360c529fba6018228538e23f5271`
- Exact-head focused NEMA checks and repository CI passed on this commit.
- Status: automated checks pass; merge, hosted acceptance, NEMA API integration, persistent storage, and institutional release remain blocked pending the gates below.
- Scope: preserves the current-main single-file `app.py` shell and adds the NEMA-AGORA page/package/tests; the older divergent branch was not merged wholesale.

## Exact-head automated evidence

- [NEMA-AGORA Pilot Checks — passed](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39754604344)
  - NEMA unit tests passed, including Earth Engine boundary and Phase 159 contract tests.
  - NEMA package/page compilation passed.
  - Static import inventory executed.
  - Streamlit pilot smoke check passed.
- [Repository CI/CD Pipeline — passed](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39754604369)
  - Full repository automated test suite passed.
  - Lightweight API container build passed.
  - API runtime import check passed.

## Static inventory result

- 180 package modules; 425 Python files scanned.
- 26 phase-suffixed package modules.
- 0 unresolved internal `nema_agora.*` imports in the scanned package/pages/tests.
- 82 modules have no detected runtime importer; all 82 are referenced by tests. These are not automatic deletion candidates.
- The existing `Dockerfile.api` launches `api_server:app`; that app does not import `nema_agora`. The separate NEMA FastAPI spatial modules are therefore not served by the current API entrypoint.
- See [`nema_agora/INTEGRATION_INVENTORY_AUDIT.md`](INTEGRATION_INVENTORY_AUDIT.md) and [`nema_agora/FEATURE_ENTRYPOINT_MAP.md`](FEATURE_ENTRYPOINT_MAP.md) for module classification and the API boundary decision.

## Current pilot boundaries

- Demo mode is session-only. Persistent mode requires explicit configuration, authenticated OIDC identity, and server-side role binding.
- The prototype is not an official NEMA service and does not submit reports to NEMA.
- Spatial evidence inputs now capture baseline and comparison AOI/grid IDs independently. Alignment defaults to unverified until the operator explicitly attests it; the attestation is not independent geospatial verification. Date-only inputs use a disclosed 10:00 UTC placeholder, not provider acquisition metadata.
- Spatial evidence inputs now capture baseline and comparison AOI/grid IDs independently. Alignment defaults to unverified until the operator explicitly attests it; this is not independent geospatial verification. Date-only inputs use a disclosed 10:00 UTC placeholder, not provider acquisition metadata.
- No live ELMIS/SWIMS integration, autonomous enforcement, regulatory endorsement, or production approval is claimed.
- Use synthetic or appropriately consented test records only.

## Required before merge or hosted release

- [x] Create a provisional feature-to-entrypoint map for all 82 no-runtime-importer modules; module-by-module contract tracing remains in progress.
- [x] Document the pilot API boundary: NEMA spatial endpoints remain unexposed; do not mount them into the existing shared-key platform API without a separately reviewed authorization design.
- [ ] Complete module-by-module contract tracing, including dynamic/external entrypoints and deployed consumers.
- [ ] Implement and independently test cryptographic credential verification and server-side role resolution before enabling any NEMA spatial API query route; current route-level containment returns HTTP 503 by default.
- [ ] Review the phase-numbered governance/reconciliation family and add regression tests before consolidation; do not mass-delete by filename.
- [ ] Verify the NEMA page appears in deployed Streamlit navigation and complete the demo-mode journey.
- [ ] Verify deployed OIDC login/logout and server-side role bindings for each provisioned role.
- [ ] Test unprovisioned accounts and direct service/repository calls; confirm deny-by-default behavior.
- [ ] In an approved persistent environment, create a synthetic record, read it back, review it, and verify actor-attributed audit history.
- [ ] Exercise backup, integrity checks, restore, rollback-failure handling, retention, and persistence across restarts.
- [ ] Verify evaluation artifacts are present, candidate-bound, and reviewable.
- [ ] Complete accessibility, low-bandwidth, consent, data-minimization, retention, and institutional governance review.
- [ ] Validate environmental data sources and obtain required institutional approvals.

## Release decision

**Not approved for production.** Do not merge or describe this as production-ready until code review, exact-head CI, hosted acceptance, API entrypoint decisions, security/storage checks, and governance gates are complete.
