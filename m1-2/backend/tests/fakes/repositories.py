from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

from app.errors import DuplicateDateError
from app.schemas.data import DataCreate, DataRecord


class InMemoryDataRepository:
    def __init__(self) -> None:
        self._records: dict[str, DataRecord] = {}

    def list(self) -> list[DataRecord]:
        return [deepcopy(record) for record in self._records.values()]

    def get(self, record_id: str) -> DataRecord | None:
        record = self._records.get(record_id)
        return deepcopy(record) if record else None

    def create(self, data: DataCreate) -> DataRecord:
        record_id = data.date.isoformat()
        if record_id in self._records:
            raise DuplicateDateError(f"A record already exists for {record_id}")
        now = datetime.now(UTC)
        record = DataRecord(id=record_id, **data.model_dump(), created_at=now, updated_at=now)
        self._records[record_id] = deepcopy(record)
        return deepcopy(record)

    def replace(self, record_id: str, data: DataCreate) -> DataRecord | None:
        current = self._records.get(record_id)
        if current is None:
            return None
        next_id = data.date.isoformat()
        if next_id != record_id and next_id in self._records:
            raise DuplicateDateError(f"A record already exists for {next_id}")
        updated = DataRecord(
            id=next_id,
            **data.model_dump(),
            created_at=current.created_at,
            updated_at=datetime.now(UTC),
        )
        del self._records[record_id]
        self._records[next_id] = deepcopy(updated)
        return deepcopy(updated)

    def delete(self, record_id: str) -> bool:
        return self._records.pop(record_id, None) is not None
