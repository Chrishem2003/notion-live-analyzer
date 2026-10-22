"""Deployment and reproducibility controls for NEMA-AGORA.

Manifests identify the code, policy, dataset bindings and non-secret runtime
configuration used for a run. They are engineering evidence, not environmental
truth, regulatory authorization, NEMA endorsement or production approval.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
import platform
import subprocess
import sys
from typing import Any, Mapping

POLICY_VERSION = "phase25-v1"
REQUIRED_KEYS = (
    "application", "git_revision", "python_version", "platform",
    "policy_versions", "dataset_bindings", "configuration_fingerprint",
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
    revision = str(git_revision or "").strip()
    if not revision or revision.upper() == "UNKNOWN":
        raise ValueError("git_revision must be explicit")
    config = dict(configuration or {})
    return ReproducibilityManifest(
        manifest_id=manifest_id or f"REPRO-{fingerprint([revision, config])[:12].upper()}",
        generated_at=generated_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
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
    revision_unknown = str(manifest.git_revision).strip().upper() == "UNKNOWN"
    secrets_included = manifest.secret_values_included is not False
    return {
        "valid": not missing and not revision_unknown and not secrets_included,
        "missing": missing,
        "secret_values_included": manifest.secret_values_included,
        "policy_version": POLICY_VERSION,
    }

def manifest_fingerprint(manifest: ReproducibilityManifest) -> str:
    return fingerprint(manifest.to_dict())

def current_git_revision() -> str:
    """Resolve a deployment revision from trusted host metadata or Git."""
    for key in ("GITHUB_SHA", "SOURCE_VERSION", "COMMIT_SHA"):
        value = os.getenv(key, "").strip()
        if value and value.upper() != "UNKNOWN":
            return value
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True, timeout=2,
        )
        value = result.stdout.strip()
        if value and value.upper() != "UNKNOWN":
            return value
    except (OSError, subprocess.SubprocessError):
        pass
    return ""

def build_runtime_manifest(
    *,
    policy_versions: Mapping[str, str] | None = None,
    dataset_bindings: Mapping[str, str] | None = None,
    configuration: Mapping[str, Any] | None = None,
    dependencies: Mapping[str, str] | None = None,
) -> ReproducibilityManifest:
    """Build only when the deployment revision can be established reliably."""
    revision = current_git_revision()
    if not revision:
        raise RuntimeError(
            "Deployment Git revision is unavailable; refusing to fabricate deployment identity"
        )
    return build_manifest(
        git_revision=revision,
        policy_versions=policy_versions,
        dataset_bindings=dataset_bindings,
        configuration=configuration,
        dependencies=dependencies,
    )
