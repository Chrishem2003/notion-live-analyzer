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


## Phase 177 — identity and configuration hardening

- [x] Unexpected identity adapter exceptions fail closed to no principal.
- [x] Persistent NEMA-AGORA page routes through the fail-closed identity resolver.
- [x] Role, groups, and is_admin claims cannot override server-side role bindings.
- [x] Backup retention configuration rejects floats and non-scalar values instead of truncating them.
- [x] Focused NEMA-AGORA checks passed: [run 39122117903](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39122117903).
- [x] Repository-wide CI passed: [run 39122117681](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39122117681).

These are code-level and CI validations. They do not prove that an external OIDC provider or production deployment is configured correctly.



## Phase 178 — persistent startup resilience

- [x] Extracted explicit persistent-service initialization into `nema_agora/runtime.py`.
- [x] Persistent startup failures display a safe, non-path-revealing message and stop the run for a provisioned user; no silent demo fallback occurs.
- [x] Added regression tests for explicit nested database initialization and unavailable storage paths.
- [x] Focused NEMA-AGORA checks passed: [run 39122825957](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39122825957).
- [x] Repository CI passed: [run 39122826042](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39122826042).

The tests verify application/runtime behavior in CI. They do not replace a live deployment test of the actual host filesystem, OIDC, persistent volume, or database recovery.


## Phase 179 — privileged role/action regression matrix

- [x] Added parameterized assertions for submitter, reviewer, coordinator, and administrator permissions across observation creation/review, case export, audit read, user management, model admission, attestation, and annotation adjudication.
- [x] Focused NEMA-AGORA checks passed on the tested candidate: [run 39123574247](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39123574247).
- [x] Repository CI passed: [run 39123574232](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39123574232).

## Phase 180 — recovery snapshot preservation

- [x] Hardened restore rollback handling: if post-restore integrity validation fails and automatic rollback replacement also fails, the only rollback snapshot is preserved instead of deleted during cleanup.
- [x] Added a failure-injection regression test that verifies the retained snapshot can restore the original target database.
- [x] Focused NEMA-AGORA checks passed: [run 39123574247](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39123574247).
- [x] Repository CI passed: [run 39123574232](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39123574232).

These checks validate the tested code paths in CI. Deployment-specific volume permissions, live identity-provider behavior, and an operational restore drill still require verification in the actual hosting environment.


## Phase 181 — evidence audit access boundary

- [x] Added a service-level regression test confirming submitters and reviewers cannot list evidence lifecycle events without `audit:read`.
- [x] Confirmed a coordinator with the required permission can retrieve the evidence lifecycle event after preparation.
- [x] Focused NEMA-AGORA checks passed: [run 39123897265](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39123897265).
- [x] Repository CI passed: [run 39123897216](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39123897216).

The test exercises service/repository policy under CI. Deployed identity-provider and account-by-account role checks remain required.

## Phase 182 — evidence lifecycle failure atomicity

- [x] Added regression coverage proving invalid human-review decisions leave the persisted evidence state and lifecycle event log unchanged.
- [x] Added replay checks proving duplicate review/export attempts cannot append duplicate lifecycle events.
- [x] Focused NEMA-AGORA CI passed: [run 39124448742](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39124448742).
- [x] Repository CI passed: [run 39124448726](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39124448726).
- [ ] Deployed write/read, identity, backup-restore, and institutional release gates remain outstanding.



## Phase 183 — atomic source-provenance revalidation

- [x] Evidence transitions now re-read the source observation inside the SQLite write transaction and verify the evidence bundle's observation fingerprint before changing lifecycle state.
- [x] Added a regression test that injects a source-record update between service precheck and transition; the review must fail and no review lifecycle event may be appended.
- [ ] Focused and repository CI must pass on this implementation before Phase 183 is verified.
- [ ] Deployed identity, persistent write/read, backup-restore, governance, and institutional release gates remain outstanding.

## Phase 184 — lifecycle history consistency verifier

- [x] Added an audit-permission-gated verifier that checks evidence lifecycle event ordering, allowed transitions, actor attribution, timestamps, and agreement with the persisted final state/fingerprint.
- [x] Added tests for a valid prepare → review → export chain and for detection of an injected extra lifecycle event.
- [ ] Focused NEMA-AGORA and repository CI must pass on the latest candidate before Phase 184 is verified.
- [ ] This is an application-level consistency check, not cryptographic tamper proofing; protect the database file and backups separately.

