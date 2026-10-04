from datetime import UTC, datetime

import pytest

from app.errors import DuplicateDateError
from app.repositories import data_repository as repository_module
from app.repositories.data_repository import FirestoreDataRepository
from app.schemas.data import DataCreate


NOW = datetime(2026, 1, 1, tzinfo=UTC)


class Snapshot:
    def __init__(self, document):
        self.document = document
        self.id = document.id

    @property
    def exists(self):
        return self.document.id in self.document.collection.documents

    def to_dict(self):
        return dict(self.document.collection.documents[self.document.id])


class Document:
    def __init__(self, collection, document_id):
        self.collection = collection
        self.id = document_id

    def get(self, transaction=None):
        return Snapshot(self)


class Query:
    def __init__(self, collection):
        self.collection = collection

    def stream(self):
        for document_id in sorted(self.collection.documents):
            yield Snapshot(Document(self.collection, document_id))


class Collection:
    def __init__(self):
        self.documents = {}
        self.ordering = None

    def document(self, document_id):
        return Document(self, document_id)

    def order_by(self, field, direction):
        self.ordering = (field, direction)
        return Query(self)


class Transaction:
    def set(self, document, payload):
        normalized = {
            key: NOW if value is SERVER_TIMESTAMP else value
            for key, value in payload.items()
        }
        document.collection.documents[document.id] = normalized

    def delete(self, document):
        document.collection.documents.pop(document.id, None)


class Client:
    def __init__(self):
        self.data = Collection()
        self.requested_collection = None

    def collection(self, name):
        self.requested_collection = name
        return self.data

    def transaction(self):
        return Transaction()


SERVER_TIMESTAMP = object()


@pytest.fixture(autouse=True)
def simple_transactions(monkeypatch):
    monkeypatch.setattr(repository_module.firestore, "SERVER_TIMESTAMP", SERVER_TIMESTAMP)
    monkeypatch.setattr(repository_module.firestore, "transactional", lambda function: function)


def create_payload(day: str, value: str = "2", memo: str = "학습"):
    return DataCreate(date=day, value=value, memo=memo)


def test_firestore_repository_uses_data_collection_date_ids_and_ordering():
    client = Client()
    repository = FirestoreDataRepository(client)
    repository.create(create_payload("2025-01-02", "3"))
    repository.create(create_payload("2025-01-01", "2"))

    records = repository.list()
    assert client.requested_collection == "data"
    assert set(client.data.documents) == {"2025-01-01", "2025-01-02"}
    assert client.data.ordering[0] == "date"
    assert [record.id for record in records] == ["2025-01-01", "2025-01-02"]
    assert records[0].created_at == NOW


def test_duplicate_create_is_atomic_and_preserves_first_record():
    repository = FirestoreDataRepository(Client())
    first = repository.create(create_payload("2025-01-01", "2", "처음"))

    with pytest.raises(DuplicateDateError):
        repository.create(create_payload("2025-01-01", "9", "중복"))

    assert repository.get(first.id) == first


def test_replace_can_move_date_and_rejects_collision_without_mutation():
    repository = FirestoreDataRepository(Client())
    first = repository.create(create_payload("2025-01-01", "2"))
    second = repository.create(create_payload("2025-01-02", "3"))

    with pytest.raises(DuplicateDateError):
        repository.replace(second.id, create_payload(first.id, "8"))
    assert repository.get(first.id) == first
    assert repository.get(second.id) == second

    moved = repository.replace(second.id, create_payload("2025-01-03", "4"))
    assert moved.id == "2025-01-03"
    assert moved.created_at == second.created_at
    assert repository.get(second.id) is None


def test_missing_replace_and_delete_return_falsey_values():
    repository = FirestoreDataRepository(Client())
    assert repository.replace("missing", create_payload("2025-01-01")) is None
    assert repository.delete("missing") is False
