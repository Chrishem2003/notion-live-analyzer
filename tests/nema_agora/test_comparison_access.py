from nema_agora.access import has_permission

def test_comparison_permission_matrix():
    assert not has_permission("submitter", "intelligence:comparison")
    assert has_permission("reviewer", "intelligence:comparison")
    assert has_permission("coordinator", "intelligence:comparison")
    assert has_permission("admin", "intelligence:comparison")
