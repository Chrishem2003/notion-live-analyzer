from nema_agora.decision_receipt_reconciliation import reconcile_decision_receipts
def test_complete_pair_reconciles():
 o=reconcile_decision_receipts(decisions=[{"decision_id":"DEC-1"}],receipts=[{"receipt_id":"R-1","decision_id":"DEC-1","payload":{"decision_id":"DEC-1","current_snapshot":{"r":"1"}}}],current_snapshot={"r":"1"})
 assert o["state"]=="RECONCILED"
def test_missing_and_orphan_receipts_fail_closed():
 o=reconcile_decision_receipts(decisions=[{"decision_id":"DEC-1"}],receipts=[{"receipt_id":"R-2","decision_id":"DEC-2","payload":{"decision_id":"DEC-2"}}],current_snapshot={})
 codes={x["code"] for x in o["findings"]}
 assert {"MISSING_RECEIPT","ORPHAN_RECEIPT"}<=codes
def test_stale_receipt_fails_closed():
 o=reconcile_decision_receipts(decisions=[{"decision_id":"DEC-1"}],receipts=[{"receipt_id":"R-1","decision_id":"DEC-1","payload":{"decision_id":"DEC-1","current_snapshot":{"r":"old"}}}],current_snapshot={"r":"new"})
 assert o["state"]=="CONTROL_REQUIRED"
 assert o["findings"][0]["code"]=="RECEIPT_SNAPSHOT_STALE"
