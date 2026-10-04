from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from dotenv import load_dotenv


def _required(source: Mapping[str, str], name: str) -> str:
    value = source.get(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class Settings:
    copa_api_key: str
    firebase_service_account_file: str
    allowed_origins: tuple[str, ...]
    ai_base_url: str = "https://copa.codyssey.kr/v1"
    ai_model: str = "gpt-5.4-mini"
    ai_max_output_tokens: int = 500

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Settings":
        if environ is None:
            load_dotenv()
            source: Mapping[str, str] = os.environ
        else:
            source = environ

        origins = tuple(
            origin.strip()
            for origin in _required(source, "ALLOWED_ORIGINS").split(",")
            if origin.strip()
        )
        if not origins:
            raise ValueError("ALLOWED_ORIGINS must contain at least one origin")
        try:
            max_tokens = int(source.get("AI_MAX_OUTPUT_TOKENS", "500"))
        except ValueError as exc:
            raise ValueError("AI_MAX_OUTPUT_TOKENS must be a positive integer") from exc
        if max_tokens <= 0:
            raise ValueError("AI_MAX_OUTPUT_TOKENS must be a positive integer")

        return cls(
            copa_api_key=_required(source, "COPA_API_KEY"),
            firebase_service_account_file=_required(
                source, "FIREBASE_SERVICE_ACCOUNT_FILE"
            ),
            allowed_origins=origins,
            ai_base_url=source.get(
                "AI_BASE_URL", "https://copa.codyssey.kr/v1"
            ).strip()
            or "https://copa.codyssey.kr/v1",
            ai_model=source.get("AI_MODEL", "gpt-5.4-mini").strip()
            or "gpt-5.4-mini",
            ai_max_output_tokens=max_tokens,
        )

    @classmethod
    def for_test(cls) -> "Settings":
        return cls(
            copa_api_key="test-key",
            firebase_service_account_file="firebase-service-account.example.json",
            allowed_origins=("http://localhost:5173",),
        )
