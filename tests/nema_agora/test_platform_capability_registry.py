from nema_agora.platform_capability_registry import validate_capabilities
def test_default_registry_is_valid():
 o=validate_capabilities(); assert o["state"]=="VALID"; assert o["capability_count"]>=10
def test_missing_dependency_fails_closed():
 o=validate_capabilities([{"capability_id":"a","name":"A","status":"PLANNED","dependencies":["missing"]}])
 assert o["state"]=="CONTROL_REQUIRED"; assert o["findings"][0]["code"]=="MISSING_DEPENDENCY"
def test_invalid_status_fails_closed():
 o=validate_capabilities([{"capability_id":"a","name":"A","status":"MAGIC","dependencies":[]}])
 assert o["state"]=="CONTROL_REQUIRED"
