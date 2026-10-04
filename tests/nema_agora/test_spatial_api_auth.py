from nema_agora.spatial_api_auth import authorize_request
def test_authorized_coordinator(): assert authorize_request(actor_id="ACTOR-1",role="coordinator",permission="spatial:evidence:query",request_id="REQ-1")["state"]=="AUTHORIZED"
def test_missing_token_is_401(): assert authorize_request(actor_id="ACTOR-1",role="reviewer",permission="spatial:evidence:read",request_id="REQ-1",token_present=False)["http_status"]==401
def test_wrong_permission_is_403(): assert authorize_request(actor_id="ACTOR-1",role="reviewer",permission="spatial:evidence:query",request_id="REQ-1")["http_status"]==403
def test_invalid_actor_fails_closed(): assert authorize_request(actor_id="bad id",role="admin",permission="spatial:evidence:admin",request_id="REQ-1")["http_status"]==403
