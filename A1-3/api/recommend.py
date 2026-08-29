"""날짜에 맞는 제철 과일을 추천하는 Vercel Serverless Function."""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler
from typing import Any

try:
    import requests
except ModuleNotFoundError:  # Codex 번들 Python의 오프라인 검증 경로
    from pip._vendor import requests

try:
    from .seasonal_data import get_monthly_fruits
except ImportError:  # Vercel이 api/를 직접 실행하는 경우
    from seasonal_data import get_monthly_fruits


COPA_CHAT_URL = "https://copa.codyssey.kr/v1/chat/completions"
LLM_MODEL = "gpt-5.4-mini"
AI_TIMEOUT_SECONDS = 15
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FRUIT_FIELDS = (
    "name",
    "emoji",
    "season_reason",
    "taste_nutrition",
    "selection_tip",
    "storage_tip",
    "recipe",
)
SEASON_NOTICE = "제철 시기는 품종, 산지와 기후에 따라 달라질 수 있습니다."


class RecommendationParseError(ValueError):
    """AI 응답이 추천 결과 스키마를 만족하지 않을 때 발생한다."""


class UpstreamApiError(RuntimeError):
    """AI API 요청 또는 응답 자체가 실패했을 때 발생한다."""


def validate_date(value: object) -> date:
    """실제로 존재하는 YYYY-MM-DD 날짜를 검증한다."""
    if not isinstance(value, str) or not DATE_PATTERN.fullmatch(value):
        raise ValueError("올바른 날짜를 입력해 주세요.")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("올바른 날짜를 입력해 주세요.") from exc


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    match = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```",
        stripped,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return match.group(1).strip() if match else stripped


def parse_ai_fruits(text: str, expected_names: list[str]) -> list[dict[str, str]]:
    """AI 텍스트를 정확히 3개의 과일 정보로 검증하고 정규화한다."""
    try:
        payload = json.loads(_strip_json_fence(text))
    except (json.JSONDecodeError, TypeError) as exc:
        raise RecommendationParseError("AI 응답이 유효한 JSON이 아닙니다.") from exc

    if isinstance(payload, dict):
        payload = payload.get("fruits")
    if not isinstance(payload, list) or len(payload) != 3:
        raise RecommendationParseError("과일 정보는 정확히 3개여야 합니다.")

    normalized: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise RecommendationParseError("과일 정보는 객체여야 합니다.")
        fruit: dict[str, str] = {}
        for field in FRUIT_FIELDS:
            value = item.get(field)
            if not isinstance(value, str) or not value.strip():
                raise RecommendationParseError(f"{field} 값이 비어 있습니다.")
            fruit[field] = value.strip()
        normalized.append(fruit)

    names = [fruit["name"] for fruit in normalized]
    if names != expected_names:
        raise RecommendationParseError("지정한 후보와 다른 과일이 포함됐습니다.")
    return normalized


def _chat_completion(
    api_key: str,
    messages: list[dict[str, str]],
    *,
    session: Any = requests,
) -> str:
    try:
        response = session.post(
            COPA_CHAT_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "messages": messages,
                "temperature": 0.4,
            },
            timeout=AI_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise KeyError("empty content")
        return content.strip()
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        detail = f"HTTP {status}" if status else "네트워크 요청 실패"
        raise UpstreamApiError(f"AI API 호출 실패: {detail}") from exc
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise UpstreamApiError("AI API 응답 형식이 올바르지 않습니다.") from exc


def request_ai_details(
    fruits: list[dict[str, str]],
    selected_date: str,
    api_key: str,
    *,
    session: Any = requests,
) -> list[dict[str, str]]:
    """후보 3종의 설명을 AI로 보강하고 형식 오류 시 한 번 교정한다."""
    expected_names = [fruit["name"] for fruit in fruits]
    schema = {
        "fruits": [
            {
                "name": "후보와 동일한 과일명",
                "emoji": "과일 이모지",
                "season_reason": "제철 이유 1~2문장",
                "taste_nutrition": "맛과 일반적인 영양 특징 1~2문장",
                "selection_tip": "잘 고르는 법 1문장",
                "storage_tip": "보관법 1문장",
                "recipe": "간단한 레시피 1문장",
            }
        ]
    }
    messages = [
        {
            "role": "system",
            "content": (
                "당신은 한국 제철 과일 안내자입니다. 제공된 후보 3종만, "
                "입력 순서 그대로 사용하세요. 의료 효능을 단정하지 말고 일반적인 "
                "영양 정보만 간결하게 설명하세요. 설명이나 코드 펜스 없이 지정된 "
                "JSON 객체만 출력하세요."
            ),
        },
        {
            "role": "user",
            "content": (
                f"기준 날짜: {selected_date}\n"
                f"후보 데이터: {json.dumps(fruits, ensure_ascii=False)}\n"
                f"출력 구조: {json.dumps(schema, ensure_ascii=False)}"
            ),
        },
    ]

    first_text = _chat_completion(api_key, messages, session=session)
    try:
        return parse_ai_fruits(first_text, expected_names)
    except RecommendationParseError:
        repair_messages = [
            {
                "role": "system",
                "content": (
                    "입력된 내용을 설명이나 코드 펜스 없이 올바른 JSON으로만 "
                    "교정하세요. 과일명과 순서는 변경하지 마세요."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"과일명 순서: {json.dumps(expected_names, ensure_ascii=False)}\n"
                    f"필수 필드: {json.dumps(FRUIT_FIELDS, ensure_ascii=False)}\n"
                    f"교정할 응답: {first_text}"
                ),
            },
        ]
        repaired_text = _chat_completion(api_key, repair_messages, session=session)
        return parse_ai_fruits(repaired_text, expected_names)


def build_recommendation(
    selected: date,
    api_key: str,
    *,
    session: Any = requests,
) -> dict[str, object]:
    """검증된 날짜로 전체 추천 응답을 만든다."""
    fallback_fruits = get_monthly_fruits(selected.month)
    try:
        fruits = request_ai_details(
            fallback_fruits,
            selected.isoformat(),
            api_key,
            session=session,
        )
        source = "ai"
        notice = SEASON_NOTICE
    except RecommendationParseError:
        fruits = fallback_fruits
        source = "fallback"
        notice = "AI 상세 설명을 불러오지 못해 기본 정보를 보여드려요."

    return {
        "date": selected.isoformat(),
        "month": selected.month,
        "source": source,
        "fruits": fruits,
        "notice": notice,
    }


def error_payload(code: str, message: str) -> dict[str, dict[str, str]]:
    return {"error": {"code": code, "message": message}}


class handler(BaseHTTPRequestHandler):
    """Vercel이 호출하는 HTTP 핸들러."""

    def send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler 규약
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0
        if content_length <= 0 or content_length > 16_384:
            self.send_json(400, error_payload("INVALID_BODY", "요청 내용을 확인해 주세요."))
            return

        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_json(400, error_payload("INVALID_BODY", "요청 내용을 확인해 주세요."))
            return
        if not isinstance(payload, dict):
            self.send_json(400, error_payload("INVALID_BODY", "요청 내용을 확인해 주세요."))
            return

        try:
            selected = validate_date(payload.get("date"))
        except ValueError as exc:
            self.send_json(400, error_payload("INVALID_DATE", str(exc)))
            return

        api_key = os.environ.get("COPA_API_KEY", "").strip()
        if not api_key:
            self.send_json(
                500,
                error_payload(
                    "CONFIGURATION_ERROR",
                    "서비스 설정을 확인하고 잠시 후 다시 시도해 주세요.",
                ),
            )
            return

        try:
            result = build_recommendation(selected, api_key)
        except UpstreamApiError:
            self.send_json(
                502,
                error_payload(
                    "UPSTREAM_ERROR",
                    "AI 추천을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.",
                ),
            )
            return
        except Exception:
            self.send_json(
                500,
                error_payload(
                    "INTERNAL_ERROR",
                    "예상하지 못한 오류가 발생했어요. 잠시 후 다시 시도해 주세요.",
                ),
            )
            return

        self.send_json(200, result)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler 규약
        self.send_response(405)
        self.send_header("Allow", "POST")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        body = json.dumps(
            error_payload("METHOD_NOT_ALLOWED", "POST 요청만 지원합니다."),
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
