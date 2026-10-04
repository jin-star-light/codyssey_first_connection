# M1-2 제출용 캡처와 설명 가이드

subject가 요구하는 핵심 증빙은 AI 채팅, 데이터 CRUD, 저장된 대화 불러오기입니다. 좁은 화면에서도 글자가 잘 보이도록 기능별로 나눠 캡처했습니다. 모든 화면은 실제 배포 서비스에서 촬영했으며 API 키와 서비스 계정 정보는 포함하지 않았습니다.

## 제출 시 우선 사용할 캡처

| 파일 | 증명하는 항목 | 설명할 때 사용할 문장 |
| --- | --- | --- |
| `01-ai-chat-summary.jpg` | 데이터 기반 질문과 AI 답변 | “140일 학습 데이터를 요약해 AI 프롬프트에 포함했고, 후속 질문까지 같은 대화 맥락에서 답변합니다.” |
| `02-data-summary.jpg` | 데이터 로딩 및 통계 요약 | “Firestore의 140개 기록을 불러와 총 408시간, 평균 2.9시간, 최근 3.2시간으로 계산해 표시합니다.” |
| `03-conversation-history.jpg` | 대화 저장 및 불러오기 | “Firestore에 저장된 대화 제목과 4개 메시지가 보이며, 항목을 선택하면 기존 대화를 이어갈 수 있습니다.” |
| `04-data-crud.jpg` | 데이터 생성과 목록 갱신 | “새 학습 기록을 저장하자 목록 최상단에 바로 반영되었습니다. 캡처 후 임시 기록은 삭제해 원래 140건으로 복구했습니다.” |

위 네 장으로 subject의 필수 스크린샷 요구사항을 충족합니다. AI 기능은 `01`과 `02`를 함께 제시하면 답변이 실제 학습 데이터 요약을 근거로 한다는 점이 더 명확합니다.

## 구현·배포 보조 증빙

| 파일 | 증명하는 항목 | 설명할 때 사용할 문장 |
| --- | --- | --- |
| `05-swagger.jpg` | Render에 배포된 FastAPI 문서 | “Render 백엔드가 공개 배포되어 있고 요약, CRUD, 대화 API를 Swagger에서 확인할 수 있습니다.” |
| `06-firestore-data.jpg` | 학습 데이터 영구 저장 | “Firestore `data` 컬렉션에 날짜별 학습시간과 메모가 저장됩니다.” |
| `07-firestore-conversations.jpg` | 대화 영구 저장 | “Firestore `conversations` 컬렉션에 사용자와 AI의 메시지 배열이 저장됩니다.” |

## 발표용 한 문단 설명

Study Rhythm은 Vercel의 Vanilla JavaScript 프런트엔드, Render의 FastAPI 백엔드, Firebase Firestore로 구성했습니다. 프런트엔드가 백엔드의 `/api/data/summary`와 CRUD API를 호출하고, 백엔드는 학습 데이터 요약을 시스템 프롬프트에 넣어 Codyssey의 OpenAI 호환 API에 전달합니다. AI 응답과 대화 내역은 다시 Firestore에 저장되므로 새로고침 후에도 과거 대화를 불러와 이어갈 수 있습니다.

## 제출 주소

- 프런트엔드: https://m1-2-study-coach.vercel.app
- 백엔드: https://m1-2-study-coach-api.onrender.com
- Swagger: https://m1-2-study-coach-api.onrender.com/docs
- GitHub: https://github.com/jin-star-light/codyssey_first_connection

## 최종 확인 결과

- Firestore 학습 데이터: 140건으로 복구 완료
- 저장 대화: 1개, 메시지 4개
- AI 질문·후속 질문 응답: 정상
- Render Swagger와 Vercel 공개 페이지: 정상
- 보너스 기능: 제출 범위에서 제외
