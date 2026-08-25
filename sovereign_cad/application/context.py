from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ApplicationContext:

    document: Any = None
    canvas: Any = None
    viewport: Any = None
    renderer: Any = None
    input_system: Any = None
    command_system: Any = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def set_metadata(
        self,
        key: str,
        value: Any,
    ) -> None:

        if not key:
            raise ValueError(
                "Metadata key must not be empty."
            )

        self.metadata[key] = value

    def get_metadata(
        self,
        key: str,
        default: Any = None,
    ) -> Any:

        return self.metadata.get(
            key,
            default,
        )

    def clear_metadata(self) -> None:
        self.metadata.clear()
