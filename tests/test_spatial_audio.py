"""Unit tests for modules.project_collaboration.webrtc_provider.SpatialAudioEngine."""
import pytest

from modules.project_collaboration import SpatialAudioEngine
from modules.project_collaboration.webrtc_provider import (
    MAX_SPATIAL_DISTANCE,
    SPATIAL_PAN_RANGE,
    AudioSpatialPosition,
)


@pytest.fixture
def engine():
    return SpatialAudioEngine()


class TestPositions:
    def test_set_position_creates_position(self, engine):
        position = engine.set_position("alice", 100, 200)
        assert isinstance(position, AudioSpatialPosition)
        assert (position.x, position.y) == (100.0, 200.0)

    def test_set_position_updates_existing_object(self, engine):
        first = engine.set_position("alice", 100, 200)
        second = engine.set_position("alice", 300, 400)
        assert first is second
        assert (second.x, second.y) == (300.0, 400.0)

    def test_remove_participant(self, engine):
        engine.set_position("alice", 10, 10)
        assert engine.remove_participant("alice") is True
        assert engine.remove_participant("alice") is False
        assert engine.mix() == {}

    def test_clear(self, engine):
        engine.set_position("alice", 10, 10)
        engine.set_position("bob", 20, 20)
        engine.clear()
        assert engine.get_state()["participant_count"] == 0


class TestParams:
    def test_unknown_participant_returns_empty(self, engine):
        assert engine.get_params("nobody") == {}

    def test_participant_to_the_right_pans_right(self, engine):
        engine.set_position("alice", MAX_SPATIAL_DISTANCE, 0)
        assert engine.get_params("alice")["pan"] == pytest.approx(SPATIAL_PAN_RANGE)

    def test_participant_to_the_left_pans_left(self, engine):
        engine.set_position("alice", -MAX_SPATIAL_DISTANCE, 0)
        assert engine.get_params("alice")["pan"] == pytest.approx(-SPATIAL_PAN_RANGE)

    def test_overlapping_cursor_is_centered_and_loud(self, engine):
        engine.set_position("alice", 0, 0)
        params = engine.get_params("alice")
        assert params["pan"] == 0.0
        assert params["volume"] == 1.0

    def test_volume_decays_with_distance(self, engine):
        engine.set_position("near", 100, 0)
        engine.set_position("far", MAX_SPATIAL_DISTANCE, 0)
        assert engine.get_params("near")["volume"] > engine.get_params("far")["volume"]

    def test_volume_never_drops_below_min_volume(self):
        engine = SpatialAudioEngine(min_volume=0.5)
        engine.set_position("far", MAX_SPATIAL_DISTANCE * 10, 0)
        assert engine.get_params("far")["volume"] == pytest.approx(0.5)

    def test_min_volume_is_clamped_to_unit_range(self):
        assert SpatialAudioEngine(min_volume=5).min_volume == 1.0
        assert SpatialAudioEngine(min_volume=-1).min_volume == 0.0

    def test_listener_position_shifts_the_pan(self, engine):
        engine.set_position("alice", 0, 0)
        engine.set_listener_position(-MAX_SPATIAL_DISTANCE, 0)
        assert engine.get_params("alice")["pan"] > 0

    def test_params_report_distance_and_azimuth(self, engine):
        engine.set_position("alice", 300, 400)
        params = engine.get_params("alice")
        assert params["distance"] == pytest.approx(500.0)
        assert params["azimuth"] == pytest.approx(53.13, abs=0.01)


class TestEnabledState:
    def test_disabled_engine_returns_neutral_params(self, engine):
        engine.set_position("alice", MAX_SPATIAL_DISTANCE, 0)
        engine.toggle()
        assert engine.is_enabled is False
        assert engine.get_params("alice") == {"pan": 0.0, "volume": 1.0, "distance": 0.0, "azimuth": 0.0}

    def test_toggle_returns_new_state(self, engine):
        assert engine.toggle() is False
        assert engine.toggle() is True


class TestMixAndState:
    def test_mix_covers_every_participant(self, engine):
        engine.set_position("alice", 100, 0)
        engine.set_position("bob", -100, 0)
        mix = engine.mix()
        assert set(mix) == {"alice", "bob"}
        assert mix["alice"]["pan"] > 0 > mix["bob"]["pan"]

    def test_state_snapshot(self, engine):
        engine.set_listener_position(5, 6)
        engine.set_position("alice", 1, 2)
        state = engine.get_state()
        assert state == {
            "is_enabled": True,
            "listener": {"x": 5.0, "y": 6.0},
            "participant_count": 1,
            "min_volume": 0.3,
            "max_distance": MAX_SPATIAL_DISTANCE,
            "pan_range": SPATIAL_PAN_RANGE,
        }
