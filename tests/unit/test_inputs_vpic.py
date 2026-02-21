"""Tests for vPIC input validators and models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.inputs import (
    DecodeVinBatchInput,
    DecodeWMIInput,
    GetEquipmentPlantCodesInput,
    GetMakesInput,
    GetManufacturersInput,
    GetModelsInput,
    GetPartsInput,
    GetVehicleTypesInput,
    GetVehicleVariablesInput,
    validate_date_mmddyyyy,
    validate_equipment_type,
    validate_manufacturer,
    validate_page,
    validate_parts_type,
    validate_positive_id,
    validate_variable_name_or_id,
    validate_vehicle_type,
    validate_vin_batch,
    validate_wmi,
)


class TestValidateWMI:
    def test_valid_3char(self):
        assert validate_wmi("1FT") == "1FT"

    def test_valid_6char(self):
        assert validate_wmi("1FTFW1") == "1FTFW1"

    def test_lowercase_uppercased(self):
        assert validate_wmi("abc") == "ABC"

    def test_invalid_length(self):
        with pytest.raises(ValueError, match="3 or 6"):
            validate_wmi("AB")

    def test_invalid_chars(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_wmi("I@@")


class TestValidateManufacturer:
    def test_valid(self):
        assert validate_manufacturer("Ford Motor Company") == "Ford Motor Company"

    def test_empty(self):
        with pytest.raises(ValueError, match="not be empty"):
            validate_manufacturer("")

    def test_too_long(self):
        with pytest.raises(ValueError, match="128"):
            validate_manufacturer("x" * 129)

    def test_invalid_chars(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_manufacturer("Ford<script>")


class TestValidatePage:
    def test_valid(self):
        assert validate_page(1) == 1
        assert validate_page(1000) == 1000

    def test_too_low(self):
        with pytest.raises(ValueError):
            validate_page(0)

    def test_too_high(self):
        with pytest.raises(ValueError):
            validate_page(1001)


class TestValidatePositiveId:
    def test_valid(self):
        assert validate_positive_id(1) == 1

    def test_zero(self):
        with pytest.raises(ValueError):
            validate_positive_id(0)

    def test_negative(self):
        with pytest.raises(ValueError):
            validate_positive_id(-5)


class TestValidateVehicleType:
    def test_valid(self):
        assert validate_vehicle_type("Passenger Car") == "Passenger Car"

    def test_empty(self):
        with pytest.raises(ValueError, match="not be empty"):
            validate_vehicle_type("")

    def test_too_long(self):
        with pytest.raises(ValueError, match="64"):
            validate_vehicle_type("x" * 65)


class TestValidateDateMMDDYYYY:
    def test_valid(self):
        assert validate_date_mmddyyyy("1/1/2020") == "1/1/2020"
        assert validate_date_mmddyyyy("12/31/2023") == "12/31/2023"

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="M/D/YYYY"):
            validate_date_mmddyyyy("2020-01-01")

    def test_invalid_month(self):
        with pytest.raises(ValueError, match="out of range"):
            validate_date_mmddyyyy("13/1/2020")


class TestValidateVariableNameOrId:
    def test_valid_name(self):
        assert validate_variable_name_or_id("Body Class") == "Body Class"

    def test_valid_id(self):
        assert validate_variable_name_or_id("5") == "5"

    def test_empty(self):
        with pytest.raises(ValueError, match="not be empty"):
            validate_variable_name_or_id("")


class TestValidateVinBatch:
    def test_valid(self):
        result = validate_vin_batch("5UXWX7C5*BA,2011;5YJSA3DS*EF")
        assert "5UXWX7C5*BA" in result

    def test_empty(self):
        with pytest.raises(ValueError, match="not be empty"):
            validate_vin_batch("")

    def test_too_many(self):
        vins = ";".join([f"VIN{i}" for i in range(51)])
        with pytest.raises(ValueError, match="50"):
            validate_vin_batch(vins)


class TestValidateEquipmentType:
    def test_valid(self):
        for t in (1, 3, 13, 16):
            assert validate_equipment_type(t) == t

    def test_invalid(self):
        with pytest.raises(ValueError, match="1, 3, 13, or 16"):
            validate_equipment_type(2)


class TestValidatePartsType:
    def test_valid(self):
        assert validate_parts_type(565) == 565
        assert validate_parts_type(566) == 566

    def test_invalid(self):
        with pytest.raises(ValueError, match="565 or 566"):
            validate_parts_type(100)


class TestDecodeWMIInput:
    def test_valid(self):
        m = DecodeWMIInput(wmi="1FT")
        assert m.wmi == "1FT"

    def test_invalid(self):
        with pytest.raises(ValidationError):
            DecodeWMIInput(wmi="X")


class TestDecodeVinBatchInput:
    def test_valid(self):
        m = DecodeVinBatchInput(vins="5UXWX7C5*BA,2011;5YJSA3DS*EF")
        assert "5UXWX7C5*BA" in m.vins


class TestGetManufacturersInput:
    def test_defaults(self):
        m = GetManufacturersInput()
        assert m.manufacturer is None
        assert m.page is None
        assert m.include_wmis is False


class TestGetMakesInput:
    def test_defaults(self):
        m = GetMakesInput()
        assert m.manufacturer is None


class TestGetModelsInput:
    def test_make_only(self):
        m = GetModelsInput(make="Honda")
        assert m.make == "Honda"

    def test_make_id_only(self):
        m = GetModelsInput(make_id=474)
        assert m.make_id == 474

    def test_both_rejected(self):
        with pytest.raises(ValidationError, match="not both"):
            GetModelsInput(make="Honda", make_id=474)

    def test_neither_rejected(self):
        with pytest.raises(ValidationError, match="either make or make_id"):
            GetModelsInput()


class TestGetVehicleTypesInput:
    def test_make(self):
        m = GetVehicleTypesInput(make="Ford")
        assert m.make == "Ford"

    def test_both_rejected(self):
        with pytest.raises(ValidationError, match="not both"):
            GetVehicleTypesInput(make="Ford", make_id=1)

    def test_neither_rejected(self):
        with pytest.raises(ValidationError, match="either make or make_id"):
            GetVehicleTypesInput()


class TestGetVehicleVariablesInput:
    def test_no_variable(self):
        m = GetVehicleVariablesInput()
        assert m.variable is None

    def test_with_variable(self):
        m = GetVehicleVariablesInput(variable="Body Class")
        assert m.variable == "Body Class"


class TestGetPartsInput:
    def test_valid(self):
        m = GetPartsInput(type=565, from_date="1/1/2020", to_date="12/31/2020")
        assert m.type == 565

    def test_invalid_type(self):
        with pytest.raises(ValidationError):
            GetPartsInput(type=100, from_date="1/1/2020", to_date="12/31/2020")


class TestGetEquipmentPlantCodesInput:
    def test_valid(self):
        m = GetEquipmentPlantCodesInput(year=2020, equipment_type=1)
        assert m.year == 2020

    def test_invalid_equipment_type(self):
        with pytest.raises(ValidationError):
            GetEquipmentPlantCodesInput(year=2020, equipment_type=99)
