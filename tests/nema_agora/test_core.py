from datetime import date

import pytest

from nema_agora.core import (
    CATEGORIES,
    make_observation,
    new_case_id,
    normalise_coordinates,
    validate_observation,
)


def test_validation_requires_site_description_and_permission():
    errors = validate_observation(site=" ", description="", consent_confirmed=False)
    assert len(errors) == 3


def test_validation_rejects_oversized_description():
    errors = validate_observation(site="Pilot A", description="x" * 1501, consent_confirmed=True)
    assert any("1,500" in error for error in errors)


def test_coordinates_treat_zero_pair_as_omitted():
    assert normalise_coordinates(0.0, 0.0) is None
    assert normalise_coordinates(2.5, 32.1) == (2.5, 32.1)


@pytest.mark.parametrize("lat,lon", [(91, 0), (0, 181), (-91, 0)])
def test_coordinates_out_of_range_raise(lat, lon):
    with pytest.raises(ValueError):
        normalise_coordinates(lat, lon)


def test_case_id_format():
    assert new_case_id().startswith("NA-")
    assert len(new_case_id()) == 11


def test_record_is_normalised_and_starts_unreviewed():
    record = make_observation(
        observation_date=date(2026, 10, 3),
        category=CATEGORIES[0],
        severity="Moderate",
        site="  Pilot A  ",
        description="  Test observation  ",
        latitude=2.5,
        longitude=32.1,
        consent_confirmed=True,
        created_at="2026-10-03T12:00:00+03:00",
        evidence_reference="  sample.png  ",
    )
    assert record["district_or_site"] == "Pilot A"
    assert record["description"] == "Test observation"
    assert record["status"] == "Received"
    assert record["latitude"] == 2.5
    assert record["evidence_reference"] == "sample.png"


def test_invalid_record_is_not_created():
    with pytest.raises(ValueError):
        make_observation(
            observation_date=date.today(),
            category=CATEGORIES[0],
            severity="Low",
            site="",
            description="",
            latitude=0,
            longitude=0,
            consent_confirmed=False,
            created_at="now",
        )



@pytest.mark.parametrize(
    "value,expected",
    [
        ("=HYPERLINK(\"https://example.invalid\")", "'=HYPERLINK(\"https://example.invalid\")"),
        ("  +SUM(A1:A2)", "'  +SUM(A1:A2)"),
        ("@SUM(A1:A2)", "'@SUM(A1:A2)"),
        ("ordinary text", "ordinary text"),
        ("", ""),
    ],
)
def test_csv_safe_value_neutralises_formula_like_text(value, expected):
    from nema_agora.core import csv_safe_value

    assert csv_safe_value(value) == expected


def test_csv_safe_value_preserves_numeric_negative_coordinates():
    from nema_agora.core import csv_safe_value

    assert csv_safe_value(-1.25) == -1.25


def test_site_label_length_is_limited():
    errors = validate_observation(
        site="S" * 121, description="An observation", consent_confirmed=True
    )
    assert any("120 characters" in error for error in errors)


def test_evidence_reference_length_is_limited():
    with pytest.raises(ValueError, match="300 characters"):
        make_observation(
            observation_date=date(2026, 10, 3),
            category=CATEGORIES[0],
            severity="Low",
            site="Pilot A",
            description="Test observation",
            latitude=0,
            longitude=0,
            consent_confirmed=True,
            created_at="2026-10-03T12:00:00+03:00",
            evidence_reference="e" * 301,
        )
