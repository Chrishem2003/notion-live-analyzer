import pytest
from nema_agora.lifecycle_provenance import LifecycleProvenanceRegistry,evaluate_provenance,validate_supersession_chain,fingerprint

def _f(x): return fingerprint(x)
def test_binding_is_append_only_and_validates_snapshot(tmp_path):
    r=LifecycleProvenanceRegistry(tmp_path/"db.sqlite")
    row=r.bind(decision_id="LIFE-1",attestation_id="ATT-1",attester_actor_id="a1",reviewer_actor_id="r1",
               reconciliation_fingerprint=_f("r"),evidence_registry_fingerprint=_f("e"),
               provenance_fingerprint=_f("p"),bound_at="2026-01-01T00:00:00+00:00")
    assert evaluate_provenance(r.list(),[{"decision_id":"LIFE-1","attestation_id":"ATT-1","actor_id":"r1","attester_actor_id":"a1"}],
        [{"attestation_id":"ATT-1"}],reconciliation_fingerprint=_f("r"),evidence_registry_fingerprint=_f("e"),provenance_fingerprint=_f("p"))["valid_count"]==1
    with pytest.raises(Exception): 
        with __import__("sqlite3").connect(tmp_path/"db.sqlite") as db: db.execute("DELETE FROM attestation_lifecycle_provenance")
def test_snapshot_change_stales_binding(tmp_path):
    r=LifecycleProvenanceRegistry(tmp_path/"db.sqlite"); r.bind(decision_id="LIFE-1",attestation_id="ATT-1",attester_actor_id="a1",reviewer_actor_id="r1",
        reconciliation_fingerprint=_f("r"),evidence_registry_fingerprint=_f("e"),provenance_fingerprint=_f("p"),bound_at="t")
    out=evaluate_provenance(r.list(),[{"decision_id":"LIFE-1","attestation_id":"ATT-1","actor_id":"r1","attester_actor_id":"a1"}],[{"attestation_id":"ATT-1"}],
        reconciliation_fingerprint=_f("r"),evidence_registry_fingerprint=_f("changed"),provenance_fingerprint=_f("p"))
    assert out["stale_count"]==1
def test_identity_mismatch_fails_closed(tmp_path):
    r=LifecycleProvenanceRegistry(tmp_path/"db.sqlite"); r.bind(decision_id="LIFE-1",attestation_id="ATT-1",attester_actor_id="a1",reviewer_actor_id="r1",
        reconciliation_fingerprint=_f("r"),evidence_registry_fingerprint=_f("e"),provenance_fingerprint=_f("p"),bound_at="t")
    out=evaluate_provenance(r.list(),[{"decision_id":"LIFE-1","attestation_id":"ATT-1","actor_id":"wrong","attester_actor_id":"a1"}],[{"attestation_id":"ATT-1"}],
        reconciliation_fingerprint=_f("r"),evidence_registry_fingerprint=_f("e"),provenance_fingerprint=_f("p"))
    assert out["failure_count"]==1
def test_supersession_requires_existing_replacement():
    assert validate_supersession_chain([{"binding_id":"b","attestation_id":"ATT-1","superseding_attestation_id":"ATT-2"}],[{"attestation_id":"ATT-1"}])["valid"] is False
    assert validate_supersession_chain([{"binding_id":"b","attestation_id":"ATT-1","superseding_attestation_id":"ATT-2"}],[{"attestation_id":"ATT-1"},{"attestation_id":"ATT-2"}])["valid"] is True
def test_separation_of_duties():
    r=LifecycleProvenanceRegistry(":memory:")
    with pytest.raises(ValueError): r.bind(decision_id="LIFE-1",attestation_id="ATT-1",attester_actor_id="same",reviewer_actor_id="same",
      reconciliation_fingerprint=_f("r"),evidence_registry_fingerprint=_f("e"),provenance_fingerprint=_f("p"),bound_at="t")


def test_duplicate_decision_binding_fails_closed(tmp_path):
    r=LifecycleProvenanceRegistry(tmp_path/"db.sqlite")
    kwargs=dict(decision_id="LIFE-1",attestation_id="ATT-1",attester_actor_id="a1",reviewer_actor_id="r1",reconciliation_fingerprint=_f("r"),evidence_registry_fingerprint=_f("e"),provenance_fingerprint=_f("p"),bound_at="2026-01-01T00:00:00+00:00")
    r.bind(**kwargs)
    r.bind(decision_id="LIFE-2",attestation_id="ATT-2",attester_actor_id="a1",reviewer_actor_id="r1",reconciliation_fingerprint=_f("r"),evidence_registry_fingerprint=_f("e"),provenance_fingerprint=_f("p"),bound_at="2026-01-01T00:00:01+00:00")
    rows=r.list()
    rows[1]["decision_id"]=rows[0]["decision_id"]
    out=evaluate_provenance(rows,[{"decision_id":"LIFE-1","attestation_id":"ATT-1","actor_id":"r1","attester_actor_id":"a1"}],[{"attestation_id":"ATT-1"},{"attestation_id":"ATT-2"}],reconciliation_fingerprint=_f("r"),evidence_registry_fingerprint=_f("e"),provenance_fingerprint=_f("p"))
    assert any(x["reason"]=="DUPLICATE_DECISION_BINDING" for x in out["failures"])

def test_supersession_cycle_fails_closed():
    out=validate_supersession_chain([{"binding_id":"b1","attestation_id":"ATT-1","superseding_attestation_id":"ATT-2"},{"binding_id":"b2","attestation_id":"ATT-2","superseding_attestation_id":"ATT-1"}],[{"attestation_id":"ATT-1"},{"attestation_id":"ATT-2"}])
    assert out["valid"] is False
    assert any(x["reason"]=="SUPERSESSION_CYCLE" for x in out["failures"])
