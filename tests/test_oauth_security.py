from modules.oauth_security import verified_google_profile, verified_github_email


def test_google_profile_requires_verified_email():
    profile = verified_google_profile({"email": "person@example.com", "email_verified": False, "sub": "123"})
    assert profile["email"] is None


def test_google_profile_rejects_missing_verification_flag():
    profile = verified_google_profile({"email": "person@example.com", "sub": "123"})
    assert profile["email"] is None


def test_google_profile_normalizes_verified_email():
    profile = verified_google_profile({"email": " Person@Example.com ", "email_verified": True, "name": "Person", "sub": "123"})
    assert profile == {"email": "person@example.com", "name": "Person", "provider_id": "123"}


def test_github_email_requires_primary_and_verified():
    entries = [
        {"email": "unverified@example.com", "primary": True, "verified": False},
        {"email": "secondary@example.com", "primary": False, "verified": True},
        {"email": " Primary@Example.com ", "primary": True, "verified": True},
    ]
    assert verified_github_email(entries) == "primary@example.com"


def test_github_email_rejects_unverified_or_missing_entries():
    assert verified_github_email([{"email": "x@example.com", "primary": True, "verified": False}]) is None
    assert verified_github_email(None) is None
