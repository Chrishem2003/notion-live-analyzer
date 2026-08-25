from sovereign_cad.core.geometry import Point2
from sovereign_cad.input import (
    InputEvent,
    InputEventType,
    MouseEvent,
    KeyEvent,
)


def test_input_event():
    event = InputEvent(
        InputEventType.MOUSE_MOVE,
        {"x": 10},
    )

    assert event.event_type == InputEventType.MOUSE_MOVE
    assert event.data["x"] == 10


def test_mouse_event_conversion():
    event = MouseEvent(
        event_type=InputEventType.MOUSE_DOWN,
        position=Point2(10, 20),
        button="left",
    )

    converted = event.to_input_event()

    assert converted.event_type == InputEventType.MOUSE_DOWN
    assert converted.data["position"] == Point2(10, 20)
    assert converted.data["button"] == "left"


def test_key_event_conversion():
    event = KeyEvent(
        event_type=InputEventType.KEY_DOWN,
        key="A",
        modifiers=("CTRL",),
    )

    converted = event.to_input_event()

    assert converted.event_type == InputEventType.KEY_DOWN
    assert converted.data["key"] == "A"
    assert converted.data["modifiers"] == ("CTRL",)
