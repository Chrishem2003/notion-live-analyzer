"""Phase 25 — deployment and reproducibility control.

Builds a non-secret deployment manifest so a NEMA-AGORA run can be identified
and reproduced from explicit code, policy, dataset, and runtime metadata.
This is engineering evidence only; it is not production approval, regulatory
authorization, NEMA endorsement, or environmental truth.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
import platform
import sys
from typing import Any, Mapping

POLICY_VERSION = "phase25-v1"
REQUIRED_KEYS = (
    "application",
    "git_revision",
    "python_version",
    "platform",
    "policy_versions",
    "dataset_bindings",
    "configuration_fingerprint",
)

@dataclass(frozen=True)
class ReproducibilityManifest:
    manifest_id: str
    generated_at: str
    application: str
    git_revision: str
    python_version: str
    platform: str
    policy_versions: dict[str, str]
    dataset_bindings: dict[str, str]
    configuration_fingerprint: str
    dependency_fingerprint: str
    secret_values_included: bool = False
    policy_version: str = POLICY_VERSION
    decision_notice: str = (
        "This manifest identifies a deployment for reproducibility. It does not "
        "establish environmental truth, regulatory status, NEMA authorization, "
        "production approval, or environmental impact."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

def fingerprint(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def _clean_mapping(value: Mapping[str, Any] | None) -> dict[str, str]:
    if not value:
        return {}
    return {str(k): str(v) for k, v in value.items()}

def build_manifest(
    *,
    git_revision: str,
    policy_versions: Mapping[str, str] | None = None,
    dataset_bindings: Mapping[str, str] | None = None,
    configuration: Mapping[str, Any] | None = None,
    dependencies: Mapping[str, str] | None = None,
    application: str = "NEMA-AGORA",
    manifest_id: str | None = None,
    generated_at: str | None = None,
) -> ReproducibilityManifest:
    revision = str(git_revision).strip()
    if not revision:
        raise ValueError("git_revision is required")
    config = dict(configuration or {})
    return ReproducibilityManifest(
        manifest_id=manifest_id or f"REPRO-{fingerprint([revision, config])[:12].upper()}",
        generated_at=generated_at or datetime.now().astimezone().isoformat(timespec="seconds"),
        application=application.strip() or "NEMA-AGORA",
        git_revision=revision,
        python_version=sys.version.split()[0],
        platform=f"{platform.system()}-{platform.release()}-{platform.machine()}",
        policy_versions=_clean_mapping(policy_versions),
        dataset_bindings=_clean_mapping(dataset_bindings),
        configuration_fingerprint=fingerprint(config),
        dependency_fingerprint=fingerprint(_clean_mapping(dependencies)),
        secret_values_included=False,
    )

def validate_manifest(manifest: ReproducibilityManifest) -> dict[str, Any]:
    payload = manifest.to_dict()
    missing = [key for key in REQUIRED_KEYS if not payload.get(key)]
    secret_flag = manifest.secret_values_included is not False
    return {
        "valid": not missing and not secret_flag,
        "missing": missing,
        "secret_values_included": manifest.secret_values_included,
        "policy_version": POLICY_VERSION,
    }

def manifest_fingerprint(manifest: ReproducibilityManifest) -> str:
    return fingerprint(manifest.to_dict())
