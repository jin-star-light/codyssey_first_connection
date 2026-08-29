# Seasonal Fruit Recommender Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `제철한입`, a responsive vanilla web service that accepts a date and returns three Korean-market seasonal fruits enriched by a Python Serverless Function and the Codyssey AI API.

**Architecture:** A static single-page frontend sends `POST /api/recommend` to a Vercel Python handler. The handler chooses three fruits from deterministic monthly data, asks `gpt-5.4-mini` to enrich only those fruits, validates the JSON, retries malformed output once, and returns a safe fallback for unrecoverable response-shape failures.

**Tech Stack:** HTML5, CSS3, vanilla JavaScript, Python 3.10+, `requests`, Vercel Python Serverless Functions, Codyssey OpenAI-compatible Chat Completions API

**Spec:** `docs/superpowers/specs/2026-08-29-seasonal-fruit-recommender-design.md`

## Global Constraints

- All implementation files live under `A1-3/`; preserve the existing `A1-3/subject.md` unchanged.
- Use no frontend framework, build tool, database, login, or external produce-data API.
- Use `COPA_API_KEY` only in the Python server environment; never expose it in browser code or logs.
- Return exactly three fruits with non-empty `name`, `emoji`, `season_reason`, `taste_nutrition`, `selection_tip`, `storage_tip`, and `recipe` strings.
- Treat the selected date by calendar month and state that seasonality varies by cultivar, region, and climate.
- Do not add automated tests or a test framework, per the user's explicit request.
- Manually verify the normal, empty-input, API-error, timeout, navigation, responsive, and keyboard flows before completion.

---

### Task 1: Deterministic Monthly Fruit Data

**Files:**
- Create: `A1-3/api/seasonal_data.py`

**Interfaces:**
- Produces: `SEASONAL_FRUITS: dict[int, tuple[dict[str, str], ...]]`
- Produces: `get_monthly_fruits(month: int) -> list[dict[str, str]]`
- Each fruit dictionary contains the seven response fields required by the API contract.

- [ ] **Step 1: Create the data module**

Define four Korean-market fruits for each month so adjacent seasons can share fruit varieties without sharing mutable dictionaries. Each item must contain complete fallback copy. Use representative fruit families including strawberry, hallabong, chamoe, watermelon, peach, grape, pear, apple, persimmon, tangerine, kiwi, plum, blueberry, fig, and pomegranate.

Implement the accessor exactly as:

```python
def get_monthly_fruits(month: int) -> list[dict[str, str]]:
    if month not in SEASONAL_FRUITS:
        raise ValueError("month must be between 1 and 12")
    return [dict(fruit) for fruit in SEASONAL_FRUITS[month][:3]]
```

- [ ] **Step 2: Run a syntax and shape check**

Run:

```powershell
python -m py_compile A1-3/api/seasonal_data.py
python -c "import sys; sys.path.insert(0, 'A1-3/api'); from seasonal_data import get_monthly_fruits; assert all(len(get_monthly_fruits(month)) == 3 for month in range(1, 13)); print('seasonal data ok')"
```

Expected: `seasonal data ok` and no traceback.

- [ ] **Step 3: Commit the data module**

```powershell
git add A1-3/api/seasonal_data.py
git commit -m "feat: add monthly seasonal fruit data"
```

### Task 2: Python Recommendation Endpoint

**Files:**
- Create: `A1-3/api/recommend.py`
- Create: `A1-3/api/__init__.py`
- Create: `A1-3/requirements.txt`

**Interfaces:**
- Consumes: `get_monthly_fruits(month: int) -> list[dict[str, str]]`
- Produces: `validate_date(value: object) -> datetime.date`
- Produces: `parse_ai_fruits(text: str, expected_names: list[str]) -> list[dict[str, str]]`
- Produces: `request_ai_details(fruits: list[dict[str, str]], selected_date: str, api_key: str, session=requests) -> list[dict[str, str]]`
- Produces: Vercel `class handler(BaseHTTPRequestHandler)` supporting `POST` and returning JSON.

- [ ] **Step 1: Implement validation and response helpers**

Use `datetime.strptime(value, "%Y-%m-%d").date()` after checking that the value is a non-empty string and matches `^\d{4}-\d{2}-\d{2}$`. Define `send_json(status: int, payload: dict[str, object])` on the handler to set `Content-Type: application/json; charset=utf-8`, `Cache-Control: no-store`, and an exact byte `Content-Length`.

Define error payloads as:

```python
{"error": {"code": code, "message": message}}
```

- [ ] **Step 2: Implement strict AI response parsing**

Strip optional JSON code fences, parse JSON, accept either a top-level `fruits` array or a direct array, require exactly three objects, require all seven fields as non-empty strings, and require fruit names to match the deterministic candidates in the same order. Raise `RecommendationParseError` on any mismatch.

- [ ] **Step 3: Implement the Codyssey API call and one repair attempt**

Call `https://copa.codyssey.kr/v1/chat/completions` with:

```python
{
    "model": "gpt-5.4-mini",
    "messages": messages,
    "temperature": 0.4,
}
```

Use `Authorization: Bearer <COPA_API_KEY>`, `Content-Type: application/json`, and a 15-second timeout. The system prompt must say that the model may enrich only the supplied fruits and must return the seven-field JSON schema. If parsing fails, send the raw response once to a repair prompt. Convert request failures and malformed HTTP payloads to `UpstreamApiError` without including credentials.

- [ ] **Step 4: Implement `POST` orchestration**

Read and parse the request body, validate `date`, call `get_monthly_fruits(selected.month)`, and require `COPA_API_KEY`. Return:

```python
{
    "date": selected.isoformat(),
    "month": selected.month,
    "source": "ai",
    "fruits": enriched_fruits,
    "notice": "제철 시기는 품종, 산지와 기후에 따라 달라질 수 있습니다.",
}
```

If both parsing attempts fail, return the deterministic fruits with `source: "fallback"` and the notice `"AI 상세 설명을 불러오지 못해 기본 정보를 보여드려요."`. Return `400` for invalid input, `500` for a missing key, `502` for transport/auth/quota failures, and `405` from `do_GET` with an `Allow: POST` header.

- [ ] **Step 5: Define dependencies and run static checks**

Set `A1-3/requirements.txt` to:

```text
requests>=2.31,<3
```

Run:

```powershell
python -m py_compile A1-3/api/seasonal_data.py A1-3/api/recommend.py
python -c "import sys; sys.path.insert(0, 'A1-3'); from api.recommend import validate_date; assert validate_date('2026-08-29').month == 8; print('api import ok')"
```

Expected: `api import ok` and no traceback.

- [ ] **Step 6: Commit the endpoint**

```powershell
git add A1-3/api/__init__.py A1-3/api/recommend.py A1-3/requirements.txt
git commit -m "feat: add seasonal fruit recommendation api"
```

### Task 3: Semantic Single-Page HTML

**Files:**
- Create: `A1-3/index.html`

**Interfaces:**
- Produces IDs consumed by JavaScript: `menu-toggle`, `primary-nav`, `recommend-form`, `date-input`, `submit-button`, `status-message`, `result-heading`, `fruit-results`.
- Produces navigation anchors: `home`, `recommend`, `calendar`, `guide`.

- [ ] **Step 1: Build the document shell and navigation**

Use `lang="ko"`, UTF-8, responsive viewport, a descriptive title and meta description, a skip link, a sticky header, and four anchor links. The mobile menu button must have `aria-controls="primary-nav"` and `aria-expanded="false"`.

- [ ] **Step 2: Build the four required content sections**

Create:

- `#home`: service name, concise value proposition, a link to `#recommend`, and decorative fruit emoji marked `aria-hidden="true"`.
- `#recommend`: heading, explainer, date form, live status, hidden result heading, and empty results grid.
- `#calendar`: twelve month cards listing the same representative fruits as the backend data.
- `#guide`: recommendation standard, seasonality disclaimer, AI health-information disclaimer, retry guidance, and FAQ details elements.

Use native `<details>` for expandable information and a footer that explains the educational-project context.

- [ ] **Step 3: Load assets and inspect the structure**

Link `css/style.css` and load `js/app.js` with `defer`. Run:

```powershell
rg -n 'id="(home|recommend|calendar|guide|recommend-form|date-input|status-message|fruit-results)"' A1-3/index.html
```

Expected: all required IDs appear exactly once.

- [ ] **Step 4: Commit the HTML**

```powershell
git add A1-3/index.html
git commit -m "feat: add seasonal fruit service layout"
```

### Task 4: Responsive Market-Style CSS

**Files:**
- Create: `A1-3/css/style.css`

**Interfaces:**
- Consumes semantic classes from `index.html` and dynamic classes from `js/app.js`: `is-open`, `is-loading`, `status--error`, `status--success`, `status--notice`, `fruit-card`, `fruit-card__emoji`, `fruit-card__details`.

- [ ] **Step 1: Define design tokens and global behavior**

Define CSS custom properties for cream background, ink text, orange primary, green accent, red accent, border, shadow, three radii, and transition timing. Add `box-sizing`, smooth scrolling with reduced-motion override, visible `:focus-visible`, readable line height, and a hidden-until-focused skip link.

- [ ] **Step 2: Style the header, hero, form, and state UI**

Create a sticky translucent header, rounded CTA buttons, a large date input, a submit-button spinner using a pseudo-element, and status variants that never rely on color alone. Mobile navigation must be hidden by default and shown by `.is-open`.

- [ ] **Step 3: Style result and calendar cards**

Give fruit cards a clear summary hierarchy, large emoji, bordered detail list, and native details disclosure. Use one-column mobile grids, two columns from `768px`, and three result columns from `1024px`; the calendar may use four columns at desktop.

- [ ] **Step 4: Add polish without external assets**

Use CSS gradients, blurred decorative circles, subtle hover lift only on hover-capable devices, and reduced motion handling. Keep every text/background pairing readable and preserve a minimum 44px pointer target for interactive controls.

- [ ] **Step 5: Inspect responsive rules and commit**

Run:

```powershell
rg -n '@media|:focus-visible|prefers-reduced-motion|\.fruit-card|\.status--error' A1-3/css/style.css
```

Expected: responsive, accessibility, card, and error-state rules are present.

```powershell
git add A1-3/css/style.css
git commit -m "feat: style responsive seasonal fruit interface"
```

### Task 5: Frontend Interaction and Safe Rendering

**Files:**
- Create: `A1-3/js/app.js`

**Interfaces:**
- Consumes: `POST /api/recommend` request `{date: string}` and the API success/error contracts.
- Produces: mobile navigation behavior, form states, 20-second timeout, three safe DOM-rendered fruit cards.

- [ ] **Step 1: Implement navigation and date defaults**

Toggle `.is-open` and synchronize `aria-expanded`. Close the menu after an anchor selection and on Escape. Set the date input to the user's local calendar date using local date parts rather than `toISOString()` to avoid timezone rollover.

- [ ] **Step 2: Implement explicit UI state helpers**

Create:

```javascript
function setStatus(message, type = "notice")
function setLoading(isLoading)
function clearResults()
function renderRecommendations(payload)
```

`setLoading(true)` disables the button, applies `.is-loading`, and changes visible text to `추천을 준비하고 있어요`. Every new request clears stale results and status.

- [ ] **Step 3: Implement safe card rendering**

Create all nodes with `document.createElement` and assign external text only through `textContent`. Each fruit card must show the fruit name, emoji, season reason, and a `<details>` section containing labeled taste/nutrition, selection, storage, and recipe rows. Reject client-side payloads without exactly three fruit items.

- [ ] **Step 4: Implement form submission and timeout**

On submit, reject an empty date before calling `fetch`. Create an `AbortController`, abort after 20,000ms, send JSON with `Content-Type: application/json`, and parse success or error JSON. Display distinct Korean messages for timeout, invalid date, server configuration, upstream API failure, malformed success payload, and generic network failure. Always clear the timer and loading state in `finally`.

- [ ] **Step 5: Run a JavaScript syntax check and commit**

Run:

```powershell
node --check A1-3/js/app.js
```

Expected: exit code 0 and no output.

```powershell
git add A1-3/js/app.js
git commit -m "feat: connect fruit form to recommendation api"
```

### Task 6: Project Documentation and Vercel Configuration

**Files:**
- Create: `A1-3/.env.example`
- Create: `A1-3/.gitignore`
- Create: `A1-3/vercel.json`
- Create: `A1-3/README.md`
- Create: `A1-3/docs/service-plan.md`

**Interfaces:**
- Documents the exact `COPA_API_KEY` environment name and the `POST /api/recommend` flow.
- Configures the `api/*.py` Serverless Functions for a 30-second maximum duration.

- [ ] **Step 1: Add safe environment and ignore files**

Set `.env.example` to `COPA_API_KEY=YOUR_CODYSSEY_VIRTUAL_KEY`. Ignore `.env`, `.env.*` while re-including `.env.example`, Python caches, `.vercel`, and OS/editor files.

- [ ] **Step 2: Add Vercel configuration**

Create:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "functions": {
    "api/*.py": {
      "maxDuration": 30
    }
  }
}
```

- [ ] **Step 3: Write README**

Document the service introduction, target users, four sections, AI hybrid approach, HTML/CSS/JavaScript/Python/Vercel/requests stack, folder structure, Python dependency installation, `COPA_API_KEY` setup, `npx vercel dev` local run, GitHub-to-Vercel deployment steps, empty deployment URL field labeled as a post-deployment update, security rules, API request flow, failure behavior, and the manual verification checklist.

- [ ] **Step 4: Write the service plan**

Include the purpose, target user, user value, section breakdown, navigation, AI input, candidate selection, AI output schema, fallback criteria, failure messages, responsive requirements, and completion criteria. Keep it concise enough to submit as the A1-3 planning artifact.

- [ ] **Step 5: Inspect secrets and commit documentation**

Run:

```powershell
rg -n 'sk-|Bearer [A-Za-z0-9]|COPA_API_KEY=' A1-3 --glob '!subject.md' --glob '!.env.example'
```

Expected: no secret-shaped values; references to the variable name without a real value are allowed.

```powershell
git add A1-3/.env.example A1-3/.gitignore A1-3/vercel.json A1-3/README.md A1-3/docs/service-plan.md
git commit -m "docs: add setup and service plan"
```

### Task 7: Manual Verification and Final Review

**Files:**
- Modify only files found defective during verification.

**Interfaces:**
- Consumes the complete static frontend and Python Serverless Function.
- Produces a manually verified local project ready for the user to connect to Vercel.

- [ ] **Step 1: Run final static checks**

```powershell
python -m py_compile A1-3/api/seasonal_data.py A1-3/api/recommend.py
node --check A1-3/js/app.js
python -c "import sys; sys.path.insert(0, 'A1-3/api'); from seasonal_data import get_monthly_fruits; assert all(len(get_monthly_fruits(month)) == 3 for month in range(1, 13)); print('static checks ok')"
```

Expected: `static checks ok`, no syntax errors.

- [ ] **Step 2: Run locally with Vercel**

Install dependencies and start the service:

```powershell
python -m pip install -r A1-3/requirements.txt
npx vercel dev A1-3
```

Provide `COPA_API_KEY` only through the local environment or Vercel prompt; never write it into tracked files.

- [ ] **Step 3: Verify required interactions manually**

Confirm in the browser:

- Header links move to all four sections.
- Mobile menu opens, closes after selection, and closes on Escape.
- Empty date shows an inline message without a request.
- A valid date shows loading, then exactly three cards.
- Each card expands to show all four detail groups.
- A fallback response displays its notice.
- API and timeout failures display safe retry instructions.
- The layout works at 360px, 768px, and 1280px.
- Tab navigation and visible focus reach every interactive control.

- [ ] **Step 4: Review the working tree and secrets**

```powershell
git status --short
git diff --check
rg -n 'sk-[A-Za-z0-9_-]{10,}|Bearer [A-Za-z0-9_-]{10,}' A1-3 --glob '!subject.md'
```

Expected: no whitespace errors, no secret values, and only intended A1-3 implementation files changed by this plan.

- [ ] **Step 5: Commit any verification fixes**

If verification required code corrections, stage only those A1-3 implementation files and commit:

```powershell
git commit -m "fix: polish seasonal fruit service"
```

If no correction was needed, do not create an empty commit.
