"""Phase 57 — NEMA-AGORA Sentinel-2 remote-sensing adapter contract."""
from __future__ import annotations
import datetime as dt
import hashlib, json, math, re
from typing import Any, Mapping

POLICY_VERSION = "phase57-v1"
PROVIDER = "sentinel-2"
_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
REQUIRED_BANDS = {"B02", "B03", "B04", "B08"}

def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()).hexdigest()

def _valid_id(value: Any) -> bool:
    return isinstance(value, str) and bool(_ID_RE.fullmatch(value))

def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False

def validate_bbox(bbox: Any) -> list[dict[str, str]]:
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return [{"code": "INVALID_BBOX"}]
    try:
        west, south, east, north = (float(x) for x in bbox)
    except (TypeError, ValueError):
        return [{"code": "INVALID_BBOX"}]
    if not all(math.isfinite(x) for x in (west, south, east, north)):
        return [{"code": "NON_FINITE_BBOX"}]
    findings=[]
    if not -180 <= west <= 180 or not -180 <= east <= 180:
        findings.append({"code":"BBOX_LONGITUDE_OUT_OF_RANGE"})
    if not -90 <= south <= 90 or not -90 <= north <= 90:
        findings.append({"code":"BBOX_LATITUDE_OUT_OF_RANGE"})
    if west > east:
        findings.append({"code":"BBOX_WEST_AFTER_EAST"})
    if south > north:
        findings.append({"code":"BBOX_SOUTH_AFTER_NORTH"})
    return findings

def validate_sentinel2_scene(scene: Mapping[str, Any]) -> dict[str, Any]:
    findings=[]
    for field in ("scene_id","product_id"):
        if not _valid_id(scene.get(field)):
            findings.append({"code":f"INVALID_{field.upper()}"})
    if scene.get("collection") not in {"S2MSI_L1C","S2MSI_L2A"}:
        findings.append({"code":"INVALID_COLLECTION"})
    if not _valid_timestamp(scene.get("acquired_at")):
        findings.append({"code":"INVALID_ACQUISITION_TIMESTAMP"})
    if scene.get("crs") != "EPSG:4326":
        findings.append({"code":"UNSUPPORTED_CRS"})
    findings.extend(validate_bbox(scene.get("bbox")))
    cloud=scene.get("cloud_cover_pct")
    if isinstance(cloud,bool) or not isinstance(cloud,(int,float)) or not math.isfinite(float(cloud)):
        findings.append({"code":"INVALID_CLOUD_COVER"})
    elif not 0 <= float(cloud) <= 100:
        findings.append({"code":"CLOUD_COVER_OUT_OF_RANGE"})
    bands=scene.get("bands")
    if not isinstance(bands,list) or not REQUIRED_BANDS.issubset(set(str(x) for x in bands)):
        findings.append({"code":"REQUIRED_BANDS_MISSING"})
    if not isinstance(scene.get("provider"),str) or not scene.get("provider").strip():
        findings.append({"code":"MISSING_PROVIDER"})
    return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED" if findings else "VALID","findings":findings,"scene_fingerprint":fingerprint(dict(scene))}

def sentinel2_scene(scene_id:str, product_id:str, acquired_at:str, cloud_cover_pct:float, bbox:list[float], *, collection:str="S2MSI_L2A", bands:tuple[str,...]=("B02","B03","B04","B08"), provider:str="sentinel-2") -> dict[str,Any]:
    row={"scene_id":scene_id,"product_id":product_id,"provider":provider,"collection":collection,"acquired_at":acquired_at,"cloud_cover_pct":cloud_cover_pct,"bbox":list(bbox),"crs":"EPSG:4326","bands":list(bands)}
    result=validate_sentinel2_scene(row)
    if result["state"]!="VALID":
        raise ValueError("Invalid Sentinel-2 scene: "+json.dumps(result["findings"],sort_keys=True))
    return row

class Sentinel2Provider:
    """Adapter boundary for Sentinel-2 providers; live credentials/network are not required by this phase."""
    provider_name=PROVIDER
    def fetch_scene(self, scene_id:str, area_of_interest:Mapping[str,Any]) -> Mapping[str,Any]:
        raise NotImplementedError("Concrete Sentinel-2 providers must implement fetch_scene().")

def remote_sensing_evidence(scene:Mapping[str,Any], *, analysis_type:str="imagery_source") -> dict[str,Any]:
    validation=validate_sentinel2_scene(scene)
    if validation["state"]!="VALID":
        return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED","findings":validation["findings"]}
    return {"policy_version":POLICY_VERSION,"state":"VALID","provider":scene["provider"],"analysis_type":analysis_type,"source_ids":[scene["scene_id"]],"evidence":{"collection":scene["collection"],"acquired_at":scene["acquired_at"],"cloud_cover_pct":scene["cloud_cover_pct"],"bands":scene["bands"],"bbox":scene["bbox"]},"confidence":None,"metadata":{"scene_fingerprint":validation["scene_fingerprint"],"quality_gate":"metadata_validated"}}
