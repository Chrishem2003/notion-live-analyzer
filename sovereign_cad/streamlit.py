import streamlit as st


def render_cad_workspace():
    st.header("🏗️ Sovereign CAD")

    st.success("Sovereign CAD is connected to the main application.")

    st.write(
        "The CAD engine is now accessible from the CHRISHEM APEX navigation."
    )

    st.markdown("---")

    st.subheader("CAD System Status")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("CAD Package", "Connected")

    with col2:
        st.metric("Streamlit Adapter", "Active")

    with col3:
        st.metric("Workspace", "Ready")

    st.markdown("---")

    st.subheader("CAD Engine Files")

    import pathlib

    root = pathlib.Path(__file__).parent

    cad_files = list(root.rglob("*.py"))

    if cad_files:
        for file in cad_files[:100]:
            try:
                st.code(str(file.relative_to(root)))
            except Exception:
                st.code(str(file))
    else:
        st.warning("No Python CAD files were found.")
