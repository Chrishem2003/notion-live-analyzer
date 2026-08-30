from __future__ import annotations

import base64

import math
import traceback

import streamlit as st
import streamlit.components.v1 as components

from sovereign_cad.application import (
    ApplicationContext,
    ApplicationShell,
)

from sovereign_cad.application.services import (
    ApplicationService,
)

from sovereign_cad.core.document import (
    Document,
)

from sovereign_cad.core.entities import (
    CircleEntity,
    EntityRegistry,
    LineEntity,
    RectangleEntity,
    ArcEntity,
)

from sovereign_cad.core.geometry import (
    Point2,
)

from sovereign_cad.ui.canvas import (
    CanvasState,
)

from sovereign_cad.ui.viewport import (
    Viewport2D,
)

from sovereign_cad.rendering import (
    Renderer2D,
)


SESSION_PREFIX = "sovereign_cad_"


def _key(name: str) -> str:
    return f"{SESSION_PREFIX}{name}"


# ============================================================
# CAD INITIALIZATION
# ============================================================

def _initialize_cad() -> None:

    if st.session_state.get(_key("initialized")):
        return

    try:

        shell = ApplicationShell()
        shell.initialize()
        shell.start()

        context = ApplicationContext()

        application_service = ApplicationService(
            shell=shell
        )

        viewport = Viewport2D(
            width=1200.0,
            height=800.0,
        )

        registry = EntityRegistry()

        document = Document()

        canvas = CanvasState(
            viewport=viewport,
            registry=registry,
        )

        renderer = Renderer2D(
            viewport
        )

        context.document = document
        context.viewport = viewport
        context.canvas = canvas
        context.renderer = renderer

        shell.register_service(
            "application",
            application_service,
        )

        st.session_state[_key("shell")] = shell
        st.session_state[_key("context")] = context
        st.session_state[_key("service")] = application_service
        st.session_state[_key("viewport")] = viewport
        st.session_state[_key("canvas")] = canvas
        st.session_state[_key("renderer")] = renderer
        st.session_state[_key("document")] = document
        st.session_state[_key("registry")] = registry

        st.session_state[_key("active_tool")] = "select"
        st.session_state[_key("pending_point")] = None
        st.session_state[_key("selected_entity")] = None

        st.session_state[_key("initialized")] = True
        st.session_state[_key("error")] = None

    except Exception:

        st.session_state[_key("initialized")] = False

        st.session_state[_key("error")] = (
            traceback.format_exc()
        )


# ============================================================
# RUNTIME ACCESS
# ============================================================

def _get_runtime():

    return {

        "shell": st.session_state.get(
            _key("shell")
        ),

        "context": st.session_state.get(
            _key("context")
        ),

        "service": st.session_state.get(
            _key("service")
        ),

        "viewport": st.session_state.get(
            _key("viewport")
        ),

        "canvas": st.session_state.get(
            _key("canvas")
        ),

        "renderer": st.session_state.get(
            _key("renderer")
        ),

        "document": st.session_state.get(
            _key("document")
        ),

        "registry": st.session_state.get(
            _key("registry")
        ),

    }


# ============================================================
# TOOL MANAGEMENT
# ============================================================

def _set_tool(tool_name: str) -> None:

    st.session_state[
        _key("active_tool")
    ] = tool_name

    st.session_state[
        _key("pending_point")
    ] = None


# ============================================================
# ENTITY CREATION
# ============================================================

def _create_line(
    runtime,
    start: Point2,
    end: Point2,
) -> None:

    line = LineEntity(
        start=start,
        end=end,
    )

    runtime["registry"].add(
        line
    )

    runtime["document"].add_entity(
        line
    )


def _create_circle(
    runtime,
    center: Point2,
    edge: Point2,
) -> None:

    radius = center.distance_to(
        edge
    )

    if radius <= 0:
        return

    circle = CircleEntity(
        center=center,
        radius=radius,
    )

    runtime["registry"].add(
        circle
    )

    runtime["document"].add_entity(
        circle
    )


def _create_rectangle(
    runtime,
    corner1: Point2,
    corner2: Point2,
) -> None:

    if corner1.almost_equal(corner2):
        return

    rectangle = RectangleEntity(
        corner1=corner1,
        corner2=corner2,
    )

    runtime["registry"].add(
        rectangle
    )

    runtime["document"].add_entity(
        rectangle
    )


def _create_arc(
    runtime,
    center: Point2,
    radius: float,
    start_angle_deg: float,
    end_angle_deg: float,
) -> None:

    if radius <= 0:
        return

    arc = ArcEntity(
        center=center,
        radius=radius,
        start_angle=math.radians(start_angle_deg),
        end_angle=math.radians(end_angle_deg),
    )

    runtime["registry"].add(
        arc
    )

    runtime["document"].add_entity(
        arc
    )


# ============================================================
# STREAMLIT DRAWING CONTROLS
# ============================================================

def _render_coordinate_input(
    runtime,
):

    st.markdown(
        "### Drawing Input"
    )

    tool = st.session_state.get(
        _key("active_tool"),
        "select",
    )

    if tool == "line":

        col1, col2 = st.columns(2)

        with col1:

            x1 = st.number_input(
                "Start X",
                value=0.0,
                key=_key("line_x1"),
            )

            y1 = st.number_input(
                "Start Y",
                value=0.0,
                key=_key("line_y1"),
            )

        with col2:

            x2 = st.number_input(
                "End X",
                value=100.0,
                key=_key("line_x2"),
            )

            y2 = st.number_input(
                "End Y",
                value=100.0,
                key=_key("line_y2"),
            )

        if st.button(
            "Create Line",
            width='stretch',
            key=_key("create_line"),
        ):

            _create_line(
                runtime,
                Point2(x1, y1),
                Point2(x2, y2),
            )

            st.rerun()

    elif tool == "circle":

        col1, col2 = st.columns(2)

        with col1:

            x = st.number_input(
                "Center X",
                value=0.0,
                key=_key("circle_x"),
            )

            y = st.number_input(
                "Center Y",
                value=0.0,
                key=_key("circle_y"),
            )

        with col2:

            radius = st.number_input(
                "Radius",
                min_value=0.1,
                value=100.0,
                key=_key("circle_radius"),
            )

        if st.button(
            "Create Circle",
            width='stretch',
            key=_key("create_circle"),
        ):

            center = Point2(
                x,
                y,
            )

            edge = Point2(
                x + radius,
                y,
            )

            _create_circle(
                runtime,
                center,
                edge,
            )

            st.rerun()

    elif tool == "select":

        registry = runtime["registry"]
        entities = registry.all()

        if not entities:
            st.info("Nothing drawn yet — pick a shape tool above to create something first.")
        else:
            labels = {
                e.entity_id: f"{type(e).__name__.replace('Entity', '')} ({e.entity_id.hex[:8]})"
                for e in entities
            }

            selected_id = st.selectbox(
                "Select an entity",
                options=list(labels.keys()),
                format_func=lambda eid: labels[eid],
                key=_key("select_target"),
            )

            col_a, col_b = st.columns(2)

            with col_a:
                if st.button("Select", width='stretch', key=_key("confirm_select")):
                    registry.clear_selection()
                    registry.select(selected_id)
                    st.rerun()

            with col_b:
                if st.button("Deselect All", width='stretch', key=_key("clear_selection")):
                    registry.clear_selection()
                    st.rerun()

            if registry.selected():
                st.caption(f"Currently selected: {len(registry.selected())} entity(ies) — use **Delete Selected** in the toolbar to remove.")

    elif tool == "rectangle":

        col1, col2 = st.columns(2)

        with col1:

            x1 = st.number_input(
                "Corner 1 X",
                value=0.0,
                key=_key("rect_x1"),
            )

            y1 = st.number_input(
                "Corner 1 Y",
                value=0.0,
                key=_key("rect_y1"),
            )

        with col2:

            x2 = st.number_input(
                "Corner 2 X",
                value=100.0,
                key=_key("rect_x2"),
            )

            y2 = st.number_input(
                "Corner 2 Y",
                value=60.0,
                key=_key("rect_y2"),
            )

        if st.button(
            "Create Rectangle",
            width='stretch',
            key=_key("create_rectangle"),
        ):

            _create_rectangle(
                runtime,
                Point2(x1, y1),
                Point2(x2, y2),
            )

            st.rerun()

    elif tool == "arc":

        col1, col2 = st.columns(2)

        with col1:

            x = st.number_input(
                "Center X",
                value=0.0,
                key=_key("arc_x"),
            )

            y = st.number_input(
                "Center Y",
                value=0.0,
                key=_key("arc_y"),
            )

            radius = st.number_input(
                "Radius",
                min_value=0.1,
                value=100.0,
                key=_key("arc_radius"),
            )

        with col2:

            start_angle = st.number_input(
                "Start Angle (deg)",
                value=0.0,
                key=_key("arc_start"),
            )

            end_angle = st.number_input(
                "End Angle (deg)",
                value=90.0,
                key=_key("arc_end"),
            )

        if st.button(
            "Create Arc",
            width='stretch',
            key=_key("create_arc"),
        ):

            _create_arc(
                runtime,
                Point2(x, y),
                radius,
                start_angle,
                end_angle,
            )

            st.rerun()


# ============================================================
# CANVAS RENDERING
# ============================================================

def _render_svg(
    runtime,
):

    viewport = runtime["viewport"]
    renderer = runtime["renderer"]
    registry = runtime["registry"]

    width = int(
        viewport.width
    )

    height = int(
        viewport.height
    )

    commands = renderer.render_registry(
        registry
    )

    elements = []

    # --------------------------------------------------------
    # BACKGROUND
    # --------------------------------------------------------

    elements.append(
        f"""
        <rect
            x="0"
            y="0"
            width="{width}"
            height="{height}"
            fill="#111111"
        />
        """
    )

    # --------------------------------------------------------
    # GRID
    # --------------------------------------------------------

    grid_spacing = 50

    for x in range(
        0,
        width + 1,
        grid_spacing,
    ):

        elements.append(
            f"""
            <line
                x1="{x}"
                y1="0"
                x2="{x}"
                y2="{height}"
                stroke="#222222"
                stroke-width="1"
            />
            """
        )

    for y in range(
        0,
        height + 1,
        grid_spacing,
    ):

        elements.append(
            f"""
            <line
                x1="0"
                y1="{y}"
                x2="{width}"
                y2="{y}"
                stroke="#222222"
                stroke-width="1"
            />
            """
        )

    # --------------------------------------------------------
    # WORLD AXES
    # --------------------------------------------------------

    center_screen = viewport.world_to_screen(
        Point2(
            0.0,
            0.0,
        )
    )

    elements.append(
        f"""
        <line
            x1="{center_screen.x}"
            y1="0"
            x2="{center_screen.x}"
            y2="{height}"
            stroke="#666666"
            stroke-width="1"
        />
        """
    )

    elements.append(
        f"""
        <line
            x1="0"
            y1="{center_screen.y}"
            x2="{width}"
            y2="{center_screen.y}"
            stroke="#666666"
            stroke-width="1"
        />
        """
    )

    # --------------------------------------------------------
    # CAD ENTITIES
    # --------------------------------------------------------

    for command in commands:

        if command.operation == "line":

            start = command.data["start"]
            end = command.data["end"]

            selected = command.data.get(
                "selected",
                False,
            )

            color = (
                "#00ccff"
                if selected
                else "#ffffff"
            )

            elements.append(
                f"""
                <line
                    x1="{start.x}"
                    y1="{start.y}"
                    x2="{end.x}"
                    y2="{end.y}"
                    stroke="{color}"
                    stroke-width="3"
                    stroke-linecap="round"
                />
                """
            )

        elif command.operation == "circle":

            center = command.data["center"]

            radius = command.data["radius"]

            selected = command.data.get(
                "selected",
                False,
            )

            color = (
                "#00ccff"
                if selected
                else "#ffffff"
            )

            elements.append(
                f"""
                <circle
                    cx="{center.x}"
                    cy="{center.y}"
                    r="{radius}"
                    fill="none"
                    stroke="{color}"
                    stroke-width="3"
                />
                """
            )

        elif command.operation == "rectangle":

            corner1 = command.data["corner1"]
            corner2 = command.data["corner2"]

            selected = command.data.get(
                "selected",
                False,
            )

            color = (
                "#00ccff"
                if selected
                else "#ffffff"
            )

            rect_x = min(corner1.x, corner2.x)
            rect_y = min(corner1.y, corner2.y)
            rect_w = abs(corner2.x - corner1.x)
            rect_h = abs(corner2.y - corner1.y)

            elements.append(
                f"""
                <rect
                    x="{rect_x}"
                    y="{rect_y}"
                    width="{rect_w}"
                    height="{rect_h}"
                    fill="none"
                    stroke="{color}"
                    stroke-width="3"
                />
                """
            )

        elif command.operation == "arc":

            center = command.data["center"]
            radius = command.data["radius"]
            start_angle = command.data["start_angle"]
            end_angle = command.data["end_angle"]

            selected = command.data.get(
                "selected",
                False,
            )

            color = (
                "#00ccff"
                if selected
                else "#ffffff"
            )

            sweep = end_angle - start_angle
            while sweep <= 0:
                sweep += 2 * math.pi

            start_x = center.x + radius * math.cos(-start_angle)
            start_y = center.y + radius * math.sin(-start_angle)
            end_x = center.x + radius * math.cos(-end_angle)
            end_y = center.y + radius * math.sin(-end_angle)
            large_arc_flag = 1 if sweep > math.pi else 0

            elements.append(
                f"""
                <path
                    d="M {start_x} {start_y} A {radius} {radius} 0 {large_arc_flag} 0 {end_x} {end_y}"
                    fill="none"
                    stroke="{color}"
                    stroke-width="3"
                />
                """
            )

    # --------------------------------------------------------
    # BUILD SVG
    # --------------------------------------------------------

    svg = f"""
    <svg
        xmlns="http://www.w3.org/2000/svg"
        width="{width}"
        height="{height}"
        viewBox="0 0 {width} {height}"
    >
        {''.join(elements)}
    </svg>
    """

    # --------------------------------------------------------
    # ENCODE SVG AS IMAGE
    # --------------------------------------------------------

    encoded_svg = base64.b64encode(
        svg.encode(
            "utf-8"
        )
    ).decode(
        "utf-8"
    )

    image_uri = (
        "data:image/svg+xml;base64,"
        + encoded_svg
    )

    # --------------------------------------------------------
    # DISPLAY CANVAS
    # --------------------------------------------------------

    st.image(
        image_uri,
        width='stretch',
    )

# ============================================================
# TOOLBAR
# ============================================================

def _render_toolbar(
    runtime,
):

    canvas = runtime["canvas"]

    st.markdown(
        "### Tools"
    )

    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

    with col1:

        if st.button(
            "Select",
            width='stretch',
            key=_key("tool_select"),
        ):

            _set_tool(
                "select"
            )

    with col2:

        if st.button(
            "Line",
            width='stretch',
            key=_key("tool_line"),
        ):

            _set_tool(
                "line"
            )

    with col3:

        if st.button(
            "Circle",
            width='stretch',
            key=_key("tool_circle"),
        ):

            _set_tool(
                "circle"
            )

    with col4:

        if st.button(
            "Rectangle",
            width='stretch',
            key=_key("tool_rectangle"),
        ):

            _set_tool(
                "rectangle"
            )

    with col5:

        if st.button(
            "Arc",
            width='stretch',
            key=_key("tool_arc"),
        ):

            _set_tool(
                "arc"
            )

    with col6:

        if st.button(
            "Delete Selected",
            width='stretch',
            key=_key("delete_selected"),
        ):

            registry = runtime["registry"]
            document = runtime["document"]
            to_delete = [e.entity_id for e in registry.selected()]

            for entity_id in to_delete:
                registry.remove(entity_id)
                document.remove_entity(entity_id)

            if to_delete:
                st.success(f"Deleted {len(to_delete)} entity(ies).")
                st.rerun()
            else:
                st.warning("No entity selected. Use the Select tool below to choose one first.")

    with col7:

        if st.button(
            "Reset View",
            width='stretch',
            key=_key("reset_view"),
        ):

            canvas.reset_view()

            st.rerun()

    zoom1, zoom2, zoom3 = st.columns(3)

    with zoom1:

        if st.button(
            "Zoom Out",
            width='stretch',
            key=_key("zoom_out"),
        ):

            canvas.zoom_out()

            st.rerun()

    with zoom2:

        if st.button(
            "Zoom In",
            width='stretch',
            key=_key("zoom_in"),
        ):

            canvas.zoom_in()

            st.rerun()

    with zoom3:

        if st.button(
            "Clear Drawing",
            width='stretch',
            key=_key("clear_drawing"),
        ):

            runtime["document"].clear()

            runtime["registry"] = EntityRegistry()

            runtime["canvas"].registry = (
                runtime["registry"]
            )

            st.session_state[
                _key("registry")
            ] = runtime["registry"]

            st.session_state[
                _key("selected_entity")
            ] = None

            st.rerun()


# ============================================================
# PROPERTIES
# ============================================================

def _render_properties(
    runtime,
):

    viewport = runtime["viewport"]
    canvas = runtime["canvas"]
    document = runtime["document"]
    shell = runtime["shell"]

    st.markdown(
        "### Properties"
    )

    st.write(
        "Viewport Center"
    )

    st.code(
        f"X: {viewport.center.x:.4f}\n"
        f"Y: {viewport.center.y:.4f}"
    )

    st.write(
        "Zoom"
    )

    st.code(
        f"{viewport.zoom:.6f}"
    )

    st.write(
        "Entities"
    )

    st.code(
        str(
            document.entity_count
        )
    )

    st.write(
        "Cursor World"
    )

    st.code(
        f"X: {canvas.cursor_world.x:.4f}\n"
        f"Y: {canvas.cursor_world.y:.4f}"
    )

    st.write(
        "Application"
    )

    if shell is not None and shell.running:

        st.success(
            "ONLINE"
        )

    else:

        st.error(
            "OFFLINE"
        )


# ============================================================
# STATUS BAR
# ============================================================

def _render_status(
    runtime,
):

    viewport = runtime["viewport"]

    active_tool = st.session_state.get(
        _key("active_tool"),
        "select",
    )

    document = runtime["document"]

    st.divider()

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.caption(
            f"Tool: {active_tool.upper()}"
        )

    with col2:

        st.caption(
            f"Center: "
            f"X={viewport.center.x:.2f}, "
            f"Y={viewport.center.y:.2f}"
        )

    with col3:

        st.caption(
            f"Zoom: {viewport.zoom:.4f}"
        )

    with col4:

        st.caption(
            f"Entities: "
            f"{document.entity_count}"
        )


# ============================================================
# MAIN WORKSPACE
# ============================================================

def render_cad_workspace():

    try:

        _initialize_cad()

        error = st.session_state.get(
            _key("error")
        )

        if error:

            st.error(
                "Sovereign CAD could not be initialized."
            )

            with st.expander(
                "Show CAD initialization details"
            ):

                st.code(
                    error
                )

            return

        runtime = _get_runtime()

        st.title(
            "Sovereign CAD"
        )

        st.caption(
            "Stage 8.5 Interactive Engineering Workspace"
        )

        _render_toolbar(
            runtime
        )

        left, center, right = st.columns(
            [1.5, 6, 1.8]
        )

        with left:

            st.markdown(
                "### CAD System"
            )

            st.success(
                "Engine Online"
            )

            st.caption(
                "Geometry"
            )

            st.caption(
                "Entities"
            )

            st.caption(
                "Document"
            )

            st.caption(
                "Commands"
            )

            st.caption(
                "Viewport"
            )

            st.caption(
                "Renderer"
            )

        with center:

            active_tool = st.session_state.get(
                _key("active_tool"),
                "select",
            )

            st.info(
                f"Active Tool: "
                f"{active_tool.upper()}"
            )

            _render_coordinate_input(
                runtime
            )

            st.markdown(
                "### Drawing Workspace"
            )

            _render_svg(
                runtime
            )

        with right:

            _render_properties(
                runtime
            )

        _render_status(
            runtime
        )

    except Exception:

        st.error(
            "Unexpected Sovereign CAD workspace error."
        )

        with st.expander(
            "Show technical traceback"
        ):

            st.code(
                traceback.format_exc()
            )