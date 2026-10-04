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
