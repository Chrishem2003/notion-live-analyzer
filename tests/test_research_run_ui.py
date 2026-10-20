"""Guard the Streamlit integration surface against syntax regressions."""
from pathlib import Path


def test_integrations_hub_compiles():
    source = Path("pages/09_Integrations_Hub.py").read_text(encoding="utf-8")
    compile(source, "pages/09_Integrations_Hub.py", "exec")
    assert "render_bio_research_runs" in source
    assert "ResearchRunClient(api_url, api_key).create_run(payload)" in source
    assert "Generate a new run ID" in source
