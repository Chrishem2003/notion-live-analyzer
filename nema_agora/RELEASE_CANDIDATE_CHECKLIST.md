# NEMA-AGORA Release Candidate

## Candidate under review

- Integration PR: [#52 — integrate NEMA-AGORA safely onto current main](https://github.com/Chrishem2003/notion-live-analyzer/pull/52)
- Branch: `integration/nema-agora-current-main`
- Code commit validated: `34100c41a4b6a7021a15c1ca0b0b750299200dc7`
- Status: automated CI passed on that exact code commit. Merge, hosted acceptance, persistent storage, and institutional release remain blocked pending the gates below.
- Scope: the integration preserves the current-main single-file `app.py` shell and adds the NEMA-AGORA page/package/tests. It does not merge the older divergent branch wholesale.

## Exact-head automated evidence

- [NEMA-AGORA Pilot Checks — passed](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39744340177)
  - NEMA unit tests passed.
  - NEMA package/page compilation passed.
  - Streamlit page smoke checks passed.
- [Repository CI/CD Pipeline — passed](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/39744340077)
  - Automated test suite passed.
  - Lightweight API container build passed.
  - API runtime import check passed.

These results validate the code commit listed above. They do not establish successful hosted deployment, real data ingestion, or production readiness. If this checklist or build-state metadata changes, rerun CI on the resulting head before treating the updated candidate as verified.

## Current pilot boundaries

- The primary NEMA workspace is `pages/18_NEMA_AGORA.py`.
- Demo mode is session-only. Persistent mode is opt-in and requires explicit authentication, authorization, and storage configuration.
- Unprovisioned users must remain denied; UI hiding alone is not an authorization boundary.
- Environmental analysis is advisory and requires human review. The prototype is not an official NEMA service and does not submit reports to NEMA.
- No official ELMIS/SWIMS integration, autonomous enforcement, or regulatory approval is claimed.
- Use synthetic or appropriately consented test records only.

## Required before merge or hosted release

- [ ] Review the inherited module inventory and dependencies. This PR contains 367 paths, including 50 phase-suffixed Python files across implementation and tests; CI passing does not prove every inherited artifact is necessary.
- [ ] Verify the NEMA page appears in the deployed Streamlit navigation and complete the demo-mode user journey without secrets or persistent storage.
- [ ] Verify OIDC login/logout on the deployed URL and server-side role bindings for each provisioned role.
- [ ] Test unprovisioned accounts and direct service/repository calls; confirm deny-by-default behavior.
- [ ] In an approved persistent environment, create a synthetic record, read it back, review it, and verify actor-attributed audit history.
- [ ] Exercise backup, integrity checks, restore, rollback-failure handling, retention, and persistence across restarts.
- [ ] Verify evaluation artifacts are present, candidate-bound, and reviewable.
- [ ] Complete accessibility, low-bandwidth, consent, data-minimization, retention, and institutional governance review.
- [ ] Validate environmental data sources and obtain required institutional approvals.

## Release decision

**Not approved for production.** Do not merge or describe this as production-ready until code review, exact-head CI, hosted acceptance, security/storage checks, and governance gates are complete.
