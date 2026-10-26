# Satellite dataset manifest contract

Status: **metadata validation only; no satellite assets or labels are fetched or independently verified**.

The validator requires stable dataset, AOI, grid and reference-set identities; sensor/product and processing version; CRS; acquisition dates; cloud and valid-pixel filtering descriptions; resolution; sampling and label-review methods; candidate-policy version; and a declared development, validation or holdout split. Quality values must be present and within bounds. An optional SHA-256 field can identify a source asset or bundle when computed by a trusted ingestion process.

The manifest digest is computed from canonical JSON. Reordering object keys does not change the digest; changing a field does. It is a reproducibility aid, not a signature or proof of authenticity.

## Required evidence before operational evaluation

- Preserve original asset/product identifiers and immutable source checksums.
- Record AOI geometry/version, CRS/grid/resolution, acquisition window, cloud mask and valid-pixel filters.
- Keep reference labels independently reviewed and traceable to reviewer, method and version.
- Separate development, validation and final holdout data by geography/time where practical; do not tune on holdout labels.
- Review sample selection, class balance, exclusions and uncertainty before interpreting precision/recall.
- Treat all candidate detections as advisory; no automated legal finding or enforcement decision.

METADATA_COMPLETE_NOT_INDEPENDENTLY_VERIFIED means required metadata passed structural checks only. It must never be presented as a verified dataset or successful environmental outcome.
