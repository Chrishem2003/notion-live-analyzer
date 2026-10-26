from nema_agora.governance_decision_execution import validate_execution_request

def _pkg():
    return {"case_id":"CASE-1","decision_status":"NOT_DECIDED","current_snapshot":{"r":"1"}}

def test_valid_request_is_ready_but_not_authorized_to_execute():
    out=validate_execution_request(prepared_package=_pkg(),decision="APPROVE",actor_id="reviewer-2",role="coordinator",current_snapshot={"r":"1"})
    assert out["state"]=="READY_FOR_HUMAN_EXECUTION"
    assert out["execution_authorized"] is False

def test_snapshot_mismatch_fails_closed():
    out=validate_execution_request(prepared_package=_pkg(),decision="APPROVE",actor_id="r",role="admin",current_snapshot={"r":"2"})
    assert out["state"]=="CONTROL_REQUIRED"
    assert "CURRENT_SNAPSHOT_MISMATCH" in out["failures"]

def test_unsupported_or_unauthorized_decision_fails_closed():
    out=validate_execution_request(prepared_package=_pkg(),decision="AUTO_APPROVE",actor_id="r",role="reviewer",current_snapshot={"r":"1"})
    assert out["state"]=="CONTROL_REQUIRED"
    assert "UNSUPPORTED_DECISION" in out["failures"]
    assert "AUTHORIZED_DECISION_ROLE_REQUIRED" in out["failures"]
