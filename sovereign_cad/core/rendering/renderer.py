from __future__ import annotations

from dataclasses import dataclass, field

from ..entities import CircleEntity, Entity, LineEntity
from ..viewport import Viewport


@dataclass(frozen=True)
class RenderCommand:
    """
    Backend-independent render command.
    """

    kind: str
    points: tuple
    entity_id: object
    selected: bool = False


@dataclass
class Renderer:
    """
    Backend-independent CAD renderer.

    Stage 5 produces render commands instead of depending on
    a specific GUI framework. A future Qt/OpenGL/Canvas backend
    can consume these commands.
    """

    viewport: Viewport
    commands: list[RenderCommand] = field(
        default_factory=list
    )

    def clear(self) -> None:
        self.commands.clear()

    def render_entity(
        self,
        entity: Entity,
    ) -> RenderCommand | None:

        if not entity.visible:
            return None

        if isinstance(entity, LineEntity):

            start = self.viewport.world_to_screen(
                entity.start
            )

            end = self.viewport.world_to_screen(
                entity.end
            )

            command = RenderCommand(
                kind="LINE",
                points=(start, end),
                entity_id=entity.entity_id,
                selected=entity.selected,
            )

        elif isinstance(entity, CircleEntity):

            center = self.viewport.world_to_screen(
                entity.center
            )

            radius = entity.radius * self.viewport.scale

            command = RenderCommand(
                kind="CIRCLE",
                points=(center, radius),
                entity_id=entity.entity_id,
                selected=entity.selected,
            )

        else:
            return None

        self.commands.append(command)

        return command

    def render(
        self,
        entities,
    ) -> list[RenderCommand]:

        self.clear()

        for entity in entities:
            self.render_entity(entity)

        return list(self.commands)
