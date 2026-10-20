from dataclasses import replace

import pytest

from nema_agora.evaluation import (
    EvaluationCase,
    build_evaluation_run,
    validate_evaluation_run,
)


def _case(case_id: str, expected: str, observed: str) -> EvaluationCase:
    return EvaluationCase(
        case_id,
        "a" * 64,
        expected,
        observed,
        "pilot-model",
        "1.0",
    )


def test_evaluation_is_reproducible_and_advisory():
    cases = [_case("c1", "A", "A"), _case("c2", "A", "B")]
    run = build_evaluation_run(
        run_id="run1",
        dataset={"dataset": "pilot", "version": 1},
        cases=cases,
    )
    assert run.accuracy == 0.5
    result = validate_evaluation_run(run)
    assert result["valid"] and result["reproducible"]
    assert len(result["artifact_fingerprint"]) == 64
    assert result["automatic_model_admission"] is False


def test_validator_recomputes_accuracy_instead_of_trusting_metadata():
    run = build_evaluation_run(
        run_id="run1",
        dataset={"dataset": "pilot", "version": 1},
        cases=[_case("c1", "A", "A"), _case("c2", "A", "B")],
    )
    tampered = replace(run, accuracy=1.0)
    result = validate_evaluation_run(tampered)
    assert not result["valid"]
    assert "accuracy_mismatch" in result["issues"]


def test_build_rejects_incomplete_model_identity_and_input_fingerprint():
    with pytest.raises(ValueError, match="missing_model_version"):
        build_evaluation_run(
            run_id="run1",
            dataset={"dataset": "pilot"},
            cases=[EvaluationCase("c1", "a" * 64, "A", "A", "pilot-model", "")],
        )
    with pytest.raises(ValueError, match="missing_input_fingerprint"):
        build_evaluation_run(
            run_id="run1",
            dataset={"dataset": "pilot"},
            cases=[EvaluationCase("c1", "", "A", "A", "pilot-model", "1.0")],
        )
