# NEMA-AGORA Phase 9 — AI Evaluation & Decision-Support Engine

## Objective

Build a measurable, governance-first evaluation layer before introducing an
external or generative AI model. Phase 9 establishes a labelled evaluation
dataset format, deterministic benchmark metrics, safety checks, and an
auditable model-adapter contract.

## Design principles

- Evaluation data is synthetic or explicitly consented.
- Ground truth is human-labelled; AI output never becomes ground truth.
- Model outputs remain advisory and cannot directly change workflow state.
- Evaluation reports distinguish accuracy from safety and governance compliance.
- No personal data, urgent incidents, enforcement decisions, or official NEMA integration.
- A model adapter must be replaceable and must not require a provider at import time.

## Phase 9 gates

1. Dataset schema validates required fields and supported labels.
2. Category suggestions can be evaluated against human labels.
3. Duplicate detection is measured with precision, recall and F1.
4. Summary evaluation has a human-reviewable faithfulness field; no automatic
   claim of semantic truth is made from text overlap alone.
5. Safety tests reject prohibited autonomous-decision fields/actions.
6. Model adapters return structured advisory output and preserve source case IDs.
7. Evaluation results are reproducible and serialisable.
8. Only after these gates should an optional model provider be introduced.

## Proposed workflow

Human-labelled pilot fixtures
→ benchmark harness
→ deterministic baseline
→ optional model adapter
→ safety validation
→ reviewer evaluation
→ versioned evaluation report

## Not yet enabled

No LLM/API provider is connected in Phase 9. Provider credentials, model
selection, data retention, external processing and cost controls must be
reviewed before any live model integration.
