import pytest

from portfolio_os.core import score_opportunity, unit_economics


def opportunity(**overrides):
    values = {
        "impact": 5,
        "urgency": 5,
        "feasibility": 4,
        "willingness_to_pay": 4,
        "strategic_fit": 5,
        "evidence_quality": 4,
        "time_to_value": 4,
        "risk": 1,
    }
    values.update(overrides)
    return values


def test_high_evidence_and_payment_signal_can_recommend_pilot():
    result = score_opportunity(opportunity())
    assert result["score"] >= 75
    assert result["recommendation"] == "Pilot with real users"
    assert result["evidence_gate_passed"] is True
    assert result["payment_signal_gate_passed"] is True


def test_high_risk_reduces_score():
    low_risk = score_opportunity(opportunity(risk=0))
    high_risk = score_opportunity(opportunity(risk=5))
    assert high_risk["score"] < low_risk["score"]
    assert high_risk["risk_penalty"] == 15


def test_weak_payment_evidence_blocks_pilot_recommendation():
    result = score_opportunity(opportunity(willingness_to_pay=1))
    assert result["recommendation"] != "Pilot with real users"
    assert result["payment_signal_gate_passed"] is False


@pytest.mark.parametrize("key", ["impact", "urgency", "feasibility", "willingness_to_pay", "strategic_fit", "evidence_quality", "time_to_value", "risk"])
def test_invalid_rating_is_rejected(key):
    with pytest.raises(ValueError):
        score_opportunity(opportunity(**{key: 6}))


def test_missing_rating_is_rejected():
    values = opportunity()
    del values["impact"]
    with pytest.raises(ValueError):
        score_opportunity(values)


def test_unit_economics_calculates_contribution_and_break_even():
    result = unit_economics(25, 5, 100)
    assert result["contribution_per_customer"] == 20
    assert result["gross_margin_pct"] == 80
    assert result["break_even_customers"] == 5


def test_unit_economics_flags_negative_contribution():
    result = unit_economics(5, 8, 100)
    assert result["viable_unit_contribution"] is False
    assert result["break_even_customers"] is None


def test_unit_economics_rejects_negative_costs():
    with pytest.raises(ValueError):
        unit_economics(10, -1, 100)
