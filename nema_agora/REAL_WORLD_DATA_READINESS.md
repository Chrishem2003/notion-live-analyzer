# NEMA-AGORA Real-World Data Readiness

## Why this exists

The platform must distinguish public information that has been researched from information that has actually been ingested, refreshed, validated, and stored by the application. A link to a government portal is not a data integration. A satellite index delta supplied by a user is not a satellite observation acquired by the platform.

The source catalogue is maintained in `source_registry.py`. Every current source is deliberately marked `reference_only`; automated ingestion is disabled until its technical and governance gates are evidenced.

## Initial grounded sources

| Source | Intended role | Current status |
|---|---|---|
| Uganda National Environment Act, Cap. 181 | Legal and workflow reference | Public reference only; current legal text must be checked |
| NEMA National Environment Research Agenda 2024/25–2028/29 | Research priority alignment | Public reference only |
| NEMA National State of the Environment Report 2024 | Dated national environmental context | Report reference only; not live monitoring |
| Ministry of Water and Environment WEIS / National Wetland Information | Potential wetland inventory and monitoring context | Portal found; machine endpoint, permissions, and terms not verified |
| Copernicus Data Space Ecosystem / Sentinel-2 | Potential satellite image source | Catalogue found; no application acquisition claim |

These sources were identified from public pages. They are not represented as official partners, API integrations, or endorsements of NEMA-AGORA.

## Mandatory gates before a source can be marked connected

1. **Authority and permission:** record the publisher, responsible data owner, licence/terms, permitted use, and any approval required for automated access.
2. **Technical contract:** document the actual API/download mechanism, authentication method, rate limits, schema, pagination, failure responses, and versioning. Do not infer an API from a web portal.
3. **Acquisition receipt:** persist source ID, retrieval time in UTC, requested period/area, response status, dataset/product identifier, version, and checksum.
4. **Spatial and temporal quality:** preserve CRS, resolution, AOI identifier, acquisition times, cloud/valid-pixel fractions where relevant, alignment checks, and uncertainty.
5. **Lineage:** every derived index or alert must reference the exact acquired assets and processing policy version. User-supplied values must remain labelled as user-supplied.
6. **Review boundary:** remote-sensing changes are candidate signals. They cannot independently establish cause, a legal violation, ownership, or an enforcement decision.
7. **Operations:** test retries, timeouts, rate limits, partial downloads, corrupted files, stale data, access denial, and recovery without silently substituting demo data.
8. **Governance:** define retention, access controls, redaction, audit history, human review, and the process for correcting disputed records.

## Suggested first live-data pilot

Start with a small, bounded wetland monitoring study—not a national dashboard claiming comprehensive coverage:

- Choose one authorized pilot area and a documented AOI polygon.
- Obtain or independently download two comparable Sentinel-2 surface-reflectance scenes with documented dates and product IDs.
- Check cloud masking, pixel validity, grid alignment, resolution, and seasonal comparability before comparing NDVI/NDWI.
- Save original assets or stable source references plus checksums and processing configuration.
- Generate a candidate-change report with uncertainty and explicit reasons for review.
- Have a qualified human compare the candidate with field observations and relevant official wetland information.
- Record reviewer decision and reasons; do not generate legal conclusions or automatic enforcement actions.

The first pilot should be considered successful only when another reviewer can reproduce the result from the same source assets, dates, AOI, and policy configuration.

## Deployment gate

No live provider, government system, NEMA workflow, or persistent production storage is claimed until an end-to-end test is run in the target deployment with approved credentials and permissions. Until then, use synthetic records or public reference material and label the source mode honestly.
