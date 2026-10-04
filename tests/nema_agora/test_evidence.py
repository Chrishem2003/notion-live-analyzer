from nema_agora.evidence import build_scorecard, fingerprint_scorecard

def test_scorecard_is_transparent_and_bounded():
    s=build_scorecard(impact_count=10,accessibility_count=5,provenance_count=20,
                      field_evaluation_count=10,human_review_count=1)
    assert 0 <= s.overall_coverage <= 1
    assert s.domain_scores["IMPACT"] == 1
    assert "ACCESSIBILITY_EVIDENCE_THIN" in s.warnings
    assert len(fingerprint_scorecard(s)) == 64
    assert "environmental truth" in s.decision_notice

def test_negative_counts_are_bounded():
    s=build_scorecard(impact_count=-5,accessibility_count=-1,provenance_count=0,
                      field_evaluation_count=0,human_review_count=0)
    assert all(v == 0 for v in s.evidence_counts.values())
