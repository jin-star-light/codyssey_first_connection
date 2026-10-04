from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService
from app.services.data_service import DataService
from app.services.summary_service import SummaryService
from tests.fakes.ai_client import FakeAIClient
from tests.fakes.repositories import InMemoryConversationRepository, InMemoryDataRepository


def client(*, fail=False):
    data = DataService(InMemoryDataRepository())
    conversations = ConversationService(InMemoryConversationRepository())
    chat = ChatService(SummaryService(data), conversations, FakeAIClient(fail=fail))
    return TestClient(
        create_app(
            Settings.for_test(),
            data_service=data,
            summary_service=SummaryService(data),
            conversation_service=conversations,
            chat_service=chat,
        ),
        raise_server_exceptions=False,
    )


def test_chat_creates_and_continues_conversation():
    api = client()
    first = api.post("/api/chat", json={"message": "분석해줘"})
    assert first.status_code == 200
    assert first.json()["answer"]
    conversation_id = first.json()["conversation_id"]
    continued = api.post(
        "/api/chat",
        json={"message": "더 알려줘", "conversation_id": conversation_id},
    )
    assert continued.status_code == 200
    detail = api.get(f"/api/conversations/{conversation_id}").json()
    assert len(detail["messages"]) == 4


def test_chat_validation_missing_history_and_provider_failure():
    api = client()
    assert api.post("/api/chat", json={"message": ""}).status_code == 422
    assert api.post(
        "/api/chat", json={"message": "질문", "conversation_id": "missing"}
    ).status_code == 404

    failed = client(fail=True).post("/api/chat", json={"message": "질문"})
    assert failed.status_code == 502
    assert failed.json()["error"]["code"] == "ai_provider_error"
    assert "provider-secret" not in failed.text
