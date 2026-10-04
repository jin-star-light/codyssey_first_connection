from __future__ import annotations

import json
from typing import Any

from app.clients.ai_client import AIClient
from app.schemas.chat import ChatRequest, ChatResult
from app.schemas.conversations import ConversationCreate, MessageInput
from app.services.conversation_service import ConversationService
from app.services.summary_service import SummaryService


def build_system_prompt(summary: dict[str, Any]) -> str:
    serialized = json.dumps(summary, ensure_ascii=False, separators=(",", ":"))
    return (
        "당신은 개인 학습시간 데이터 기반 AI 학습 코치입니다. "
        "아래 통계에 근거해 한국어로 간결하고 실천 가능한 조언을 하세요. "
        "없는 데이터는 만들지 말고 추측이 필요하면 데이터가 부족하다고 명시하세요. "
        f"현재 학습 통계: {serialized}"
    )


class ChatService:
    def __init__(
        self,
        summary_service: SummaryService,
        conversation_service: ConversationService,
        ai_client: AIClient,
    ) -> None:
        self.summary_service = summary_service
        self.conversation_service = conversation_service
        self.ai_client = ai_client

    def chat(self, request: ChatRequest) -> ChatResult:
        history: list[dict[str, str]] = []
        if request.conversation_id:
            conversation = self.conversation_service.get(request.conversation_id)
            history = [
                {"role": message.role, "content": message.content}
                for message in conversation.messages
            ]

        summary = self.summary_service.get_summary().model_dump(mode="json")
        messages = [*history, {"role": "user", "content": request.message}]
        answer = self.ai_client.complete(
            system_prompt=build_system_prompt(summary), messages=messages
        )

        if request.conversation_id:
            saved = self.conversation_service.append_exchange(
                request.conversation_id, request.message, answer
            )
        else:
            saved = self.conversation_service.create(
                ConversationCreate(
                    messages=[
                        MessageInput(role="user", content=request.message),
                        MessageInput(role="assistant", content=answer),
                    ]
                )
            )
        return ChatResult(conversation_id=saved.id, answer=answer)
