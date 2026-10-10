# Phase 21 — Controlled Field Evaluation Laboratory

Phase 21-v2 evaluates NEMA-AGORA against a fixed six-scenario catalogue:
complete, incomplete, duplicate, ambiguous, unsafe-advisory, and
conflicting-human-review cases.

## v2 methodology

The laboratory no longer depends on manually supplied observed quality outputs
for the controlled suite. Each synthetic scenario is executed through the
actual application chain:

**Observation → Quality → Intelligence → Reviewer Copilot**

The suite then evaluates:

- the quality status produced by the real quality module;
- required quality flags for incomplete, duplicate, and ambiguous cases;
- the mandatory human_review_required contract;
- reviewer-copilot source-case binding;
- the explicit safety contract blocking autonomous decision-making;
- scenario-level pass/fail evidence.

build_controlled_scenarios() supplies deterministic synthetic records and peer
records. The duplicate scenario therefore exercises the real duplicate
heuristic rather than a manually asserted duplicate result.

The persistent FieldEvaluationStore records the resulting evidence without
changing the underlying observation workflow. The service layer exposes a
principal-bound operation to run the complete controlled suite.

The older manual evaluation vocabulary remains accepted for compatibility with
existing stored/lab workflows, but new controlled-suite evidence is generated
from real pipeline execution.

## Governance boundary

Controlled field evaluation is software-behaviour evidence only. A passing
scenario suite does **not** establish environmental truth, environmental
impact, regulatory status, NEMA authorization, enforcement authority, emergency
response authority, or production approval.

All scenario records are synthetic unless a separately governed, explicitly
consented test record is used. The laboratory must remain isolated from
official reporting and enforcement workflows.

## Reproducibility

The scenario catalogue has a SHA-256 fingerprint. Evaluation records include
the scenario ID, observed pipeline outputs, expected contract, policy version,
and timestamp. The suite is deterministic in its scenario inputs; generated
evaluation IDs and timestamps are intentionally runtime-specific.

## Future strengthening

Future controlled evaluations can add independently labelled field datasets,
but must continue to execute the actual observation-to-review pipeline rather
than injecting expected outputs directly.
