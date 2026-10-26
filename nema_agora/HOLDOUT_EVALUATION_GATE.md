# Holdout evaluation gate

`nema_agora/evaluation_gate.py` composes the reference-review metadata validator, declared split-overlap audit, and offline confusion-matrix evaluator.

Before computing metrics it requires:
1. A valid reference-review metadata package declared as `holdout`.
2. No exact unit-ID overlap between development, validation, and holdout manifests.
3. Exactly one holdout manifest matching the review package's reference-set ID and version.
4. Exact equality between reviewed holdout IDs, manifest holdout IDs, and evaluation record IDs.
5. Evaluation-record reference labels matching the reviewed package labels.

A failed prerequisite raises `EvaluationGateError` and no metric report is produced. Unverified or unusable rows are still explicitly excluded by the underlying evaluator, with counts.

## Limits

The gate enforces consistency of declarations, not scientific authenticity. It cannot prove reviewer identity or blinding, inspect evidence, detect aliases/spatial/temporal/asset leakage, or prove the holdout was never used during tuning. The result state deliberately says declarations are not authenticated. Independent review remains mandatory before external claims or decisions.
