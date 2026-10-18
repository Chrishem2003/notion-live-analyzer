# NEMA-AGORA Release Candidate Checklist

## Candidate

- Pull request: [#23 — clean main-based integration](https://github.com/Chrishem2003/notion-live-analyzer/pull/23)
- Branch: `feature/nema-agora-clean-integration`
- Candidate commit verified before this checklist update: `2aa350dddb7d08b5f74dd131f646a30bc667cb74`
- CI evidence: [focused NEMA-AGORA checks](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39117864979) · [repository CI](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39117864940)

## Verified on the candidate commit

- [x] Focused NEMA-AGORA test suite passed.
- [x] Python compilation passed for the NEMA package and curated app entrypoints.
- [x] Streamlit startup smoke test passed for `app.py`.
- [x] Navigation contract tests cover hiding specialist NEMA pages from sidebar discovery.
- [x] One visible NEMA-AGORA workspace is registered by the curated app entrypoint.
- [x] Historical divergent PR #10 is marked superseded; PR #23 is the intended integration candidate.

The build-state metadata update itself must receive a fresh CI run before its commit is treated as verified.

## Required before production or real-user data

- [ ] Configure OIDC credentials and callback URL in the deployment secret manager; never commit secrets.
- [ ] Test login/logout and explicit server-side role bindings for each provisioned role.
- [ ] Verify unauthorized and unprovisioned users fail closed, including direct navigation and direct service/repository calls.
- [ ] In an approved persistent environment, create a record, read it back, review it, and verify actor-attributed audit history.
- [ ] Exercise backup, restore, integrity checks, and retention against the deployed storage configuration.
- [ ] Confirm persistent storage survives restarts and has documented access controls and recovery ownership.
- [ ] Review accessibility, low-bandwidth use, consent, data minimization, retention, and institutional governance.
- [ ] Validate any environmental data sources and obtain required institutional approvals.

## Safety and scope boundary

NEMA-AGORA remains an independent student-led prototype. It is not an official NEMA service and does not claim NEMA endorsement, ELMIS/SWIMS integration, official report submission, autonomous enforcement, or production approval. Use synthetic or appropriately consented test records until governance and deployment gates are complete.
