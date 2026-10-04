from pathlib import Path

import pytest

from app.services.data_service import DataService
from scripts.import_csv import import_records, parse_csv
from tests.fakes.repositories import InMemoryDataRepository


def write(path: Path, text: str, *, bom=False):
    path.write_text(text, encoding="utf-8-sig" if bom else "utf-8")


def test_parse_csv_supports_bom_blank_rows_and_reports_invalid(tmp_path: Path):
    path = tmp_path / "data.csv"
    write(
        path,
        "date,value,memo\n2025-01-01,2,학습\n,,\n2025-01-02,0,오류\n",
        bom=True,
    )
    batch = parse_csv(path)
    assert len(batch.records) == 1
    assert len(batch.errors) == 1
    assert batch.errors[0]["row"] == 4


def test_parse_csv_requires_exact_headers_and_rejects_duplicate_dates(tmp_path: Path):
    bad_headers = tmp_path / "headers.csv"
    write(bad_headers, "value,date,memo\n2,2025-01-01,x\n")
    with pytest.raises(ValueError, match="date,value,memo"):
        parse_csv(bad_headers)

    duplicates = tmp_path / "duplicates.csv"
    write(
        duplicates,
        "date,value,memo\n2025-01-01,2,첫째\n2025-01-01,3,둘째\n",
    )
    batch = parse_csv(duplicates)
    assert len(batch.records) == 1
    assert len(batch.errors) == 1


def test_dry_run_performs_no_writes(tmp_path: Path):
    path = tmp_path / "data.csv"
    write(path, "date,value,memo\n2025-01-01,2,학습\n")
    service = DataService(InMemoryDataRepository())
    report = import_records(service, parse_csv(path), dry_run=True)
    assert report.model_dump() == {"valid": 1, "created": 0, "skipped": 0, "failed": 0}
    assert service.list_records() == []


def test_import_creates_records_and_skips_dates_already_stored(tmp_path: Path):
    path = tmp_path / "data.csv"
    write(path, "date,value,memo\n2025-01-01,2,학습\n")
    service = DataService(InMemoryDataRepository())
    batch = parse_csv(path)
    assert import_records(service, batch, dry_run=False).created == 1
    report = import_records(service, batch, dry_run=False)
    assert report.created == 0
    assert report.skipped == 1
    assert report.failed == 0
