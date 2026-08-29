# A1-2 Travel Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI that combines the Codyssey OpenAI-compatible API and Kakao Local API to create saved domestic-travel data and a Markdown report.

**Architecture:** Keep the learning project in one importable `travel_planner.py`, with narrow functions for validation, HTTP calls, parsing, normalization, persistence, and orchestration. Inject HTTP sessions and output paths so unit tests can exercise every failure path without network access.

**Tech Stack:** Python 3.10+, `argparse`, `requests`, `python-dotenv`, `unittest`, `unittest.mock`

**Spec:** `docs/superpowers/specs/2026-08-29-a1-2-travel-planner-design.md`

## Global Constraints

- LLM endpoint: `https://copa.codyssey.kr/v1/chat/completions`
- LLM model: `gpt-5.4-mini`
- API key variables: `COPA_API_KEY`, `KAKAO_REST_API_KEY`
- Kakao keyword endpoint: `https://dapi.kakao.com/v2/local/search/keyword.json`
- CLI supports both `-date` and `--date` with a real `YYYY-MM-DD` date.
- Recommendation JSON parsing gets at most one retry.
- Kakao failures never prevent report generation.
- Secrets never appear in source, logs, README examples, or result files.
- Git commit steps are recorded but may be skipped while `.git` is read-only.

---

### Task 1: CLI validation and configuration

**Files:**
- Create: `A1-2/travel_planner.py`
- Create: `A1-2/tests/__init__.py`
- Create: `A1-2/tests/test_travel_planner.py`
- Create: `A1-2/requirements.txt`
- Create: `A1-2/.env.example`
- Create: `A1-2/.gitignore`

**Interfaces:**
- Produces: `validate_date(value: str) -> str`
- Produces: `load_api_keys(environ: Mapping[str, str] | None = None) -> tuple[str, str]`
- Produces: `ConfigurationError`

- [ ] **Step 1: Write failing validation and configuration tests**

```python
class ValidationTests(unittest.TestCase):
    def test_validate_date_accepts_real_iso_date(self):
        self.assertEqual(planner.validate_date("2026-03-15"), "2026-03-15")

    def test_validate_date_rejects_nonexistent_date(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            planner.validate_date("2026-02-30")

    def test_load_api_keys_lists_missing_variable(self):
        with self.assertRaisesRegex(planner.ConfigurationError, "COPA_API_KEY"):
            planner.load_api_keys({"KAKAO_REST_API_KEY": "kakao"})
```

- [ ] **Step 2: Run tests and confirm import failure**

Run: `python -m unittest A1-2/tests/test_travel_planner.py -v`
Expected: FAIL because `travel_planner` does not exist.

- [ ] **Step 3: Implement the minimal validation and configuration code**

```python
def validate_date(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("날짜는 실제 YYYY-MM-DD 형식이어야 합니다.") from exc
    return value

def load_api_keys(environ=None):
    source = os.environ if environ is None else environ
    missing = [name for name in ("COPA_API_KEY", "KAKAO_REST_API_KEY") if not source.get(name)]
    if missing:
        raise ConfigurationError(f"API 키가 없습니다: {', '.join(missing)}")
    return source["COPA_API_KEY"], source["KAKAO_REST_API_KEY"]
```

Add `requests>=2.31,<3` and `python-dotenv>=1.0,<2` to `requirements.txt`. Put only variable names and placeholder values in `.env.example`; ignore `.env`, `results/`, and Python cache files.

- [ ] **Step 4: Run Task 1 tests**

Run: `python -m unittest discover -s A1-2/tests -v`
Expected: all Task 1 tests PASS.

- [ ] **Step 5: Commit Task 1**

```bash
git add A1-2/travel_planner.py A1-2/tests A1-2/requirements.txt A1-2/.env.example A1-2/.gitignore
git commit -m "feat: add travel planner CLI validation"
```

### Task 2: LLM recommendation client and retry

**Files:**
- Modify: `A1-2/travel_planner.py`
- Modify: `A1-2/tests/test_travel_planner.py`

**Interfaces:**
- Consumes: `COPA_API_KEY`
- Produces: `chat_completion(api_key: str, messages: list[dict[str, str]], session=requests, timeout: int = 30) -> str`
- Produces: `parse_recommendation(text: str) -> dict[str, object]`
- Produces: `create_recommendation(travel_date: str, api_key: str, session=requests) -> dict[str, object]`
- Produces: `ApiError`, `RecommendationParseError`

- [ ] **Step 1: Write failing LLM tests**

```python
def test_chat_completion_uses_documented_endpoint_model_and_bearer_header(self):
    session = Mock()
    session.post.return_value = fake_response({"choices": [{"message": {"content": "{}"}}]})
    planner.chat_completion("secret", [{"role": "user", "content": "hello"}], session=session)
    _, kwargs = session.post.call_args
    self.assertEqual(session.post.call_args.args[0], planner.COPA_CHAT_URL)
    self.assertEqual(kwargs["json"]["model"], "gpt-5.4-mini")
    self.assertEqual(kwargs["headers"]["Authorization"], "Bearer secret")

def test_parse_recommendation_accepts_json_code_fence(self):
    parsed = planner.parse_recommendation(
        '```json\n{"recommended_city":"제주","weather":"온화","events":[],"reason":"봄 여행에 좋습니다. 야외 활동이 편합니다."}\n```'
    )
    self.assertEqual(parsed["recommended_city"], "제주")

def test_create_recommendation_retries_once_after_invalid_json(self):
    session = Mock()
    session.post.side_effect = [
        fake_response({"choices": [{"message": {"content": "not json"}}]}),
        fake_response({"choices": [{"message": {"content": VALID_RECOMMENDATION}}]}),
    ]
    result = planner.create_recommendation("2026-03-15", "secret", session=session)
    self.assertEqual(result["recommended_city"], "제주")
    self.assertEqual(session.post.call_count, 2)
```

- [ ] **Step 2: Run only LLM tests and verify failures**

Run: `python -m unittest A1-2.tests.test_travel_planner.LlmTests -v`
Expected: FAIL because LLM functions are undefined.

- [ ] **Step 3: Implement POST, parsing, schema validation, and one retry**

Use `response.raise_for_status()`, verify `choices[0].message.content`, strip an optional Markdown JSON fence, parse with `json.loads`, and require exactly these minimum types: string `recommended_city`, string `weather`, list of strings `events`, string `reason`. `create_recommendation` sends the original structured-output prompt, catches only `RecommendationParseError`, and sends one repair prompt containing the invalid text. A second parse failure is raised; HTTP errors are wrapped as `ApiError` without retry.

- [ ] **Step 4: Run LLM tests and full suite**

Run: `python -m unittest discover -s A1-2/tests -v`
Expected: all tests PASS and retry call count is exactly 2.

- [ ] **Step 5: Commit Task 2**

```bash
git add A1-2/travel_planner.py A1-2/tests/test_travel_planner.py
git commit -m "feat: generate structured travel recommendation"
```

### Task 3: Kakao restaurant search with graceful failure

**Files:**
- Modify: `A1-2/travel_planner.py`
- Modify: `A1-2/tests/test_travel_planner.py`

**Interfaces:**
- Consumes: recommendation `recommended_city`, `KAKAO_REST_API_KEY`
- Produces: `search_restaurants(city: str, api_key: str, errors: list[dict[str, str]], session=requests) -> list[dict[str, object]]`

- [ ] **Step 1: Write failing Kakao tests**

```python
def test_search_restaurants_normalizes_kakao_fields(self):
    session = Mock()
    session.get.return_value = fake_response({"documents": [{
        "place_name": "바다식당", "road_address_name": "제주로 1",
        "address_name": "제주시", "category_name": "음식점 > 한식",
        "place_url": "https://place.map.kakao.com/1", "x": "126.5", "y": "33.5"
    }]})
    errors = []
    places = planner.search_restaurants("제주", "key", errors, session=session)
    self.assertEqual(places[0]["name"], "바다식당")
    self.assertEqual(places[0]["x"], 126.5)
    self.assertEqual(errors, [])

def test_search_restaurants_records_http_error_and_returns_empty_list(self):
    session = Mock()
    session.get.side_effect = requests.RequestException("offline")
    errors = []
    self.assertEqual(planner.search_restaurants("제주", "key", errors, session=session), [])
    self.assertEqual(errors[0]["step"], "place_search")

def test_search_restaurants_records_empty_result(self):
    session = Mock()
    session.get.return_value = fake_response({"documents": []})
    errors = []
    self.assertEqual(planner.search_restaurants("제주", "key", errors, session=session), [])
    self.assertEqual(errors[0]["type"], "EMPTY_RESULT")
```

- [ ] **Step 2: Run Kakao tests and verify failures**

Run: `python -m unittest A1-2.tests.test_travel_planner.KakaoTests -v`
Expected: FAIL because `search_restaurants` is undefined.

- [ ] **Step 3: Implement Kakao GET and normalization**

Call the fixed endpoint with `Authorization: KakaoAK <key>`, query `<city> 맛집`, and `size=5`. Prefer `road_address_name`, then `address_name`; turn nonempty `x` and `y` strings into floats. Catch request, status, and response-shape errors, append `{step, type, message}` without request headers, and return `[]`. Record `EMPTY_RESULT` for no documents.

- [ ] **Step 4: Run Kakao tests and full suite**

Run: `python -m unittest discover -s A1-2/tests -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit Task 3**

```bash
git add A1-2/travel_planner.py A1-2/tests/test_travel_planner.py
git commit -m "feat: add Kakao restaurant search"
```

### Task 4: Report generation, fallback, and persistence

**Files:**
- Modify: `A1-2/travel_planner.py`
- Modify: `A1-2/tests/test_travel_planner.py`

**Interfaces:**
- Consumes: raw data `{date, recommendation, restaurants, errors}`
- Produces: `generate_report(raw_data: dict[str, object], api_key: str, session=requests) -> str`
- Produces: `build_fallback_report(raw_data: dict[str, object]) -> str`
- Produces: `save_results(raw_data: dict[str, object], report: str, results_dir: Path) -> tuple[Path, Path]`

- [ ] **Step 1: Write failing report and persistence tests**

```python
def test_fallback_report_marks_missing_restaurants_and_has_required_sections(self):
    report = planner.build_fallback_report(RAW_DATA_WITHOUT_RESTAURANTS)
    for heading in ("## 추천 지역", "## 추천 이유", "## 날씨 요약", "## 행사/축제", "## 맛집 추천", "## 1일 일정 제안", "## 오류 요약(errors)"):
        self.assertIn(heading, report)
    self.assertIn("데이터 없음", report)

def test_save_results_writes_utf8_json_and_markdown(self):
    with TemporaryDirectory() as tmp:
        raw_path, report_path = planner.save_results(RAW_DATA, "# 리포트", Path(tmp))
        saved = json.loads(raw_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["recommendation"]["recommended_city"], "제주")
        self.assertEqual(report_path.read_text(encoding="utf-8"), "# 리포트")
```

- [ ] **Step 2: Run report tests and verify failures**

Run: `python -m unittest A1-2.tests.test_travel_planner.ReportTests -v`
Expected: FAIL because report and save functions are undefined.

- [ ] **Step 3: Implement report prompt, deterministic fallback, and file writes**

Serialize raw data into the LLM prompt with `ensure_ascii=False`. Require all specified headings and morning/afternoon/evening suggestions. If the final LLM call raises `ApiError`, append a `report_generation` error and use `build_fallback_report`. `save_results` creates the directory, writes `<date>_raw_data.json` with indentation, then writes `<date>_travel_plan.md`.

- [ ] **Step 4: Run report tests and full suite**

Run: `python -m unittest discover -s A1-2/tests -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit Task 4**

```bash
git add A1-2/travel_planner.py A1-2/tests/test_travel_planner.py
git commit -m "feat: save travel data and report"
```

### Task 5: Orchestration, CLI behavior, and documentation

**Files:**
- Modify: `A1-2/travel_planner.py`
- Modify: `A1-2/tests/test_travel_planner.py`
- Create: `A1-2/README.md`

**Interfaces:**
- Consumes: all earlier functions
- Produces: `run(travel_date: str, copa_api_key: str, kakao_api_key: str, results_dir: Path = DEFAULT_RESULTS_DIR, session=requests) -> tuple[Path, Path]`
- Produces: `build_parser() -> argparse.ArgumentParser`, `main() -> int`

- [ ] **Step 1: Write failing orchestration tests**

```python
@patch.object(planner, "generate_report", return_value="# 완성")
@patch.object(planner, "search_restaurants", return_value=[])
@patch.object(planner, "create_recommendation", return_value=RECOMMENDATION)
def test_run_connects_all_steps_and_saves_outputs(self, recommend, search, report):
    with TemporaryDirectory() as tmp:
        raw_path, report_path = planner.run("2026-03-15", "copa", "kakao", Path(tmp))
        self.assertTrue(raw_path.exists())
        self.assertTrue(report_path.exists())
        search.assert_called_once_with("제주", "kakao", unittest.mock.ANY, session=unittest.mock.ANY)

def test_parser_accepts_single_dash_date_alias(self):
    args = planner.build_parser().parse_args(["-date", "2026-03-15"])
    self.assertEqual(args.date, "2026-03-15")
```

- [ ] **Step 2: Run orchestration tests and verify failures**

Run: `python -m unittest A1-2.tests.test_travel_planner.OrchestrationTests -v`
Expected: FAIL because `run` and `build_parser` are undefined.

- [ ] **Step 3: Implement orchestration and CLI entry point**

Print `[1/3]`, `[2/3]`, `[3/3]` progress lines; build raw data before report generation; save the report after any report-generation error has been appended. `main` loads `.env`, validates keys, returns exit code 2 for configuration problems and 1 for unrecoverable LLM recommendation failures, and prints both saved paths on success.

- [ ] **Step 4: Write README**

Document overview, Python setup, `pip install -r requirements.txt`, `.env.example` copying, both key variables, `python travel_planner.py --date "2026-03-15"`, output files, GET vs POST, structured JSON handoff, representative errors, and explicit warnings never to commit `.env` or paste keys into logs/results.

- [ ] **Step 5: Run automated verification**

Run: `python -m unittest discover -s A1-2/tests -v`
Expected: all tests PASS with no network requests.

Run: `python A1-2/travel_planner.py --help`
Expected: usage lists `-date DATE, --date DATE`.

Run: `python A1-2/travel_planner.py --date 2026-02-30`
Expected: usage and the Korean date-format error; no traceback.

- [ ] **Step 6: Inspect for leaked secrets and generated artifacts**

Run: `rg -n "Bearer [A-Za-z0-9]|KakaoAK [A-Za-z0-9]" A1-2 -g '!api문서.png'`
Expected: no matches containing an actual credential.

- [ ] **Step 7: Commit Task 5**

```bash
git add A1-2/travel_planner.py A1-2/tests/test_travel_planner.py A1-2/README.md
git commit -m "docs: complete A1-2 travel planner"
```
