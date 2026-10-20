"""Phase 27 award/demo evidence pack.

Builds a session-only end-to-end demonstration artifact from the synthetic
dataset. It is separate from persistent pilot evidence.
"""
from __future__ import annotations

from typing import Any

from nema_agora.copilot import build_reviewer_copilot
from nema_agora.demo import build_demo_dataset, validate_demo_dataset
from nema_agora.intelligence import analyze_observation
from nema_agora.provenance import fingerprint
from nema_agora.quality import assess_observation
from nema_agora.reproducibility import build_manifest, manifest_fingerprint

POLICY_VERSION = "phase27-v1"


def build_demo_evidence_pack(*, git_revision: str, version: str = "demo-v1") -> dict[str, Any]:
    """Run the demonstration chain without writing to persistent storage."""
    if not str(git_revision).strip():
        raise ValueError("An explicit Git revision is required.")
    demo = build_demo_dataset(version=version)
    validation = validate_demo_dataset(demo)
    if not validation["valid"]:
        raise ValueError("Synthetic demonstration dataset failed validation.")

    results = []
    for record in demo.records:
        peers = [item for item in demo.records if item.get("case_id") != record.get("case_id")]
        quality = assess_observation(record, peer_records=peers)
        analysis = analyze_observation(record, peer_records=peers)
        copilot = build_reviewer_copilot(record, analysis)
        results.append({
            "case_id": record["case_id"],
            "quality": quality,
            "analysis": analysis,
            "reviewer_copilot": copilot,
        })

    dataset_hash = fingerprint(demo.records)
    manifest = build_manifest(
        git_revision=git_revision,
        policy_versions={"demo": POLICY_VERSION},
        dataset_bindings={demo.version: dataset_hash},
        configuration={"mode": "demo", "persistent": False, "official_integration_enabled": False},
        dependencies={"pipeline": "quality+intelligence+copilot"},
        manifest_id=f"DEMO-MANIFEST-{fingerprint({'version': version, 'git_revision': git_revision})[:16]}",
        generated_at="2026-01-01T00:00:00+00:00",
    )
    evidence = {
        "stage_order": [
            "OBSERVATION", "QUALITY", "INTELLIGENCE",
            "HUMAN_REVIEW_SUPPORT", "PROVENANCE_FINGERPRINT", "REPRODUCIBILITY",
        ],
        "dataset": {
            "dataset_id": demo.dataset_id,
            "version": demo.version,
            "synthetic": demo.synthetic,
            "persistent": demo.persistent,
            "fingerprint": dataset_hash,
        },
        "records": results,
        "reproducibility": {
            "manifest": manifest.to_dict(),
            "manifest_fingerprint": manifest_fingerprint(manifest),
        },
        "safety": {
            "persistent_state_written": False,
            "official_integration_enabled": False,
            "autonomous_decision_making": False,
            "notice": demo.safety_notice,
        },
    }
    evidence["evidence_fingerprint"] = fingerprint(evidence)
    return evidence
