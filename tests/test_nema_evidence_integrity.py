"""Tests for local evidence asset hashing and path safety."""
import hashlib
import pytest

from nema_agora.evidence_integrity import EvidenceIntegrityError, verify_evidence_assets


def entry(evidence_id, relative_path, payload, digest=None):
    return {"evidence_id": evidence_id, "relative_path": relative_path,
            "sha256": digest or hashlib.sha256(payload).hexdigest()}


def test_hashes_actual_file_bytes_and_reports_match(tmp_path):
    payload = b"field note evidence"
    (tmp_path / "note.txt").write_bytes(payload)
    result = verify_evidence_assets(root_directory=tmp_path,
                                    evidence_assets=[entry("note-1", "note.txt", payload)])
    assert result["decision"] == "HASHES_MATCH"
    assert result["assets"][0]["actual_sha256"] == hashlib.sha256(payload).hexdigest()
    assert result["total_bytes_hashed"] == len(payload)


def test_tampered_file_fails_closed(tmp_path):
    (tmp_path / "note.txt").write_bytes(b"changed")
    result = verify_evidence_assets(root_directory=tmp_path,
        evidence_assets=[{"evidence_id": "note-1", "relative_path": "note.txt", "sha256": "0" * 64}])
    assert result["decision"] == "BLOCK_EVIDENCE_USE"
    assert result["assets"][0]["state"] == "HASH_MISMATCH"


@pytest.mark.parametrize("relative_path", ["../secret.txt", "/etc/passwd", "folder/../secret.txt"])
def test_traversal_and_absolute_paths_rejected(tmp_path, relative_path):
    with pytest.raises(EvidenceIntegrityError, match="unsafe relative_path"):
        verify_evidence_assets(root_directory=tmp_path, evidence_assets=[
            {"evidence_id": "e1", "relative_path": relative_path, "sha256": "0" * 64}])


def test_duplicate_ids_and_paths_rejected(tmp_path):
    (tmp_path / "x").write_bytes(b"x")
    item = entry("e1", "x", b"x")
    with pytest.raises(EvidenceIntegrityError, match="duplicate evidence_id"):
        verify_evidence_assets(root_directory=tmp_path, evidence_assets=[item, dict(item, relative_path="y")])
    with pytest.raises(EvidenceIntegrityError, match="duplicate evidence path"):
        verify_evidence_assets(root_directory=tmp_path, evidence_assets=[item, dict(item, evidence_id="e2")])


def test_symlink_is_rejected(tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("x")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable on this platform")
    with pytest.raises(EvidenceIntegrityError, match="symlink"):
        verify_evidence_assets(root_directory=tmp_path,
            evidence_assets=[{"evidence_id": "e1", "relative_path": "link.txt",
                              "sha256": hashlib.sha256(b"x").hexdigest()}])


def test_size_limit_is_enforced(tmp_path):
    (tmp_path / "large.bin").write_bytes(b"12345")
    with pytest.raises(EvidenceIntegrityError, match="size limit"):
        verify_evidence_assets(root_directory=tmp_path,
            evidence_assets=[{"evidence_id": "e1", "relative_path": "large.bin",
                              "sha256": hashlib.sha256(b"12345").hexdigest()}], max_asset_bytes=4)
