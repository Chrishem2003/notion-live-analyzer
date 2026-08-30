from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sovereign_cad.core.geometry import Point2
from sovereign_cad.core.entities import (
    CircleEntity,
    Entity,
    LineEntity,
    RectangleEntity,
    ArcEntity,
)

from sovereign_cad.ui.viewport import Viewport


@dataclass
class RenderCommand:
    operation: str
    data: dict[str, Any] = field(
        default_factory=dict
    )


class Renderer2D:
    """
    Converts SovereignCAD entities into backend-neutral
    2D rendering commands.
    """

    def __init__(self, viewport: Viewport):
        self.viewport = viewport

    def render_entity(self, entity: Entity):
        if not entity.visible:
            return None

        if isinstance(entity, LineEntity):
            start = self.viewport.world_to_screen(
                entity.start
            )

            end = self.viewport.world_to_screen(
                entity.end
            )

            return RenderCommand(
                operation="line",
                data={
                    "entity_id": entity.entity_id,
                    "start": start,
                    "end": end,
                    "selected": entity.selected,
                    "layer": entity.layer,
                },
            )

        if isinstance(entity, CircleEntity):
            center = self.viewport.world_to_screen(
                entity.center
            )

            radius = (
                entity.radius
                * self.viewport.zoom
            )

            return RenderCommand(
                operation="circle",
                data={
                    "entity_id": entity.entity_id,
                    "center": center,
                    "radius": radius,
                    "selected": entity.selected,
                    "layer": entity.layer,
                },
            )

        if isinstance(entity, RectangleEntity):
            corner1_screen = self.viewport.world_to_screen(entity.min_corner)
            corner2_screen = self.viewport.world_to_screen(entity.max_corner)
            return RenderCommand(
                operation="rectangle",
                data={
                    "entity_id": entity.entity_id,
                    "corner1": corner1_screen,
                    "corner2": corner2_screen,
                    "selected": entity.selected,
                    "layer": entity.layer,
                },
            )

        if isinstance(entity, ArcEntity):
            center = self.viewport.world_to_screen(entity.center)
            radius = entity.radius * self.viewport.zoom
            return RenderCommand(
                operation="arc",
                data={
                    "entity_id": entity.entity_id,
                    "center": center,
                    "radius": radius,
                    "start_angle": entity.start_angle,
                    "end_angle": entity.end_angle,
                    "selected": entity.selected,
                    "layer": entity.layer,
                },
            )

        return RenderCommand(
            operation="entity",
            data={
                "entity_id": entity.entity_id,
                "entity_type": entity.entity_type,
                "selected": entity.selected,
                "layer": entity.layer,
            },
        )

    def render_entities(self, entities):
        commands = []

        for entity in entities:
            command = self.render_entity(entity)

            if command is not None:
                commands.append(command)

        return commands

    def render_registry(self, registry):
        return self.render_entities(
            registry.visible()
        )

    def render_grid(
        self,
        spacing: float = 10.0,
        extent: float = 1000.0,
    ):
        if spacing <= 0:
            raise ValueError(
                "Grid spacing must be positive."
            )

        if extent <= 0:
            raise ValueError(
                "Grid extent must be positive."
            )

        commands = []

        value = -extent

        while value <= extent:
            vertical_start = (
                self.viewport.world_to_screen(
                    Point2(value, -extent)
                )
            )

            vertical_end = (
                self.viewport.world_to_screen(
                    Point2(value, extent)
                )
            )

            commands.append(
                RenderCommand(
                    operation="grid_line",
                    data={
                        "start": vertical_start,
                        "end": vertical_end,
                    },
                )
            )

            horizontal_start = (
                self.viewport.world_to_screen(
                    Point2(-extent, value)
                )
            )

            horizontal_end = (
                self.viewport.world_to_screen(
                    Point2(extent, value)
                )
            )

            commands.append(
                RenderCommand(
                    operation="grid_line",
                    data={
                        "start": horizontal_start,
                        "end": horizontal_end,
                    },
                )
            )

            value += spacing

        return commands


# Compatibility name used by Stage 5 consumers.
Renderer = Renderer2D