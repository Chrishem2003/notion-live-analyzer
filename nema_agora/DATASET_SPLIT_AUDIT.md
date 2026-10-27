# Dataset split leakage audit

The module `nema_agora/split_audit.py` compares declared unit IDs across development, validation and holdout manifests for each reference-set ID. It rejects malformed manifests, duplicate IDs within a split, duplicate manifest entries, and reports cross-split overlap. The same unit ID is treated as overlap even if the declared reference-set version differs.

## Interpretation

- `NO_DECLARED_UNIT_ID_OVERLAP` means only that exact declared unit IDs do not overlap in the supplied manifests.
- `BLOCK_EVALUATION` means a declared unit appears in multiple splits; resolve the split design before reporting evaluation metrics.
- The report contains a stable SHA-256 digest of canonicalized manifest declarations.

This is not a complete leakage proof. It cannot detect aliases, overlapping or adjacent geographies, temporal leakage, shared imagery/tiles, shared derived features, duplicate evidence under different IDs, or whether holdout data influenced model or threshold tuning. It does not authenticate source evidence or reviewers. A separate independent audit of spatial, temporal, and asset-level separation remains required.
