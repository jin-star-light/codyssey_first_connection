from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ValidationError

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import Settings
from app.errors import DuplicateDateError
from app.firebase import create_firestore_client
from app.repositories.data_repository import FirestoreDataRepository
from app.schemas.data import DataCreate
from app.services.data_service import DataService


HEADERS = ["date", "value", "memo"]


@dataclass(frozen=True)
class ImportBatch:
    records: list[DataCreate]
    errors: list[dict[str, object]]


class ImportReport(BaseModel):
    valid: int
    created: int
    skipped: int
    failed: int


def parse_csv(path: Path) -> ImportBatch:
    records: list[DataCreate] = []
    errors: list[dict[str, object]] = []
    seen_dates: set[str] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != HEADERS:
            raise ValueError("CSV headers must be exactly: date,value,memo")
        for row_number, row in enumerate(reader, start=2):
            if not any((value or "").strip() for value in row.values()):
                continue
            try:
                record = DataCreate(**row)
                key = record.date.isoformat()
                if key in seen_dates:
                    raise ValueError("duplicate date in CSV")
                seen_dates.add(key)
                records.append(record)
            except (ValidationError, ValueError) as error:
                errors.append({"row": row_number, "message": str(error)})
    return ImportBatch(records=records, errors=errors)


def import_records(
    service: DataService | None,
    batch: ImportBatch,
    *,
    dry_run: bool,
) -> ImportReport:
    if dry_run:
        return ImportReport(
            valid=len(batch.records),
            created=0,
            skipped=0,
            failed=len(batch.errors),
        )
    if service is None:
        raise ValueError("data service is required unless --dry-run is used")
    created = 0
    skipped = 0
    failed = len(batch.errors)
    for record in batch.records:
        try:
            service.create_record(record)
            created += 1
        except DuplicateDateError:
            skipped += 1
        except Exception:
            failed += 1
    return ImportReport(
        valid=len(batch.records),
        created=created,
        skipped=skipped,
        failed=failed,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="학습시간 CSV를 Firestore에 가져옵니다.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args()
    batch = parse_csv(arguments.path)
    service = None
    if not arguments.dry_run:
        settings = Settings.from_env()
        client = create_firestore_client(settings.firebase_service_account_file)
        service = DataService(FirestoreDataRepository(client))
    report = import_records(service, batch, dry_run=arguments.dry_run)
    print(json.dumps(report.model_dump(), ensure_ascii=False))
    return 1 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
