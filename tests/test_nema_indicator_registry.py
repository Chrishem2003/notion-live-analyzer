"""Contract tests for the NEMA-AGORA pilot indicator registry."""
import json
from pathlib import Path


def _registry():
    path = Path(__file__).resolve().parents[1] / "nema_agora" / "indicator_registry.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_indicator_registry_covers_all_four_expected_results():
    registry = _registry()
    assert registry["schema_version"]
    assert {item["result_id"] for item in registry["indicators"]} == {
        "ER1", "ER2", "ER3", "ER4"
    }


def test_indicator_ids_are_unique_and_evidence_is_defined():
    indicators = _registry()["indicators"]
    ids = [item["id"] for item in indicators]
    assert len(ids) == len(set(ids))
    assert all(item.get("name") and item.get("unit") for item in indicators)
    assert all(item.get("required_evidence") for item in indicators)


def test_targets_are_not_misrepresented_as_achievements():
    registry = _registry()
    assert registry["rules"]["targets_are_not_achievements"] is True
    assert registry["rules"]["missing_is_not_zero"] is True
    assert all(item["status"] == "not_started" for item in registry["indicators"])


def test_spatial_detection_target_is_scoped_to_a_declared_evaluation_set():
    registry = _registry()
    item = next(item for item in registry["indicators"] if item["id"] == "ENV-DETECT-002")
    assert item["target"] == 100
    assert item["target_type"] == "stretch_target_on_declared_evaluation_set"
    assert "confidence interval" in item["quality_companions"]


def test_dashboard_latency_target_uses_percentile_measurement():
    registry = _registry()
    item = next(item for item in registry["indicators"] if item["id"] == "DASH-LATENCY-001")
    assert item["target"] == 2
    assert item["target_type"] == "less_than_p95"
    assert "p50, p95, and p99" in item["calculation"]


def test_community_target_counts_unique_onboarded_users():
    registry = _registry()
    item = next(item for item in registry["indicators"] if item["id"] == "COM-ONBOARD-001")
    assert item["target"] == 500
    assert "deduplicated" in item["calculation"]
