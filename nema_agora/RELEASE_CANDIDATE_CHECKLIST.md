# NEMA-AGORA Release Candidate Checklist

## Candidate

- Pull request: [#23 — clean main-based integration](https://github.com/Chrishem2003/notion-live-analyzer/pull/23)
- Branch: `feature/nema-agora-clean-integration`
- Latest verified implementation commit (Phase 176): `77e3c8ba2266fc7fcefe81d05480797a506e173d`
- Phase 175 CI: [focused NEMA-AGORA checks](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39120517179) · [repository CI](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39120517124)

## Verified before Phase 175

- [x] Focused NEMA-AGORA test suite passed on prior candidate commit.
- [x] Python compilation passed for the NEMA package and curated app entrypoints on prior candidate commit.
- [x] Streamlit startup smoke test passed for `app.py` on prior candidate commit.
- [x] Navigation contract tests cover hiding specialist NEMA pages from sidebar discovery.
- [x] One visible NEMA-AGORA workspace is registered by the curated app entrypoint.
- [x] Repository-wide CI passed for the prior candidate.

## Phase 175 — configuration hardening

- [x] Added regression tests for invalid or malformed deployment mode values defaulting to demo.
- [x] Added tests requiring an explicit database path rather than guessing a location.
- [x] Added tests for backup-retention bounds and malformed values.
- [x] Added tests for absent or malformed backup directory configuration.
- [x] Focused CI passed after Phase 175 and Phase 176 implementation (run 39120517179).
- [x] Repository CI passed after Phase 175 and Phase 176 implementation (run 39120517124).

Do not mark Phase 175 complete until the two CI runs above finish successfully.

## Required before production or real-user data

- [ ] Configure OIDC credentials and callback URL in the deployment secret manager; never commit secrets.
- [ ] Test login/logout and explicit server-side role bindings for each provisioned role.
- [ ] Verify unauthorized and unprovisioned users fail closed, including direct navigation and direct service/repository calls.
- [ ] In an approved persistent environment, create a record, read it back, review it, and verify actor-attributed audit history.
- [ ] Exercise backup, restore, integrity checks, and retention against the deployed storage configuration.
- [ ] Confirm persistent storage survives restarts and has documented access controls and recovery ownership.
- [ ] Review accessibility, low-bandwidth use, consent, data minimization, retention, and institutional governance.
- [ ] Validate environmental data sources and obtain required institutional approvals.

## Safety and scope boundary

NEMA-AGORA remains an independent student-led prototype. It is not an official NEMA service and does not claim NEMA endorsement, ELMIS/SWIMS integration, official report submission, autonomous enforcement, or production approval. Use synthetic or appropriately consented test records until governance and deployment gates are complete.


## Phase 176 — persistence and audit reliability

- [x] Reject empty string paths before `Path` normalization can turn them into the current directory.
- [x] Test backup helper behavior for invalid retention bounds, missing source databases, and corrupt source files.
- [x] Make audit, operational, and intelligence event records append-only at the SQLite trigger layer.
- [x] Regression tests confirm update/delete attempts are rejected for those event logs.
- [x] Focused NEMA-AGORA CI passed: [run 39120517179](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39120517179).
- [x] Repository-wide CI passed: [run 39120517124](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39120517124).

These controls are defense in depth only. They do not protect against an operator who can replace the database file or alter its schema, so deployed access controls and independent backups remain mandatory.


## Phase 177 — identity resolution hardening

- [x] Unexpected identity SDK/adapter exceptions fail closed to no principal.
- [x] Regression tests cover errors reading identity claims and login state.
- [x] Regression tests verify role, groups, and is_admin claims cannot override server-side role bindings.
- [x] Focused NEMA-AGORA checks passed: [run 39121794403](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39121794403).
- [x] Repository-wide CI passed: [run 39121794437](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39121794437).

This validates application-level fail-closed behavior and tests; it does not establish that an external OIDC provider is deployed or configured correctly.
