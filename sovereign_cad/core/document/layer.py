from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Layer:
    """
    CAD drawing layer.
    """

    name: str
    visible: bool = True
    locked: bool = False

    def __post_init__(self) -> None:

        if not self.name:
            raise ValueError("Layer name cannot be empty.")

    def show(self) -> None:
        self.visible = True

    def hide(self) -> None:
        self.visible = False

    def lock(self) -> None:
        self.locked = True

    def unlock(self) -> None:
        self.locked = False
