from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from firebase_admin import firestore

from app.errors import DuplicateDateError
from app.schemas.data import DataCreate, DataRecord


class DataRepository(Protocol):
    def list(self) -> list[DataRecord]: ...

    def get(self, record_id: str) -> DataRecord | None: ...

    def create(self, data: DataCreate) -> DataRecord: ...

    def replace(self, record_id: str, data: DataCreate) -> DataRecord | None: ...

    def delete(self, record_id: str) -> bool: ...


class FirestoreDataRepository:
    def __init__(self, client: Any) -> None:
        self.collection = client.collection("data")
        self.client = client

    @staticmethod
    def _payload(data: DataCreate, *, preserve_created_at: Any = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "date": data.date.isoformat(),
            "value": float(data.value),
            "memo": data.memo,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
        payload["created_at"] = (
            preserve_created_at
            if preserve_created_at is not None
            else firestore.SERVER_TIMESTAMP
        )
        return payload

    @staticmethod
    def _record(snapshot: Any) -> DataRecord:
        payload = snapshot.to_dict()
        return DataRecord(id=snapshot.id, **payload)

    def list(self) -> list[DataRecord]:
        query = self.collection.order_by(
            "date", direction=firestore.Query.ASCENDING
        )
        return [self._record(snapshot) for snapshot in query.stream()]

    def get(self, record_id: str) -> DataRecord | None:
        snapshot = self.collection.document(record_id).get()
        return self._record(snapshot) if snapshot.exists else None

    def create(self, data: DataCreate) -> DataRecord:
        record_id = data.date.isoformat()
        reference = self.collection.document(record_id)
        transaction = self.client.transaction()

        @firestore.transactional
        def create_in_transaction(active_transaction: Any) -> None:
            if reference.get(transaction=active_transaction).exists:
                raise DuplicateDateError(f"A record already exists for {record_id}")
            active_transaction.set(reference, self._payload(data))

        create_in_transaction(transaction)
        record = self.get(record_id)
        if record is None:
            raise RuntimeError("Firestore did not return the created record")
        return record

    def replace(self, record_id: str, data: DataCreate) -> DataRecord | None:
        current_reference = self.collection.document(record_id)
        next_id = data.date.isoformat()
        next_reference = self.collection.document(next_id)
        transaction = self.client.transaction()

        @firestore.transactional
        def replace_in_transaction(active_transaction: Any) -> bool:
            current = current_reference.get(transaction=active_transaction)
            if not current.exists:
                return False
            if next_id != record_id and next_reference.get(
                transaction=active_transaction
            ).exists:
                raise DuplicateDateError(f"A record already exists for {next_id}")
            created_at: datetime = current.to_dict()["created_at"]
            active_transaction.set(
                next_reference,
                self._payload(data, preserve_created_at=created_at),
            )
            if next_id != record_id:
                active_transaction.delete(current_reference)
            return True

        if not replace_in_transaction(transaction):
            return None
        return self.get(next_id)

    def delete(self, record_id: str) -> bool:
        reference = self.collection.document(record_id)
        transaction = self.client.transaction()

        @firestore.transactional
        def delete_in_transaction(active_transaction: Any) -> bool:
            if not reference.get(transaction=active_transaction).exists:
                return False
            active_transaction.delete(reference)
            return True

        return delete_in_transaction(transaction)
