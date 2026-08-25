def test_streamlit_workspace_import():

    from sovereign_cad.streamlit import (
        render_cad_workspace,
    )

    assert callable(
        render_cad_workspace
    )