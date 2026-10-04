from nema_agora.access import has_permission

def test_model_admission_permission_matrix():
    assert not has_permission("submitter","intelligence:admit_model")
    assert not has_permission("reviewer","intelligence:admit_model")
    assert has_permission("coordinator","intelligence:admit_model")
    assert has_permission("admin","intelligence:admit_model")
