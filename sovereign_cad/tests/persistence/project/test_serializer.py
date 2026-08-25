from sovereign_cad.persistence import (
    ProjectFile,
    ProjectSerializer,
)


def test_serializer_produces_json():
    project = ProjectFile(name="Serializer Test")

    text = ProjectSerializer.dumps(project)

    assert '"format": "SovereignCAD"' in text
    assert '"name": "Serializer Test"' in text


def test_invalid_format_rejected():
    bad = '{"format": "UnknownCAD", "version": "1.0"}'

    try:
        ProjectSerializer.loads(bad)
    except ValueError:
        return

    raise AssertionError("Invalid project format was accepted.")