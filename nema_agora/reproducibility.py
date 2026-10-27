"""Phase 25/27 reproducibility manifests with explicit no-secret boundaries."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib, json, os, platform, subprocess, sys

POLICY_VERSION="phase25-v1"
REQUIRED_KEYS=("application","git_revision","python_version","platform","policy_versions","dataset_bindings","configuration_fingerprint")

def fingerprint(value):
    payload=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()

@dataclass(frozen=True)
class ReproducibilityManifest:
    manifest_id:str
    generated_at:str
    application:str
    git_revision:str
    python_version:str
    platform:str
    policy_versions:dict
    dataset_bindings:dict
    configuration_fingerprint:str
    dependency_fingerprint:str
    secret_values_included:bool=False
    policy_version:str=POLICY_VERSION
    decision_notice:str="Engineering/research reproducibility evidence only; not environmental truth, NEMA authorization, regulatory status, production approval, or environmental impact."

    def to_dict(self):
        return asdict(self)

def _clean_mapping(value):
    return {str(k): value[k] for k in sorted(value or {})}

def build_manifest(*, git_revision, policy_versions=None, dataset_bindings=None, configuration=None, dependencies=None, manifest_id=None, generated_at=None, application="NEMA-AGORA"):
    revision=str(git_revision or "").strip()
    if not revision or revision.upper()=="UNKNOWN":
        raise ValueError("git_revision must be explicit")
    generated_at=generated_at or datetime.now(timezone.utc).isoformat()
    manifest_id=manifest_id or "MANIFEST-"+fingerprint({"revision":revision,"generated_at":generated_at})[:16]
    policies=_clean_mapping(policy_versions)
    datasets=_clean_mapping(dataset_bindings)
    return ReproducibilityManifest(
        manifest_id=manifest_id, generated_at=generated_at, application=application,
        git_revision=revision, python_version=sys.version.split()[0], platform=platform.platform(),
        policy_versions=policies, dataset_bindings=datasets,
        configuration_fingerprint=fingerprint(_clean_mapping(configuration)),
        dependency_fingerprint=fingerprint(_clean_mapping(dependencies)),
    )

def validate_manifest(manifest):
    data=manifest.to_dict()
    missing=[key for key in REQUIRED_KEYS if not data.get(key)]
    valid=not missing and manifest.secret_values_included is False and manifest.git_revision.strip().upper()!="UNKNOWN"
    return {"valid":valid,"missing":missing,"secrets_included":manifest.secret_values_included}

def manifest_fingerprint(manifest):
    return fingerprint(manifest.to_dict())

def current_git_revision():
    for key in ("GITHUB_SHA","SOURCE_VERSION","COMMIT_SHA"):
        value=os.getenv(key,"").strip()
        if value:
            return value
    try:
        result=subprocess.run(["git","rev-parse","HEAD"],capture_output=True,text=True,check=True,timeout=2)
        value=result.stdout.strip()
        if value:
            return value
    except (OSError, subprocess.SubprocessError):
        pass
    return ""

def build_runtime_manifest(*, policy_versions=None, dataset_bindings=None, configuration=None, dependencies=None):
    revision=current_git_revision()
    if not revision:
        raise RuntimeError("Deployment Git revision is unavailable; refusing to fabricate deployment identity")
    return build_manifest(git_revision=revision,policy_versions=policy_versions,dataset_bindings=dataset_bindings,configuration=configuration,dependencies=dependencies)
