from nema_agora.shadow_monitoring import ShadowMonitoringPolicy, build_shadow_monitoring_snapshot

def _run(i, *, status="SHADOW_OK", latency=100.0, review=True, output=None, model="model-1"):
    return {
        "run_id": f"CSR-{i}", "admission_id": "ADM-1", "case_id": f"CASE-{i}",
        "actor_id": "reviewer-1", "provider": "provider-a", "model_version": model,
        "adapter_name": "adapter-a", "status": status, "latency_ms": latency,
        "human_review_required": review,
        "output": output if output is not None else {
            "source_case_id": f"CASE-{i}", "summary": "advisory", "category_suggestions": [],
            "priority_advisory": "review", "quality_status": "VALID", "quality_flags": [],
            "human_review_required": True, "decision_notice": "Advisory only.",
        },
    }

def test_monitoring_requires_enough_shadow_evidence():
    snapshot = build_shadow_monitoring_snapshot([_run(1)])
    assert snapshot.status == "NOT_ENOUGH_DATA"
    assert "INSUFFICIENT_SHADOW_RUNS" in snapshot.alerts

def test_monitoring_reports_healthy_shadow_lane():
    snapshot = build_shadow_monitoring_snapshot([_run(i, latency=100+i) for i in range(10)])
    assert snapshot.status == "HEALTHY_WITHIN_SHADOW_POLICY"
    assert snapshot.total_runs == 10
    assert snapshot.successful_runs == 10
    assert snapshot.unique_cases == 10
    assert snapshot.error_rate == 0.0
    assert snapshot.p95_latency_ms > 0

def test_monitoring_fails_closed_on_safety_contract_violation():
    bad = _run(1, output={"source_case_id": "CASE-1", "human_review_required": False})
    snapshot = build_shadow_monitoring_snapshot([bad], policy=ShadowMonitoringPolicy(minimum_runs_for_stability=1))
    assert snapshot.status == "CONTROL_REQUIRED"
    assert snapshot.safety_contract_violations == 1
    assert "SAFETY_CONTRACT_VIOLATION" in snapshot.alerts

def test_monitoring_detects_error_and_latency_policy_breaches():
    runs = [_run(i, status="SHADOW_ERROR" if i == 1 else "SHADOW_OK", latency=6000) for i in range(10)]
    snapshot = build_shadow_monitoring_snapshot(runs)
    assert snapshot.status == "WATCH"
    assert "ERROR_RATE_ABOVE_POLICY" in snapshot.alerts
    assert "P95_LATENCY_ABOVE_POLICY" in snapshot.alerts

def test_monitoring_detects_identity_drift():
    runs = [_run(i) for i in range(10)]
    runs[-1]["model_version"] = "model-2"
    snapshot = build_shadow_monitoring_snapshot(runs)
    assert snapshot.status == "CONTROL_REQUIRED"
    assert snapshot.identity_consistency_violations == 1
    assert "MODEL_IDENTITY_DRIFT" in snapshot.alerts
