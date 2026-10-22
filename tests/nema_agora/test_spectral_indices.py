from nema_agora.spectral_indices import (
    calculate_ndvi,
    calculate_ndwi,
    spectral_index_evidence,
    validate_spectral_inputs,
)


def test_ndvi_formula():
    assert calculate_ndvi(red=0.2, nir=0.8) == 0.6


def test_mcfeeters_ndwi_formula():
    assert calculate_ndwi(green=0.6, nir=0.2) == 0.5


def test_zero_denominator_fails_closed():
    result = validate_spectral_inputs(scene_id="S2-1", band_values={"B03": 0, "B04": 0, "B08": 0})
    assert result["state"] == "VALID"
    evidence = spectral_index_evidence(scene_id="S2-1", band_values={"B03": 0, "B04": 0, "B08": 0})
    assert evidence["state"] == "CONTROL_REQUIRED"
    assert {"INDEX_DENOMINATOR_ZERO"} <= {item["code"] for item in evidence["findings"]}


def test_invalid_reflectance_fails_closed():
    result = validate_spectral_inputs(
        scene_id="S2-1", band_values={"B03": 1.2, "B04": 0.2, "B08": 0.8}
    )
    assert result["state"] == "CONTROL_REQUIRED"
    assert {"INVALID_B03_REFLECTANCE"} <= {item["code"] for item in result["findings"]}


def test_evidence_is_deterministic_and_non_regulatory():
    bands = {"B03": 0.6, "B04": 0.2, "B08": 0.8}
    first = spectral_index_evidence(scene_id="S2-1", band_values=bands)
    second = spectral_index_evidence(scene_id="S2-1", band_values=bands)
    assert first["state"] == "VALID"
    assert first["fingerprint"] == second["fingerprint"]
    assert "conclusion" not in first
    assert "violation" not in first


def test_missing_band_is_reported():
    result = validate_spectral_inputs(scene_id="S2-1", band_values={"B04": 0.2, "B08": 0.8})
    assert result["state"] == "CONTROL_REQUIRED"
    assert {"MISSING_B03"} <= {item["code"] for item in result["findings"]}


def test_invalid_scene_id_fails_closed():
    result = validate_spectral_inputs(scene_id="", band_values={"B03": 0.6, "B04": 0.2, "B08": 0.8})
    assert result["state"] == "CONTROL_REQUIRED"
    assert {"INVALID_SCENE_ID"} <= {item["code"] for item in result["findings"]}
