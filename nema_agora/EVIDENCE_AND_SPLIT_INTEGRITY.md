# Evidence integrity and spatiotemporal split audit

## Local evidence hash verification

`nema_agora/evidence_integrity.py` hashes actual local file bytes and compares the SHA-256 digest with the supplied manifest. It rejects absolute paths, parent traversal, symlink components, duplicate IDs/paths, missing files, non-regular files and files exceeding the configurable size cap. It never fetches remote URLs.

A hash match is not provenance: it proves only that the local bytes match the supplied digest. The expected digest must come from a trusted independent record to provide meaningful tamper evidence.

## Spatial/temporal separation

`nema_agora/spatiotemporal_audit.py` compares declared WGS84 bounding boxes and timezone-aware observation intervals across different splits. Any intersection is conservatively flagged for review; the result should be treated as a block until resolved.

This is a coarse guard, not a GIS-grade independence proof. It does not check proximity buffers, shared satellite tiles/assets, duplicate derived features, or whether holdout data influenced tuning. Dateline-crossing extents are not accepted. Independent GIS/scientific review remains necessary.
