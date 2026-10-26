# NEMA-AGORA Satellite Change Evaluation Harness

Status: **offline evaluation code added; no live imagery evaluation has been run**.

The module `nema_agora/satellite_evaluation.py` computes a confusion matrix and standard metrics for a supplied evaluation fixture. It requires each unit to have a stable ID, an area in hectares, a candidate-detection boolean, independently verified reference-change boolean, verification flag, and usability flag.

## Eligibility and exclusions

- Only units with area **strictly greater than** the configured threshold (default 0.1 ha) are eligible.
- Reference labels must be independently verified.
- Units marked unusable are excluded.
- Every exclusion category is counted and returned.
- Duplicate IDs, missing truth labels, non-boolean flags, negative/non-finite areas, and malformed input are rejected.
- A metric with a zero denominator is returned as `null`, not fabricated as zero.

## Reported metrics

- Precision = TP / (TP + FP)
- Recall = TP / (TP + FN)
- F1 = 2TP / (2TP + FP + FN)
- False-positive rate = FP / (FP + TN)

## Evidence requirements before real evaluation

Use a versioned, independently verified reference set; record its geography, time window, sampling method, sensor/product versions, cloud and valid-pixel filters, spatial resolution, candidate policy version, sample size, exclusions, and uncertainty. Keep the fixture and report traceable by stable IDs and hashes. Do not optimize thresholds on the same set used for final evaluation without declaring the leakage and using a separate holdout set.

## Safety and limitations

This is an offline metric calculator, not a satellite-data ingestion pipeline. It does not establish that the supplied reference set is representative, fetch imagery, or verify the underlying labels. Results apply only to the supplied units and exclusions. A detected candidate is an advisory signal for human review, never a legal finding or enforcement action. No metrics should be shown as pilot achievements until real evidence is independently reviewed.
