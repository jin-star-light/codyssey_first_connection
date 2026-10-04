from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

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


class DatePeriod(BaseModel):
    start: date
    end: date


class DateValue(BaseModel):
    date: date
    value: Decimal

    @field_serializer("value", when_used="json")
    def serialize_value(self, value: Decimal) -> float:
        return float(value)


class ExtremeMetric(DateValue):
    pass


class SummaryMetrics(BaseModel):
    total: Decimal
    average: Decimal
    minimum: ExtremeMetric
    maximum: ExtremeMetric
    first: DateValue
    latest: DateValue
    total_change: Decimal

    @field_serializer("total", "average", "total_change", when_used="json")
    def serialize_decimal(self, value: Decimal) -> float:
        return float(value)


class TrendResult(BaseModel):
    status: Literal["no_data", "insufficient_data", "increase", "decrease", "maintain"]
    previous_average: Decimal | None = None
    recent_average: Decimal | None = None
    difference: Decimal | None = None

    @field_serializer(
        "previous_average", "recent_average", "difference", when_used="json"
    )
    def serialize_optional_decimal(self, value: Decimal | None) -> float | None:
        return float(value) if value is not None else None


class DataSummary(BaseModel):
    count: int
    period: DatePeriod | None
    metrics: SummaryMetrics | None
    trend: TrendResult
