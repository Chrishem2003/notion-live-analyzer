from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ApplicationShell:

    running: bool = False
    initialized: bool = False

    services: dict[str, Any] = field(
        default_factory=dict
    )

    def initialize(self) -> None:
        self.initialized = True

    def start(self) -> None:
        if not self.initialized:
            self.initialize()

        self.running = True

    def stop(self) -> None:
        self.running = False

    def register_service(
        self,
        name: str,
        service: Any,
    ) -> None:

        if not name:
            raise ValueError(
                "Service name must not be empty."
            )

        self.services[name] = service

    def get_service(
        self,
        name: str,
    ) -> Any:

        return self.services.get(name)

    def has_service(
        self,
        name: str,
    ) -> bool:

        return name in self.services

    def remove_service(
        self,
        name: str,
    ) -> Any:

        return self.services.pop(
            name,
            None,
        )

    def clear_services(self) -> None:
        self.services.clear()
