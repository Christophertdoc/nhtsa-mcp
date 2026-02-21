"""Tests for app/models/inputs.py — all validation paths."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models.inputs import (
    CarseatByGeoInput,
    CarseatByStateInput,
    CarseatByZipInput,
    ComplaintsByOdiInput,
    ComplaintsByVehicleInput,
    DecodeVinInput,
    RatingsByVehicleIdInput,
    RatingsSearchInput,
    RecallsByCampaignInput,
    RecallsByVehicleInput,
)


class TestVinValidation:
    def test_valid_vin(self):
        inp = DecodeVinInput(vin="1FA6P8AM0G5227539")
        assert inp.vin == "1FA6P8AM0G5227539"

    def test_vin_lowercased(self):
        inp = DecodeVinInput(vin="1fa6p8am0g5227539")
        assert inp.vin == "1FA6P8AM0G5227539"

    def test_vin_too_short(self):
        with pytest.raises(ValidationError, match="17 characters"):
            DecodeVinInput(vin="1FA6P8AM0G522753")

    def test_vin_too_long(self):
        with pytest.raises(ValidationError, match="17 characters"):
            DecodeVinInput(vin="1FA6P8AM0G52275390")

    def test_vin_with_I(self):
        with pytest.raises(ValidationError, match="invalid characters"):
            DecodeVinInput(vin="IFA6P8AM0G5227539")

    def test_vin_with_O(self):
        with pytest.raises(ValidationError, match="invalid characters"):
            DecodeVinInput(vin="OFA6P8AM0G5227539")

    def test_vin_with_Q(self):
        with pytest.raises(ValidationError, match="invalid characters"):
            DecodeVinInput(vin="QFA6P8AM0G5227539")

    def test_vin_with_special_chars(self):
        with pytest.raises(ValidationError):
            DecodeVinInput(vin="1FA6P8AM0G5227!39")

    def test_vin_with_spaces(self):
        with pytest.raises(ValidationError):
            DecodeVinInput(vin="1FA6P8AM0G5 27539")

    def test_vin_with_model_year(self):
        inp = DecodeVinInput(vin="1FA6P8AM0G5227539", model_year=2016)
        assert inp.model_year == 2016

    def test_vin_extended(self):
        inp = DecodeVinInput(vin="1FA6P8AM0G5227539", extended=True)
        assert inp.extended is True


class TestModelYear:
    def test_valid_year(self):
        inp = RatingsSearchInput(model_year=2020, make="Toyota", model="Camry")
        assert inp.model_year == 2020

    def test_year_1980(self):
        inp = RatingsSearchInput(model_year=1980, make="Toyota", model="Camry")
        assert inp.model_year == 1980

    def test_year_1979_fails(self):
        with pytest.raises(ValidationError, match="1980"):
            RatingsSearchInput(model_year=1979, make="Toyota", model="Camry")

    def test_year_current_plus_1(self):
        next_year = datetime.now(tz=UTC).year + 1
        inp = RatingsSearchInput(model_year=next_year, make="Toyota", model="Camry")
        assert inp.model_year == next_year

    def test_year_current_plus_2_fails(self):
        future = datetime.now(tz=UTC).year + 2
        with pytest.raises(ValidationError):
            RatingsSearchInput(model_year=future, make="Toyota", model="Camry")


class TestMakeModel:
    def test_title_case_normalization(self):
        inp = RatingsSearchInput(model_year=2020, make="toyota", model="camry")
        assert inp.make == "Toyota"
        assert inp.model == "Camry"

    def test_hyphenated(self):
        inp = RecallsByVehicleInput(model_year=2020, make="Mercedes-Benz", model="C-Class")
        assert inp.make == "Mercedes-Benz"
        assert inp.model == "C-Class"

    def test_empty_fails(self):
        with pytest.raises(ValidationError, match="empty"):
            RatingsSearchInput(model_year=2020, make="", model="Camry")

    def test_too_long_fails(self):
        with pytest.raises(ValidationError, match="64"):
            RatingsSearchInput(model_year=2020, make="A" * 65, model="Camry")

    def test_special_chars_fail(self):
        with pytest.raises(ValidationError):
            RatingsSearchInput(model_year=2020, make="Toyota!", model="Camry")


class TestCampaignNumber:
    def test_valid(self):
        inp = RecallsByCampaignInput(campaign_number="20V123000")
        assert inp.campaign_number == "20V123000"

    def test_lowercase_normalized(self):
        inp = RecallsByCampaignInput(campaign_number="20v123000")
        assert inp.campaign_number == "20V123000"

    def test_invalid_format(self):
        with pytest.raises(ValidationError, match="pattern"):
            RecallsByCampaignInput(campaign_number="INVALID")


class TestOdiNumber:
    def test_valid(self):
        inp = ComplaintsByOdiInput(odi_number="12345")
        assert inp.odi_number == "12345"

    def test_valid_long(self):
        inp = ComplaintsByOdiInput(odi_number="123456789012")
        assert inp.odi_number == "123456789012"

    def test_too_short(self):
        with pytest.raises(ValidationError, match="5-12"):
            ComplaintsByOdiInput(odi_number="1234")

    def test_too_long(self):
        with pytest.raises(ValidationError, match="5-12"):
            ComplaintsByOdiInput(odi_number="1234567890123")

    def test_non_digits(self):
        with pytest.raises(ValidationError):
            ComplaintsByOdiInput(odi_number="1234A")


class TestZipCode:
    def test_valid_5_digit(self):
        inp = CarseatByZipInput(zip="20001")
        assert inp.zip == "20001"

    def test_zip_plus_4_normalized(self):
        inp = CarseatByZipInput(zip="20001-1234")
        assert inp.zip == "20001"

    def test_invalid_zip(self):
        with pytest.raises(ValidationError, match="5-digit"):
            CarseatByZipInput(zip="2000")

    def test_non_numeric(self):
        with pytest.raises(ValidationError):
            CarseatByZipInput(zip="ABCDE")


class TestStateCode:
    def test_valid_state(self):
        inp = CarseatByStateInput(state="CA")
        assert inp.state == "CA"

    def test_lowercase_normalized(self):
        inp = CarseatByStateInput(state="ca")
        assert inp.state == "CA"

    def test_dc(self):
        inp = CarseatByStateInput(state="DC")
        assert inp.state == "DC"

    def test_territory_pr(self):
        inp = CarseatByStateInput(state="PR")
        assert inp.state == "PR"

    def test_invalid_state(self):
        with pytest.raises(ValidationError, match="valid US state"):
            CarseatByStateInput(state="XX")


class TestLang:
    def test_en(self):
        inp = CarseatByZipInput(zip="20001", lang="en")
        assert inp.lang == "english"

    def test_english(self):
        inp = CarseatByZipInput(zip="20001", lang="english")
        assert inp.lang == "english"

    def test_es(self):
        inp = CarseatByZipInput(zip="20001", lang="es")
        assert inp.lang == "spanish"

    def test_spanish(self):
        inp = CarseatByZipInput(zip="20001", lang="spanish")
        assert inp.lang == "spanish"

    def test_none(self):
        inp = CarseatByZipInput(zip="20001", lang=None)
        assert inp.lang is None

    def test_invalid(self):
        with pytest.raises(ValidationError, match="lang must be"):
            CarseatByZipInput(zip="20001", lang="fr")


class TestGeoInputs:
    def test_valid(self):
        inp = CarseatByGeoInput(lat=38.9, long=-77.0, miles=50)
        assert inp.lat == 38.9
        assert inp.long == -77.0
        assert inp.miles == 50

    def test_defaults(self):
        inp = CarseatByGeoInput(lat=0.0, long=0.0)
        assert inp.miles == 25

    def test_lat_out_of_range(self):
        with pytest.raises(ValidationError):
            CarseatByGeoInput(lat=91.0, long=0.0)

    def test_long_out_of_range(self):
        with pytest.raises(ValidationError):
            CarseatByGeoInput(lat=0.0, long=181.0)

    def test_miles_too_small(self):
        with pytest.raises(ValidationError):
            CarseatByGeoInput(lat=0.0, long=0.0, miles=0)

    def test_miles_too_large(self):
        with pytest.raises(ValidationError):
            CarseatByGeoInput(lat=0.0, long=0.0, miles=201)


class TestVehicleId:
    def test_valid(self):
        inp = RatingsByVehicleIdInput(vehicle_id=12345)
        assert inp.vehicle_id == 12345

    def test_zero_fails(self):
        with pytest.raises(ValidationError):
            RatingsByVehicleIdInput(vehicle_id=0)

    def test_negative_fails(self):
        with pytest.raises(ValidationError):
            RatingsByVehicleIdInput(vehicle_id=-1)


class TestFrozenModels:
    def test_decode_vin_immutable(self):
        inp = DecodeVinInput(vin="1FA6P8AM0G5227539")
        with pytest.raises(ValidationError):
            inp.vin = "XXXXXXXXXXXXX1234"  # type: ignore[misc]

    def test_complaints_immutable(self):
        inp = ComplaintsByVehicleInput(model_year=2020, make="Toyota", model="Camry")
        with pytest.raises(ValidationError):
            inp.model_year = 2021  # type: ignore[misc]
