from datetime import date, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.data import DataCreate, DataRecord, DataUpdate


@pytest.mark.parametrize("value", [0, -1, 24.1])
def test_study_hours_reject_out_of_range(value):
    with pytest.raises(ValidationError):
        DataCreate(date="2026-01-01", value=value, memo="")


def test_data_create_rejects_future_date_and_extra_fields():
    with pytest.raises(ValidationError):
        DataCreate(
            date=date.today() + timedelta(days=1),
            value=1,
            memo="",
            secret="x",
        )


def test_data_create_normalizes_decimal_and_memo_limit():
    record = DataCreate(date="2026-01-01", value="2.50", memo="집중 학습")
    assert record.value == Decimal("2.50")
    assert record.model_dump(mode="json")["value"] == 2.5

    with pytest.raises(ValidationError):
        DataUpdate(date="2026-01-01", value=2, memo="가" * 201)


def test_data_record_serializes_decimal_as_json_number():
    record = DataRecord(
        id="2026-01-01",
        date="2026-01-01",
        value="3.25",
        memo="복습",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    assert record.model_dump(mode="json")["value"] == 3.25
