import pytest
from nema_agora.fastapi_spatial_evidence_app import app_contract, FASTAPI_AVAILABLE


def test_contract_is_read_only_and_query_disabled_by_default():
    contract = app_contract()
    assert contract["read_only"] is True
    assert contract["authorization_required"] is True
    assert contract["identity_verifier_configured"] is False
    assert contract["query_enabled_by_default"] is False
    assert contract["environmental_conclusion"] is None
    assert contract["regulatory_conclusion"] is None


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI optional")
def test_health_is_public_but_query_requires_trusted_identity():
    from fastapi.testclient import TestClient
    from nema_agora.fastapi_spatial_evidence_app import app

    client = TestClient(app)
    health = client.get("/api/v1/spatial-evidence/health")
    assert health.status_code == 200
    assert health.json()["query_access"] == "disabled_until_identity_verifier_is_configured"

    query = client.get(
        "/api/v1/spatial-evidence/query",
        params={
            "request_id": "REQ-84",
            "database_path": "/tmp/attacker-selected.db",
        },
    )
    assert query.status_code == 503
    assert "identity verification is not configured" in query.json()["detail"]
