from nema_agora.provenance import fingerprint, make_provenance, verify_provenance_chain

def test_fingerprint_is_deterministic():
    assert fingerprint({"b": 2, "a": 1}) == fingerprint({"a": 1, "b": 2})

def test_provenance_records_bind_event_dataset_model_and_evidence():
    record = make_provenance(
        event_type="MODEL_COMPARISON", event_id="CMP-1", actor_id="coord-1",
        dataset_version="v1", dataset_hash="abc123",
        model_identity={"provider":"provider-a","model_version":"model-1","adapter_name":"adapter-a"},
        evidence={"accuracy":0.9},
    )
    assert record.event_id == "CMP-1"
    assert len(record.evidence_hash) == 64

def test_chain_verification_detects_missing_parent():
    record = make_provenance(event_type="CONTROLLED_SHADOW", event_id="RUN-1",
                             actor_id="reviewer-1", dataset_version="v1", dataset_hash="abc",
                             parent_ids=("PROV-MISSING",))
    result = verify_provenance_chain([record.to_dict()])
    assert result["valid"] is False
    assert result["missing_parents"] == ["PROV-MISSING"]

def test_chain_verification_accepts_complete_chain():
    parent = make_provenance(event_type="MODEL_ADMISSION", event_id="ADM-1",
                             actor_id="coord-1", dataset_version="v1", dataset_hash="abc")
    child = make_provenance(event_type="CONTROLLED_SHADOW", event_id="RUN-1",
                            actor_id="reviewer-1", dataset_version="v1", dataset_hash="abc",
                            parent_ids=(parent.provenance_id,))
    assert verify_provenance_chain([parent.to_dict(), child.to_dict()])["valid"] is True
