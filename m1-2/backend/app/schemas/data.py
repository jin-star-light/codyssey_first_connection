from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class DataCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    value: Decimal = Field(gt=0, le=24)
    memo: str = Field(default="", max_length=200)

    @field_validator("date")
    @classmethod
    def reject_future_date(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("date must not be in the future")
        return value

    @field_serializer("value", when_used="json")
    def serialize_value(self, value: Decimal) -> float:
        return float(value)


class DataUpdate(DataCreate):
    pass


class DataRecord(DataCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class DataListResponse(BaseModel):
    items: list[DataRecord]
    count: int
