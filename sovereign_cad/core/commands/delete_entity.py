﻿from __future__ import annotations

from uuid import UUID

from sovereign_cad.core.document import Document
from sovereign_cad.core.entities import Entity

from .command import Command


class DeleteEntityCommand(Command):
    """
    Removes an entity from a document.

    Undo restores the exact same entity.
    """

    def __init__(
        self,
        document: Document,
        entity_id: UUID,
    ) -> None:

        self.document = document
        self.entity_id = entity_id
        self._entity: Entity | None = None
        self._executed = False

    @property
    def name(self) -> str:
        return "Delete Entity"

    def execute(self) -> None:

        if self._executed:
            return

        self._entity = self.document.remove_entity(
            self.entity_id
        )

        self._executed = True

    def undo(self) -> None:

        if not self._executed:
            return

        if self._entity is None:
            raise RuntimeError(
                "Cannot undo deletion without stored entity."
            )

        self.document.add_entity(self._entity)

        self._executed = False
