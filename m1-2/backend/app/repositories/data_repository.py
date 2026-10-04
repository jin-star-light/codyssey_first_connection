from __future__ import annotations

from typing import Protocol

from app.schemas.data import DataCreate, DataRecord


class DataRepository(Protocol):
    def list(self) -> list[DataRecord]: ...

    def get(self, record_id: str) -> DataRecord | None: ...

    def create(self, data: DataCreate) -> DataRecord: ...

    def replace(self, record_id: str, data: DataCreate) -> DataRecord | None: ...

    def delete(self, record_id: str) -> bool: ...
