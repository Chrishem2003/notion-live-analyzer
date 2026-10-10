from __future__ import annotations
import unittest
from nema_agora.aoi_registry import build_asset
from nema_agora.gee_boundary import execute_scene_request, validate_scene_request

def asset():
    return build_asset("wetland-demo-01", "Synthetic test wetland", "WETLAND",
        {"type": "Polygon", "coordinates": [[[32.0, 1.0], [32.1, 1.0], [32.1, 1.1],
         [32.0, 1.1], [32.0, 1.0]]]}, "synthetic_test_fixture", "fixture://wetland-demo-01")

class FakeProvider:
    def __init__(self, scenes): self.scenes = scenes
    def list_scenes(self, request): return self.scenes

class FailingProvider:
    def list_scenes(self, request): raise RuntimeError("secret provider detail")

class TestGeeBoundary(unittest.TestCase):
    def test_valid_request_only_validates(self):
        r = validate_scene_request(asset(), "2026-01-01", "2026-02-01")
        self.assertEqual(r["state"], "REQUEST_VALIDATED")
        self.assertEqual(r["request"]["collection_id"], "COPERNICUS/S2_SR_HARMONIZED")
    def test_unconfigured_credentials_fail_closed(self):
        r = execute_scene_request(validate_scene_request(asset(), "2026-01-01", "2026-02-01"),
                                  provider=FakeProvider([]))
        self.assertEqual(r["state"], "PROVIDER_NOT_CONFIGURED")
        self.assertEqual(r["scenes"], [])
    def test_unvalidated_request_cannot_execute(self):
        r = execute_scene_request({"state": "CONTROL_REQUIRED"}, provider=FakeProvider([]),
                                  credentials_configured=True)
        self.assertEqual(r["state"], "CONTROL_REQUIRED")
    def test_missing_provider_fails_closed(self):
        r = execute_scene_request(validate_scene_request(asset(), "2026-01-01", "2026-02-01"),
                                  provider=None, credentials_configured=True)
        self.assertEqual(r["state"], "PROVIDER_NOT_CONFIGURED")
    def test_reversed_dates_rejected(self):
        r = validate_scene_request(asset(), "2026-02-01", "2026-01-01")
        self.assertIn("DATE_RANGE_REVERSED", {f["code"] for f in r["findings"]})
    def test_over_90_day_window_rejected(self):
        r = validate_scene_request(asset(), "2026-01-01", "2026-04-05")
        self.assertIn("DATE_WINDOW_TOO_LARGE", {f["code"] for f in r["findings"]})
    def test_invalid_date_rejected(self):
        r = validate_scene_request(asset(), "2026-02-30", "2026-03-01")
        self.assertIn("INVALID_START_DATE", {f["code"] for f in r["findings"]})
    def test_unknown_collection_rejected(self):
        r = validate_scene_request(asset(), "2026-01-01", "2026-02-01", collection="fake/collection")
        self.assertIn("COLLECTION_NOT_ALLOWLISTED", {f["code"] for f in r["findings"]})
    def test_invalid_cloud_threshold_rejected(self):
        r = validate_scene_request(asset(), "2026-01-01", "2026-02-01", cloud_max=101)
        self.assertIn("INVALID_CLOUD_THRESHOLD", {f["code"] for f in r["findings"]})
    def test_bad_geometry_rejected(self):
        a = dict(asset()); a["geometry"] = {"type": "Polygon", "coordinates": [[[999, 1], [1, 1], [1, 2], [999, 1]]]}
        r = validate_scene_request(a, "2026-01-01", "2026-02-01")
        self.assertIn("INVALID_GEOJSON_GEOMETRY", {f["code"] for f in r["findings"]})
    def test_provider_error_sanitized(self):
        r = execute_scene_request(validate_scene_request(asset(), "2026-01-01", "2026-02-01"),
                                  provider=FailingProvider(), credentials_configured=True)
        self.assertEqual(r["state"], "PROVIDER_ERROR")
        self.assertEqual(r["findings"], [{"code": "SCENE_PROVIDER_FAILED"}])
    def test_scenes_filtered_and_sorted(self):
        req = validate_scene_request(asset(), "2026-01-01", "2026-02-01", cloud_max=20)
        scenes = [{"scene_id":"S2-B","acquired_date":"2026-01-20","cloud_percent":10},
                  {"scene_id":"S2-CLOUDY","acquired_date":"2026-01-10","cloud_percent":70},
                  {"scene_id":"S2-A","acquired_date":"2026-01-10","cloud_percent":5}]
        r = execute_scene_request(req, provider=FakeProvider(scenes), credentials_configured=True)
        self.assertEqual(r["state"], "PROVIDER_QUERY_COMPLETE")
        self.assertEqual([s["scene_id"] for s in r["scenes"]], ["S2-A", "S2-B"])
    def test_duplicate_scene_ids_rejected(self):
        req = validate_scene_request(asset(), "2026-01-01", "2026-02-01")
        scene = {"scene_id":"S2-A","acquired_date":"2026-01-10","cloud_percent":5}
        r = execute_scene_request(req, provider=FakeProvider([scene, scene]), credentials_configured=True)
        self.assertEqual(r["state"], "PROVIDER_ERROR"); self.assertEqual(r["scenes"], [])
    def test_out_of_window_scene_rejected(self):
        req = validate_scene_request(asset(), "2026-01-01", "2026-02-01")
        r = execute_scene_request(req, provider=FakeProvider([{"scene_id":"S2-X","acquired_date":"2026-02-01","cloud_percent":5}]),
                                  credentials_configured=True)
        self.assertEqual(r["state"], "PROVIDER_ERROR")
    def test_bad_provider_shape_rejected(self):
        req = validate_scene_request(asset(), "2026-01-01", "2026-02-01")
        r = execute_scene_request(req, provider=FakeProvider({"not":"a list"}), credentials_configured=True)
        self.assertEqual(r["state"], "PROVIDER_ERROR")
    def test_metadata_not_compliance_determination(self):
        req = validate_scene_request(asset(), "2026-01-01", "2026-02-01")
        r = execute_scene_request(req, provider=FakeProvider([{"scene_id":"S2-A","acquired_date":"2026-01-10","cloud_percent":5}]),
                                  credentials_configured=True)
        self.assertIn("not a compliance finding", r["evidence_note"])

if __name__ == "__main__":
    unittest.main()
