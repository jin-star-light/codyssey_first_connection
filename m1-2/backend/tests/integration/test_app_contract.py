from fastapi.testclient import TestClient

from app.config import Settings
from app.errors import DataStoreError
from app.main import create_app


class FailingDataService:
    def list_records(self, *, descending=True):
        raise DataStoreError("database-password=should-never-leak")


class EmptySummaryService:
    def get_summary(self):
        raise AssertionError("not used")


def test_datastore_errors_are_safe_and_stable():
    api = TestClient(
        create_app(
            Settings.for_test(),
            data_service=FailingDataService(),
            summary_service=EmptySummaryService(),
        ),
        raise_server_exceptions=False,
    )
    response = api.get("/api/data")
    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "datastore_unavailable",
        "message": "데이터 저장소를 일시적으로 사용할 수 없습니다.",
        "details": None,
    }
    assert "database-password" not in response.text
