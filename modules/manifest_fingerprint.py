"""Versioned, keyed fingerprints for research-run manifests.

This module is a pure primitive. It does not load, generate, persist, rotate, or
log keys, and it is deliberately not wired into the Notion handoff until the
owner approves tenant scoping, key custody, rotation, and migration semantics.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
from collections.abc import Mapping
from typing import Any

_DOMAIN = b"bio-research-enterprise:manifest-fingerprint:v1\\x00"
_KEY_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_MIN_KEY_BYTES = 32
_PREFIX = "br-hmac-sha256:v1"


class ManifestFingerprintError(ValueError):
    """Raised when a manifest or key cannot be fingerprinted safely."""


def _normalize_json(value: Any, path: str = "$") -> Any:
    """Return a strict JSON value, rejecting ambiguous/non-portable inputs."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ManifestFingerprintError(f"non-finite number at {path}")
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ManifestFingerprintError(f"non-string object key at {path}")
            normalized[key] = _normalize_json(item, f"{path}.{key}")
        return normalized
    if isinstance(value, list):
        return [_normalize_json(item, f"{path}[{index}]") for index, item in enumerate(value)]
    raise ManifestFingerprintError(f"unsupported JSON value at {path}: {type(value).__name__}")


def canonical_manifest_bytes(manifest: Mapping[str, Any]) -> bytes:
    """Serialize a manifest deterministically using the v1 Python JSON contract."""
    if not isinstance(manifest, Mapping):
        raise ManifestFingerprintError("manifest must be a mapping")
    normalized = _normalize_json(manifest)
    try:
        return json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ManifestFingerprintError("manifest cannot be canonically encoded") from exc


def manifest_fingerprint(
    manifest: Mapping[str, Any],
    *,
    key: bytes,
    key_id: str,
) -> str:
    """Return a versioned HMAC-SHA-256 fingerprint; never accept text/weak keys."""
    if not isinstance(key, bytes) or len(key) < _MIN_KEY_BYTES:
        raise ManifestFingerprintError("fingerprint key must be at least 32 bytes")
    if not isinstance(key_id, str) or not _KEY_ID_RE.fullmatch(key_id):
        raise ManifestFingerprintError("key_id must be 1–64 ASCII letters, digits, '.', '_' or '-'")
    message = _DOMAIN + key_id.encode("ascii") + b"\\x00" + canonical_manifest_bytes(manifest)
    digest = hmac.new(key, message, hashlib.sha256).hexdigest()
    return f"{_PREFIX}:{key_id}:{digest}"


def verify_manifest_fingerprint(
    manifest: Mapping[str, Any],
    fingerprint: str,
    *,
    key: bytes,
    key_id: str,
) -> bool:
    """Constant-time comparison against a fingerprint produced with this key ID."""
    if not isinstance(fingerprint, str) or not fingerprint.isascii():
        return False
    expected = manifest_fingerprint(manifest, key=key, key_id=key_id)
    return hmac.compare_digest(expected, fingerprint)
