# NEMA-AGORA Phase 15 — Controlled Model Comparison

Phase 15 adds a frozen-dataset comparison layer for advisory models.

## Control flow
1. Freeze a human-labelled dataset into a versioned manifest with SHA-256.
2. Give every adapter the same case record.
3. Validate every output against the existing safety contract.
4. Treat adapter failures as failures, never as guessed predictions.
5. Measure models independently and by slice.
6. Compare model disagreement and regression against a named baseline.
7. Persist only comparison evidence; live workflow state is untouched.

## Metrics
Category accuracy; macro precision/recall/F1; duplicate precision/recall/F1;
duplicate false positives/false negatives; summary-label coverage/rate; confidence
Brier score when available; latency; failure rate; slice performance; disagreement;
baseline deltas; provider/model version; dataset version/hash.

## Readiness
At least 25 frozen cases, zero adapter failures, category accuracy >= 80%, and
duplicate F1 >= 80% for every compared adapter produces READY_FOR_REVIEW.
This is not production approval, environmental truth, legal sufficiency, regulatory
compliance, NEMA endorsement, or permission for autonomous action.

The default adapter remains the deterministic local baseline. External AI providers
are not silently connected.
