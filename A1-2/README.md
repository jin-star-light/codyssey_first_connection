# A1-2 국내 여행 추천 프로그램

사용자가 입력한 여행 날짜를 바탕으로 다음 작업을 순서대로 실행하는 Python CLI 프로그램입니다.

1. Codyssey OpenAI 호환 LLM API의 `gpt-5.4-mini`가 여행 도시·날씨·행사를 JSON으로 추천합니다.
2. Kakao Local API가 추천 도시의 맛집을 최대 5곳 검색합니다.
3. LLM이 추천 및 맛집 데이터를 조합해 Markdown 여행 리포트를 만듭니다.
4. 원본 JSON과 최종 Markdown을 `results/` 폴더에 저장합니다.

## 요구 환경

- Python 3.10 이상
- Codyssey API 콘솔에서 발급한 virtual key
- Kakao Developers에서 발급한 REST API 키와 Local API 사용 권한

## 설치

`A1-2` 폴더에서 가상환경을 만들고 의존성을 설치합니다.

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

macOS/Linux:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## API 키 설정

`.env.example`을 `.env`로 복사한 후 실제 키를 입력합니다.

```dotenv
COPA_API_KEY=YOUR_CODYSSEY_VIRTUAL_KEY
KAKAO_REST_API_KEY=YOUR_KAKAO_REST_API_KEY
```

또는 현재 터미널 세션에 환경변수를 설정할 수 있습니다.

Windows PowerShell:

```powershell
$env:COPA_API_KEY="YOUR_CODYSSEY_VIRTUAL_KEY"
$env:KAKAO_REST_API_KEY="YOUR_KAKAO_REST_API_KEY"
```

macOS/Linux:

```bash
export COPA_API_KEY="YOUR_CODYSSEY_VIRTUAL_KEY"
export KAKAO_REST_API_KEY="YOUR_KAKAO_REST_API_KEY"
```

### 보안 주의 사항

- 실제 키를 소스 코드, README, 결과 JSON, 화면 캡처 또는 로그에 넣지 마세요.
- `.env`는 `.gitignore`에 포함되어 있으므로 저장소에 커밋하지 마세요.
- 키가 노출되었다면 즉시 제공자 콘솔에서 폐기하고 새 키를 발급하세요.
- 환경변수를 사용하면 키 교체 시 코드를 수정하지 않아도 되고, 협업 중 실수로 키를 공개할 위험을 줄일 수 있습니다.

## 실행

```bash
python travel_planner.py --date "2026-03-15"
```

과제 명세의 단일 하이픈 표기도 지원합니다.

```bash
python travel_planner.py -date "2026-03-15"
```

날짜는 실제로 존재하는 `YYYY-MM-DD` 형식이어야 합니다. 예를 들어 `2026-02-30`이나 `2026/03/15`는 사용법과 오류 메시지를 출력하고 종료합니다.

정상 실행 시 다음과 같은 진행 로그가 표시됩니다.

```text
[1/3] 1차 추천 생성 중(LLM)...
[2/3] 맛집 검색 중(Kakao Local)...
[3/3] 최종 리포트 생성 중(LLM)...
완료! 원본 데이터: .../results/2026-03-15_raw_data.json
완료! 여행 리포트: .../results/2026-03-15_travel_plan.md
```

## 결과 확인

실행 날짜를 기준으로 `results/`에 두 파일이 생성됩니다.

- `<YYYY-MM-DD>_raw_data.json`: 입력 날짜, 1차 추천 JSON, 맛집 목록, 오류 목록
- `<YYYY-MM-DD>_travel_plan.md`: 추천 지역·이유·날씨·행사·맛집·1일 일정·오류 요약

맛집 검색 결과가 없거나 Kakao API가 실패하더라도 프로그램은 중단되지 않습니다. 원본 JSON의 `errors`에 원인이 기록되고, Markdown 맛집 섹션에는 `데이터 없음`이 표시됩니다. 최종 LLM 리포트 호출이 실패하면 프로그램이 같은 원본 데이터로 기본 Markdown 리포트를 생성합니다.

## API 요청 흐름

### POST: LLM 요청

LLM은 서버에 프롬프트와 모델 설정을 보내 새 결과를 생성하므로 `POST`를 사용합니다.

- URL: `https://copa.codyssey.kr/v1/chat/completions`
- 모델: `gpt-5.4-mini`
- 인증: `Authorization: Bearer <COPA_API_KEY>`

1차 응답은 다음 필드를 갖는 JSON 객체여야 합니다.

```json
{
  "recommended_city": "제주",
  "weather": "해당 시기의 일반적인 날씨 요약",
  "events": ["행사 또는 축제 후보"],
  "reason": "추천 근거"
}
```

JSON 파싱이나 필드 타입 검사가 실패하면 필수 키만 올바른 JSON으로 다시 출력하도록 LLM에 한 번만 재요청합니다.

### GET: 장소 검색

Kakao Local은 기존 장소 데이터를 검색하므로 `GET`을 사용합니다.

- URL: `https://dapi.kakao.com/v2/local/search/keyword.json`
- 검색어: `<recommended_city> 맛집`
- 인증: `Authorization: KakaoAK <KAKAO_REST_API_KEY>`
- 최대 결과: 5곳

응답의 장소 이름, 주소, 카테고리, URL, x/y 좌표를 공통 형식으로 정리해 최종 리포트 입력으로 넘깁니다.

## 대표 오류와 대응

- 키 미설정: 필요한 환경변수 이름과 설정 방법을 출력하고 즉시 종료합니다.
- `401`/`403`: 키 값, 인증 헤더, Kakao 앱 권한을 확인합니다.
- `429`: 사용량 및 쿼터를 확인합니다.
- 네트워크 오류: 인터넷 연결과 API 상태를 확인합니다.
- LLM JSON 오류: 자동으로 한 번 교정 요청한 후에도 실패하면 종료합니다.
- 장소 검색 오류 또는 0건: `errors`에 기록하고 빈 맛집 목록으로 리포트 생성을 계속합니다.

## 테스트

테스트는 실제 외부 API를 호출하지 않고 HTTP 경계를 모킹합니다.

```bash
python -m unittest discover -s tests -v
```

날짜 검증, API 요청 규격, LLM JSON 재시도, Kakao 오류 복구, 결과 파일 저장, 대체 리포트 생성을 검증합니다.
