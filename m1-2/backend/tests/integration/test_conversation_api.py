from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.conversation_service import ConversationService
from tests.fakes.repositories import InMemoryConversationRepository


def client():
    return TestClient(
        create_app(
            Settings.for_test(),
            conversation_service=ConversationService(
                InMemoryConversationRepository()
            ),
        )
    )


def payload(content="학습시간을 분석해줘"):
    return {"messages": [{"role": "user", "content": content}]}


def test_conversation_create_list_detail_and_delete_contract():
    api = client()
    created_response = api.post("/api/conversations", json=payload())
    assert created_response.status_code == 201
    created = created_response.json()
    assert created["title"] == "학습시간을 분석해줘"

    listing = api.get("/api/conversations")
    assert listing.status_code == 200
    assert listing.json()["items"][0]["message_count"] == 1
    assert "messages" not in listing.json()["items"][0]

    detail = api.get(f"/api/conversations/{created['id']}")
    assert detail.status_code == 200
    assert detail.json()["messages"][0]["content"] == "학습시간을 분석해줘"

    deleted = api.delete(f"/api/conversations/{created['id']}")
    assert deleted.status_code == 204
    assert api.get(f"/api/conversations/{created['id']}").status_code == 404


def test_conversation_validation_and_missing_errors():
    api = client()
    assert api.post("/api/conversations", json={"messages": []}).status_code == 422
    response = api.get("/api/conversations/unknown")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "record_not_found"
