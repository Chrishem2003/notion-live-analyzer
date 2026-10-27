"""Server-side Supabase Storage adapter for immutable NEMA evidence artifacts.

This module is not wired to an HTTP route. It uploads only after the caller has
authenticated and authorized the actor, and it never stores user-provided paths.
The object key is derived from a validated digest so retries are deterministic.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
from typing import Any
from urllib.parse import quote, urlparse

import requests


class EvidenceStorageError(RuntimeError):
    """Raised when an evidence artifact cannot be safely persisted."""


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_BUCKET_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,62}$")


class SupabaseEvidenceObjectStore:
    """Minimal server-side upload adapter for private Supabase Storage buckets."""

    def __init__(self, *, session: Any | None = None, timeout: float = 10.0) -> None:
        base_url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
        service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        bucket = os.environ.get("NEMA_EVIDENCE_BUCKET", "").strip()
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise EvidenceStorageError("Evidence storage requires a configured HTTPS Supabase URL.")
        if not service_key:
            raise EvidenceStorageError("Evidence storage server credentials are not configured.")
        if not _BUCKET_RE.fullmatch(bucket):
            raise EvidenceStorageError("Evidence storage bucket name is missing or invalid.")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 60:
            raise EvidenceStorageError("Evidence storage timeout must be between 0 and 60 seconds.")
        self._base_url = base_url
        self._bucket = bucket
        self._timeout = float(timeout)
        self._session = session or requests.Session()
        self._session.headers.update({
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/octet-stream",
            "x-upsert": "false",
            "cache-control": "no-store",
        })

    def close(self) -> None:
        close = getattr(self._session, "close", None)
        if callable(close):
            close()

    def _object_url(self, object_key: str) -> str:
        return (
            f"{self._base_url}/storage/v1/object/"
            f"{quote(self._bucket, safe='')}/{quote(object_key, safe='/')}"
        )

    def get_verified_artifact(self, *, object_key: str, expected_sha256: str) -> bytes:
        """Read a stored artifact and return bytes only when the digest matches."""
        if not isinstance(expected_sha256, str) or not _SHA256_RE.fullmatch(expected_sha256):
            raise EvidenceStorageError("Evidence SHA-256 must be a lowercase 64-character digest.")
        if not isinstance(object_key, str) or object_key != f"sha256/{expected_sha256[:2]}/{expected_sha256}":
            raise EvidenceStorageError("Evidence object key must match its content digest.")
        try:
            response = self._session.get(self._object_url(object_key), timeout=self._timeout)
            response.raise_for_status()
            stored_content = response.content
        except (requests.RequestException, ValueError, TypeError, AttributeError) as exc:
            raise EvidenceStorageError("Evidence artifact read-back failed.") from exc
        if not isinstance(stored_content, bytes):
            raise EvidenceStorageError("Evidence storage returned a non-byte artifact.")
        actual = hashlib.sha256(stored_content).hexdigest()
        if not hmac.compare_digest(actual, expected_sha256):
            raise EvidenceStorageError("Stored evidence digest does not match the expected SHA-256.")
        return stored_content

    def put_verified_artifact(self, *, content: bytes, expected_sha256: str) -> dict[str, str]:
        """Persist bytes and verify read-back before returning a usable reference."""
        if not isinstance(content, bytes) or not content:
            raise EvidenceStorageError("Evidence content must be non-empty bytes.")
        if not isinstance(expected_sha256, str) or not _SHA256_RE.fullmatch(expected_sha256):
            raise EvidenceStorageError("Evidence SHA-256 must be a lowercase 64-character digest.")
        actual = hashlib.sha256(content).hexdigest()
        if not hmac.compare_digest(actual, expected_sha256):
            raise EvidenceStorageError("Evidence content does not match the declared SHA-256 digest.")
        object_key = f"sha256/{actual[:2]}/{actual}"
        url = self._object_url(object_key)
        try:
            response = self._session.post(
                url,
                data=content,
                headers={"x-upsert": "false", "x-metadata": '{"sha256":"' + actual + '"}'},
                timeout=self._timeout,
            )
            if response.status_code == 409:
                # Idempotent retries are accepted only after the pre-existing bytes verify.
                self.get_verified_artifact(object_key=object_key, expected_sha256=actual)
            else:
                response.raise_for_status()
                self.get_verified_artifact(object_key=object_key, expected_sha256=actual)
        except EvidenceStorageError:
            raise
        except (requests.RequestException, ValueError, TypeError, AttributeError) as exc:
            raise EvidenceStorageError("Evidence artifact upload or read-back failed.") from exc
        return {"bucket": self._bucket, "object_key": object_key, "sha256": actual}
