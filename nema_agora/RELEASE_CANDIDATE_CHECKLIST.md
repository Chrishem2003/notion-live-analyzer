# NEMA-AGORA Release Candidate

## Candidate

- Integration PR: [#23 — clean main-based integration](https://github.com/Chrishem2003/notion-live-analyzer/pull/23)
- Branch: `feature/nema-agora-clean-integration`
- Last previously verified candidate: `707c94c1dff787279257845c4e57df18b64ebf1f`
- Latest Phase 187 implementation commit: `56231f374fc4ffc532ea1940e62fbfe156100d62`
- Status: Phase 186 CI passed. Phase 187 deployment-preflight code and regression tests are committed; confirmation of CI for the latest commit is still pending. Release remains blocked on deployment and governance evidence.

## Verified automated checks

The following workflows passed on the current tracker commit:

- [NEMA-AGORA Pilot Checks](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39133042467)
- [Repository CI/CD Pipeline](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39133042477)

The focused workflow runs the NEMA test suite, compiles the NEMA package and curated Streamlit entrypoints, and smoke-tests the consolidated `app.py` routing. The repository workflow provides broader regression coverage. These are CI results, not proof of a live production deployment.

## Implemented and CI-covered controls

- One visible NEMA-AGORA workspace in the curated Streamlit navigation; specialist NEMA pages are kept out of the main sidebar.
- Explicit demo versus persistent modes; persistent startup does not silently fall back to demo storage.
- Server-configured role bindings and deny-by-default authorization; unprovisioned users are denied.
- SQLite repository/service permission checks and actor-attributed audit events.
- Append-only event-log triggers, backup validation, restore rollback-snapshot preservation, and bounded retention configuration.
- Evidence lifecycle transitions revalidate source-observation fingerprints inside the write transaction.
- Lifecycle history checks validate transitions, actor attribution, timezone-aware timestamps, chronology, and agreement with persisted state.
- Release-readiness reports remain advisory: production approval, official integration, official submission, autonomous deployment, regulatory conclusions, and enforcement actions are explicitly disallowed.

## Required before production or real-user data

- [ ] Configure OIDC credentials and exact callback URL in the deployment secret manager; never commit secrets.
- [ ] Test login/logout on the deployed URL and verify server-side role bindings for each provisioned role.
- [ ] Test unprovisioned accounts and direct service/repository calls; confirm access is denied where required.
- [ ] In an approved persistent environment, create a synthetic record, read it back, review it, and verify actor-attributed audit history.
- [ ] Exercise backup, integrity check, restore, rollback failure handling, and retention against deployed storage.
- [ ] Confirm persistent storage survives restarts and document access controls, backup ownership, and recovery steps.
- [ ] Verify evaluation artifacts are present, candidate-bound, and reviewable.
- [ ] Review accessibility, low-bandwidth use, consent, data minimization, retention, and institutional governance.
- [ ] Validate environmental data sources and obtain required institutional approvals.

## Release boundary

NEMA-AGORA is an independent student-led prototype, not an official NEMA service or endorsement. No ELMIS/SWIMS integration, official report submission, autonomous enforcement, or production approval is claimed. Use synthetic or appropriately consented test records until all deployment and governance gates are closed.

## Phase 186 — verified

The focused NEMA-AGORA Pilot Checks and repository CI/CD Pipeline both completed successfully for candidate `707c94c1dff787279257845c4e57df18b64ebf1f`. This verifies the recorded automated test/compile/startup checks for that candidate only; it does not establish live deployment readiness.

## Current next step — Phase 187: deployment preflight

A fail-closed `deployment_preflight()` now checks persistent-mode OIDC setting shape, explicit server-side role bindings, database path, backup directory, and retention configuration without returning secret values. It always keeps production approval false and the execution gate closed. Regression tests cover malformed settings, demo-mode boundaries, missing persistent requirements, invalid roles, invalid retention, and secret redaction.

- [ ] Verify CI for the latest Phase 187 implementation commit.
- [ ] Run the preflight against the actual deployment secret configuration without exposing secret values.
- [ ] Test deployed login/logout and role boundaries for provisioned and unprovisioned users.
- [ ] Verify persistent write/read/audit, restart durability, backup/restore, and retention in the target environment.
- [ ] Complete accessibility, data-governance, and institutional review.

Do not merge or describe the system as production-ready while any required gate remains open.
