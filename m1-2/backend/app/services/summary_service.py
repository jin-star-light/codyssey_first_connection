from __future__ import annotations

from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

from app.schemas.data import (
    DataRecord,
    DataSummary,
    DatePeriod,
    DateValue,
    ExtremeMetric,
    SummaryMetrics,
    TrendResult,
)
from app.services.data_service import DataService


ONE_DECIMAL = Decimal("0.1")
TREND_THRESHOLD = Decimal("0.2")


def _round(value: Decimal) -> Decimal:
    return value.quantize(ONE_DECIMAL, rounding=ROUND_HALF_UP)


def _average(records: Sequence[DataRecord]) -> Decimal:
    return sum((record.value for record in records), Decimal("0")) / len(records)


def calculate_summary(records: Sequence[DataRecord]) -> DataSummary:
    ordered = sorted(records, key=lambda record: record.date)
    if not ordered:
        return DataSummary(
            count=0,
            period=None,
            metrics=None,
            trend=TrendResult(status="no_data"),
        )

    first = ordered[0]
    latest = ordered[-1]
    minimum = min(ordered, key=lambda record: record.value)
    maximum = max(ordered, key=lambda record: record.value)
    total = sum((record.value for record in ordered), Decimal("0"))

    if len(ordered) < 20:
        trend = TrendResult(status="insufficient_data")
    else:
        previous_average = _average(ordered[-20:-10])
        recent_average = _average(ordered[-10:])
        difference = recent_average - previous_average
        if difference > TREND_THRESHOLD:
            status = "increase"
        elif difference < -TREND_THRESHOLD:
            status = "decrease"
        else:
            status = "maintain"
        trend = TrendResult(
            status=status,
            previous_average=_round(previous_average),
            recent_average=_round(recent_average),
            difference=_round(difference),
        )

    return DataSummary(
        count=len(ordered),
        period=DatePeriod(start=first.date, end=latest.date),
        metrics=SummaryMetrics(
            total=_round(total),
            average=_round(total / len(ordered)),
            minimum=ExtremeMetric(date=minimum.date, value=_round(minimum.value)),
            maximum=ExtremeMetric(date=maximum.date, value=_round(maximum.value)),
            first=DateValue(date=first.date, value=_round(first.value)),
            latest=DateValue(date=latest.date, value=_round(latest.value)),
            total_change=_round(latest.value - first.value),
        ),
        trend=trend,
    )


class SummaryService:
    def __init__(self, data_service: DataService) -> None:
        self.data_service = data_service

    def get_summary(self) -> DataSummary:
        return calculate_summary(
            self.data_service.list_records(descending=False)
        )
