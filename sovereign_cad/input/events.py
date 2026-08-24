from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from sovereign_cad.core.geometry import Point2


class InputEventType(str, Enum):
    MOUSE_DOWN = "mouse_down"
    MOUSE_UP = "mouse_up"
    MOUSE_MOVE = "mouse_move"
    MOUSE_WHEEL = "mouse_wheel"
    KEY_DOWN = "key_down"
    KEY_UP = "key_up"


@dataclass(frozen=True)
class InputEvent:
    event_type: InputEventType
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MouseEvent:
    event_type: InputEventType
    position: Point2
    button: str | None = None
    delta: float = 0.0
    modifiers: tuple[str, ...] = ()

    def to_input_event(self) -> InputEvent:
        return InputEvent(
            event_type=self.event_type,
            data={
                "position": self.position,
                "button": self.button,
                "delta": self.delta,
                "modifiers": self.modifiers,
            },
        )


@dataclass(frozen=True)
class KeyEvent:
    event_type: InputEventType
    key: str
    modifiers: tuple[str, ...] = ()

    def to_input_event(self) -> InputEvent:
        return InputEvent(
            event_type=self.event_type,
            data={
                "key": self.key,
                "modifiers": self.modifiers,
            },
        )
