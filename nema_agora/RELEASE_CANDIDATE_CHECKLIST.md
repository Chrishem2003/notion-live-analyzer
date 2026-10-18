# NEMA-AGORA Release Candidate Checklist

## Candidate

- Pull request: [#23 — clean main-based integration](https://github.com/Chrishem2003/notion-live-analyzer/pull/23)
- Branch: `feature/nema-agora-clean-integration`
- Current Phase 175 commit: `68fa6759baa97ad4ee317ca5edaf5a4e104afa5f`
- Phase 175 CI: [focused NEMA-AGORA checks](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39119277886) · [repository CI](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39119277876)

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
- [ ] Focused CI for Phase 175 commit completed successfully.
- [ ] Repository CI for Phase 175 commit completed successfully.

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
