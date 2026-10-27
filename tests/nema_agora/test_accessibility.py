from nema_agora.accessibility import make_observation, summarise, fingerprint

def test_accessibility_summary():
    rows=[
        make_observation(scenario_id="S1",channel="WEB",outcome="COMPLETED",
                         steps_completed=4,steps_expected=4,accessibility_barrier=False,
                         review_required=True),
        make_observation(scenario_id="S2",channel="LOW_BANDWIDTH",outcome="PARTIAL",
                         steps_completed=2,steps_expected=4,accessibility_barrier=True,
                         review_required=True),
    ]
    s=summarise(rows)
    assert s["total_observations"]==2
    assert s["completion_rate"]==0.5
    assert s["barrier_rate"]==0.5
    assert len(fingerprint(rows))==64

def test_invalid_channel_rejected():
    try:
        make_observation(scenario_id="S",channel="PHONE",outcome="COMPLETED",
                         steps_completed=1,steps_expected=1,accessibility_barrier=False,
                         review_required=True)
    except ValueError:
        return
    assert False
