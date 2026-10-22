from nema_agora.api_audit_casebook import build_api_audit_case
def data():
 e={"event_id":"API-1","request_id":"REQ-1","audit_fingerprint":"e"*64}
 r={"state":"RECONCILED","reconciliation_fingerprint":"a"*64}
 l={"event_id":"API-1","lifecycle_fingerprint":"b"*64}
 d={"event_id":"API-1","reconciliation_fingerprint":"a"*64,"lifecycle_fingerprint":"b"*64,"decision_id":"DEC-1","decision_fingerprint":"d"*64}
 dr={"state":"RECONCILED","reconciliation_fingerprint":"c"*64}
 return e,r,l,d,dr
def test_case_ready():
 x=build_api_audit_case(event=data()[0],reconciliation=data()[1],lifecycle=data()[2],decision=data()[3],decision_reconciliation=data()[4]);assert x["state"]=="CASEBOOK_READY" and x["case_id"].startswith("API-CASE-")
def test_reconciliation_required():
 e,r,l,d,dr=data();dr["state"]="CONTROL_REQUIRED"
 assert build_api_audit_case(event=e,reconciliation=r,lifecycle=l,decision=d,decision_reconciliation=dr)["state"]=="CONTROL_REQUIRED"
def test_binding_mismatch():
 e,r,l,d,dr=data();d["lifecycle_fingerprint"]="x"*64
 assert build_api_audit_case(event=e,reconciliation=r,lifecycle=l,decision=d,decision_reconciliation=dr)["state"]=="CONTROL_REQUIRED"
