import argparse
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import ANY, Mock, patch

try:
    import requests
except ModuleNotFoundError:  # Codex 번들 테스트 환경의 오프라인 대체 경로
    from pip._vendor import requests

    sys.modules["requests"] = requests


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

import travel_planner as planner


VALID_RECOMMENDATION = json.dumps(
    {
        "recommended_city": "제주",
        "weather": "봄바람이 불고 비교적 온화합니다.",
        "events": ["유채꽃 행사"],
        "reason": "봄꽃을 즐기기 좋은 시기입니다. 야외 활동에도 적합합니다.",
    },
    ensure_ascii=False,
)

RECOMMENDATION = json.loads(VALID_RECOMMENDATION)
RAW_DATA = {
    "date": "2026-03-15",
    "recommendation": RECOMMENDATION,
    "restaurants": [
        {
            "name": "바다식당",
            "address": "제주로 1",
            "category": "음식점 > 한식",
            "url": "https://place.map.kakao.com/1",
            "x": 126.5,
            "y": 33.5,
        }
    ],
    "errors": [],
}
COMPLETE_REPORT = """# 여행 리포트
## 추천 지역
제주
## 추천 이유
봄 여행에 좋습니다.
## 날씨 요약
온화합니다.
## 행사/축제
- 유채꽃 행사
## 맛집 추천
- 바다식당
## 1일 일정 제안
- 오전/오후/저녁
## 오류 요약(errors)
- 없음
"""


def fake_response(payload, status_code=200):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(
            f"HTTP {status_code}", response=response
        )
    else:
        response.raise_for_status.return_value = None
    return response


class ValidationTests(unittest.TestCase):
    def test_validate_date_accepts_real_iso_date(self):
        self.assertEqual(planner.validate_date("2026-03-15"), "2026-03-15")

    def test_validate_date_rejects_nonexistent_date(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            planner.validate_date("2026-02-30")

    def test_validate_date_rejects_wrong_format(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            planner.validate_date("2026/03/15")

        with self.assertRaises(argparse.ArgumentTypeError):
            planner.validate_date("2026-3-5")

    def test_load_api_keys_returns_both_keys(self):
        self.assertEqual(
            planner.load_api_keys(
                {"COPA_API_KEY": "copa", "KAKAO_REST_API_KEY": "kakao"}
            ),
            ("copa", "kakao"),
        )

    def test_load_api_keys_lists_every_missing_variable(self):
        with self.assertRaises(planner.ConfigurationError) as context:
            planner.load_api_keys({})

        message = str(context.exception)
        self.assertIn("COPA_API_KEY", message)
        self.assertIn("KAKAO_REST_API_KEY", message)


class LlmTests(unittest.TestCase):
    def test_chat_completion_uses_documented_api_contract(self):
        session = Mock()
        session.post.return_value = fake_response(
            {"choices": [{"message": {"content": "완료"}}]}
        )

        content = planner.chat_completion(
            "secret",
            [{"role": "user", "content": "안녕하세요"}],
            session=session,
        )

        self.assertEqual(content, "완료")
        args, kwargs = session.post.call_args
        self.assertEqual(args[0], "https://copa.codyssey.kr/v1/chat/completions")
        self.assertEqual(kwargs["json"]["model"], "gpt-5.4-mini")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer secret")
        self.assertEqual(kwargs["timeout"], 30)

    def test_chat_completion_rejects_malformed_api_response(self):
        session = Mock()
        session.post.return_value = fake_response({"choices": []})

        with self.assertRaises(planner.ApiError):
            planner.chat_completion("secret", [], session=session)

    def test_parse_recommendation_accepts_json_code_fence(self):
        parsed = planner.parse_recommendation(
            f"```json\n{VALID_RECOMMENDATION}\n```"
        )

        self.assertEqual(parsed["recommended_city"], "제주")
        self.assertEqual(parsed["events"], ["유채꽃 행사"])

    def test_parse_recommendation_rejects_wrong_field_type(self):
        invalid = json.dumps(
            {
                "recommended_city": "제주",
                "weather": "온화",
                "events": "유채꽃 행사",
                "reason": "봄 여행에 좋습니다.",
            },
            ensure_ascii=False,
        )

        with self.assertRaises(planner.RecommendationParseError):
            planner.parse_recommendation(invalid)

    def test_parse_recommendation_requires_one_to_three_events(self):
        for events in ([], ["행사1", "행사2", "행사3", "행사4"]):
            invalid = json.dumps(
                {
                    "recommended_city": "제주",
                    "weather": "온화",
                    "events": events,
                    "reason": "봄 여행에 좋습니다.",
                },
                ensure_ascii=False,
            )

            with self.subTest(events=events), self.assertRaises(
                planner.RecommendationParseError
            ):
                planner.parse_recommendation(invalid)

    def test_create_recommendation_retries_once_after_invalid_json(self):
        session = Mock()
        session.post.side_effect = [
            fake_response({"choices": [{"message": {"content": "not json"}}]}),
            fake_response(
                {"choices": [{"message": {"content": VALID_RECOMMENDATION}}]}
            ),
        ]

        result = planner.create_recommendation(
            "2026-03-15", "secret", session=session
        )

        self.assertEqual(result["recommended_city"], "제주")
        self.assertEqual(session.post.call_count, 2)

    def test_create_recommendation_does_not_retry_http_error(self):
        session = Mock()
        session.post.side_effect = requests.RequestException("offline")

        with self.assertRaises(planner.ApiError):
            planner.create_recommendation("2026-03-15", "secret", session=session)

        self.assertEqual(session.post.call_count, 1)


class KakaoTests(unittest.TestCase):
    def test_search_restaurants_normalizes_kakao_fields(self):
        session = Mock()
        session.get.return_value = fake_response(
            {
                "documents": [
                    {
                        "id": "1",
                        "place_name": "바다식당",
                        "category_name": "음식점 > 한식",
                        "category_group_code": "FD6",
                        "category_group_name": "음식점",
                        "phone": "064-000-0000",
                        "address_name": "제주특별자치도 제주시",
                        "road_address_name": "제주로 1",
                        "x": "126.5",
                        "y": "33.5",
                        "place_url": "https://place.map.kakao.com/1",
                        "distance": "",
                    }
                ],
                "meta": {
                    "is_end": True,
                    "pageable_count": 1,
                    "same_name": None,
                    "total_count": 1,
                },
            }
        )
        errors = []

        places = planner.search_restaurants(
            "제주", "key", errors, session=session
        )

        self.assertEqual(
            places,
            [
                {
                    "name": "바다식당",
                    "address": "제주로 1",
                    "category": "음식점 > 한식",
                    "url": "https://place.map.kakao.com/1",
                    "x": 126.5,
                    "y": 33.5,
                }
            ],
        )
        self.assertEqual(errors, [])
        args, kwargs = session.get.call_args
        self.assertEqual(
            args[0], "https://dapi.kakao.com/v2/local/search/keyword.json"
        )
        self.assertEqual(kwargs["headers"]["Authorization"], "KakaoAK key")
        self.assertEqual(kwargs["params"], {"query": "제주 맛집", "size": 5})

    def test_search_restaurants_records_network_error_and_returns_empty(self):
        session = Mock()
        session.get.side_effect = requests.RequestException("offline")
        errors = []

        places = planner.search_restaurants(
            "제주", "key", errors, session=session
        )

        self.assertEqual(places, [])
        self.assertEqual(errors[0]["step"], "place_search")
        self.assertEqual(errors[0]["type"], "NETWORK_ERROR")
        self.assertNotIn("key", errors[0]["message"])

    def test_search_restaurants_classifies_authentication_error(self):
        session = Mock()
        session.get.return_value = fake_response({}, status_code=401)
        errors = []

        self.assertEqual(
            planner.search_restaurants("제주", "key", errors, session=session),
            [],
        )

        self.assertEqual(errors[0]["type"], "AUTH_ERROR")
        self.assertEqual(errors[0]["message"], "HTTP 401")

    def test_search_restaurants_records_empty_result(self):
        session = Mock()
        session.get.return_value = fake_response(
            {
                "documents": [],
                "meta": {
                    "is_end": True,
                    "pageable_count": 0,
                    "same_name": None,
                    "total_count": 0,
                },
            }
        )
        errors = []

        self.assertEqual(
            planner.search_restaurants("제주", "key", errors, session=session),
            [],
        )

        self.assertEqual(
            errors,
            [
                {
                    "step": "place_search",
                    "type": "EMPTY_RESULT",
                    "message": "0 results for query=제주 맛집",
                }
            ],
        )


class ReportTests(unittest.TestCase):
    def test_generate_report_passes_complete_raw_data_to_llm(self):
        session = Mock()
        session.post.return_value = fake_response(
            {"choices": [{"message": {"content": COMPLETE_REPORT}}]}
        )

        report = planner.generate_report(RAW_DATA, "secret", session=session)

        self.assertEqual(report, COMPLETE_REPORT.strip())
        sent_messages = session.post.call_args.kwargs["json"]["messages"]
        user_prompt = sent_messages[-1]["content"]
        self.assertIn('"recommended_city": "제주"', user_prompt)
        self.assertIn('"name": "바다식당"', user_prompt)
        self.assertIn("## 오류 요약(errors)", user_prompt)

    def test_generate_report_rejects_missing_required_sections(self):
        session = Mock()
        session.post.return_value = fake_response(
            {"choices": [{"message": {"content": "# 여행 리포트"}}]}
        )

        with self.assertRaises(planner.ApiError):
            planner.generate_report(RAW_DATA, "secret", session=session)

    def test_fallback_report_marks_missing_restaurants(self):
        raw_data = {
            **RAW_DATA,
            "restaurants": [],
            "errors": [
                {
                    "step": "place_search",
                    "type": "EMPTY_RESULT",
                    "message": "검색 결과 0건",
                }
            ],
        }

        report = planner.build_fallback_report(raw_data)

        for heading in (
            "## 추천 지역",
            "## 추천 이유",
            "## 날씨 요약",
            "## 행사/축제",
            "## 맛집 추천",
            "## 1일 일정 제안",
            "## 오류 요약(errors)",
        ):
            self.assertIn(heading, report)
        self.assertIn("데이터 없음", report)
        self.assertIn("EMPTY_RESULT", report)

    def test_fallback_report_lists_restaurant_details(self):
        report = planner.build_fallback_report(RAW_DATA)

        self.assertIn("바다식당", report)
        self.assertIn("제주로 1", report)
        self.assertIn("https://place.map.kakao.com/1", report)
        self.assertNotIn("데이터 없음", report)

    def test_save_results_writes_utf8_json_and_markdown(self):
        with TemporaryDirectory() as tmp:
            raw_path, report_path = planner.save_results(
                RAW_DATA, "# 리포트", Path(tmp)
            )

            raw_text = raw_path.read_text(encoding="utf-8")
            saved = json.loads(raw_text)
            self.assertEqual(
                saved["recommendation"]["recommended_city"], "제주"
            )
            self.assertIn("제주", raw_text)
            self.assertEqual(report_path.read_text(encoding="utf-8"), "# 리포트")
            self.assertEqual(raw_path.name, "2026-03-15_raw_data.json")
            self.assertEqual(report_path.name, "2026-03-15_travel_plan.md")


class OrchestrationTests(unittest.TestCase):
    def test_parser_accepts_both_date_option_spellings(self):
        parser = planner.build_parser()

        short_args = parser.parse_args(["-date", "2026-03-15"])
        long_args = parser.parse_args(["--date", "2026-04-20"])

        self.assertEqual(short_args.date, "2026-03-15")
        self.assertEqual(long_args.date, "2026-04-20")

    @patch.object(planner, "generate_report", return_value="# 완성")
    @patch.object(planner, "search_restaurants", return_value=[])
    @patch.object(planner, "create_recommendation", return_value=RECOMMENDATION)
    def test_run_connects_steps_and_saves_outputs(
        self, create_mock, search_mock, report_mock
    ):
        with TemporaryDirectory() as tmp:
            raw_path, report_path = planner.run(
                "2026-03-15", "copa", "kakao", Path(tmp)
            )

            saved = json.loads(raw_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["recommendation"]["recommended_city"], "제주")
            self.assertEqual(saved["restaurants"], [])
            self.assertEqual(report_path.read_text(encoding="utf-8"), "# 완성")
            create_mock.assert_called_once_with("2026-03-15", "copa", session=ANY)
            search_mock.assert_called_once_with("제주", "kakao", ANY, session=ANY)
            report_mock.assert_called_once()

    @patch.object(planner, "generate_report", side_effect=planner.ApiError("offline"))
    @patch.object(planner, "search_restaurants", return_value=[])
    @patch.object(planner, "create_recommendation", return_value=RECOMMENDATION)
    def test_run_saves_fallback_and_report_error(
        self, create_mock, search_mock, report_mock
    ):
        with TemporaryDirectory() as tmp:
            raw_path, report_path = planner.run(
                "2026-03-15", "copa", "kakao", Path(tmp)
            )

            saved = json.loads(raw_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["errors"][-1]["step"], "report_generation")
            self.assertEqual(saved["errors"][-1]["type"], "API_ERROR")
            self.assertIn(
                "## 오류 요약(errors)",
                report_path.read_text(encoding="utf-8"),
            )

    def test_main_returns_two_and_explains_missing_keys(self):
        stderr = io.StringIO()

        with patch.dict(os.environ, {}, clear=True), redirect_stderr(stderr):
            exit_code = planner.main(["--date", "2026-03-15"])

        self.assertEqual(exit_code, 2)
        self.assertIn("COPA_API_KEY", stderr.getvalue())
        self.assertIn("KAKAO_REST_API_KEY", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
