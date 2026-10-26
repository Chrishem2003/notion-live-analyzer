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


## Source asset and derived-data lineage screening

The gate requires `asset_lineage_records` and runs `nema_agora/asset_lineage_audit.py` before metrics can be computed. Records declare a unique record ID, split, source-asset SHA-256, satellite tile IDs, and parent record IDs in `derived_from`. Reused source hashes, tile identifiers, or derived parents across different splits block metric generation. Unknown parents and lineage cycles are rejected.

**Fail-closed requirement:** a caller that omits the manifest or supplies an empty manifest is blocked before metrics are computed. The Streamlit workspace includes the manifest in its JSON template and passes it to the gate. Replace template placeholders with SHA-256 hashes of actual source bytes and stable tile/parent identifiers. The audit only checks declared hashes/IDs/links; hashes should be independently anchored to a trusted source.

The audit cannot identify undeclared relationships, alternate encodings, shared model weights, derived-feature leakage not represented in the graph, or holdout-informed tuning. A clean result is not proof of complete independence.
