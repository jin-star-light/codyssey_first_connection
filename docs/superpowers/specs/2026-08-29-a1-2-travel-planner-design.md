# A1-2 국내 여행 추천 프로그램 설계

## 목표

사용자가 입력한 국내 여행 날짜를 바탕으로 LLM이 여행지를 추천하고, Kakao Local API가 추천 지역의 맛집을 검색한 뒤, LLM이 최종 Markdown 여행 리포트를 작성하는 Python 3.10 이상 CLI 프로그램을 만든다.

## 범위

- `argparse` 기반 `-date` 및 `--date` 필수 옵션과 `YYYY-MM-DD` 형식 검증
- Codyssey OpenAI 호환 API의 `gpt-5.4-mini` 모델을 이용한 추천 JSON 및 최종 리포트 생성
- Kakao Local 키워드 검색 API를 이용한 추천 지역 맛집 최대 5곳 검색
- 원본 JSON과 최종 Markdown 리포트를 `results/`에 저장
- 환경변수 및 `.env`를 통한 API 키 관리
- API·파싱 오류 처리와 단위 테스트
- 실행 및 보안 안내를 포함한 README

보너스인 복수 지역 추천과 결과 캐싱은 구현하지 않는다.

## 구조

프로그램은 `A1-2/travel_planner.py`에 두되, CLI 처리와 외부 연동을 독립 함수로 분리한다. 작은 학습용 과제이므로 불필요한 패키지 계층은 만들지 않는다.

주요 함수의 책임은 다음과 같다.

- 날짜 파싱 및 검증
- 환경변수에서 `COPA_API_KEY`, `KAKAO_REST_API_KEY` 로드 및 누락 검사
- Codyssey OpenAI 호환 Chat Completions API 호출
- 추천 JSON 추출·필수 키 및 타입 검증·최대 1회 재시도
- Kakao Local 맛집 검색 및 공통 필드로 정규화
- 최종 리포트 생성
- 원본 JSON과 Markdown 파일 저장
- 전체 작업 흐름 실행과 진행 로그 출력

외부 HTTP 호출에는 `requests`, `.env` 로드에는 `python-dotenv`를 사용한다.

## API 연동

LLM 요청은 API 문서에 맞춰 `https://copa.codyssey.kr/v1/chat/completions`에 POST로 전송한다. `Authorization: Bearer <COPA_API_KEY>`와 `Content-Type: application/json` 헤더를 사용하고, 모델은 정확한 ID인 `gpt-5.4-mini`로 고정한다.

장소 요청은 Kakao Local 키워드 검색 엔드포인트에 GET으로 전송한다. `Authorization: KakaoAK <KAKAO_REST_API_KEY>` 헤더를 사용하고 검색어는 `<추천 도시> 맛집`, 결과 개수는 5개로 제한한다. 응답은 `name`, `address`, `category`, `url`, `x`, `y` 필드로 정규화하며 좌표는 가능한 경우 숫자로 변환한다.

## 데이터 흐름

1. CLI에서 날짜를 입력받아 실제 달력 날짜인지 검증한다.
2. API 키 두 개를 확인하고 누락 시 설정 방법과 함께 종료한다.
3. LLM에 날짜를 전달해 `recommended_city`, `weather`, `events`, `reason`을 포함한 JSON을 요청한다.
4. 응답을 파싱하고 스키마를 검사한다. 실패하면 필수 키만 갖는 JSON을 다시 출력하도록 한 번 재요청한다.
5. 추천 도시를 Kakao 검색어로 사용해 맛집을 최대 5곳 조회한다.
6. 추천 결과, 맛집 목록, 오류 목록을 원본 JSON으로 저장한다.
7. 같은 데이터를 LLM에 전달해 필수 섹션이 포함된 Markdown 여행 리포트를 생성한다.
8. Markdown을 저장하고 두 결과 파일의 경로를 출력한다.

원본 JSON 최상위 구조는 `date`, `recommendation`, `restaurants`, `errors`로 고정한다. `errors`의 각 항목은 `step`, `type`, `message`를 가진다.

## 오류 처리

- 날짜 오류: `argparse` 사용법과 오류를 출력하고 API 호출 없이 종료한다.
- API 키 누락: 누락된 환경변수와 설정 예시를 출력하고 즉시 종료한다.
- LLM 추천 HTTP·응답 구조 오류: 오류 내용을 표시하고 종료한다. JSON 파싱 및 스키마 오류만 한 번 재시도한다.
- Kakao 네트워크·인증·쿼터·응답 오류: 오류를 `errors`에 추가하고 빈 맛집 목록으로 계속한다.
- Kakao 검색 결과 0건: `EMPTY_RESULT`를 기록하고 계속한다.
- 최종 LLM 리포트 생성 실패: 저장된 원본 데이터를 바탕으로 필수 섹션을 갖춘 로컬 Markdown 대체 리포트를 생성하여 결과물 생성을 보장한다.

로그와 오류 메시지에는 키 또는 인증 헤더를 포함하지 않는다.

## 결과 파일

`A1-2/results/`를 자동 생성하고 입력 날짜를 기준으로 다음 파일을 쓴다.

- `<YYYY-MM-DD>_raw_data.json`
- `<YYYY-MM-DD>_travel_plan.md`

JSON은 UTF-8, 한글 비 ASCII 이스케이프 없이 들여쓰기하여 저장한다. Markdown 리포트에는 추천 지역, 추천 이유, 날씨, 행사·축제, 맛집, 오전·오후·저녁 일정, 오류 요약을 포함한다. 맛집이 없으면 `데이터 없음`을 명시한다.

## 테스트

`unittest`와 `unittest.mock`으로 실제 네트워크를 사용하지 않는 테스트를 작성한다.

- 올바른 날짜와 존재하지 않는 날짜 검증
- 추천 JSON 정상 파싱과 코드 펜스 제거
- 잘못된 추천 JSON에 대한 정확히 한 번의 재시도
- Kakao 응답 필드 정규화
- Kakao 실패 및 0건 결과가 전체 흐름을 중단하지 않는지 확인
- 원본 JSON 및 Markdown 파일 생성과 필수 내용 확인
- 모델 ID, 엔드포인트, 인증 헤더가 문서 규격대로 요청되는지 확인

## 제출 파일

- `A1-2/travel_planner.py`
- `A1-2/tests/test_travel_planner.py`
- `A1-2/requirements.txt`
- `A1-2/.env.example`
- `A1-2/.gitignore`
- `A1-2/README.md`
- 실행 시 생성되는 `A1-2/results/*.json`, `A1-2/results/*.md`
