from datetime import date

import pytest

from app.errors import DuplicateDateError, RecordNotFoundError
from app.schemas.data import DataCreate, DataUpdate
from app.services.data_service import DataService
from tests.fakes.repositories import InMemoryDataRepository


def payload(day: str, value: str = "2.5", memo: str = "학습") -> DataCreate:
    return DataCreate(date=day, value=value, memo=memo)


def test_create_get_and_newest_first_listing():
    service = DataService(InMemoryDataRepository())
    older = service.create_record(payload("2026-01-01"))
    newer = service.create_record(payload("2026-01-03", "4"))

    assert service.get_record(older.id) == older
    assert [item.id for item in service.list_records()] == [newer.id, older.id]
    assert [item.id for item in service.list_records(descending=False)] == [older.id, newer.id]


def test_update_can_change_date_and_preserves_created_at():
    service = DataService(InMemoryDataRepository())
    original = service.create_record(payload("2026-01-01"))

    updated = service.update_record(
        original.id,
        DataUpdate(date=date(2026, 1, 2), value="3.75", memo="수정"),
    )

    assert updated.id == "2026-01-02"
    assert updated.created_at == original.created_at
    assert updated.updated_at >= original.updated_at
    with pytest.raises(RecordNotFoundError):
        service.get_record(original.id)


def test_delete_and_missing_records_raise_not_found():
    service = DataService(InMemoryDataRepository())
    record = service.create_record(payload("2026-01-01"))
    service.delete_record(record.id)

    for operation in (
        lambda: service.get_record(record.id),
        lambda: service.update_record(record.id, DataUpdate(**payload("2026-01-02").model_dump())),
        lambda: service.delete_record(record.id),
    ):
        with pytest.raises(RecordNotFoundError):
            operation()


def test_duplicate_create_preserves_first_record():
    service = DataService(InMemoryDataRepository())
    first = service.create_record(payload("2026-01-01", "2", "처음"))

    with pytest.raises(DuplicateDateError):
        service.create_record(payload("2026-01-01", "8", "중복"))

    assert service.get_record(first.id) == first


def test_update_to_existing_date_is_rejected_without_mutation():
    service = DataService(InMemoryDataRepository())
    first = service.create_record(payload("2026-01-01", "2", "첫째"))
    second = service.create_record(payload("2026-01-02", "3", "둘째"))

    with pytest.raises(DuplicateDateError):
        service.update_record(
            second.id,
            DataUpdate(date=first.date, value="9", memo="덮어쓰기 시도"),
        )

    assert service.get_record(first.id) == first
    assert service.get_record(second.id) == second
