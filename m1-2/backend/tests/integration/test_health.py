from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health_and_cors_contract() -> None:
    client = TestClient(create_app(Settings.for_test()))

    assert client.get("/health").json() == {"status": "ok"}
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
