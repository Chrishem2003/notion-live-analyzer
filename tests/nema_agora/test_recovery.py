from nema_agora.recovery import run_recovery_smoke


def test_recovery_smoke_is_isolated_and_healthy():
    result = run_recovery_smoke()
    assert result["healthy"] is True
    assert result["persistent_database_touched"] is False
    assert all(result["checks"].values())


def test_recovery_smoke_is_deterministically_scoped_to_temp_storage():
    result = run_recovery_smoke()
    assert result["policy_version"] == "phase27-v1"
    assert "persistent database" in result["decision_notice"]
