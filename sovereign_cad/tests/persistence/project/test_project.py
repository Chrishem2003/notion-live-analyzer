from sovereign_cad.persistence import (
    ProjectFile,
    ProjectSerializer,
    ProjectPersistence,
)


def test_project_defaults():
    project = ProjectFile()

    assert project.version == "1.0"
    assert project.name
    assert isinstance(project.metadata, dict)
    assert isinstance(project.document, dict)


def test_project_round_trip():
    project = ProjectFile(
        name="Stage 8 Test",
        metadata={"author": "SovereignCAD"},
        document={"entities": []},
    )

    text = ProjectSerializer.dumps(project)

    restored = ProjectSerializer.loads(text)

    assert restored.name == project.name
    assert restored.metadata == project.metadata
    assert restored.document == project.document


def test_project_persistence(tmp_path):
    project = ProjectFile(
        name="Persistence Test",
        document={"entities": []},
    )

    persistence = ProjectPersistence(tmp_path)

    path = persistence.save(project, "test_project")

    assert path.exists()
    assert path.suffix == ".scad"

    loaded = persistence.load(path)

    assert loaded.name == "Persistence Test"
    assert loaded.document == {"entities": []}