from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.schemas.data import DataRecord
from app.services.data_service import DataService
from app.services.summary_service import SummaryService, calculate_summary
from tests.fakes.repositories import InMemoryDataRepository


def record(day: date, value: str) -> DataRecord:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    return DataRecord(
        id=day.isoformat(),
        date=day,
        value=value,
        memo="",
        created_at=timestamp,
        updated_at=timestamp,
    )


def records(count: int, *, value: str = "2") -> list[DataRecord]:
    start = date(2025, 1, 1)
    return [record(start + timedelta(days=index), value) for index in range(count)]


def window_records(previous: str, recent: str) -> list[DataRecord]:
    start = date(2025, 1, 1)
    values = [previous] * 10 + [recent] * 10
    return [record(start + timedelta(days=index), value) for index, value in enumerate(values)]


def test_empty_summary_has_no_period_or_metrics():
    result = calculate_summary([])
    assert result.count == 0
    assert result.period is None
    assert result.metrics is None
    assert result.trend.status == "no_data"


def test_nineteen_records_report_insufficient_trend():
    result = calculate_summary(records(19))
    assert result.trend.status == "insufficient_data"
    assert result.trend.previous_average is None
    assert result.trend.recent_average is None


def test_summary_sorts_and_calculates_metrics_with_one_decimal_rounding():
    input_records = [
        record(date(2025, 1, 3), "3.24"),
        record(date(2025, 1, 1), "1.01"),
        record(date(2025, 1, 2), "2.10"),
    ]
    result = calculate_summary(input_records)

    assert result.period.start == date(2025, 1, 1)
    assert result.period.end == date(2025, 1, 3)
    assert result.metrics.total == Decimal("6.4")
    assert result.metrics.average == Decimal("2.1")
    assert result.metrics.minimum.date == date(2025, 1, 1)
    assert result.metrics.minimum.value == Decimal("1.0")
    assert result.metrics.maximum.date == date(2025, 1, 3)
    assert result.metrics.maximum.value == Decimal("3.2")
    assert result.metrics.first.value == Decimal("1.0")
    assert result.metrics.latest.value == Decimal("3.2")
    assert result.metrics.total_change == Decimal("2.2")


def test_trend_compares_latest_ten_with_previous_ten():
    result = calculate_summary(window_records(previous="2", recent="3"))
    assert result.trend.status == "increase"
    assert result.trend.previous_average == Decimal("2.0")
    assert result.trend.recent_average == Decimal("3.0")
    assert result.trend.difference == Decimal("1.0")


def test_trend_detects_decrease_and_maintain_threshold():
    assert calculate_summary(window_records("4", "3")).trend.status == "decrease"
    assert calculate_summary(window_records("2", "2.2")).trend.status == "maintain"
    assert calculate_summary(window_records("2", "2.21")).trend.status == "increase"


def test_summary_service_requests_oldest_first_records():
    class TrackingDataService(DataService):
        def __init__(self) -> None:
            super().__init__(InMemoryDataRepository())
            self.descending = None

        def list_records(self, *, descending: bool = True) -> list[DataRecord]:
            self.descending = descending
            return records(1)

    data_service = TrackingDataService()
    result = SummaryService(data_service).get_summary()
    assert result.count == 1
    assert data_service.descending is False
