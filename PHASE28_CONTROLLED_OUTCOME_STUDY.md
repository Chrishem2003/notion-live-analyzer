# Phase 28 — Controlled Outcome Study

Phase 28 converts the existing Phase 22 impact observations into reproducible
paired comparisons. A scenario is compared only when the same scenario ID has
both a BASELINE and ASSISTED observation.

## Evidence protocol

- Pairing is deterministic by scenario identifier.
- Unmatched observations are excluded rather than fabricated.
- The study records a dataset fingerprint and policy version.
- Metrics are reported as assisted-minus-baseline deltas.
- Evidence is about workflow/software behaviour, not environmental impact.
- No result can authorize enforcement, emergency response, official reporting,
  regulatory action, NEMA endorsement, or autonomous decisions.

## Metrics

The study compares time to review, evidence completeness, duplicate detection,
reviewer workload, correction rate, and end-to-end workflow success.

## Interpretation

A positive or negative delta is an engineering observation. It must be
interpreted with sample size, study design, data quality, and human review.
Synthetic demonstrations must remain separate from pilot evidence.
