from nema_agora.auth import is_logged_in, principal_from_streamlit_user, role_bindings_from_secrets

ISSUER = "https://accounts.example.test"
SUBJECT = "oidc-user-123"
KEY = f"{ISSUER}|{SUBJECT}"

class FakeUser:
    is_logged_in = True
    def to_dict(self):
        return {"iss": ISSUER, "sub": SUBJECT, "email": "person@example.test"}

def test_secret_role_bindings_are_normalised():
    bindings = role_bindings_from_secrets({"nema_agora": {"role_bindings": {f" {KEY} ": " REVIEWER "}}})
    assert bindings == {KEY: "reviewer"}

def test_missing_secret_section_fails_closed():
    assert role_bindings_from_secrets({}) == {}

def test_streamlit_user_maps_to_server_side_role():
    principal = principal_from_streamlit_user(FakeUser(), {"nema_agora": {"role_bindings": {KEY: "reviewer"}}})
    assert principal is not None
    assert principal.subject_key == KEY
    assert principal.role == "reviewer"

def test_user_without_binding_is_not_authorised():
    principal = principal_from_streamlit_user(FakeUser(), {"nema_agora": {"role_bindings": {}}})
    assert principal is not None
    assert principal.role is None
    assert not principal.is_authorised

def test_unconfigured_user_is_not_logged_in():
    class LocalUser: pass
    assert not is_logged_in(LocalUser())
    assert principal_from_streamlit_user(LocalUser(), {}) is None



def test_resolve_principal_uses_server_side_role_bindings():
    from nema_agora.auth import resolve_principal

    class FakeStreamlit:
        user = FakeUser()
        secrets = {"nema_agora": {"role_bindings": {KEY: "reviewer"}}}

    principal = resolve_principal(FakeStreamlit())
    assert principal is not None
    assert principal.is_authorised
    assert principal.role == "reviewer"


def test_resolve_principal_fails_closed_without_user_or_secrets():
    from nema_agora.auth import resolve_principal

    class UnconfiguredStreamlit:
        pass

    assert resolve_principal(UnconfiguredStreamlit()) is None

    class InvalidSecretsStreamlit:
        user = FakeUser()
        secrets = None

    assert resolve_principal(InvalidSecretsStreamlit()) is None


def test_resolve_principal_fails_closed_when_identity_sdk_raises_unexpected_error():
    from nema_agora.auth import resolve_principal

    class BrokenUser:
        is_logged_in = True

        def to_dict(self):
            raise RuntimeError("identity SDK unavailable")

    class BrokenStreamlit:
        user = BrokenUser()
        secrets = {"nema_agora": {"role_bindings": {KEY: "admin"}}}

    assert resolve_principal(BrokenStreamlit()) is None


def test_resolve_principal_fails_closed_when_login_state_accessor_raises():
    from nema_agora.auth import resolve_principal

    class BrokenUser:
        @property
        def is_logged_in(self):
            raise RuntimeError("session state unavailable")

    class BrokenStreamlit:
        user = BrokenUser()
        secrets = {"nema_agora": {"role_bindings": {KEY: "admin"}}}

    assert resolve_principal(BrokenStreamlit()) is None


def test_claimed_privilege_fields_never_override_server_role_binding():
    principal = principal_from_streamlit_user(
        type("ClaimedAdmin", (), {
            "is_logged_in": True,
            "to_dict": lambda self: {
                "iss": ISSUER, "sub": SUBJECT, "role": "admin",
                "groups": ["admin"], "is_admin": True,
            },
        })(),
        {"nema_agora": {"role_bindings": {KEY: "submitter"}}},
    )
    assert principal is not None
    assert principal.role == "submitter"
    assert not principal.is_authorised is False
