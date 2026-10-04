from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.data_service import DataService
from app.services.summary_service import SummaryService
from tests.fakes.repositories import InMemoryDataRepository


def client() -> TestClient:
    data_service = DataService(InMemoryDataRepository())
    return TestClient(
        create_app(
            Settings.for_test(),
            data_service=data_service,
            summary_service=SummaryService(data_service),
        )
    )


def payload(day="2025-01-01", value=2.5, memo="알고리즘 학습"):
    return {"date": day, "value": value, "memo": memo}


def test_create_list_update_delete_and_summary_contract():
    api = client()
    created = api.post("/api/data", json=payload())
    assert created.status_code == 201
    assert created.json()["id"] == "2025-01-01"

    listing = api.get("/api/data")
    assert listing.status_code == 200
    assert listing.json()["count"] == 1
    assert listing.json()["items"][0]["value"] == 2.5

    summary = api.get("/api/data/summary")
    assert summary.status_code == 200
    assert summary.json()["count"] == 1
    assert summary.json()["trend"]["status"] == "insufficient_data"

    updated = api.put(
        "/api/data/2025-01-01",
        json=payload(day="2025-01-02", value=4, memo="수정"),
    )
    assert updated.status_code == 200
    assert updated.json()["id"] == "2025-01-02"

    deleted = api.delete("/api/data/2025-01-02")
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert api.get("/api/data").json() == {"items": [], "count": 0}


def test_validation_not_found_and_duplicate_errors_use_public_envelope():
    api = client()
    invalid = api.post("/api/data", json=payload(value=0))
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"
    assert "input" not in str(invalid.json())

    missing = api.put("/api/data/missing", json=payload())
    assert missing.status_code == 404
    assert missing.json()["error"] == {
        "code": "record_not_found",
        "message": "요청한 데이터를 찾을 수 없습니다.",
        "details": None,
    }

    assert api.post("/api/data", json=payload()).status_code == 201
    duplicate = api.post("/api/data", json=payload(value=8, memo="중복"))
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "duplicate_date"
    assert api.get("/api/data").json()["items"][0]["memo"] == "알고리즘 학습"


def test_summary_route_is_not_treated_as_record_identifier():
    response = client().get("/api/data/summary")
    assert response.status_code == 200
    assert response.json()["trend"]["status"] == "no_data"
