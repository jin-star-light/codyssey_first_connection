from __future__ import annotations

from app.errors import RecordNotFoundError
from app.repositories.data_repository import DataRepository
from app.schemas.data import DataCreate, DataRecord, DataUpdate


class DataService:
    def __init__(self, repository: DataRepository) -> None:
        self.repository = repository

    def create_record(self, data: DataCreate) -> DataRecord:
        return self.repository.create(data)

    def list_records(self, *, descending: bool = True) -> list[DataRecord]:
        return sorted(
            self.repository.list(),
            key=lambda record: record.date,
            reverse=descending,
        )

    def get_record(self, record_id: str) -> DataRecord:
        record = self.repository.get(record_id)
        if record is None:
            raise RecordNotFoundError(f"Record not found: {record_id}")
        return record

    def update_record(self, record_id: str, data: DataUpdate) -> DataRecord:
        record = self.repository.replace(record_id, DataCreate(**data.model_dump()))
        if record is None:
            raise RecordNotFoundError(f"Record not found: {record_id}")
        return record

    def delete_record(self, record_id: str) -> None:
        if not self.repository.delete(record_id):
            raise RecordNotFoundError(f"Record not found: {record_id}")
