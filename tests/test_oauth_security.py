from modules.oauth_security import verified_google_profile


def test_google_profile_requires_verified_email():
    profile = verified_google_profile({"email": "person@example.com", "email_verified": False, "sub": "123"})
    assert profile["email"] is None


def test_google_profile_rejects_missing_verification_flag():
    profile = verified_google_profile({"email": "person@example.com", "sub": "123"})
    assert profile["email"] is None


def test_google_profile_normalizes_verified_email():
    profile = verified_google_profile({"email": " Person@Example.com ", "email_verified": True, "name": "Person", "sub": "123"})
    assert profile == {"email": "person@example.com", "name": "Person", "provider_id": "123"}
