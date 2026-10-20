"""Deployment contract checks for the Docker-based Streamlit web service."""
from pathlib import Path


def test_dockerfile_declares_streamlit_start_command_and_dynamic_port():
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    assert 'CMD ["sh", "-c", "streamlit run app.py' in dockerfile
    assert "\${PORT:-8501}" in dockerfile
