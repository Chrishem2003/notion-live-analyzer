from __future__ import annotations

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
            use_container_width=True,
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
            use_container_width=True,
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


# ============================================================
# CANVAS RENDERING
# ============================================================

def _render_svg(
    runtime,
):

    viewport = runtime["viewport"]
    renderer = runtime["renderer"]
    registry = runtime["registry"]

    width = int(viewport.width)
    height = int(viewport.height)

    commands = renderer.render_registry(
        registry
    )

    elements = []

    # ========================================================
    # BACKGROUND
    # ========================================================

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

    # ========================================================
    # GRID
    # ========================================================

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

    # ========================================================
    # WORLD AXES
    # ========================================================

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

    # ========================================================
    # CAD ENTITIES
    # ========================================================

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

    # ========================================================
    # SVG
    # ========================================================

    svg = f"""
    <svg
        width="100%"
        height="{height}"
        viewBox="0 0 {width} {height}"
        xmlns="http://www.w3.org/2000/svg"
        style="
            display: block;
            width: 100%;
            height: auto;
            background: #111111;
            border: 1px solid #444444;
            border-radius: 8px;
        "
    >
        {''.join(elements)}
    </svg>
    """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                margin: 0;
                padding: 0;
                background: transparent;
                overflow: hidden;
            }}

            svg {{
                display: block;
                width: 100%;
            }}
        </style>
    </head>

    <body>

        {svg}

    </body>
    </html>
    """

    components.html(
        html,
        height=height + 20,
        scrolling=False,
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

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        if st.button(
            "Select",
            use_container_width=True,
            key=_key("tool_select"),
        ):

            _set_tool(
                "select"
            )

    with col2:

        if st.button(
            "Line",
            use_container_width=True,
            key=_key("tool_line"),
        ):

            _set_tool(
                "line"
            )

    with col3:

        if st.button(
            "Circle",
            use_container_width=True,
            key=_key("tool_circle"),
        ):

            _set_tool(
                "circle"
            )

    with col4:

        if st.button(
            "Reset View",
            use_container_width=True,
            key=_key("reset_view"),
        ):

            canvas.reset_view()

            st.rerun()

    zoom1, zoom2, zoom3 = st.columns(3)

    with zoom1:

        if st.button(
            "Zoom Out",
            use_container_width=True,
            key=_key("zoom_out"),
        ):

            canvas.zoom_out()

            st.rerun()

    with zoom2:

        if st.button(
            "Zoom In",
            use_container_width=True,
            key=_key("zoom_in"),
        ):

            canvas.zoom_in()

            st.rerun()

    with zoom3:

        if st.button(
            "Clear Drawing",
            use_container_width=True,
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