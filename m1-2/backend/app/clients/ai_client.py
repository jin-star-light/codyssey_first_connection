from __future__ import annotations

from typing import Any, Protocol

from openai import OpenAI

from app.config import Settings
from app.errors import AIProviderError


class AIClient(Protocol):
    def complete(
        self, *, system_prompt: str, messages: list[dict[str, str]]
    ) -> str: ...


class CodysseyAIClient:
    def __init__(self, settings: Settings, *, sdk_client: Any = None) -> None:
        self.settings = settings
        self.client = sdk_client or OpenAI(
            api_key=settings.copa_api_key,
            base_url=settings.ai_base_url,
        )

    def complete(
        self, *, system_prompt: str, messages: list[dict[str, str]]
    ) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.settings.ai_model,
                max_completion_tokens=self.settings.ai_max_output_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *messages,
                ],
            )
            if not response.choices:
                raise AIProviderError("AI 응답을 받지 못했습니다.")
            content = response.choices[0].message.content
            if not isinstance(content, str) or not content.strip():
                raise AIProviderError("AI 응답을 받지 못했습니다.")
            return content.strip()
        except AIProviderError:
            raise
        except Exception as exc:
            raise AIProviderError("AI 제공자 요청에 실패했습니다.") from exc
