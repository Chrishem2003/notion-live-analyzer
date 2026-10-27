import pytest

from nema_agora.identity import principal_from_claims, subject_key


ISSUER = "https://accounts.example.test"
SUBJECT = "oidc-user-123"
KEY = f"{ISSUER}|{SUBJECT}"


def test_subject_key_requires_issuer_and_subject():
    assert subject_key(f" {ISSUER} ", f" {SUBJECT} ") == KEY
    with pytest.raises(ValueError):
        subject_key("", SUBJECT)
    with pytest.raises(ValueError):
        subject_key(ISSUER, "  ")


def test_logged_out_user_has_no_principal():
    assert principal_from_claims(
        is_logged_in=False,
        claims={"iss": ISSUER, "sub": SUBJECT},
        role_bindings={KEY: "admin"},
    ) is None


@pytest.mark.parametrize(
    "claims",
    [
        None,
        {},
        {"iss": ISSUER},
        {"sub": SUBJECT},
        {"iss": "", "sub": SUBJECT},
        {"iss": ISSUER, "sub": " "},
    ],
)
def test_missing_identity_claims_fail_closed(claims):
    assert principal_from_claims(
        is_logged_in=True, claims=claims, role_bindings={KEY: "admin"}
    ) is None


def test_server_side_binding_assigns_role_and_stable_subject_key():
    principal = principal_from_claims(
        is_logged_in=True,
        claims={
            "iss": ISSUER,
            "sub": SUBJECT,
            "email": "person@example.test",
            "name": "Example Person",
        },
        role_bindings={KEY: "reviewer"},
    )
    assert principal is not None
    assert principal.subject_key == KEY
    assert principal.role == "reviewer"
    assert principal.is_authorised
    assert principal.email == "person@example.test"


def test_unregistered_user_is_authenticated_but_not_authorised():
    principal = principal_from_claims(
        is_logged_in=True,
        claims={"iss": ISSUER, "sub": SUBJECT, "role": "admin"},
        role_bindings={},
    )
    assert principal is not None
    assert principal.role is None
    assert not principal.is_authorised


def test_untrusted_role_claim_cannot_override_server_side_binding():
    principal = principal_from_claims(
        is_logged_in=True,
        claims={"iss": ISSUER, "sub": SUBJECT, "role": "admin"},
        role_bindings={KEY: "submitter"},
    )
    assert principal is not None
    assert principal.role == "submitter"


def test_unknown_configured_role_fails_closed():
    principal = principal_from_claims(
        is_logged_in=True,
        claims={"iss": ISSUER, "sub": SUBJECT},
        role_bindings={KEY: "superuser"},
    )
    assert principal is not None
    assert principal.role is None
    assert not principal.is_authorised


def test_subject_is_namespaced_by_issuer():
    different_issuer_key = f"https://other.example.test|{SUBJECT}"
    principal = principal_from_claims(
        is_logged_in=True,
        claims={"iss": ISSUER, "sub": SUBJECT},
        role_bindings={different_issuer_key: "admin"},
    )
    assert principal is not None
    assert principal.role is None
