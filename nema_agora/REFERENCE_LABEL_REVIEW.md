# Independent Reference-Label Review Gate

Status: **metadata validation implemented; no reference imagery or labels independently audited by this tool**.

The module `nema_agora/reference_review.py` validates a JSON package containing a reference-set ID/version, declared split, and unit-level review metadata. Each unit must include a stable ID, boolean reference-change label, at least two distinct reviewer IDs, a timezone-aware review timestamp, one or more evidence references, and an explicit declaration that reviewers were blinded to candidate detections.

## Fail-closed checks

- Reject missing or malformed package metadata.
- Reject duplicate unit IDs.
- Reject non-boolean reference labels.
- Require at least two distinct reviewer identifiers per unit.
- Require timezone-aware ISO-8601 review timestamps.
- Require evidence references and a positive blinding declaration.
- Produce a deterministic SHA-256 digest of canonical validated metadata.

## What the gate does not prove

Reviewer IDs, timestamps, evidence references, blinding and split assignments are user-supplied declarations. The gate does not authenticate reviewers, open or hash referenced evidence assets, establish reviewer independence, prove reference-label correctness, detect disagreement, or prove holdout independence from model/threshold tuning. A reviewer workflow should record disagreement and adjudication explicitly, verify evidence asset hashes, audit sampling and spatial/temporal representativeness, and keep final holdout units out of all tuning decisions.

The state `REVIEW_METADATA_COMPLETE_NOT_AUTHENTICATED` means only that the declared metadata passed structural checks. It must not be represented as a verified dataset or live model-performance result.
