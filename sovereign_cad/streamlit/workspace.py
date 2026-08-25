from __future__ import annotations

import traceback

import streamlit as st


SESSION_PREFIX = "sovereign_cad_"


def _key(name: str) -> str:
    return f"{SESSION_PREFIX}{name}"


def _initialize_cad() -> None:
    """
    Initialize the SovereignCAD runtime once per Streamlit session.

    Existing CAD engine files are not modified.
    """

    if st.session_state.get(_key("initialized")):
        return

    try:
        from sovereign_cad.application import (
            ApplicationShell,
            ApplicationContext,
        )

        from sovereign_cad.application.services import (
            ApplicationService,
        )

        from sovereign_cad.ui.viewport import (
            Viewport2D,
        )

        from sovereign_cad.ui.canvas import (
            CanvasState,
        )

        from sovereign_cad.rendering import (
            Renderer2D,
        )

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

        canvas = CanvasState(
            viewport=viewport
        )

        renderer = Renderer2D(
            viewport
        )

        context.viewport = viewport
        context.canvas = canvas
        context.renderer = renderer

        shell.register_service(
            "application",
            application_service
        )

        st.session_state[_key("shell")] = shell
        st.session_state[_key("context")] = context
        st.session_state[_key("service")] = application_service
        st.session_state[_key("viewport")] = viewport
        st.session_state[_key("canvas")] = canvas
        st.session_state[_key("renderer")] = renderer

        st.session_state[_key("initialized")] = True
        st.session_state[_key("error")] = None

    except Exception:
        st.session_state[_key("initialized")] = False
        st.session_state[_key("error")] = traceback.format_exc()


def _get_runtime():
    return {
        "shell": st.session_state.get(_key("shell")),
        "context": st.session_state.get(_key("context")),
        "service": st.session_state.get(_key("service")),
        "viewport": st.session_state.get(_key("viewport")),
        "canvas": st.session_state.get(_key("canvas")),
        "renderer": st.session_state.get(_key("renderer")),
    }


def _render_header():
    left, middle, right = st.columns(
        [2, 6, 2]
    )

    with left:
        st.subheader("📐 Sovereign CAD")

    with middle:
        st.caption(
            "Stage 8.5 Streamlit Workspace"
        )

    with right:
        if st.button(
            "Reset CAD",
            key=_key("reset")
        ):
            for key in list(st.session_state.keys()):
                if key.startswith(SESSION_PREFIX):
                    del st.session_state[key]

            st.rerun()


def _render_toolbar(runtime):
    viewport = runtime["viewport"]
    canvas = runtime["canvas"]

    st.markdown("### Tools")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button(
            "↖ Select",
            use_container_width=True,
            key=_key("tool_select")
        ):
            st.session_state[_key("active_tool")] = "select"

    with col2:
        if st.button(
            "╱ Line",
            use_container_width=True,
            key=_key("tool_line")
        ):
            st.session_state[_key("active_tool")] = "line"

    with col3:
        if st.button(
            "○ Circle",
            use_container_width=True,
            key=_key("tool_circle")
        ):
            st.session_state[_key("active_tool")] = "circle"

    with col4:
        if st.button(
            "▣ Reset View",
            use_container_width=True,
            key=_key("reset_view")
        ):
            canvas.reset_view()

    zoom1, zoom2, zoom3 = st.columns(3)

    with zoom1:
        if st.button(
            "− Zoom Out",
            use_container_width=True,
            key=_key("zoom_out")
        ):
            canvas.zoom_out()

    with zoom2:
        if st.button(
            "+ Zoom In",
            use_container_width=True,
            key=_key("zoom_in")
        ):
            canvas.zoom_in()

    with zoom3:
        if st.button(
            "⌂ Home",
            use_container_width=True,
            key=_key("zoom_home")
        ):
            canvas.reset_view()

    return viewport


def _render_canvas(runtime):
    viewport = runtime["viewport"]

    st.markdown("### Drawing Workspace")

    active_tool = st.session_state.get(
        _key("active_tool"),
        "select"
    )

    st.info(
        f"Active tool: {active_tool.upper()}"
    )

    canvas_height = 520

    st.markdown(
        f"""
        <div style="
            height: {canvas_height}px;
            width: 100%;
            border: 2px solid #444;
            border-radius: 8px;
            position: relative;
            overflow: hidden;
            background-color: #111;
            background-image:
                linear-gradient(#222 1px, transparent 1px),
                linear-gradient(90deg, #222 1px, transparent 1px);
            background-size: 20px 20px;
        ">
            <div style="
                position: absolute;
                top: 10px;
                left: 12px;
                color: #ddd;
                font-family: monospace;
                font-size: 13px;
            ">
                SOVEREIGN CAD CANVAS
                <br>
                Center: ({viewport.center.x:.2f}, {viewport.center.y:.2f})
                <br>
                Zoom: {viewport.zoom:.4f}
            </div>

            <div style="
                position: absolute;
                left: 50%;
                top: 0;
                width: 1px;
                height: 100%;
                background: #666;
            "></div>

            <div style="
                position: absolute;
                top: 50%;
                left: 0;
                width: 100%;
                height: 1px;
                background: #666;
            "></div>

            <div style="
                position: absolute;
                left: 50%;
                top: 50%;
                width: 12px;
                height: 12px;
                transform: translate(-50%, -50%);
                border: 2px solid #00ccff;
                border-radius: 50%;
            "></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_properties(runtime):
    viewport = runtime["viewport"]
    canvas = runtime["canvas"]
    shell = runtime["shell"]

    st.markdown("### Properties")

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
        "Cursor World"
    )

    st.code(
        f"X: {canvas.cursor_world.x:.4f}\n"
        f"Y: {canvas.cursor_world.y:.4f}"
    )

    st.write(
        "Application"
    )

    status = "ONLINE"

    if shell is None or not shell.running:
        status = "OFFLINE"

    st.success(
        status
    )


def _render_status(runtime):
    viewport = runtime["viewport"]

    active_tool = st.session_state.get(
        _key("active_tool"),
        "select"
    )

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.caption(
            f"Command: {active_tool.upper()}"
        )

    with col2:
        st.caption(
            f"Center: X={viewport.center.x:.2f}, "
            f"Y={viewport.center.y:.2f}"
        )

    with col3:
        st.caption(
            f"Zoom: {viewport.zoom:.4f}"
        )


def render_cad_workspace():
    """
    Main Streamlit entry point for Sovereign CAD.

    This function is intentionally isolated from the
    main application so CAD failures do not affect
    unrelated platform sections.
    """

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

        _render_header()

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
                "Selection"
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
            _render_canvas(
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
            "Show workspace error"
        ):
            st.code(
                traceback.format_exc()
            )