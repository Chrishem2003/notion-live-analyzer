﻿from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ApplicationService:

    shell: Any = None

    state: dict[str, Any] = field(
        default_factory=dict
    )

    def set(
        self,
        key: str,
        value: Any,
    ) -> None:

        if not key:
            raise ValueError(
                "State key must not be empty."
            )

        self.state[key] = value

    def get(
        self,
        key: str,
        default: Any = None,
    ) -> Any:

        return self.state.get(
            key,
            default,
        )

    def remove(
        self,
        key: str,
    ) -> Any:

        return self.state.pop(
            key,
            None,
        )

    def clear(self) -> None:
        self.state.clear()
