from __future__ import annotations

from datetime import UTC, datetime

from app.errors import RecordNotFoundError
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.conversations import (
    Conversation,
    ConversationCreate,
    ConversationMessage,
    ConversationSummary,
)


def _default_title(content: str) -> str:
    return content if len(content) <= 60 else f"{content[:57]}..."


class ConversationService:
    def __init__(self, repository: ConversationRepository) -> None:
        self.repository = repository

    def create(self, request: ConversationCreate) -> Conversation:
        now = datetime.now(UTC)
        messages = [
            ConversationMessage(**message.model_dump(), created_at=now)
            for message in request.messages
        ]
        first_user = next(message for message in request.messages if message.role == "user")
        title = request.title or _default_title(first_user.content)
        return self.repository.create(title, messages)

    def list(self) -> list[ConversationSummary]:
        records = sorted(
            self.repository.list(), key=lambda item: item.updated_at, reverse=True
        )
        return [
            ConversationSummary(
                id=item.id,
                title=item.title,
                message_count=len(item.messages),
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in records
        ]

    def get(self, conversation_id: str) -> Conversation:
        record = self.repository.get(conversation_id)
        if record is None:
            raise RecordNotFoundError(f"Conversation not found: {conversation_id}")
        return record

    def delete(self, conversation_id: str) -> None:
        if not self.repository.delete(conversation_id):
            raise RecordNotFoundError(f"Conversation not found: {conversation_id}")

    def append_exchange(
        self, conversation_id: str, user_content: str, assistant_content: str
    ) -> Conversation:
        now = datetime.now(UTC)
        user_message = ConversationMessage(
            role="user", content=user_content, created_at=now
        )
        assistant_message = ConversationMessage(
            role="assistant", content=assistant_content, created_at=now
        )
        record = self.repository.append_exchange(
            conversation_id, user_message, assistant_message
        )
        if record is None:
            raise RecordNotFoundError(f"Conversation not found: {conversation_id}")
        return record
