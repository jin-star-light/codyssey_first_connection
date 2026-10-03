# M1-2 Study Coach Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deployable FastAPI and vanilla JavaScript service that stores daily study hours in Firestore, summarizes the time series, answers with Codyssey AI using injected data context, and saves and reloads conversations.

**Architecture:** Split `m1-2` into a FastAPI backend and a static vanilla frontend. The backend follows Router -> Service -> Repository boundaries and injects in-memory fakes in tests while production uses Firestore and the Codyssey OpenAI-compatible API. The frontend is a small ES-module dashboard whose build step writes the public Render URL to `dist/config.js`.

**Tech Stack:** Python 3.10+, FastAPI, Pydantic v2, Uvicorn, Firebase Admin SDK, OpenAI Python SDK, python-dotenv, pytest, HTTPX, HTML5, CSS3, vanilla JavaScript ES modules, Node.js built-in test runner, Render, Vercel

**Spec:** `docs/superpowers/specs/2026-10-03-m1-2-study-coach-design.md`

## Global Constraints

- Implement only the required assignment scope; do not add Function Calling, MCP/GPT Actions, charts, exports, dark mode, or a custom domain.
- Store at least 120 sample rows with exact CSV headers `date,value,memo`.
- Accept study hours only when `0 < value <= 24`, reject future dates, and cap memo text at 200 characters.
- Use Firestore collections named exactly `data` and `conversations`.
- Use `https://copa.codyssey.kr/v1`, model `gpt-5.4-mini`, a 500-token output cap, and the server-only `COPA_API_KEY` variable.
- Never commit or log `.env`, Firebase credentials, `m1-2/Codyssey ai api키.pdf`, generated `dist`, caches, or virtual environments.
- Use Render Secret File `/etc/secrets/firebase-service-account.json` in production and inject only `API_BASE_URL` into the browser bundle.
- Render user-provided memos and messages with `textContent`, never `innerHTML`.
- User-facing text and documentation are Korean; identifiers and HTTP contracts remain concise English.

## Review Focus

- A missing, malformed, or unreadable Firebase credential must fail with a configuration error before the app accepts requests; pin this in Task 4.
- A duplicate or concurrently created date must return 409 without replacing the existing record; pin this in Tasks 2, 4, and 5.
- Empty and 1-19 row datasets must return valid summaries rather than divide by zero or claim a trend; pin this in Task 3.
- AI timeouts, malformed provider responses, or empty output must return a safe 502 and must not save a conversation; pin this in Task 8.
- A failed frontend mutation or chat request must restore an operable form and must not leave optimistic/stale state on screen; pin this in Tasks 9 and 10.

---

### Task 1: Backend Foundation, Configuration, and Health Contract

**Files:**
- Create: `m1-2/.gitignore`
- Create: `m1-2/backend/app/__init__.py`
- Create: `m1-2/backend/app/config.py`
- Create: `m1-2/backend/app/errors.py`
- Create: `m1-2/backend/app/main.py`
- Create: `m1-2/backend/.env.example`
- Create: `m1-2/backend/requirements.txt`
- Create: `m1-2/backend/tests/conftest.py`
- Create: `m1-2/backend/tests/unit/test_config.py`
- Create: `m1-2/backend/tests/integration/test_health.py`

**Interfaces:**
- Consumes: environment variables only.
- Produces: `Settings.from_env(environ: Mapping[str, str] | None = None) -> Settings`; `Settings.for_test() -> Settings`; `create_app(settings: Settings | None = None, **service_overrides) -> FastAPI`.

- [ ] **Step 1: Write failing configuration and health tests**

```python
def test_settings_use_codyssey_defaults():
    settings = Settings.from_env(required_env())
    assert settings.ai_base_url == "https://copa.codyssey.kr/v1"
    assert settings.ai_model == "gpt-5.4-mini"
    assert settings.ai_max_output_tokens == 500

def test_settings_reject_missing_secret():
    with pytest.raises(ValueError, match="COPA_API_KEY"):
        Settings.from_env({"ALLOWED_ORIGINS": "http://localhost:5173"})

def test_health_and_cors_contract(client):
    assert client.get("/health").json() == {"status": "ok"}
    response = client.options("/health", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
```

- [ ] **Step 2: Run the focused tests and verify the missing modules fail**

Run: `cd m1-2/backend; python -m pytest tests/unit/test_config.py tests/integration/test_health.py -v`

Expected: FAIL during import because `app.config` and `app.main` do not exist.

- [ ] **Step 3: Implement the foundation**

Implement immutable `Settings` fields `copa_api_key`, `ai_base_url`, `ai_model`, `ai_max_output_tokens`, `firebase_service_account_file`, and `allowed_origins`. Make only the key, Firebase path, and origins required; validate positive integer token count and at least one normalized origin. Create the FastAPI factory, `/health`, CORS middleware, and safe public error envelope helper.

- [ ] **Step 4: Add dependency pins and secret exclusions**

Set compatible bounded ranges for FastAPI, Uvicorn, Firebase Admin, OpenAI SDK, python-dotenv, pytest, and HTTPX. Ignore the attached API-key PDF by exact name plus `.env`, Firebase JSON patterns, `.venv`, `__pycache__`, `.pytest_cache`, `frontend/dist`, and `node_modules`.

- [ ] **Step 5: Run the focused tests**

Run: `cd m1-2/backend; python -m pytest tests/unit/test_config.py tests/integration/test_health.py -v`

Expected: PASS.

- [ ] **Step 6: Commit the backend foundation**

```bash
git add m1-2/.gitignore m1-2/backend
git commit -m "feat: scaffold M1-2 backend"
```

### Task 2: Study Data Models and In-Memory CRUD Service

**Files:**
- Create: `m1-2/backend/app/schemas/__init__.py`
- Create: `m1-2/backend/app/schemas/data.py`
- Create: `m1-2/backend/app/repositories/__init__.py`
- Create: `m1-2/backend/app/repositories/data_repository.py`
- Create: `m1-2/backend/app/services/__init__.py`
- Create: `m1-2/backend/app/services/data_service.py`
- Create: `m1-2/backend/tests/fakes/__init__.py`
- Create: `m1-2/backend/tests/fakes/repositories.py`
- Create: `m1-2/backend/tests/unit/test_data_schemas.py`
- Create: `m1-2/backend/tests/unit/test_data_service.py`

**Interfaces:**
- Consumes: no prior service interfaces.
- Produces: `DataCreate`, `DataUpdate`, `DataRecord`, `DataListResponse`; `DataRepository.list/get/create/replace/delete`; `DataService.create_record/list_records/get_record/update_record/delete_record`.

- [ ] **Step 1: Write failing schema boundary tests**

```python
@pytest.mark.parametrize("value", [0, -1, 24.1])
def test_study_hours_reject_out_of_range(value):
    with pytest.raises(ValidationError):
        DataCreate(date="2026-01-01", value=value, memo="")

def test_data_create_rejects_future_date_and_extra_fields():
    with pytest.raises(ValidationError):
        DataCreate(date=date.today() + timedelta(days=1), value=1, memo="", secret="x")
```

- [ ] **Step 2: Write failing service behavior tests**

Cover creation, newest-first listing, retrieval, update with a changed date, delete, missing IDs, and duplicate date preservation. Assert a second create raises `DuplicateDateError` and the first record remains unchanged.

- [ ] **Step 3: Run tests and verify failure**

Run: `cd m1-2/backend; python -m pytest tests/unit/test_data_schemas.py tests/unit/test_data_service.py -v`

Expected: FAIL because schemas and services are missing.

- [ ] **Step 4: Implement the data contracts and service**

Use `Decimal` validation and JSON serialization to a number. Define repository protocols with typed methods, map repository false/missing results to `RecordNotFoundError`, and keep ordering choices in `DataService.list_records(*, descending: bool = True)`.

- [ ] **Step 5: Implement the deterministic in-memory repository**

Use date ISO strings as IDs, copy objects on read/write, preserve `created_at`, update `updated_at`, and make the duplicate check atomic within the fake's single operation.

- [ ] **Step 6: Run tests**

Run: `cd m1-2/backend; python -m pytest tests/unit/test_data_schemas.py tests/unit/test_data_service.py -v`

Expected: PASS.

- [ ] **Step 7: Commit data-domain behavior**

```bash
git add m1-2/backend/app m1-2/backend/tests
git commit -m "feat: add study data domain"
```

### Task 3: Time-Series Summary and Trend Rules

**Files:**
- Modify: `m1-2/backend/app/schemas/data.py`
- Create: `m1-2/backend/app/services/summary_service.py`
- Create: `m1-2/backend/tests/unit/test_summary_service.py`

**Interfaces:**
- Consumes: `DataService.list_records(descending=False) -> list[DataRecord]` from Task 2.
- Produces: `calculate_summary(records: Sequence[DataRecord]) -> DataSummary`; `SummaryService.get_summary() -> DataSummary`.

- [ ] **Step 1: Write failing summary tests**

```python
def test_empty_summary_has_no_period_or_metrics():
    result = calculate_summary([])
    assert result.count == 0
    assert result.period is None
    assert result.metrics is None
    assert result.trend.status == "no_data"

def test_nineteen_records_report_insufficient_trend():
    assert calculate_summary(records(19)).trend.status == "insufficient_data"

def test_trend_compares_latest_ten_with_previous_ten():
    result = calculate_summary(records_with_windows(previous=2.0, recent=3.0))
    assert result.trend.status == "increase"
    assert result.trend.difference == Decimal("1.0")
```

Also assert period, count, one-decimal average, extrema with dates, first/latest values, total change, decrease, and maintain within a `0.2`-hour threshold.

- [ ] **Step 2: Run and verify failure**

Run: `cd m1-2/backend; python -m pytest tests/unit/test_summary_service.py -v`

Expected: FAIL because the summary service is missing.

- [ ] **Step 3: Implement summary schemas and calculations**

Add `DatePeriod`, `DateValue`, `ExtremeMetric`, `SummaryMetrics`, `TrendResult`, and `DataSummary`. Sort by date; use `Decimal` and `ROUND_HALF_UP`; compare rows `[-20:-10]` and `[-10:]`; use strict thresholds below `-0.2` and above `0.2`.

- [ ] **Step 4: Run tests**

Run: `cd m1-2/backend; python -m pytest tests/unit/test_summary_service.py -v`

Expected: PASS.

- [ ] **Step 5: Commit summary behavior**

```bash
git add m1-2/backend/app/schemas/data.py m1-2/backend/app/services/summary_service.py m1-2/backend/tests/unit/test_summary_service.py
git commit -m "feat: summarize study time series"
```

### Task 4: Firebase Initialization and Firestore Data Repository

**Files:**
- Create: `m1-2/backend/app/firebase.py`
- Modify: `m1-2/backend/app/repositories/data_repository.py`
- Create: `m1-2/backend/firebase-service-account.example.json`
- Create: `m1-2/backend/tests/unit/test_firebase.py`
- Create: `m1-2/backend/tests/unit/test_firestore_data_repository.py`

**Interfaces:**
- Consumes: data schemas and `DataRepository` protocol from Task 2; `Settings.firebase_service_account_file` from Task 1.
- Produces: `load_service_account(path: str) -> dict[str, Any]`; `create_firestore_client(path: str) -> Any`; `FirestoreDataRepository(client)` implementing the protocol.

- [ ] **Step 1: Write failing credential tests**

Assert a missing file, invalid JSON, non-object JSON, and absent service-account keys produce readable `ValueError` or `FileNotFoundError` messages without echoing secret content. Assert a valid temporary JSON object is returned.

- [ ] **Step 2: Write failing Firestore repository tests**

Use a controlled fake Firestore client to assert collection name `data`, ISO date document IDs, timestamps, ordered queries, not-found behavior, and transactional duplicate protection. Simulate two creates for one date and assert the second raises `DuplicateDateError` without replacing the first.

- [ ] **Step 3: Run tests and verify failure**

Run: `cd m1-2/backend; python -m pytest tests/unit/test_firebase.py tests/unit/test_firestore_data_repository.py -v`

Expected: FAIL because Firebase integration is missing.

- [ ] **Step 4: Implement Firebase initialization**

Resolve relative paths from the backend root, validate the loaded JSON object, reuse an initialized Firebase app when present, and return `firestore.client(app=app)`. The example JSON contains placeholders only.

- [ ] **Step 5: Implement transactional Firestore CRUD**

Use `client.collection("data")`, date IDs, Firestore server timestamps, query ordering by `date`, and transactions for create, date-changing replace, and delete.

- [ ] **Step 6: Run tests**

Run: `cd m1-2/backend; python -m pytest tests/unit/test_firebase.py tests/unit/test_firestore_data_repository.py -v`

Expected: PASS.

- [ ] **Step 7: Commit Firestore data persistence**

```bash
git add m1-2/backend/app m1-2/backend/firebase-service-account.example.json m1-2/backend/tests
git commit -m "feat: persist study data in Firestore"
```

### Task 5: Data HTTP API and Public Errors

**Files:**
- Create: `m1-2/backend/app/dependencies.py`
- Create: `m1-2/backend/app/routers/__init__.py`
- Create: `m1-2/backend/app/routers/data.py`
- Modify: `m1-2/backend/app/main.py`
- Create: `m1-2/backend/tests/integration/test_data_api.py`
- Create: `m1-2/backend/tests/integration/test_app_contract.py`

**Interfaces:**
- Consumes: `DataService`, `SummaryService`, schemas, and domain errors from Tasks 2-3.
- Produces: all five required `/api/data` endpoints and standard `{"error":{"code","message","details"}}` errors.

- [ ] **Step 1: Write failing API contract tests**

Test 201 create, GET list, 200 replace, 204 delete, summary response, 422 invalid input, 404 missing ID, and 409 duplicate date. Assert `/api/data/summary` is not captured as `{record_id}` and unsafe exception text is absent from error payloads.

- [ ] **Step 2: Run and verify failure**

Run: `cd m1-2/backend; python -m pytest tests/integration/test_data_api.py tests/integration/test_app_contract.py -v`

Expected: FAIL with 404 routes.

- [ ] **Step 3: Implement dependencies, router ordering, and handlers**

Define `get_data_service` and `get_summary_service` from `request.app.state`. Register `/summary` before `/{record_id}`. Convert validation, duplicate, not-found, and datastore errors to 422, 409, 404, and 503 respectively.

- [ ] **Step 4: Run tests**

Run: `cd m1-2/backend; python -m pytest tests/integration/test_data_api.py tests/integration/test_app_contract.py -v`

Expected: PASS.

- [ ] **Step 5: Commit the data API**

```bash
git add m1-2/backend/app m1-2/backend/tests/integration
git commit -m "feat: expose study data API"
```

### Task 6: Conversation Persistence and HTTP API

**Files:**
- Create: `m1-2/backend/app/schemas/conversations.py`
- Create: `m1-2/backend/app/repositories/conversation_repository.py`
- Create: `m1-2/backend/app/services/conversation_service.py`
- Create: `m1-2/backend/app/routers/conversations.py`
- Modify: `m1-2/backend/app/dependencies.py`
- Modify: `m1-2/backend/app/main.py`
- Modify: `m1-2/backend/tests/fakes/repositories.py`
- Create: `m1-2/backend/tests/unit/test_conversation_service.py`
- Create: `m1-2/backend/tests/integration/test_conversation_api.py`

**Interfaces:**
- Consumes: Firestore client and app dependency pattern from Tasks 4-5.
- Produces: `ConversationService.create/list/get/delete/append_exchange`; `ConversationRepository` and Firestore implementation; required conversation endpoints including `GET /api/conversations/{id}`.

- [ ] **Step 1: Write failing conversation service tests**

Assert at least one user message is required, titles default from the first user message and are capped at 60 display characters, messages are limited to 4,000 characters each and 100 per manual create, appending adds exactly one user/assistant pair, and missing IDs raise `RecordNotFoundError`.

- [ ] **Step 2: Write failing conversation API tests**

Assert POST 201, newest-first list summaries without full messages, detail with full messages, delete 204, missing 404, and validation 422.

- [ ] **Step 3: Run and verify failure**

Run: `cd m1-2/backend; python -m pytest tests/unit/test_conversation_service.py tests/integration/test_conversation_api.py -v`

Expected: FAIL because conversation modules are missing.

- [ ] **Step 4: Implement conversation schemas, fake, service, and Firestore repository**

Store messages as `{role, content, created_at}` maps in `conversations`, order list queries by `updated_at` descending, use server timestamps on documents, and append exchanges transactionally.

- [ ] **Step 5: Implement router and app wiring**

Add `POST/GET /api/conversations`, `GET/DELETE /api/conversations/{id}`, inject the service through app state, and reuse the public error handlers.

- [ ] **Step 6: Run tests**

Run: `cd m1-2/backend; python -m pytest tests/unit/test_conversation_service.py tests/integration/test_conversation_api.py -v`

Expected: PASS.

- [ ] **Step 7: Commit conversation persistence**

```bash
git add m1-2/backend/app m1-2/backend/tests
git commit -m "feat: save and reload conversations"
```

### Task 7: Reproducible Sample Dataset and Idempotent Import

**Files:**
- Create: `m1-2/backend/scripts/__init__.py`
- Create: `m1-2/backend/scripts/generate_sample_csv.py`
- Create: `m1-2/backend/scripts/import_csv.py`
- Create: `m1-2/backend/data/study_hours.csv`
- Create: `m1-2/backend/tests/unit/test_sample_csv.py`
- Create: `m1-2/backend/tests/unit/test_import_csv.py`

**Interfaces:**
- Consumes: `DataCreate`, `DataService`, settings, and Firebase factory.
- Produces: `generate_records() -> list[dict[str, str]]`; `parse_csv(path: Path) -> ImportBatch`; `import_records(service: DataService, batch: ImportBatch, *, dry_run: bool) -> ImportReport`; CLI commands documented in the spec.

- [ ] **Step 1: Write failing dataset tests**

Assert deterministic output, exact headers, at least 120 unique non-future dates, values within `(0, 24]`, nonempty representative memos, and regeneration byte-for-byte equality.

- [ ] **Step 2: Write failing importer tests**

Assert exact-header enforcement, UTF-8 BOM support, blank required rows skipped, invalid rows reported, duplicate CSV dates failed, `--dry-run` performs zero writes, and already stored dates increment `skipped` rather than `failed`.

- [ ] **Step 3: Run and verify failure**

Run: `cd m1-2/backend; python -m pytest tests/unit/test_sample_csv.py tests/unit/test_import_csv.py -v`

Expected: FAIL because scripts and CSV are missing.

- [ ] **Step 4: Implement deterministic generation and CSV parsing**

Use a fixed start date and a deterministic weekday/weekend pattern with bounded variation; do not use runtime randomness. Validate each parsed row with `DataCreate` before any write.

- [ ] **Step 5: Implement import reporting and CLI**

Print JSON with `valid`, `created`, `skipped`, and `failed`; exit nonzero on failed rows; initialize Firestore only when not in dry-run mode.

- [ ] **Step 6: Generate and verify the committed CSV**

Run: `cd m1-2/backend; python scripts/generate_sample_csv.py; python scripts/import_csv.py data/study_hours.csv --dry-run`

Expected: at least `valid: 120`, `created: 0`, `failed: 0`.

- [ ] **Step 7: Run tests and commit**

Run: `cd m1-2/backend; python -m pytest tests/unit/test_sample_csv.py tests/unit/test_import_csv.py -v`

Expected: PASS.

```bash
git add m1-2/backend/scripts m1-2/backend/data m1-2/backend/tests
git commit -m "feat: add sample study dataset"
```

### Task 8: Codyssey AI Context Injection and Automatic Chat Saving

**Files:**
- Create: `m1-2/backend/app/clients/__init__.py`
- Create: `m1-2/backend/app/clients/ai_client.py`
- Create: `m1-2/backend/app/schemas/chat.py`
- Create: `m1-2/backend/app/services/chat_service.py`
- Create: `m1-2/backend/app/routers/chat.py`
- Create: `m1-2/backend/app/bootstrap.py`
- Modify: `m1-2/backend/app/dependencies.py`
- Modify: `m1-2/backend/app/main.py`
- Create: `m1-2/backend/tests/fakes/ai_client.py`
- Create: `m1-2/backend/tests/unit/test_ai_client.py`
- Create: `m1-2/backend/tests/unit/test_chat_service.py`
- Create: `m1-2/backend/tests/integration/test_chat_api.py`

**Interfaces:**
- Consumes: `SummaryService`, `ConversationService`, production repositories, and Settings.
- Produces: `AIClient.complete(*, system_prompt: str, messages: list[dict[str, str]]) -> str`; `CodysseyAIClient`; `build_system_prompt(summary: dict[str, Any]) -> str`; `ChatService.chat(request: ChatRequest) -> ChatResult`; `POST /api/chat`; `build_services(settings: Settings) -> Services`.

- [ ] **Step 1: Write failing provider client tests**

Use a fake SDK client and assert `base_url`, `gpt-5.4-mini`, `max_completion_tokens=500`, system role ordering, and extracted nonempty text. Assert no choices, empty text, timeout, and SDK errors become `AIProviderError` without key or upstream body leakage.

- [ ] **Step 2: Write failing chat-service tests**

```python
def test_chat_injects_current_summary_and_saves_successful_exchange():
    result = service.chat(ChatRequest(message="최근 학습량이 어때?"))
    assert '"증가"' in fake_ai.system_prompt
    assert result.answer == "최근 학습시간이 증가했어요."
    assert conversations.get(result.conversation_id).messages[-1].role == "assistant"

def test_ai_failure_does_not_save_conversation():
    with pytest.raises(AIProviderError):
        failing_service.chat(ChatRequest(message="분석해줘"))
    assert conversations.list() == []
```

Also assert an existing conversation's messages are passed before the new question, missing IDs return 404, input is capped at 1,000 characters, and the prompt prohibits inventing missing records.

- [ ] **Step 3: Write failing chat API tests**

Assert 200 response with `conversation_id` and `answer`, automatic history creation, continuation by ID, 422 empty input, 404 missing conversation, and safe 502 provider failure.

- [ ] **Step 4: Run and verify failure**

Run: `cd m1-2/backend; python -m pytest tests/unit/test_ai_client.py tests/unit/test_chat_service.py tests/integration/test_chat_api.py -v`

Expected: FAIL because AI and chat modules are missing.

- [ ] **Step 5: Implement provider client and context-only chat flow**

Instantiate `OpenAI(api_key=settings.copa_api_key, base_url=settings.ai_base_url)`, call Chat Completions without tools, inject serialized current summary in the system prompt, include stored history when supplied, and save only after a nonempty final answer. Do not implement Function Calling.

- [ ] **Step 6: Assemble production services and register the router**

`build_services` creates one Firestore client, both repositories, all services, and the Codyssey client. `create_app()` without overrides loads settings and production services; tests continue injecting fakes.

- [ ] **Step 7: Run focused and full backend tests**

Run: `cd m1-2/backend; python -m pytest tests/unit/test_ai_client.py tests/unit/test_chat_service.py tests/integration/test_chat_api.py -v; python -m pytest -q`

Expected: all PASS.

- [ ] **Step 8: Commit AI chat**

```bash
git add m1-2/backend/app m1-2/backend/tests
git commit -m "feat: add data-aware AI chat"
```

### Task 9: Frontend Build, API Client, and State Core

**Files:**
- Create: `m1-2/frontend/package.json`
- Create: `m1-2/frontend/vercel.json`
- Create: `m1-2/frontend/scripts/build.mjs`
- Create: `m1-2/frontend/src/js/api.js`
- Create: `m1-2/frontend/src/js/state.js`
- Create: `m1-2/frontend/src/js/utils.js`
- Create: `m1-2/frontend/tests/api.test.js`
- Create: `m1-2/frontend/tests/state.test.js`
- Create: `m1-2/frontend/tests/utils.test.js`
- Create: `m1-2/frontend/tests/build.test.js`

**Interfaces:**
- Consumes: HTTP contracts from Tasks 5, 6, and 8.
- Produces: `createApi({baseUrl, fetchImpl})`; `ApiError`; all required endpoint methods; `createInitialState()`; `createStore(initial)`; display formatters; build-generated `window.APP_CONFIG.API_BASE_URL`.

- [ ] **Step 1: Write failing API and failure-state tests**

Assert URL normalization, JSON request bodies, 204 handling, safe backend error extraction, malformed JSON fallback, and network errors. For mutation/chat failure helpers, assert loading returns to false and no optimistic row/message remains.

- [ ] **Step 2: Write failing build tests**

Assert missing `API_BASE_URL` exits nonzero, a valid URL produces `dist/config.js`, source assets are copied, and secret variable names or values never appear in `dist`.

- [ ] **Step 3: Run and verify failure**

Run: `cd m1-2/frontend; npm test`

Expected: FAIL because frontend modules are missing.

- [ ] **Step 4: Implement dependency-free modules and build**

Use only Node built-ins in development and browser APIs at runtime. Expose methods for data CRUD, summary, conversations, and chat. Reject a blank base URL before any fetch.

- [ ] **Step 5: Run tests and a build**

Run: `cd m1-2/frontend; npm test; $env:API_BASE_URL='http://localhost:8000'; npm run build`

Expected: tests PASS and `dist/config.js` contains only the public API URL.

- [ ] **Step 6: Commit frontend infrastructure**

```bash
git add m1-2/frontend
git commit -m "feat: add frontend API foundation"
```

### Task 10: Responsive Dashboard and User Workflows

**Files:**
- Create: `m1-2/frontend/src/index.html`
- Create: `m1-2/frontend/src/favicon.svg`
- Create: `m1-2/frontend/src/css/styles.css`
- Create: `m1-2/frontend/src/js/app.js`
- Create: `m1-2/frontend/src/js/data.js`
- Create: `m1-2/frontend/src/js/summary.js`
- Create: `m1-2/frontend/src/js/chat.js`
- Create: `m1-2/frontend/src/js/conversations.js`
- Create: `m1-2/frontend/tests/data.test.js`
- Create: `m1-2/frontend/tests/chat.test.js`
- Create: `m1-2/frontend/tests/conversations.test.js`
- Create: `m1-2/frontend/tests/summary.test.js`

**Interfaces:**
- Consumes: `createApi`, store, state transitions, and formatters from Task 9.
- Produces: one responsive dashboard implementing summary, full data CRUD, loading chat, and conversation list/load/delete/new flows.

- [ ] **Step 1: Write failing pure UI behavior tests**

Test data validation `(0, 24]`, memo length, payload normalization, summary view models for empty and populated states, chat submit/complete/fail transitions, conversation selection/new/delete transitions, and cold-start label selection after 8 seconds.

- [ ] **Step 2: Run and verify failure**

Run: `cd m1-2/frontend; npm test`

Expected: FAIL because UI modules are missing.

- [ ] **Step 3: Implement semantic HTML and responsive layout**

Create four visible sections: conversation history, AI chat, study summary, and data management. Provide form labels, live regions, keyboard submit, mobile layout at 760px, disabled/loading states, and confirmation before deletion.

- [ ] **Step 4: Implement UI controllers**

Load summary, records, and conversations on startup; refresh summary after successful mutations; preserve form input after a failed save; remove optimistic user chat content after a failed request; refresh history after a successful chat; use only `textContent` for external strings.

- [ ] **Step 5: Run frontend tests and build**

Run: `cd m1-2/frontend; npm test; $env:API_BASE_URL='http://localhost:8000'; npm run build`

Expected: all tests PASS and the build succeeds.

- [ ] **Step 6: Perform static accessibility and security checks**

Run: `rg -n "innerHTML|COPA_API_KEY|FIREBASE" m1-2/frontend/src m1-2/frontend/dist`

Expected: no matches for secrets or `innerHTML`; Firebase and AI variables are absent from the bundle.

- [ ] **Step 7: Commit the dashboard**

```bash
git add m1-2/frontend
git commit -m "feat: build study coach dashboard"
```

### Task 11: Deployment Configuration and Submission Documentation

**Files:**
- Create: `m1-2/backend/render.yaml`
- Create: `m1-2/README.md`
- Create: `m1-2/backend/README.md`
- Create: `m1-2/frontend/README.md`
- Create: `m1-2/screenshots/README.md`
- Create: `m1-2/backend/tests/unit/test_deliverables.py`

**Interfaces:**
- Consumes: final commands, environment names, routes, and build output from Tasks 1-10.
- Produces: reproducible local setup, Render/Vercel configuration, user action checklist, deployment URL placeholders, and screenshot checklist.

- [ ] **Step 1: Write failing deliverable tests**

Assert `render.yaml` contains root directory, build/start command, `/health`, Python version, `COPA_API_KEY`, fixed AI URL/model, Firebase secret-file path, and `ALLOWED_ORIGINS`. Assert README documents all required endpoints, local commands, environment variables, free-tier cold start, sample import, deployment sequence, and three required screenshots.

- [ ] **Step 2: Run and verify failure**

Run: `cd m1-2/backend; python -m pytest tests/unit/test_deliverables.py -v`

Expected: FAIL because deployment and README files are missing.

- [ ] **Step 3: Implement Render and Vercel instructions**

Use backend root `m1-2/backend`, `pip install -r requirements.txt`, `uvicorn app.main:create_app --factory --host 0.0.0.0 --port $PORT`, `/health`, and secret file `/etc/secrets/firebase-service-account.json`. Use frontend root `m1-2/frontend`, build `npm run build`, output `dist`, and public `API_BASE_URL`.

- [ ] **Step 4: Write the user-owned setup checklist**

Document Codyssey virtual key entry, Firebase project/Firestore/service-account creation, GitHub connection, Render deployment, sample import, Vercel deployment, CORS update, `/docs` check, final functional checks, and screenshot capture. Mark live URLs as post-deployment fields rather than inventing values.

- [ ] **Step 5: Run documentation tests**

Run: `cd m1-2/backend; python -m pytest tests/unit/test_deliverables.py -v`

Expected: PASS.

- [ ] **Step 6: Commit deployment documentation**

```bash
git add m1-2/backend/render.yaml m1-2/README.md m1-2/backend/README.md m1-2/frontend/README.md m1-2/screenshots m1-2/backend/tests/unit/test_deliverables.py
git commit -m "docs: add M1-2 deployment guide"
```

### Task 12: Full Verification and Secret Audit

**Files:**
- Modify only files whose verification reveals a defect.

**Interfaces:**
- Consumes: all prior task outputs.
- Produces: a verified local deliverable ready for the user's Firebase, Render, and Vercel setup.

- [ ] **Step 1: Run the complete backend suite and compile check**

Run: `cd m1-2/backend; python -m pytest -q; python -m compileall -q app scripts`

Expected: all tests PASS and compilation exits 0.

- [ ] **Step 2: Validate the sample import without credentials**

Run: `cd m1-2/backend; python scripts/import_csv.py data/study_hours.csv --dry-run`

Expected: at least 120 valid rows, zero created rows, and zero failures.

- [ ] **Step 3: Run frontend tests and production build**

Run: `cd m1-2/frontend; npm test; $env:API_BASE_URL='https://example.onrender.com'; npm run build`

Expected: all tests PASS; build exits 0.

- [ ] **Step 4: Audit tracked files for secrets**

Run the two commands separately: `git ls-files m1-2` and `rg -n "sk-[A-Za-z0-9_-]{12,}|private_key|COPA_API_KEY=.+" m1-2 --glob '!*.example.*' --glob '!.env.example' --glob '!README.md' --glob '!test_*.py'`.

Expected: the PDF, `.env`, Firebase credential JSON, and real keys are not tracked; no probable secret value is found.

- [ ] **Step 5: Review assignment coverage**

Check every mandatory line in `m1-2/m1-2 subject` against the README, API tests, frontend UI, and deployment files. Record that actual URLs, live credential checks, and screenshots remain user-owned post-deployment steps.

- [ ] **Step 6: Fix any discovered defect with a failing regression test first**

For each defect, add the narrowest failing test, run it to confirm failure, implement the correction, then rerun the focused and complete suites.

- [ ] **Step 7: Commit final verification fixes if any**

```bash
git add m1-2
git commit -m "test: verify M1-2 deliverables"
```

- [ ] **Step 8: Hand off the deployment checklist**

Report local verification evidence, list the exact remaining user actions, and do not claim live deployment, Firestore connectivity, AI connectivity, or screenshots until those checks have actually been completed.
