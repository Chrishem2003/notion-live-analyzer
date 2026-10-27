# Phase 194 — Reference-set change evaluation uncertainty

Status: implementation added; final-head CI pending.

## What changed

- `nema_agora/change_evaluation.py` computes precision, recall, specificity, F1 and false-positive rate from confusion-matrix counts, with Wilson confidence intervals for precision, recall and specificity.
- `tests/test_nema_change_evaluation.py` covers expected values, interval bounds, zero-denominator behavior, invalid counts and invalid thresholds.
- The existing one-page Streamlit NEMA-AGORA workspace now displays 95% Wilson intervals for the uploaded or synthetic offline satellite evaluation. It uses the source artifact SHA-256 as the evaluation-set identifier and labels the interpretation as limited to that supplied dataset.

## Interpretation controls

- No reference units means evaluation is rejected.
- Zero denominators produce `null` metrics and no interval, not a fabricated zero score.
- Confidence intervals quantify sampling uncertainty under the observed sample; they do not fix biased sampling or establish that reference labels are independent.
- The tool does not fetch satellite imagery or assert legal findings. Synthetic example results remain clearly labelled as synthetic.
- No indicator registry status is automatically promoted and no measurement is persisted by this feature.

## Release boundary

No production deployment, database migration, secret change, or official NEMA integration was performed. The feature must pass NEMA-focused CI, full repository CI and auth-role checks on the final candidate before it is considered validated.
