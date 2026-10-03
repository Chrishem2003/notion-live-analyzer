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
