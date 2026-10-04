import pytest
from pydantic import ValidationError

from app.errors import AIProviderError, RecordNotFoundError
from app.schemas.chat import ChatRequest
from app.schemas.data import DataCreate
from app.services.chat_service import ChatService, build_system_prompt
from app.services.conversation_service import ConversationService
from app.services.data_service import DataService
from app.services.summary_service import SummaryService
from tests.fakes.ai_client import FakeAIClient
from tests.fakes.repositories import (
    InMemoryConversationRepository,
    InMemoryDataRepository,
)


def services(ai=None):
    data = DataService(InMemoryDataRepository())
    for index in range(20):
        data.create_record(
            DataCreate(date=f"2025-01-{index + 1:02d}", value=2 if index < 10 else 3)
        )
    conversations = ConversationService(InMemoryConversationRepository())
    ai = ai or FakeAIClient()
    return ChatService(SummaryService(data), conversations, ai), conversations, ai


def test_chat_injects_current_summary_and_saves_successful_exchange():
    service, conversations, ai = services()
    result = service.chat(ChatRequest(message="최근 학습량이 어때?"))
    assert '"increase"' in ai.system_prompt
    assert result.answer == "최근 학습시간이 증가했어요."
    saved = conversations.get(result.conversation_id)
    assert [message.role for message in saved.messages] == ["user", "assistant"]


def test_existing_history_is_passed_before_new_question():
    service, conversations, ai = services()
    first = service.chat(ChatRequest(message="첫 질문"))
    service.chat(ChatRequest(message="후속 질문", conversation_id=first.conversation_id))
    assert [message["content"] for message in ai.messages][-3:] == [
        "첫 질문",
        "최근 학습시간이 증가했어요.",
        "후속 질문",
    ]
    assert len(conversations.get(first.conversation_id).messages) == 4


def test_ai_failure_does_not_save_conversation():
    service, conversations, _ai = services(FakeAIClient(fail=True))
    with pytest.raises(AIProviderError):
        service.chat(ChatRequest(message="분석해줘"))
    assert conversations.list() == []


def test_chat_validates_input_and_missing_conversation():
    service, _conversations, _ai = services()
    with pytest.raises(ValidationError):
        ChatRequest(message="가" * 1001)
    with pytest.raises(RecordNotFoundError):
        service.chat(ChatRequest(message="질문", conversation_id="missing"))


def test_system_prompt_prohibits_inventing_missing_records():
    prompt = build_system_prompt({"count": 0, "trend": {"status": "no_data"}})
    assert "없는 데이터" in prompt
    assert "추측" in prompt
