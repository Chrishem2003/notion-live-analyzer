# Phase 111 — Recovery Review Reconciliation & Evidence Integrity

Phase 111 closes the verification loop between Phase 109 integrity-monitor reports and Phase 110 human recovery-review records.

## Contract
- Read-only; no repair, restore, rewrite, delete, or recovery execution.
- Validates Phase 109 monitor fingerprints and Phase 110 review fingerprints/IDs.
- Detects unreviewed reports, orphan reviews, duplicates, policy mismatches, state/recommendation mismatches, invalid no-action outcomes, unexpected recovery flags, and expected-count mismatches.
- Clean evidence returns RECONCILED; any integrity gap returns CONTROL_REQUIRED.
- Produces a deterministic reconciliation fingerprint.
- Environmental, regulatory, enforcement, and emergency conclusions remain absent/None.

## Review boundary
A supplied monitor-report set is the reconciliation scope: every valid report in that set is expected to have exactly one corresponding human review. This does not imply every historical report must be reviewed outside the supplied scope.

The Streamlit page uses synthetic data only. NEMA-AGORA remains an independent prototype and claims no official NEMA integration or authority.

## Verification
Run focused Phase 111 tests, Python compilation, and the Streamlit smoke path in GitHub Actions before calling the phase CI-green.
