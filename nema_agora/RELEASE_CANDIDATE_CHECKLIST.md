# NEMA-AGORA Release Candidate

## Candidate

- Integration PR: [#115 — NEMA-AGORA mainline integration candidate](https://github.com/Chrishem2003/notion-live-analyzer/pull/115)
- Branch: `integration/nema-agora-mainline-20261026`
- Phase 188 verified candidate: `b247c838f8a6447bf020c6d629f06f538e058890`
- Phase 189 verified candidate: `b9f11fa494fb069feae39ca264043e4e30f255f6`
- Phase 190 search-path migration candidate: `15a1615f7fdb2e7b87ce5ac5857040ceb8fe975d`
- Base branch: `main` at `43ef47b404977dc6af5db45164ffc8a9d2f3f755`
- Status: draft and unmerged. Phase 189 repository CI/CD, NEMA integration checks, and authentication-role security checks all passed on `b9f11fa494fb069feae39ca264043e4e30f255f6`. Phase 190 adds an additive search-path hardening migration candidate; its CI is pending. Staging is not release-ready.

## Verified automated checks

The following workflows passed on the preceding code commit (`8075c4e8588dd66058b7fa0a41ab6a16146d1abd`), not yet on the documentation-only follow-up:

- [NEMA-AGORA focused checks](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/40377656381)
- [Full repository CI](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/40377656415)
- [Authentication-role security checks](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/40377656146)

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



## Phase 189 — Staging-readiness findings

See [the read-only staging audit](STAGING_READINESS_AUDIT_PHASE189.md). The Streamlit and API health endpoints returned HTTP 200 after cold starts. The NEMA case API is not ready: unauthenticated requests returned HTTP 503 because the staging API has no `PLATFORM_API_KEY`. The deployed staging schema lacks `owner_id` because migration 002 is not applied; migration 003 is also pending. The staging services still track `feat/shared-ai-gateway-rebase-oct25`, not the current integration branch. No secrets were changed and no database migrations were applied.

The client now requires `NEMA_CASE_API_BASE_URL` explicitly and will not default to the production API. Phase 189 CI passed on the recorded candidate. Phase 190 adds `005_nema_audit_search_path_hardening.sql`; it has not been applied to any database.

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

## Phase 190 — additive audit-trigger hardening candidate

Added `migrations/supabase/005_nema_audit_search_path_hardening.sql`, which pins the existing append-only audit trigger function's `search_path` to `pg_catalog`. This is additive configuration only; it does not change rows, grants, RLS, or write permissions. The migration is **not applied** and requires CI verification plus explicit approval before staging application.

## Current next step — Phase 190: staging readiness

Read-only observations from the current Render/Supabase staging environment:

- Streamlit staging health endpoint returned HTTP 200 after a cold start.
- API health returned HTTP 200 and explicitly reports research-run write-back disabled.
- NEMA case API requests without service authentication returned HTTP 503 with `PLATFORM_API_KEY is not configured`; authenticated reads have not been tested.
- Staging Supabase has `public.nema_cases` and `public.nema_case_audit`, both RLS-enabled with no client policies. This is fail-closed for direct anon/authenticated access and should remain so.
- The deployed staging schema does not include `owner_id`; repository migration `002_nema_case_owner_scope.sql` is not applied. Migration `003_nema_case_owner_integrity.sql` is also not applied.
- Supabase reports a mutable `search_path` warning for `public.reject_nema_case_audit_mutation`.
- Render staging services currently track `feat/shared-ai-gateway-rebase-oct25`, not the NEMA integration branch. Do not claim the latest candidate is deployed.
- The NEMA client is being hardened to require an explicit `NEMA_CASE_API_BASE_URL`; it must never silently default to the production API.

No environment secrets were changed and no database migration was applied. Before staging authenticated reads: configure separate service/signing secrets in Render for the staging app and API, explicitly point the app to the staging API URL, review/apply owner-scope migrations only with explicit staging approval, then test signed read-only access and denial of unauthenticated access. Production remains unchanged.


## Phase 191 — measurement evidence record contract

Added `nema_agora/indicator_evidence.py` and `tests/test_nema_indicator_evidence.py`, and integrated JSON-record validation into the existing single-page NEMA-AGORA Pilot metrics workspace. Validation checks reporting periods, units, source IDs, artifact digest format, method version, calculation arithmetic, and independent-review fields for `verified` records. It does not persist uploaded records or alter registry status. Passing structural validation is not a claim of artifact authenticity or authenticated reviewer identity.

Current CI must run against the final integration-branch head before this phase is considered verified. Release remains blocked by staging branch mismatch, missing API authentication configuration, unapplied owner-scope migrations, and unverified authenticated storage reads. No database migrations or environment secrets were changed.


## Phase 192 — uploaded artifact digest consistency

The evidence validator accepts optional evidence bytes and independently computes SHA-256. The one-page Pilot metrics workspace now lets reviewers supply both the measurement JSON and the referenced artifact; a digest mismatch is rejected, while omission of artifact bytes is explicitly reported as unchecked. Automated tests cover match, mismatch, and omission. This is byte-integrity checking only—not source authenticity, reviewer authentication, or institutional verification. No persistence or registry status mutation is enabled.
