from __future__ import annotations

from uuid import UUID

from sovereign_cad.core.document import Document

from .command import Command


class ChangeLayerCommand(Command):
    """
    Moves an entity between layers.
    """

    def __init__(
        self,
        document: Document,
        entity_id: UUID,
        new_layer: str,
    ) -> None:

        self.document = document
        self.entity_id = entity_id
        self.new_layer = new_layer

        self.old_layer: str | None = None
        self._executed = False

    @property
    def name(self) -> str:
        return "Change Layer"

    def execute(self) -> None:

        if self._executed:
            return

        entity = self.document.get_entity(
            self.entity_id
        )

        if entity is None:
            raise KeyError(self.entity_id)

        self.old_layer = entity.layer

        if self.new_layer not in self.document.layers:
            self.document.add_layer(self.new_layer)

        entity.set_layer(self.new_layer)

        self._executed = True

    def undo(self) -> None:

        if not self._executed:
            return

        entity = self.document.get_entity(
            self.entity_id
        )

        if entity is None:
            raise KeyError(self.entity_id)

        if self.old_layer is None:
            raise RuntimeError(
                "Original layer was not recorded."
            )

        entity.set_layer(self.old_layer)

        self._executed = False
