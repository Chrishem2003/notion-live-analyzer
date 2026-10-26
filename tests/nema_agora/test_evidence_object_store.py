from __future__ import annotations

import hashlib

import pytest

from nema_agora.evidence_object_store import EvidenceStorageError, SupabaseEvidenceObjectStore


class FakeResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("remote failure")


class FakeSession:
    def __init__(self, status_code=200):
        self.headers = {}
        self.status_code = status_code
        self.calls = []
        self.closed = False

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self.status_code)

    def close(self):
        self.closed = True


def configure(monkeypatch, *, url="https://example.supabase.co", key="server-secret", bucket="nema-evidence"):
    monkeypatch.setenv("SUPABASE_URL", url)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", key)
    monkeypatch.setenv("NEMA_EVIDENCE_BUCKET", bucket)


def test_upload_uses_digest_derived_key_and_no_overwrite(monkeypatch):
    configure(monkeypatch)
    session = FakeSession()
    store = SupabaseEvidenceObjectStore(session=session)
    content = b"verified field artifact"
    digest = hashlib.sha256(content).hexdigest()

    result = store.put_verified_artifact(content=content, expected_sha256=digest)

    assert result == {
        "bucket": "nema-evidence",
        "object_key": f"sha256/{digest[:2]}/{digest}",
        "sha256": digest,
    }
    url, kwargs = session.calls[0]
    assert url.endswith(f"/nema-evidence/sha256/{digest[:2]}/{digest}")
    assert kwargs["data"] == content
    assert kwargs["headers"]["x-upsert"] == "false"
    assert kwargs["timeout"] > 0
    assert "server-secret" not in url


def test_digest_mismatch_fails_before_network_call(monkeypatch):
    configure(monkeypatch)
    session = FakeSession()
    store = SupabaseEvidenceObjectStore(session=session)

    with pytest.raises(EvidenceStorageError, match="does not match"):
        store.put_verified_artifact(content=b"artifact", expected_sha256="0" * 64)

    assert session.calls == []


@pytest.mark.parametrize("content,digest", [(b"", hashlib.sha256(b"").hexdigest()), (b"abc", "ABC"), (b"abc", "short")])
def test_invalid_artifact_or_digest_fails_closed(monkeypatch, content, digest):
    configure(monkeypatch)
    session = FakeSession()
    store = SupabaseEvidenceObjectStore(session=session)

    with pytest.raises(EvidenceStorageError):
        store.put_verified_artifact(content=content, expected_sha256=digest)

    assert session.calls == []


def test_storage_configuration_requires_https_and_private_bucket_name(monkeypatch):
    configure(monkeypatch, url="http://example.supabase.co")
    with pytest.raises(EvidenceStorageError, match="HTTPS"):
        SupabaseEvidenceObjectStore(session=FakeSession())

    configure(monkeypatch, bucket="../public")
    with pytest.raises(EvidenceStorageError, match="bucket"):
        SupabaseEvidenceObjectStore(session=FakeSession())


def test_existing_content_addressed_object_is_not_silently_trusted(monkeypatch):
    configure(monkeypatch)
    session = FakeSession(status_code=409)
    store = SupabaseEvidenceObjectStore(session=session)
    content = b"artifact"

    with pytest.raises(EvidenceStorageError, match="verify stored bytes"):
        store.put_verified_artifact(
            content=content,
            expected_sha256=hashlib.sha256(content).hexdigest(),
        )
