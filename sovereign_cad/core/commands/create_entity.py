from __future__ import annotations

from sovereign_cad.core.document import Document
from sovereign_cad.core.entities import Entity

from .command import Command


class CreateEntityCommand(Command):
    """
    Adds an entity to a document.

    Undo removes the entity.
    Redo adds the same entity again.
    """

    def __init__(
        self,
        document: Document,
        entity: Entity,
    ) -> None:

        self.document = document
        self.entity = entity
        self._executed = False

    @property
    def name(self) -> str:
        return f"Create {self.entity.entity_type}"

    def execute(self) -> None:

        if self._executed:
            return

        self.document.add_entity(self.entity)

        self._executed = True

    def undo(self) -> None:

        if not self._executed:
            return

        self.document.remove_entity(
            self.entity.entity_id
        )

        self._executed = False
