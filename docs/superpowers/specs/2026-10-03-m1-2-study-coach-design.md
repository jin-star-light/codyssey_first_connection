# M1-2 학습시간 AI 코치 설계

## 1. 목적과 범위

`m1-2/m1-2 subject`의 필수 요구사항을 충족하는 반응형 웹 서비스를 구현한다. 사용자는 날짜별 학습시간과 메모를 저장하고, 요약 통계를 확인하고, 저장된 데이터를 근거로 AI에게 질문할 수 있다.

서비스 주제는 **개인 학습시간 데이터 기반 AI 학습 코치**다. 초기 샘플 CSV에는 120개 이상의 학습 기록을 넣어 사용자가 직접 데이터를 하나씩 입력하지 않아도 전체 기능을 확인할 수 있게 한다.

선택 보너스인 Function Calling, MCP/GPT Actions, 그래프, CSV/JSON 내보내기, 다크 모드는 구현하지 않는다. 사용자 지정 도메인도 구매하지 않고 Render와 Vercel이 제공하는 기본 주소를 사용한다.

## 2. 성공 기준

- 120개 이상의 샘플 학습 기록을 Firestore에 중복 없이 가져올 수 있다.
- 사용자가 웹 화면에서 기록을 추가, 수정, 삭제하면 목록과 요약이 즉시 갱신된다.
- `/api/data/summary`가 기간, 개수, 평균, 최대, 최소, 최근 추세를 반환한다.
- AI 채팅이 현재 데이터 요약을 시스템 프롬프트에 포함하고 코디세이 OpenAI 호환 API를 호출한다.
- 채팅 성공 시 사용자 질문과 AI 답변이 `conversations`에 자동 저장된다.
- 대화 목록, 상세 불러오기, 삭제가 정상 작동한다.
- 외부 키 없이 백엔드와 프론트엔드 자동 테스트를 실행할 수 있다.
- Render 배포 URL의 `/health`와 `/docs`, Vercel 프론트엔드가 접속 가능하다.

## 3. 프로젝트 구조

```text
m1-2/
├── README.md
├── .gitignore
├── backend/
│   ├── app/
│   │   ├── clients/
│   │   ├── repositories/
│   │   ├── routers/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── firebase.py
│   │   └── main.py
│   ├── data/study_hours.csv
│   ├── scripts/import_csv.py
│   ├── tests/
│   ├── .env.example
│   ├── render.yaml
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── css/
    │   ├── js/
    │   └── index.html
    ├── scripts/build.mjs
    ├── tests/
    ├── package.json
    └── vercel.json
```

백엔드는 Router → Service → Repository 방향으로 의존한다. Router는 HTTP 계약, Service는 업무 규칙, Repository는 Firestore 접근만 담당한다. 테스트는 같은 Service에 메모리 Repository와 가짜 AI 클라이언트를 주입한다.

## 4. 데이터 모델과 Firestore

### data 콜렉션

```json
{
  "date": "2026-06-01",
  "value": 3.5,
  "memo": "Python 복습",
  "created_at": "server timestamp",
  "updated_at": "server timestamp"
}
```

- 문서 ID는 ISO 날짜를 사용해 날짜 중복을 차단한다.
- `value`는 0보다 크고 24 이하인 실수로 검증한다.
- `memo`는 선택 입력이며 최대 200자다.
- 미래 날짜를 기록할 수 없다.
- 데이터가 없는 날은 임의로 보간하지 않는다.

### conversations 콜렉션

```json
{
  "title": "최근 학습 추세가 어때?",
  "messages": [
    {"role": "user", "content": "...", "created_at": "timestamp"},
    {"role": "assistant", "content": "...", "created_at": "timestamp"}
  ],
  "created_at": "server timestamp",
  "updated_at": "server timestamp"
}
```

- 대화 목록은 `updated_at` 최신순으로 반환한다.
- 상세 API는 전체 `messages`를 반환한다.
- 기존 대화에 질문하면 사용자/AI 메시지 쌍을 트랜잭션으로 추가한다.

### 샘플 데이터

CSV 헤더는 `date,value,memo`로 고정한다. 120개 이상의 현실적인 학습 기록을 재현 가능하게 생성하고, import 스크립트는 다음을 수행한다.

- 헤더와 행별 Pydantic 검증
- `--dry-run`을 통한 저장 전 검증
- CSV 내부 중복 날짜 거부
- Firestore에 이미 존재하는 날짜는 건너뜀
- `valid`, `created`, `skipped`, `failed` 결과 보고

## 5. API 계약

### 데이터

- `POST /api/data`: 학습 기록 추가
- `GET /api/data`: 최신순 목록 조회
- `PUT /api/data/{id}`: 학습 기록 전체 수정
- `DELETE /api/data/{id}`: 학습 기록 삭제
- `GET /api/data/summary`: 전체 요약 조회

`summary`는 다음 정보를 반환한다.

- 기간 시작일/종료일
- 기록 개수
- 평균, 최대, 최소 학습시간
- 첫 기록, 최근 기록, 전체 변화량
- 최근 10개와 이전 10개의 평균 차이를 이용한 `증가`, `유지`, `감소`, `데이터 부족`

### 대화

- `POST /api/conversations`: 대화 수동 저장
- `GET /api/conversations`: 대화 목록 조회
- `GET /api/conversations/{id}`: 전체 메시지를 포함한 대화 상세 조회
- `DELETE /api/conversations/{id}`: 대화 삭제

### AI 채팅

- `POST /api/chat`
- 입력: `message`, 선택 `conversation_id`
- 출력: `conversation_id`, `answer`

처리 순서는 다음과 같다.

1. Firestore에서 현재 데이터를 읽어 요약을 계산한다.
2. 요약 JSON을 학습 코치 시스템 프롬프트에 주입한다.
3. 기존 `conversation_id`가 있으면 저장된 메시지를 문맥에 포함한다.
4. 코디세이 OpenAI 호환 Chat Completions API를 호출한다.
5. 성공한 질문과 답변만 대화에 저장한다.
6. 최종 답변과 대화 ID를 프론트엔드에 반환한다.

## 6. AI 연동

코디세이 OpenAI 호환 API를 Python `openai` 패키지로 호출한다.

```text
Base URL: https://copa.codyssey.kr/v1
Model: gpt-5.4-mini
Authentication: Bearer <virtual-key>
```

서버 환경 변수는 다음과 같다.

- `COPA_API_KEY`
- `AI_BASE_URL` (기본값 `https://copa.codyssey.kr/v1`)
- `AI_MODEL` (기본값 `gpt-5.4-mini`)
- `AI_MAX_OUTPUT_TOKENS` (기본값 500)

실제 키는 로컬 `.env`와 Render 환경 변수에만 저장한다. PDF, `.env`, Firebase 서비스 계정 키는 `.gitignore`에 포함하고 프론트엔드와 로그에 포함하지 않는다.

## 7. 프론트엔드 UX

하나의 반응형 대시보드에 다음 영역을 배치한다.

- 대화 기록: 최신순 목록, 상세 불러오기, 삭제, 새 대화
- AI 채팅: 메시지 목록, 질문 입력, 전송 중 로딩 표시
- 학습 요약: 기간, 개수, 평균, 최대, 최소, 추세
- 데이터 관리: 추가/수정 폼, 최신순 목록, 삭제

채팅 중에는 중복 전송을 막고 로딩 메시지를 표시한다. 8초 이상 답변이 없으면 Render 무료 서버가 깨어나는 중일 수 있다는 안내로 바꾼다. 모든 사용자 메모와 AI 메시지는 `textContent`로 렌더링한다.

브라우저가 읽는 `API_BASE_URL`은 Vercel 빌드 시 `dist/config.js`로 생성한다. AI와 Firebase 비밀 값은 프론트엔드에 전달하지 않는다.

## 8. 오류 처리와 보안

- Pydantic은 알 수 없는 추가 필드를 거부한다.
- 검증 실패는 422, 중복 날짜는 409, 없는 자원은 404를 반환한다.
- AI 공급자 실패는 502, Firestore 실패는 503으로 변환한다.
- 공개 오류 응답은 `error.code`, `error.message`, 안전한 `error.details`만 포함한다.
- 오류 응답과 로그에 API 키, Firebase 자격 증명, 시스템 프롬프트를 노출하지 않는다.
- 생성/수정/삭제는 자동 재시도하지 않는다.
- CORS는 `ALLOWED_ORIGINS`에 지정한 로컬과 Vercel Origin만 허용한다.

## 9. 테스트 전략

### 백엔드

- Pydantic 경계값, 미래 날짜, 중복 날짜 검증
- CRUD Service와 Repository 계약
- 빈 데이터, 부족한 데이터, 증가/유지/감소 추세
- CSV 헤더, 행 검증, dry-run, 중복 가져오기
- 대화 생성, 목록, 상세, 추가, 삭제
- 요약이 AI 시스템 프롬프트에 포함되는지 확인
- AI 성공 시만 대화가 저장되는지 확인
- 필수 API 정상/오류 계약과 `/health`, `/docs`

### 프론트엔드

- API URL 결합과 공개 오류 처리
- 입력 검증과 상태 변환
- 채팅 로딩/성공/실패 상태
- 대화 불러오기와 새 대화
- `API_BASE_URL`이 없을 때 빌드 실패

파이썬 테스트는 메모리 Repository와 가짜 AI 클라이언트를 사용하며, JavaScript 테스트는 외부 npm 패키지 없이 Node.js 내장 테스트 러너를 사용한다.

## 10. 배포와 사용자 작업

### Render 백엔드

- Root Directory: `m1-2/backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:create_app --factory --host 0.0.0.0 --port $PORT`
- Health Check: `/health`
- 코디세이 가상 키는 `COPA_API_KEY` 환경 변수로 등록한다.
- Firebase JSON은 Render Secret File `firebase-service-account.json`로 등록하고 `FIREBASE_SERVICE_ACCOUNT_FILE=/etc/secrets/firebase-service-account.json`을 사용한다.
- `ALLOWED_ORIGINS`에 로컬과 배포된 Vercel Origin을 설정한다.

### Vercel 프론트엔드

- Root Directory: `m1-2/frontend`
- Build Command: `npm run build`
- Output Directory: `dist`
- `API_BASE_URL`에 Render 백엔드 URL을 등록한다.

### 배포 후 확인

1. Render `/health`와 `/docs`를 확인한다.
2. CSV import 스크립트로 120개 이상을 Firestore에 등록한다.
3. Vercel 주소를 Render `ALLOWED_ORIGINS`에 추가한 뒤 재배포한다.
4. 요약, CRUD, AI 채팅, 대화 불러오기를 수동 확인한다.
5. 필수 스크린샷 3종을 촬영한다.

## 11. 비밀 정보 방침

- `m1-2/Codyssey ai api키.pdf`
- `m1-2/backend/.env`
- Firebase 서비스 계정 JSON
- Python/Node 캐시, 백엔드 가상환경, 프론트엔드 `dist`

위 파일과 생성물은 Git 추적에서 제외한다. `.env.example`과 Firebase 구조 예시에는 가짜 값만 넣는다.

## 12. 참고 구현에서 채택하는 패턴

`42yk/inno` M1-2를 구조 참고용으로 검토했다. 다음 패턴은 요구사항에 부합하므로 채택한다.

- Router/Service/Repository 분리
- 메모리 저장소와 가짜 AI를 이용한 테스트
- CSV dry-run과 중복 방지
- Render Secret File로 Firebase 자격 증명 관리
- 빌드 시 프론트엔드 API URL 주입
- 공개 오류 envelope와 콜드스타트 안내

코드와 문구를 복사하지 않고 이 설계와 학습시간 도메인에 맞게 독립적으로 구현한다. Function Calling, 사용자 지정 도메인, 체중 도메인 규칙은 채택하지 않는다.
