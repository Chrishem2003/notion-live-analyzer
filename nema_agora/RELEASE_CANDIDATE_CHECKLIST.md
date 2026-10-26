# NEMA-AGORA Release Candidate

## Candidate

- Integration PR: [#115 — NEMA-AGORA mainline integration candidate](https://github.com/Chrishem2003/notion-live-analyzer/pull/115)
- Branch: `integration/nema-agora-mainline-20261026`
- Current candidate commit at this checklist revision: `46315fdc2981dd5033f5e70192079a24cd306cfd`
- Base branch: `main` at `43ef47b404977dc6af5db45164ffc8a9d2f3f755`
- Status: draft and unmerged. The latest code/security workflows passed on parent commit `8075c4e8588dd66058b7fa0a41ab6a16146d1abd`; this documentation-only follow-up still needs its own CI result. Release remains blocked on deployment and governance evidence.

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

## Current next step — Phase 186

Reconcile release evidence against the exact candidate, verify the consolidated user journey and direct authorization boundaries, then run deployment-backed operational checks. Do not merge or describe the system as production-ready while any required gate remains open.
