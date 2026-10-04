# M1-2 Study Rhythm — 개인 학습시간 기반 AI 코치

매일의 학습시간을 Firebase Firestore에 저장하고, 요약·추세와 함께 Codyssey AI가 학습 조언을 제공하는 웹 서비스입니다. 보너스 항목인 Function Calling, MCP/GPT Actions는 구현하지 않았습니다.

## 구성

- 백엔드: FastAPI, Firebase Admin SDK, Codyssey OpenAI 호환 API
- 프런트엔드: HTML/CSS/Vanilla JavaScript, Vercel 정적 배포
- 데이터: `data`, `conversations` Firestore 컬렉션
- 샘플: `backend/data/study_hours.csv`의 140행

## API

| 기능 | 엔드포인트 |
|---|---|
| 학습 기록 생성 | `POST /api/data` |
| 학습 기록 목록 | `GET /api/data` |
| 학습 요약 | `GET /api/data/summary` |
| 학습 기록 수정 | `PUT /api/data/{id}` |
| 학습 기록 삭제 | `DELETE /api/data/{id}` |
| AI 질문 | `POST /api/chat` |
| 대화 생성·목록 | `POST /api/conversations`, `GET /api/conversations` |
| 대화 상세·삭제 | `GET /api/conversations/{id}`, `DELETE /api/conversations/{id}` |
| 상태·문서 | `GET /health`, `GET /docs` |

## 로컬 실행

Python 3.10 이상과 Node.js 20 이상이 필요합니다. `backend/.env.example`을 `backend/.env`로 복사하고 실제 값은 로컬 파일에만 입력합니다.

```powershell
cd m1-2/backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:create_app --factory --reload
```

필수 백엔드 환경 변수:

- `COPA_API_KEY`: Codyssey API 콘솔에서 발급한 전체 키
- `FIREBASE_SERVICE_ACCOUNT_FILE`: Firebase 서비스 계정 JSON 경로
- `ALLOWED_ORIGINS`: 프런트엔드 주소. 여러 개면 쉼표로 구분
- `AI_BASE_URL=https://copa.codyssey.kr/v1`
- `AI_MODEL=gpt-5.4-mini`

샘플 검증과 실제 입력:

```powershell
python scripts/import_csv.py data/study_hours.csv --dry-run
python scripts/import_csv.py data/study_hours.csv
```

프런트엔드는 공개 백엔드 주소만 받습니다. AI 키나 Firebase 키를 넣지 않습니다.

```powershell
cd m1-2/frontend
$env:API_BASE_URL="http://localhost:8000"
npm run build
python -m http.server 5173 -d dist
```

## 사용자가 직접 해야 하는 배포 작업

아래 서비스는 과제 규모에서 무료 요금제로 시작할 수 있습니다. 별도 유료 도구는 필수가 아닙니다. Render 무료 서버는 한동안 요청이 없으면 잠들 수 있어 첫 응답이 최대 약 1분 느릴 수 있습니다.

1. **Firebase**
   - Firebase Console에서 프로젝트를 만들고 Firestore Database를 Native 모드로 생성합니다.
   - 프로젝트 설정 → 서비스 계정 → 새 비공개 키 생성으로 JSON을 내려받습니다.
   - JSON은 GitHub에 올리지 않습니다. 로컬에서는 `backend/.env`가 가리키게 합니다.
2. **GitHub**
   - 이 프로젝트를 본인 비공개 또는 공개 저장소에 push합니다.
   - `Codyssey ai api키.pdf`, `.env`, 실제 서비스 계정 JSON이 커밋되지 않았는지 확인합니다.
3. **Render 백엔드**
   - GitHub 저장소를 연결하고 `backend/render.yaml` Blueprint를 사용하거나 같은 값으로 Web Service를 만듭니다.
   - Secret 환경 변수 `COPA_API_KEY`를 입력합니다.
   - Secret File 경로 `/etc/secrets/firebase-service-account.json`에 Firebase JSON 내용을 등록합니다.
   - 처음에는 `ALLOWED_ORIGINS`를 로컬 주소로 두고 배포합니다. 배포 후 `https://본인서비스.onrender.com/health`와 `/docs`를 확인합니다.
4. **샘플 데이터 입력**
   - 로컬 `.env`에서 배포용 Firebase 서비스 계정을 가리킨 뒤 위 `python scripts/import_csv.py ...` 명령을 실행합니다.
   - 140행이 생성되고 두 번째 실행은 중복 날짜를 `skipped`로 표시해야 합니다.
5. **Vercel 프런트엔드**
   - 같은 GitHub 저장소를 연결하고 Root Directory를 `m1-2/frontend`로 지정합니다.
   - Build Command는 `npm run build`, Output Directory는 `dist`입니다.
   - 환경 변수 `API_BASE_URL`에 Render의 `https://...onrender.com` 주소를 입력합니다.
   - Vercel 배포 주소가 나오면 Render의 `ALLOWED_ORIGINS`를 그 주소로 변경하고 재배포합니다.
6. **최종 확인과 제출**
   - 데이터 생성·수정·삭제, 요약 갱신, AI 새 대화·이어가기·삭제를 직접 확인합니다.
   - `screenshots/README.md` 체크리스트에 따라 스크린샷을 촬영합니다.
   - 아래 실제 주소를 제출 문서에 사용합니다.

```
Frontend URL: https://m1-2-study-coach.vercel.app
Backend URL:  https://m1-2-study-coach-api.onrender.com
API Docs:     https://m1-2-study-coach-api.onrender.com/docs
GitHub URL:   https://github.com/jin-star-light/codyssey_first_connection
```

## 테스트

```powershell
cd m1-2/backend
python -m pytest -q
python -m compileall -q app scripts

cd ../frontend
npm test
$env:API_BASE_URL="https://example.onrender.com"
npm run build
```

배포와 제출용 캡처까지 완료했습니다. 실제 API 키와 Firebase 서비스 계정 JSON은 저장소에 포함하지 않습니다.
