"""
Sovereign CAD Streamlit Integration Layer.

This module is the single entry point used by the main Chrishem
Science Hub app. It safely discovers and renders Sovereign CAD
Stages 1 through 8 without crashing the entire application when
an individual stage is missing or still under development.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import traceback

import streamlit as st


def _candidate_modules(stage_number: int):
    """
    Generate likely module names for each CAD stage.

    The discovery system supports multiple naming conventions so the
    existing Sovereign CAD repository does not need to be rewritten.
    """
    n = stage_number

    return [
        f"sovereign_cad.stage{n}",
        f"sovereign_cad.stage_{n}",
        f"sovereign_cad.stages.stage{n}",
        f"sovereign_cad.stages.stage_{n}",
        f"sovereign_cad.stages.stage{n}.main",
        f"sovereign_cad.stages.stage_{n}.main",
    ]


def _candidate_functions(stage_number: int):
    """
    Generate likely renderer/entry function names.
    """
    n = stage_number

    return [
        f"render_stage_{n}",
        f"render_stage{n}",
        f"stage_{n}",
        f"stage{n}",
        f"run_stage_{n}",
        f"run_stage{n}",
        "render",
        "main",
        "run",
    ]


def _call_safely(func):
    """
    Call a stage function safely.

    Streamlit is rerun-based, so stage renderers normally need no
    arguments. If a function has no required parameters, it is called.
    Otherwise the user receives a clear integration message instead
    of the entire app crashing.
    """

    try:
        signature = inspect.signature(func)

        required = [
            p
            for p in signature.parameters.values()
            if p.default is inspect.Parameter.empty
            and p.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            )
        ]

        if required:
            st.warning(
                "This stage was found, but its entry function requires "
                f"parameters: {', '.join(p.name for p in required)}"
            )

            st.code(
                f"{func.__module__}.{func.__name__}"
            )

            st.info(
                "The CAD engine is connected, but this stage needs its "
                "existing application state/dependencies wired into the "
                "Streamlit bridge."
            )

            return False

        func()
        return True

    except Exception as exc:

        st.error(
            f"Sovereign CAD stage crashed: {type(exc).__name__}: {exc}"
        )

        with st.expander("Show technical traceback"):
            st.code(traceback.format_exc())

        return False


def _render_stage(stage_number: int):
    """
    Locate and render one Sovereign CAD stage.
    """

    import_errors = []

    for module_name in _candidate_modules(stage_number):

        try:
            module = importlib.import_module(module_name)

        except ModuleNotFoundError as exc:

            # Ignore only when the candidate module itself does not exist.
            if exc.name == module_name:
                continue

            import_errors.append(
                f"{module_name}\n{traceback.format_exc()}"
            )

            continue

        except Exception:

            import_errors.append(
                f"{module_name}\n{traceback.format_exc()}"
            )

            continue

        for function_name in _candidate_functions(stage_number):

            function = getattr(module, function_name, None)

            if callable(function):

                st.success(
                    f"Connected: {module_name}.{function_name}()"
                )

                return _call_safely(function)

        st.warning(
            f"Stage {stage_number} module was found:\n\n"
            f"`{module_name}`\n\n"
            "But no compatible entry function was found."
        )

        st.caption(
            "Expected one of: "
            + ", ".join(
                _candidate_functions(stage_number)
            )
        )

        return False

    st.warning(
        f"Sovereign CAD Stage {stage_number} has not been located yet."
    )

    if import_errors:

        with st.expander(
            f"Show Stage {stage_number} import diagnostics"
        ):

            for error in import_errors:
                st.code(error)

    st.info(
        "The main Sovereign CAD workspace is connected correctly. "
        "This individual stage still needs its module/function mapping."
    )

    return False


def _show_package_map():
    """
    Diagnostic view of all discovered Python modules inside sovereign_cad.
    """

    try:
        import sovereign_cad

        modules = sorted(
            module.name
            for module in pkgutil.walk_packages(
                sovereign_cad.__path__,
                sovereign_cad.__name__ + "."
            )
        )

        if modules:

            st.code("\n".join(modules))

        else:

            st.caption(
                "No submodules were discovered."
            )

    except Exception:

        st.code(traceback.format_exc())


def render_cad_workspace():
    """
    Main Sovereign CAD workspace entry point.
    Called directly from app.py.
    """

    st.title("🏗️ Sovereign CAD")
    st.caption(
        "Integrated engineering and CAD development environment"
    )

    st.divider()

    stage_names = {
        "1️⃣ Stage 1": 1,
        "2️⃣ Stage 2": 2,
        "3️⃣ Stage 3": 3,
        "4️⃣ Stage 4": 4,
        "5️⃣ Stage 5": 5,
        "6️⃣ Stage 6": 6,
        "7️⃣ Stage 7": 7,
        "8️⃣ Stage 8": 8,
        "🔍 CAD Diagnostics": 0,
    }

    selected_label = st.radio(
        "Sovereign CAD Development Stage",
        list(stage_names.keys()),
        horizontal=True,
        key="sovereign_cad_stage_selector",
    )

    selected_stage = stage_names[selected_label]

    if selected_stage == 0:

        st.subheader("Sovereign CAD Package Diagnostics")

        st.write(
            "The following modules were discovered inside the "
            "`sovereign_cad` package:"
        )

        _show_package_map()

        return

    st.subheader(
        f"Sovereign CAD — Stage {selected_stage}"
    )

    _render_stage(selected_stage)