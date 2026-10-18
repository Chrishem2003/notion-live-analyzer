from nema_agora.api_governance_snapshot import build_snapshot,diff_snapshots
def base(count=1):
 o={"state":"READY_FOR_HUMAN_REVIEW","counts":{"audit_events":count},"control_required_sources":0};h={"state":"HEALTHY","coverage_state":"COMPLETE","finding_count":0}
 return build_snapshot(observatory=o,health=h,captured_at="2026-10-04T12:00:00+00:00")
def test_snapshot():
 s=base();assert s["snapshot_id"].startswith("API-SNAPSHOT-")
def test_diff():
 a=base();b=base(2);d=diff_snapshots(a,b);assert d["changed"] is True
def test_no_diff():
 a=base();b=base();assert diff_snapshots(a,b)["changed"] is False
