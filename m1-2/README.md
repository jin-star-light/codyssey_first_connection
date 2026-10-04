# Study Rhythm — 데이터 기반 AI 학습 코치

## 서비스 소개

Study Rhythm은 140일간의 학습시간 데이터를 분석하고, 그 결과를 근거로 개인화된 답변을 제공하는 AI 웹 서비스입니다. 날짜에 따라 변화가 드러나고 다음 학습 계획으로 연결하기 좋은 학습시간을 분석 대상으로 선택했습니다. 사용자는 학습 기록을 추가·수정·삭제하고, AI와 나눈 대화를 저장한 뒤 다시 불러와 이어갈 수 있습니다.

## 배포 주소

| 구분 | 주소 |
| --- | --- |
| 프런트엔드 | https://m1-2-study-coach.vercel.app |
| 백엔드 API | https://m1-2-study-coach-api.onrender.com |
| Swagger UI | https://m1-2-study-coach-api.onrender.com/docs |
| GitHub | https://github.com/jin-star-light/codyssey_first_connection |

Render 무료 서버가 잠든 경우 첫 요청에 약 1분이 걸릴 수 있습니다. 이후 요청은 정상 속도로 처리됩니다.

## 구현 범위

| 기능 | 구현 내용 | 관련 화면·API |
| --- | --- | --- |
| 학습시간 시계열 데이터 | 2025-01-01부터 2025-05-20까지 학습시간 140건 | 학습 요약, Firestore `data` |
| 데이터 요약 | 기간, 개수, 합계, 평균, 최솟값, 최댓값, 최근 기록, 추세 계산 | `GET /api/data/summary` |
| 데이터 CRUD | 추가·목록·수정·삭제 구현 | 학습시간 관리 화면, `/api/data` |
| 데이터 기반 AI 채팅 | 현재 데이터 요약을 시스템 프롬프트에 넣어 답변 생성 | `POST /api/chat` |
| 채팅 로딩 표시 | AI 응답을 기다리는 동안 로딩 상태 표시 | AI 코치 화면 |
| 대화 저장·조회·불러오기·삭제 | AI 대화를 Firestore에 자동 저장하고 기존 대화를 다시 표시 | 대화 기록 화면, `/api/conversations` |
| Firestore 컬렉션 | `data`, `conversations` 사용 | Firebase Console |
| FastAPI 및 Swagger | API 문서 공개 | Render `/docs` |
| 바닐라 프런트엔드 | HTML, CSS, JavaScript만 사용 | Vercel 배포 화면 |
| 환경변수와 키 관리 | AI 키·Firebase 키·CORS 주소를 코드와 분리 | `.env.example`, Render 환경변수 |
| 서비스 배포 | 백엔드 Render, 프런트엔드 Vercel | 위 배포 주소 |

## 주요 기능

다음 스크린샷은 실제 배포 환경에서 동작하는 화면입니다. API 키와 Firebase 서비스 계정 정보는 포함하지 않았습니다.

### 1. 저장된 데이터에 근거한 AI 채팅

![학습 데이터에 근거한 AI 질문과 답변](./screenshots/01-ai-chat-summary.jpg)

AI는 일반적인 답변만 생성하지 않습니다. 백엔드가 현재 학습 데이터 요약을 먼저 조회하고 시스템 프롬프트에 포함하므로, 답변에 실제 평균 2.9시간과 최근 기록 3.2시간이 반영됩니다. 같은 대화에서 후속 질문을 보내면 이전 메시지까지 함께 전달해 맥락을 유지합니다. 요청 중에는 전송 버튼을 비활성화하고 “답변을 만들고 있어요”를 표시하며, 8초가 지나면 Render 콜드 스타트를 안내하는 문구로 바뀝니다.

![AI 답변의 근거가 되는 학습 데이터 요약](./screenshots/02-data-summary.jpg)

화면에 표시된 요약은 140개 원본 기록으로 계산한 결과입니다.

- 기간: 2025-01-01 ~ 2025-05-20
- 기록 수: 140일
- 총 학습시간: 408시간
- 하루 평균: 2.9시간
- 최근 기록: 3.2시간
- 최근 추세: 유지

### 2. 데이터 관리와 CRUD

![새 학습 기록을 저장해 목록이 갱신된 화면](./screenshots/04-data-crud.jpg)

사용자는 `(date, value, memo)` 형태의 학습 기록을 관리할 수 있습니다. 위 화면은 새 기록을 생성한 직후 목록 최상단에 결과가 반영된 모습입니다. 생성·수정·삭제가 끝날 때마다 목록과 요약을 다시 조회해 화면의 통계도 최신 상태로 맞춥니다. 기능 확인에 사용한 추가 기록은 삭제했고 기본 데이터셋은 140건을 유지하고 있습니다.

구현된 API는 다음과 같습니다.

| 동작 | API |
| --- | --- |
| 생성 | `POST /api/data` |
| 목록 조회 | `GET /api/data` |
| 수정 | `PUT /api/data/{id}` |
| 삭제 | `DELETE /api/data/{id}` |
| 요약 조회 | `GET /api/data/summary` |

### 3. 대화 기록 저장과 불러오기

![저장된 대화 목록과 불러온 대화](./screenshots/03-conversation-history.jpg)

첫 질문을 보내면 대화가 자동으로 생성되고, 후속 질문과 답변은 같은 대화에 추가됩니다. 왼쪽 대화 기록에는 저장된 제목과 메시지 수가 표시되며, 항목을 선택하면 Firestore에서 전체 메시지를 불러와 다시 표시합니다.

| 동작 | API |
| --- | --- |
| 대화 저장 | `POST /api/conversations` |
| 목록 조회 | `GET /api/conversations` |
| 특정 대화 불러오기 | `GET /api/conversations/{id}` |
| 대화 삭제 | `DELETE /api/conversations/{id}` |

### 4. 배포와 API 문서

![Render에 배포된 FastAPI Swagger UI](./screenshots/05-swagger.jpg)

Swagger UI에서 데이터 요약, CRUD, 대화 기록, AI 채팅 API를 확인하고 직접 요청할 수 있습니다. 프런트엔드는 Vercel, 백엔드는 Render에 각각 배포했습니다.

### 5. Firestore 영구 저장

![Firestore data 컬렉션](./screenshots/06-firestore-data.jpg)

`data` 컬렉션은 날짜를 문서 ID로 사용하며 `date`, `value`, `memo`를 저장합니다. 같은 날짜가 중복 생성되는 것을 막고 날짜별 기록을 바로 찾을 수 있습니다.

![Firestore conversations 컬렉션](./screenshots/07-firestore-conversations.jpg)

`conversations` 컬렉션에는 제목, 생성·수정 시각, 사용자와 AI의 메시지 배열을 저장합니다. 따라서 페이지를 새로 열어도 이전 대화를 불러올 수 있습니다.

## 핵심 동작 흐름

```text
사용자 질문
  → FastAPI POST /api/chat
  → Firestore data 조회
  → 기간·통계·최근 추세 요약
  → 요약 정보를 시스템 프롬프트에 주입
  → Codyssey OpenAI 호환 API 호출
  → 답변과 대화 내용을 conversations에 저장
  → 프런트엔드에 답변과 갱신된 대화 기록 표시
```

이 방식이 컨텍스트 주입입니다. 모델을 별도로 학습시키지 않고, 요청 시점의 최신 데이터 요약을 시스템 프롬프트로 제공해 사용자의 실제 상황을 반영합니다. 프롬프트에는 “없는 데이터는 만들지 말고, 데이터가 부족하면 명시하라”는 조건도 포함했습니다.

## 설계와 구현

### 시계열 데이터 요약

기록을 날짜순으로 정렬한 뒤 기간, 개수, 합계, 평균, 최솟값, 최댓값, 최초·최근 값과 전체 변화를 계산합니다. 최근 추세는 최근 10개 평균과 그 이전 10개 평균을 비교하며, 차이가 0.2시간 이내이면 `유지`, 그보다 크면 `증가`, 작으면 `감소`로 판정합니다.

### FastAPI 구조 분리 기준

- `routers`: URL과 HTTP 요청·응답 처리
- `schemas`: Pydantic 요청·응답 형식과 검증 규칙
- `services`: 요약 계산, 채팅, 대화 처리 같은 업무 로직
- `repositories`: Firestore 읽기와 쓰기
- `clients`: 외부 AI API 호출

각 계층의 역할을 분리했기 때문에 통계 계산이나 데이터 저장 방식을 변경해도 다른 계층에 미치는 영향을 줄일 수 있습니다.

### 입력 검증과 오류 처리

Pydantic으로 API 경계에서 날짜, 학습시간, 메모와 메시지 형식을 검증합니다. 미래 날짜는 허용하지 않고, 학습시간은 0시간 초과 24시간 이하, 메모는 최대 200자, 메시지는 1자 이상 4,000자 이하로 제한합니다. 정의하지 않은 필드도 거부해 잘못된 값이 Firestore나 AI 요청까지 전달되지 않게 했습니다.

검증 실패는 `422`, 같은 날짜의 중복 생성은 `409`, 존재하지 않는 데이터는 `404`, Firestore 장애는 `503`, AI 제공자 오류는 `502`로 구분합니다. 프런트엔드는 API가 반환한 오류 문구를 각 입력 영역이나 전체 상태 영역에 표시합니다.

### CORS·환경변수·키 관리

Vercel과 Render는 서로 다른 도메인이므로 백엔드의 `ALLOWED_ORIGINS`에 실제 Vercel 주소를 지정해야 합니다. AI API 키와 Firebase 서비스 계정은 저장소에 넣지 않고 Render의 환경변수와 Secret File로 관리합니다. 프런트엔드에는 비밀키를 두지 않고 공개 백엔드 주소만 `API_BASE_URL`로 주입합니다.

## 기술 스택

- 프런트엔드: HTML, CSS, Vanilla JavaScript, Vercel
- 백엔드: Python 3.10+, FastAPI, Uvicorn, Pydantic, python-dotenv, Render
- 데이터베이스: Firebase Firestore, firebase-admin
- AI: Codyssey OpenAI 호환 API, OpenAI Python SDK
- 테스트: pytest, Node.js test runner

## 로컬 실행

### 백엔드

```powershell
cd m1-2/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:create_app --factory --reload
```

Firebase 서비스 계정 JSON을 `backend/firebase-service-account.json`에 두고 `.env` 값을 설정합니다. 실제 키 파일은 Git에 커밋하지 않습니다.

기본 학습시간 데이터 140건은 다음 명령으로 Firestore에 입력합니다. 같은 날짜가 이미 있으면 중복 생성하지 않고 건너뜁니다.

```powershell
python scripts/import_csv.py data/study_hours.csv
```

### 프런트엔드

```powershell
cd m1-2/frontend
npm install
$env:API_BASE_URL="http://localhost:8000"
npm run build
python -m http.server 5173 -d dist
```

브라우저에서 `http://localhost:5173`에 접속합니다.

## 환경변수

| 변수 | 위치 | 용도 |
| --- | --- | --- |
| `COPA_API_KEY` | 백엔드 | Codyssey에서 발급한 OpenAI 호환 API 키 |
| `AI_BASE_URL` | 백엔드 | Codyssey API 기본 주소 |
| `AI_MODEL` | 백엔드 | 사용할 AI 모델 |
| `AI_MAX_OUTPUT_TOKENS` | 백엔드 | 응답 토큰 상한 |
| `FIREBASE_SERVICE_ACCOUNT_FILE` | 백엔드 | Firebase 서비스 계정 JSON 경로 |
| `ALLOWED_ORIGINS` | 백엔드 | 허용할 프런트엔드 도메인 |
| `API_BASE_URL` | 프런트엔드 빌드 | Render 백엔드 공개 주소 |

Codyssey가 OpenAI 호환 API를 제공하므로 일반적인 `OPENAI_API_KEY`에 해당하는 역할을 이 프로젝트에서는 `COPA_API_KEY`가 담당합니다.

## 전체 구성 요약

Study Rhythm은 140일의 학습시간 데이터를 Firestore에 저장하고 통계와 최근 추세를 계산합니다. 사용자가 질문하면 FastAPI가 최신 요약을 시스템 프롬프트에 넣어 Codyssey AI를 호출하므로 실제 학습 상태에 맞는 답변을 제공합니다. 데이터 CRUD와 대화 저장·불러오기를 포함하며, 프런트엔드는 Vercel, 백엔드는 Render에서 동작합니다.
