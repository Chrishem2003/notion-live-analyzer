# Phase 171 — Release-Candidate Readiness Evidence Gate

## Why this phase exists
Phase 170 says the product should move to release-readiness verification, not another sequence of narrowly renamed registries. Phase 171 implements that direction: a fail-closed evidence gate bound to the exact Git commit under review.

## Required gates
1. Focused GitHub Actions checks on the exact candidate SHA.
2. End-to-end tests in a clean environment.
3. Role isolation, authentication, authorization and audit-access verification.
4. Backup and restore verification.
5. Retention and evidence-preservation verification.
6. Recomputed evaluation artifacts and model identity/version verification.
7. Accessibility and data-governance review.
8. Institutional/supervisor approval.

Every gate requires a PASS status, a traceable evidence reference, an offset-aware ISO 8601 verification timestamp, and the exact candidate SHA. Missing, malformed, stale-to-another-commit, failed or unrecognized gate evidence prevents a positive result.

## Output contract
- `NOT_READY` if any gate is missing or invalid.
- `READY_FOR_HUMAN_RELEASE_REVIEW` only when all eight gates are complete and no findings remain.
- A positive result is not release approval or production readiness.
- The execution gate remains CLOSED; deployment and official submission are never performed.
- Reports are deterministically fingerprinted and can be revalidated for tampering.

## User interface
The authenticated Streamlit page is `pages/171_NEMA_AGORA_RELEASE_READINESS.py`. It requires the existing `intelligence:pilot_readiness` permission, offers a JSON evidence template, reports each gate and finding, and supports downloading the assessment.

## Validation gate
Run:
- `python -m pytest -q tests/nema_agora/test_release_readiness.py`
- `python -m compileall -q nema_agora pages`
- the full focused NEMA-AGORA CI workflow, including the Streamlit smoke test, on the exact release-candidate commit.

CI must be observed passing on that exact commit before the readiness evidence can truthfully record the focused-CI gate as PASS.

## Safety boundary
NEMA-AGORA remains an independent pilot prototype. This phase does not imply NEMA endorsement, official NEMA/ELMIS/SWIMS integration, environmental truth, regulatory status, enforcement authority, emergency-response authority, or production approval.
