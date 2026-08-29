"""LLM과 Kakao Local API를 조합한 국내 여행 추천 CLI."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Mapping

import requests


DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
COPA_CHAT_URL = "https://copa.codyssey.kr/v1/chat/completions"
KAKAO_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
LLM_MODEL = "gpt-5.4-mini"
DEFAULT_RESULTS_DIR = Path(__file__).resolve().with_name("results")
REPORT_HEADINGS = (
    "## 추천 지역",
    "## 추천 이유",
    "## 날씨 요약",
    "## 행사/축제",
    "## 맛집 추천",
    "## 1일 일정 제안",
    "## 오류 요약(errors)",
)


class ConfigurationError(RuntimeError):
    """필수 환경 설정이 누락되었을 때 발생한다."""


class ApiError(RuntimeError):
    """외부 API 요청 또는 응답이 유효하지 않을 때 발생한다."""


class RecommendationParseError(ValueError):
    """LLM 추천 결과가 필수 JSON 스키마를 만족하지 않을 때 발생한다."""


def validate_date(value: str) -> str:
    """실제로 존재하는 YYYY-MM-DD 날짜를 검증한다."""
    if not DATE_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError(
            "날짜는 실제 YYYY-MM-DD 형식이어야 합니다."
        )

    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "날짜는 실제 YYYY-MM-DD 형식이어야 합니다."
        ) from exc
    return value


def load_api_keys(
    environ: Mapping[str, str] | None = None,
) -> tuple[str, str]:
    """환경변수에서 LLM 및 Kakao API 키를 읽는다."""
    source = os.environ if environ is None else environ
    names = ("COPA_API_KEY", "KAKAO_REST_API_KEY")
    missing = [name for name in names if not source.get(name)]
    if missing:
        raise ConfigurationError(
            "API 키가 설정되지 않았습니다: "
            f"{', '.join(missing)}. .env 또는 환경변수를 확인하세요."
        )
    return source["COPA_API_KEY"], source["KAKAO_REST_API_KEY"]


def chat_completion(
    api_key: str,
    messages: list[dict[str, str]],
    *,
    session=requests,
    timeout: int = 30,
) -> str:
    """Codyssey OpenAI 호환 Chat Completions API를 호출한다."""
    try:
        response = session.post(
            COPA_CHAT_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"model": LLM_MODEL, "messages": messages},
            timeout=timeout,
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
        raise ApiError(f"LLM API 호출 실패: {detail}") from exc
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ApiError("LLM API 응답 형식이 올바르지 않습니다.") from exc


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else stripped


def parse_recommendation(text: str) -> dict[str, object]:
    """LLM 텍스트를 추천 스키마에 맞는 딕셔너리로 변환한다."""
    try:
        data = json.loads(_strip_json_fence(text))
    except (json.JSONDecodeError, TypeError) as exc:
        raise RecommendationParseError("추천 결과가 유효한 JSON이 아닙니다.") from exc

    if not isinstance(data, dict):
        raise RecommendationParseError("추천 결과의 최상위 값은 객체여야 합니다.")

    string_fields = ("recommended_city", "weather", "reason")
    if any(not isinstance(data.get(name), str) or not data[name].strip() for name in string_fields):
        raise RecommendationParseError("추천 결과의 필수 문자열 필드가 올바르지 않습니다.")

    events = data.get("events")
    if (
        not isinstance(events, list)
        or not 1 <= len(events) <= 3
        or any(not isinstance(item, str) or not item.strip() for item in events)
    ):
        raise RecommendationParseError(
            "events는 비어 있지 않은 문자열 1~3개의 배열이어야 합니다."
        )
    return data


def create_recommendation(
    travel_date: str,
    api_key: str,
    *,
    session=requests,
) -> dict[str, object]:
    """여행 추천 JSON을 만들고 파싱 실패 시 한 번만 교정 요청한다."""
    schema = (
        '{"recommended_city": string, "weather": string, '
        '"events": string[], "reason": string}'
    )
    messages = [
        {
            "role": "system",
            "content": (
                "당신은 국내 여행 전문가입니다. 설명이나 코드 펜스 없이 "
                f"반드시 다음 스키마의 JSON 객체만 출력하세요: {schema}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"여행 날짜는 {travel_date}입니다. 해당 시기에 여행하기 좋은 "
                "국내 도시 한 곳, 일반적인 날씨, 행사 후보 1~3개, 추천 근거 "
                "2~4문장을 작성하세요. 행사 일정은 변동 가능성을 고려하세요."
            ),
        },
    ]
    first_text = chat_completion(api_key, messages, session=session)
    try:
        return parse_recommendation(first_text)
    except RecommendationParseError:
        repair_messages = [
            {
                "role": "system",
                "content": (
                    "입력 내용을 설명이나 코드 펜스 없이 필수 키만 포함한 "
                    f"유효한 JSON으로 교정하세요. 스키마: {schema}"
                ),
            },
            {"role": "user", "content": first_text},
        ]
        repaired_text = chat_completion(api_key, repair_messages, session=session)
        return parse_recommendation(repaired_text)


def _optional_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _place_error(error_type: str, message: str) -> dict[str, str]:
    return {"step": "place_search", "type": error_type, "message": message}


def search_restaurants(
    city: str,
    api_key: str,
    errors: list[dict[str, str]],
    *,
    session=requests,
) -> list[dict[str, object]]:
    """Kakao Local에서 도시 맛집을 찾고 공통 필드로 정규화한다."""
    query = f"{city} 맛집"
    try:
        response = session.get(
            KAKAO_SEARCH_URL,
            headers={"Authorization": f"KakaoAK {api_key}"},
            params={"query": query, "size": 5},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        documents = payload["documents"]
        if not isinstance(documents, list):
            raise TypeError("documents is not a list")
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status in (401, 403):
            error_type = "AUTH_ERROR"
        elif status == 429:
            error_type = "QUOTA_ERROR"
        elif status:
            error_type = "HTTP_ERROR"
        else:
            error_type = "NETWORK_ERROR"
        message = f"HTTP {status}" if status else "장소 API 네트워크 요청 실패"
        errors.append(_place_error(error_type, message))
        return []
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(_place_error("RESPONSE_ERROR", "장소 API 응답 형식 오류"))
        return []

    if not documents:
        errors.append(
            _place_error("EMPTY_RESULT", f"0 results for query={query}")
        )
        return []

    restaurants: list[dict[str, object]] = []
    for place in documents[:5]:
        if not isinstance(place, dict):
            continue
        restaurants.append(
            {
                "name": str(place.get("place_name", "")),
                "address": str(
                    place.get("road_address_name")
                    or place.get("address_name")
                    or ""
                ),
                "category": str(place.get("category_name", "")),
                "url": str(place.get("place_url", "")),
                "x": _optional_float(place.get("x")),
                "y": _optional_float(place.get("y")),
            }
        )
    return restaurants


def generate_report(
    raw_data: dict[str, object],
    api_key: str,
    *,
    session=requests,
) -> str:
    """추천과 장소 데이터를 바탕으로 LLM Markdown 리포트를 만든다."""
    required_headings = ", ".join(REPORT_HEADINGS)
    messages = [
        {
            "role": "system",
            "content": (
                "당신은 국내 여행 리포트 작성자입니다. 제공된 데이터만 바탕으로 "
                "한국어 Markdown을 작성하세요. 사실이 불확실한 행사 정보는 일정이 "
                "변경될 수 있음을 알리고, 없는 데이터는 '데이터 없음'으로 표시하세요."
            ),
        },
        {
            "role": "user",
            "content": (
                f"다음 데이터를 사용하세요:\n{json.dumps(raw_data, ensure_ascii=False, indent=2)}\n\n"
                f"반드시 다음 제목을 모두 포함하세요: {required_headings}. "
                "1일 일정은 오전, 오후, 저녁으로 제안하세요."
            ),
        },
    ]
    report = chat_completion(api_key, messages, session=session)
    missing = [heading for heading in REPORT_HEADINGS if heading not in report]
    if missing:
        raise ApiError(
            "최종 리포트에 필수 섹션이 없습니다: " + ", ".join(missing)
        )
    return report


def build_fallback_report(raw_data: dict[str, object]) -> str:
    """LLM 리포트 생성 실패 시 사용할 결정적 Markdown을 만든다."""
    travel_date = str(raw_data.get("date", "날짜 미상"))
    recommendation = raw_data.get("recommendation")
    if not isinstance(recommendation, dict):
        recommendation = {}
    city = str(recommendation.get("recommended_city", "데이터 없음"))
    reason = str(recommendation.get("reason", "데이터 없음"))
    weather = str(recommendation.get("weather", "데이터 없음"))

    events = recommendation.get("events", [])
    event_lines = (
        [f"- {event}" for event in events]
        if isinstance(events, list) and events
        else ["- 데이터 없음"]
    )

    restaurants = raw_data.get("restaurants", [])
    restaurant_lines: list[str] = []
    if isinstance(restaurants, list):
        for place in restaurants:
            if not isinstance(place, dict):
                continue
            name = place.get("name") or "이름 없음"
            address = place.get("address") or "주소 없음"
            category = place.get("category") or "분류 없음"
            url = place.get("url") or "링크 없음"
            restaurant_lines.append(
                f"- **{name}** — {address} / {category} / {url}"
            )
    if not restaurant_lines:
        restaurant_lines = ["- 데이터 없음 (장소 검색 결과 0건)"]

    errors = raw_data.get("errors", [])
    error_lines: list[str] = []
    if isinstance(errors, list):
        for error in errors:
            if not isinstance(error, dict):
                continue
            error_lines.append(
                f"- `{error.get('step', 'unknown')}` / "
                f"`{error.get('type', 'ERROR')}`: {error.get('message', '')}"
            )
    if not error_lines:
        error_lines = ["- 없음"]

    lines = [
        f"# {travel_date} 국내 여행 추천 리포트",
        "",
        "## 추천 지역",
        city,
        "",
        "## 추천 이유",
        reason,
        "",
        "## 날씨 요약",
        weather,
        "",
        "## 행사/축제",
        *event_lines,
        "",
        "## 맛집 추천",
        *restaurant_lines,
        "",
        "## 1일 일정 제안",
        f"- 오전: {city}의 대표 명소와 주변 산책로 둘러보기",
        f"- 오후: {city}의 지역 행사 또는 문화 공간 방문하기",
        "- 저녁: 추천 맛집을 확인하고 지역 음식 즐기기",
        "",
        "## 오류 요약(errors)",
        *error_lines,
    ]
    return "\n".join(lines) + "\n"


def save_results(
    raw_data: dict[str, object],
    report: str,
    results_dir: Path,
) -> tuple[Path, Path]:
    """원본 JSON과 Markdown 리포트를 날짜 기반 파일명으로 저장한다."""
    results_dir.mkdir(parents=True, exist_ok=True)
    travel_date = str(raw_data["date"])
    raw_path = results_dir / f"{travel_date}_raw_data.json"
    report_path = results_dir / f"{travel_date}_travel_plan.md"
    raw_path.write_text(
        json.dumps(raw_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(report, encoding="utf-8")
    return raw_path, report_path


def run(
    travel_date: str,
    copa_api_key: str,
    kakao_api_key: str,
    results_dir: Path = DEFAULT_RESULTS_DIR,
    *,
    session=requests,
) -> tuple[Path, Path]:
    """추천, 장소 검색, 리포트 생성을 순서대로 실행한다."""
    errors: list[dict[str, str]] = []

    print("[1/3] 1차 추천 생성 중(LLM)...")
    recommendation = create_recommendation(
        travel_date, copa_api_key, session=session
    )
    print(f"  - recommended_city: {recommendation['recommended_city']}")

    print("[2/3] 맛집 검색 중(Kakao Local)...")
    restaurants = search_restaurants(
        str(recommendation["recommended_city"]),
        kakao_api_key,
        errors,
        session=session,
    )
    if restaurants:
        print(f"  - 맛집 {len(restaurants)}곳 검색 완료")
    else:
        print("  - 검색 결과 없음 또는 API 오류(리포트 생성을 계속합니다)")

    raw_data: dict[str, object] = {
        "date": travel_date,
        "recommendation": recommendation,
        "restaurants": restaurants,
        "errors": errors,
    }

    print("[3/3] 최종 리포트 생성 중(LLM)...")
    try:
        report = generate_report(raw_data, copa_api_key, session=session)
        print("  - 리포트 생성 완료")
    except ApiError as exc:
        errors.append(
            {
                "step": "report_generation",
                "type": "API_ERROR",
                "message": str(exc),
            }
        )
        report = build_fallback_report(raw_data)
        print("  - LLM 오류로 기본 리포트를 생성했습니다")

    raw_path, report_path = save_results(raw_data, report, results_dir)
    print(f"완료! 원본 데이터: {raw_path}")
    print(f"완료! 여행 리포트: {report_path}")
    return raw_path, report_path


def build_parser() -> argparse.ArgumentParser:
    """CLI 인자 파서를 생성한다."""
    parser = argparse.ArgumentParser(
        description="LLM과 Kakao Local API로 국내 여행 리포트를 생성합니다."
    )
    parser.add_argument(
        "-date",
        "--date",
        dest="date",
        required=True,
        type=validate_date,
        metavar="YYYY-MM-DD",
        help="여행 날짜(필수)",
    )
    return parser


def _load_dotenv_file() -> None:
    """python-dotenv가 설치되어 있으면 A1-2/.env를 불러온다."""
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        return
    load_dotenv(Path(__file__).resolve().with_name(".env"))


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점."""
    args = build_parser().parse_args(argv)
    _load_dotenv_file()
    try:
        copa_api_key, kakao_api_key = load_api_keys()
    except ConfigurationError as exc:
        print(f"설정 오류: {exc}", file=sys.stderr)
        print(
            "설정 예: .env 파일에 COPA_API_KEY와 "
            "KAKAO_REST_API_KEY를 입력하세요.",
            file=sys.stderr,
        )
        return 2

    try:
        run(args.date, copa_api_key, kakao_api_key)
    except (ApiError, RecommendationParseError) as exc:
        print(f"실행 오류: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
