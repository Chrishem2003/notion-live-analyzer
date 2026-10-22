# NEMA-AGORA Release Candidate

## Candidate under review

- Integration PR: [#52 — integrate NEMA-AGORA safely onto current main](https://github.com/Chrishem2003/notion-live-analyzer/pull/52)
- Branch: `integration/nema-agora-current-main`
- Last code commit with completed automated CI: `7060ce845ca29cdfcd412d33883c3644474ec1db`
- Status: exact-head automated CI passed. Merge, hosted acceptance, persistent storage, and institutional release remain blocked pending the gates below.
- Scope: preserves the current-main single-file `app.py` shell and adds the existing NEMA-AGORA page/package/tests; the older divergent branch was not merged wholesale.

## Automated evidence on exact head

- [NEMA-AGORA Pilot Checks — passed](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39747986849)
  - NEMA unit tests passed.
  - NEMA package/page compilation passed.
  - Streamlit pilot and release-readiness smoke checks passed.
- [Repository CI/CD Pipeline — passed](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39747986838)
  - Full repository automated test suite passed, including the new import-inventory regression tests.
  - Lightweight API container build passed.
  - API runtime import check passed.

## Inventory audit

- Added `nema_agora/INTEGRATION_INVENTORY_AUDIT.md` with first-pass architecture, security, and cleanup findings.
- Added `scripts/audit_nema_agora_inventory.py` to report static package imports, importer counts, phase-suffixed module names, and unresolved internal imports.
- Added `tests/test_nema_agora_inventory_audit.py` to cover package-relative imports, import references, phase suffix reporting, unresolved internal imports, and missing-package failure.
- The tool is deliberately a triage tool, not a deletion oracle. Dynamic imports, API routes, deployment configuration, external consumers, and public entrypoints still need review.

## Current pilot boundaries

- Demo mode is session-only. Persistent mode requires explicit configuration, authenticated OIDC identity, and server-side role binding.
- The prototype is not an official NEMA service and does not submit reports to NEMA.
- No live ELMIS/SWIMS integration, autonomous enforcement, regulatory endorsement, or production approval is claimed.
- Use synthetic or appropriately consented test records only.

## Required before merge or hosted release

- [ ] Run the inventory tool against the full candidate and review its generated JSON output.
- [ ] Trace phase-numbered governance/reconciliation modules, dynamic imports, API entrypoints, and tests before proposing consolidation; do not mass-delete based on naming or missing static imports.
- [ ] Verify the NEMA page appears in the deployed Streamlit navigation and complete the demo-mode user journey.
- [ ] Verify deployed OIDC login/logout and server-side role bindings for each provisioned role.
- [ ] Test unprovisioned accounts and direct service/repository calls; confirm deny-by-default behavior.
- [ ] In an approved persistent environment, create a synthetic record, read it back, review it, and verify actor-attributed audit history.
- [ ] Exercise backup, integrity checks, restore, rollback-failure handling, retention, and persistence across restarts.
- [ ] Verify evaluation artifacts are present, candidate-bound, and reviewable.
- [ ] Complete accessibility, low-bandwidth, consent, data-minimization, retention, and institutional governance review.
- [ ] Validate environmental data sources and obtain required institutional approvals.

## Release decision

**Not approved for production.** Do not merge or describe this as production-ready until code review, exact-head CI, hosted acceptance, security/storage checks, and governance gates are complete.
