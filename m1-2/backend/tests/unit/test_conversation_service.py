import pytest
from pydantic import ValidationError

from app.errors import RecordNotFoundError
from app.schemas.conversations import ConversationCreate, MessageInput
from app.services.conversation_service import ConversationService
from tests.fakes.repositories import InMemoryConversationRepository


def request(content="첫 번째 질문", *, role="user", title=None):
    return ConversationCreate(
        title=title,
        messages=[MessageInput(role=role, content=content)],
    )


def test_create_requires_user_message_and_defaults_capped_title():
    service = ConversationService(InMemoryConversationRepository())
    text = "가" * 80
    created = service.create(request(text))
    assert len(created.title) == 60
    assert created.title.endswith("...")
    assert created.messages[0].content == text

    with pytest.raises(ValidationError):
        request("assistant only", role="assistant")


def test_message_limits_are_validated():
    with pytest.raises(ValidationError):
        request("가" * 4001)
    with pytest.raises(ValidationError):
        ConversationCreate(
            messages=[MessageInput(role="user", content="질문")] * 101
        )


def test_list_is_newest_first_and_omits_message_bodies():
    service = ConversationService(InMemoryConversationRepository())
    first = service.create(request("첫 대화"))
    second = service.create(request("두 번째 대화"))
    service.append_exchange(first.id, "후속 질문", "후속 답변")

    items = service.list()
    assert items[0].id == first.id
    assert items[0].message_count == 3
    assert items[1].id == second.id
    assert not hasattr(items[0], "messages")


def test_get_append_and_delete_missing_ids_raise_not_found():
    service = ConversationService(InMemoryConversationRepository())
    created = service.create(request())
    updated = service.append_exchange(created.id, "추가 질문", "추가 답변")
    assert [message.role for message in updated.messages[-2:]] == ["user", "assistant"]
    assert service.get(created.id).messages[-1].content == "추가 답변"
    service.delete(created.id)

    for operation in (
        lambda: service.get(created.id),
        lambda: service.append_exchange(created.id, "질문", "답변"),
        lambda: service.delete(created.id),
    ):
        with pytest.raises(RecordNotFoundError):
            operation()
