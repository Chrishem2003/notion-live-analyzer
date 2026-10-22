"""Security contract tests for OIDC claim-to-principal mapping.

These tests do not validate OIDC tokens; they verify that the app maps only
already-authenticated claims and trusted server-side role bindings to roles.
"""
import pytest

from nema_agora.identity import principal_from_claims, subject_key


def test_subject_key_is_namespaced_by_issuer_and_rejects_blank_values():
    assert subject_key(" https://issuer-a ", " user-1 ") == "https://issuer-a|user-1"
    assert subject_key("https://issuer-a", "user-1") != subject_key("https://issuer-b", "user-1")
    with pytest.raises(ValueError):
        subject_key(" ", "user-1")
    with pytest.raises(ValueError):
        subject_key("https://issuer-a", " ")


def test_trusted_role_binding_grants_only_the_configured_role():
    claims = {
        "iss": "https://issuer.example",
        "sub": "user-123",
        "email": "user@example.test",
        "name": "Synthetic User",
        "role": "admin",
        "groups": ["admins"],
        "is_admin": True,
    }
    principal = principal_from_claims(
        is_logged_in=True,
        claims=claims,
        role_bindings={"https://issuer.example|user-123": "reviewer"},
    )
    assert principal is not None
    assert principal.subject_key == "https://issuer.example|user-123"
    assert principal.role == "reviewer"
    assert principal.is_authorised is True
    assert principal.email == "user@example.test"
    assert principal.display_name == "Synthetic User"


def test_claims_cannot_self_assign_privileged_role():
    principal = principal_from_claims(
        is_logged_in=True,
        claims={"iss": "https://issuer.example", "sub": "user-123", "role": "admin"},
        role_bindings={},
    )
    assert principal is not None
    assert principal.role is None
    assert principal.is_authorised is False


@pytest.mark.parametrize(
    "logged_in,claims",
    [
        (False, {"iss": "https://issuer.example", "sub": "user-123"}),
        (True, None),
        (True, []),
        (True, {"iss": "", "sub": "user-123"}),
        (True, {"iss": "https://issuer.example", "sub": " "}),
        (True, {"iss": 12, "sub": "user-123"}),
        (True, {"iss": "https://issuer.example"}),
    ],
)
def test_invalid_or_unauthenticated_claims_do_not_create_principal(logged_in, claims):
    assert principal_from_claims(
        is_logged_in=logged_in,
        claims=claims,
        role_bindings={"https://issuer.example|user-123": "admin"},
    ) is None


@pytest.mark.parametrize("binding", ["root", "unknown-role", "", None, 7])
def test_unknown_or_malformed_role_binding_fails_closed(binding):
    principal = principal_from_claims(
        is_logged_in=True,
        claims={"iss": "https://issuer.example", "sub": "user-123"},
        role_bindings={"https://issuer.example|user-123": binding},
    )
    assert principal is not None
    assert principal.role is None
    assert principal.is_authorised is False


def test_role_binding_is_case_and_whitespace_normalized_but_not_claim_controlled():
    principal = principal_from_claims(
        is_logged_in=True,
        claims={"iss": "https://issuer.example", "sub": "user-123", "role": "admin"},
        role_bindings={"https://issuer.example|user-123": " REVIEWER "},
    )
    assert principal is not None
    assert principal.role == "reviewer"
