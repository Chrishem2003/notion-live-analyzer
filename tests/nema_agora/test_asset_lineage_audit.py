import pytest

from nema_agora.asset_lineage_audit import AssetLineageAuditError, audit_asset_lineage


def record(record_id, split, digest, tiles=None, parents=None):
    return {
        "record_id": record_id,
        "split": split,
        "source_asset_sha256": digest,
        "tile_ids": tiles or [],
        "derived_from": parents or [],
    }


def test_disjoint_assets_and_tiles_have_no_declared_reuse():
    report = audit_asset_lineage([
        record("dev-1", "development", "a" * 64, ["tile-dev"]),
        record("hold-1", "holdout", "b" * 64, ["tile-hold"]),
    ])
    assert report["decision"] == "NO_DECLARED_REUSE_FOUND"
    assert report["finding_count"] == 0
    assert len(report["manifest_sha256"]) == 64
    assert report["limitations"]


def test_same_source_asset_across_splits_is_flagged():
    report = audit_asset_lineage([
        record("dev-1", "development", "a" * 64),
        record("hold-1", "holdout", "A" * 64),
    ])
    assert report["decision"] == "REVIEW_AND_BLOCK_UNTIL_RESOLVED"
    assert report["findings"][0]["lineage_kind"] == "source_asset_sha256"


def test_shared_tile_across_splits_is_flagged():
    report = audit_asset_lineage([
        record("dev-1", "development", "a" * 64, ["sentinel-tile-42"]),
        record("hold-1", "holdout", "b" * 64, ["sentinel-tile-42"]),
    ])
    assert any(item["lineage_kind"] == "tile_id" for item in report["findings"])


def test_shared_derived_parent_across_splits_is_flagged():
    report = audit_asset_lineage([
        record("source", "development", "a" * 64),
        record("derived-dev", "development", "b" * 64, parents=["source"]),
        record("derived-hold", "holdout", "c" * 64, parents=["source"]),
    ])
    assert any(item["lineage_kind"] == "derived_parent" for item in report["findings"])


@pytest.mark.parametrize("records", [
    [],
    [record("same", "development", "a" * 64), record("same", "holdout", "b" * 64)],
    [record("bad", "holdout", "not-a-digest")],
    [record("bad", "other", "a" * 64)],
    [record("child", "holdout", "a" * 64, parents=["missing"])],
    [
        record("a", "development", "a" * 64, parents=["b"]),
        record("b", "holdout", "b" * 64, parents=["a"]),
    ],
])
def test_malformed_or_cyclic_lineage_is_rejected(records):
    with pytest.raises(AssetLineageAuditError):
        audit_asset_lineage(records)
