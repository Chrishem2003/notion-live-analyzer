from unittest.mock import Mock, patch
import pytest
from nema_agora.client import NemaApiError, get_case, list_cases

@patch.dict("os.environ", {"NEMA_CASE_API_BASE_URL": "https://api.example.test", "PLATFORM_API_KEY": "test-secret", "NEMA_PORTAL_SIGNING_SECRET": "test-signing-secret-with-at-least-32-characters"})
@patch("nema_agora.client.requests.get")
def test_list_cases_uses_server_side_auth_and_bounded_timeout(mock_get):
    response = Mock()
    response.ok = True
    response.status_code = 200
    response.json.return_value = {"items": [], "count": 0, "mode": "read_only"}
    mock_get.return_value = response
    result = list_cases("https://issuer.example|reviewer-1", "reviewer", limit=25)
    assert result["mode"] == "read_only"
    kwargs = mock_get.call_args.kwargs
    assert kwargs["headers"]["X-API-Key"] == "test-secret"
    assert kwargs["timeout"] == (3.05, 12)
    assert "test-secret" not in repr(result)

@patch.dict("os.environ", {"NEMA_CASE_API_BASE_URL": "https://api.example.test", "PLATFORM_API_KEY": "test-secret", "NEMA_PORTAL_SIGNING_SECRET": "test-signing-secret-with-at-least-32-characters"})
@patch("nema_agora.client.requests.get")
def test_unauthorized_response_has_safe_message(mock_get):
    response = Mock()
    response.status_code = 401
    response.ok = False
    mock_get.return_value = response
    with pytest.raises(NemaApiError, match="same PLATFORM_API_KEY"):
        get_case("case-1", "https://issuer.example|reviewer-1", "reviewer")

@patch.dict("os.environ", {"NEMA_CASE_API_BASE_URL": "http://insecure.example.test", "PLATFORM_API_KEY": "test-secret", "NEMA_PORTAL_SIGNING_SECRET": "test-signing-secret-with-at-least-32-characters"})
def test_rejects_non_https_api_url():
    with pytest.raises(NemaApiError, match="HTTPS"):
        list_cases("https://issuer.example|reviewer-1", "reviewer")

def test_list_limit_is_bounded():
    with pytest.raises(ValueError):
        list_cases(limit=1001)

def test_case_id_is_validated_before_request():
    with pytest.raises(ValueError):
        get_case("  ", "https://issuer.example|reviewer-1", "reviewer")


@patch.dict("os.environ", {"NEMA_CASE_API_BASE_URL": "https://api.example.test", "PLATFORM_API_KEY": "test-secret"}, clear=True)
def test_client_fails_closed_without_separate_identity_signing_secret():
    with pytest.raises(NemaApiError, match="signing is not configured"):
        list_cases("https://issuer.example|reviewer-1", "reviewer")


@patch.dict("os.environ", {
    "NEMA_CASE_API_BASE_URL": "https://api.example.test",
    "PLATFORM_API_KEY": "reused-secret",
    "NEMA_PORTAL_SIGNING_SECRET": "reused-secret",
}, clear=True)
def test_client_rejects_reused_api_and_signing_secret():
    with pytest.raises(NemaApiError, match="separate secret"):
        list_cases("https://issuer.example|reviewer-1", "reviewer")


@patch.dict("os.environ", {"PLATFORM_API_KEY": "test-secret", "NEMA_PORTAL_SIGNING_SECRET": "test-signing-secret-with-at-least-32-characters"}, clear=True)
def test_client_requires_explicit_api_base_url_and_never_defaults_to_production():
    with pytest.raises(NemaApiError, match="will not fall back to a production API"):
        list_cases("https://issuer.example|reviewer-1", "reviewer")


def test_connection_diagnostics_report_missing_secrets_without_revealing_values():
    from nema_agora.client import get_connection_diagnostics

    with patch.dict("os.environ", {
        "NEMA_CASE_API_BASE_URL": "https://api.example.test",
    }, clear=True), patch("nema_agora.client.requests.get") as mock_get:
        response = Mock()
        response.status_code = 200
        mock_get.return_value = response
        result = get_connection_diagnostics()

    assert result == {
        "api_base_url_configured": True,
        "platform_api_key_configured": False,
        "portal_signing_secret_valid": False,
        "api_health": "reachable",
        "api_health_http_status": 200,
    }
    assert "secret" not in repr(result).lower()
    mock_get.assert_called_once_with(
        "https://api.example.test/api/v1/health", timeout=(2.0, 5.0)
    )


def test_connection_diagnostics_never_probes_an_unconfigured_api_url():
    from nema_agora.client import get_connection_diagnostics

    with patch.dict("os.environ", {}, clear=True), patch("nema_agora.client.requests.get") as mock_get:
        result = get_connection_diagnostics()

    assert result["api_base_url_configured"] is False
    assert result["api_health"] == "not_checked_invalid_or_missing_url"
    mock_get.assert_not_called()


def test_connection_diagnostics_marks_api_unreachable_without_exposing_exception():
    from requests import ConnectionError
    from nema_agora.client import get_connection_diagnostics

    with patch.dict("os.environ", {
        "NEMA_CASE_API_BASE_URL": "https://api.example.test",
        "PLATFORM_API_KEY": "never-return-this",
        "NEMA_PORTAL_SIGNING_SECRET": "a-distinct-signing-secret-with-at-least-32-chars",
    }, clear=True), patch("nema_agora.client.requests.get", side_effect=ConnectionError("never-return-this")):
        result = get_connection_diagnostics()

    assert result["api_health"] == "unreachable"
    assert "never-return-this" not in repr(result)
