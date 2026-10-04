from nema_agora.access import has_permission

def test_model_admission_permission_matrix():
    assert not has_permission("submitter","intelligence:admit_model")
    assert not has_permission("reviewer","intelligence:admit_model")
    assert has_permission("coordinator","intelligence:admit_model")
    assert has_permission("admin","intelligence:admit_model")


def test_controlled_shadow_permission_matrix():
    assert not has_permission("submitter", "intelligence:controlled_shadow")
    assert has_permission("reviewer", "intelligence:controlled_shadow")
    assert has_permission("coordinator", "intelligence:controlled_shadow")
    assert has_permission("admin", "intelligence:controlled_shadow")


def test_shadow_monitoring_permission_matrix():
    assert not has_permission("submitter", "intelligence:monitor")
    assert has_permission("reviewer", "intelligence:monitor")
    assert has_permission("coordinator", "intelligence:monitor")
    assert has_permission("admin", "intelligence:monitor")


def test_human_review_governance_permission_matrix():
    assert not has_permission("submitter", "intelligence:review_shadow")
    assert has_permission("reviewer", "intelligence:review_shadow")
    assert has_permission("coordinator", "intelligence:review_shadow")
    assert has_permission("admin", "intelligence:review_shadow")
    assert not has_permission("submitter", "intelligence:govern_shadow")
    assert not has_permission("reviewer", "intelligence:govern_shadow")
    assert has_permission("coordinator", "intelligence:govern_shadow")
    assert has_permission("admin", "intelligence:govern_shadow")
