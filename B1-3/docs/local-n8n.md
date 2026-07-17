# 로컬 n8n 실행 및 설정

Make와 n8n 자동화 프로젝트를 로컬 n8n에서 실행하기 위한 안내입니다. n8n은 Docker Compose의 단일 컨테이너로 실행하며, 워크플로우와 자격증명은 Docker의 `n8n_data` 볼륨에 저장됩니다.

## 준비 사항

- Docker Desktop
- Google 계정과 Google Sheets 문서
- Discord Webhook 또는 Discord Bot 자격증명
- 저장소 밖에 별도로 보관한 `project1.json`, `project2.json`

## Docker Compose 실행

PowerShell에서 다음 명령을 실행합니다.

```powershell
Set-Location B1-3
Copy-Item .env.example .env
docker compose up -d
docker compose ps
```

브라우저에서 `http://localhost:5678`을 열고 n8n 소유자 계정을 생성합니다.

Docker CLI가 PATH에 없지만 Docker Desktop이 기본 경로에 설치되어 있다면 다음과 같이 실행할 수 있습니다.

```powershell
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' compose up -d
```

## Google Sheets와 Discord 수동 설정

### Google Sheets

1. n8n의 **Credentials**에서 Google Sheets 자격증명을 생성합니다.
2. 서비스 계정을 사용하는 경우 대상 Spreadsheet를 서비스 계정 이메일에 편집 권한으로 공유합니다.
3. Google Sheets 노드에 사용할 문서와 원본·합격·불합격 시트를 지정합니다.
4. 원본 시트에는 이름과 점수 열을 만들고, 프로젝트 2에서는 중복 갱신을 위한 식별값 열도 준비합니다.

### Discord

1. Discord 채널 설정에서 Webhook을 만들거나 Bot 자격증명을 준비합니다.
2. n8n의 **Credentials**에 Discord 자격증명을 등록합니다.
3. 오류·합격·불합격 Discord 노드에 같은 자격증명과 대상 채널을 지정합니다.
4. Webhook URL, Bot Token과 OAuth Token은 워크플로우 표현식이나 공개 문서에 직접 적지 않습니다.

### 분기 규칙

Switch 노드에 다음 세 경로를 설정합니다.

| 경로 | 조건 | 다음 작업 |
| --- | --- | --- |
| 오류 | 점수가 비어 있거나 판정 불가 | Discord 오류 메시지 전송 |
| 합격 | 50점 이상 | 합격 시트 기록 후 Discord 합격 메시지 전송 |
| 불합격 | 50점 미만 | 불합격 시트 기록 후 Discord 불합격 메시지 전송 |

프로젝트 2의 Schedule Trigger는 15분마다 실행하도록 설정하고 워크플로우를 활성화합니다.

## 워크플로우 가져오기

워크플로우 내보내기 파일은 저장소와 분리하여 다음 이름으로 보관합니다.

- 프로젝트 1: `project1.json`
- 프로젝트 2: `project2.json`

n8n의 워크플로우 화면에서 **Import from File**을 선택하고 각 JSON 파일을 가져옵니다. 내보내기 파일에는 실제 자격증명이 포함되지 않으므로 가져온 뒤 Google Sheets와 Discord Credentials를 직접 연결해야 합니다.

`project1.json`은 Make와 비교하기 위한 수동 실행 워크플로우로 사용합니다. `project2.json`은 Schedule Trigger를 15분으로 설정하고 합격·불합격 시트에 `Append or Update`를 사용합니다.

## 테스트 방법

원본 시트에 다음 세 종류의 데이터를 준비합니다.

| 테스트 데이터 | 예상 경로 | 확인 항목 |
| --- | --- | --- |
| 50점 이상 | 합격 | 합격 시트 기록 및 Discord 합격 메시지 |
| 50점 미만 | 불합격 | 불합격 시트 기록 및 Discord 불합격 메시지 |
| 점수 없음 | 오류 | 결과 시트에 기록하지 않고 Discord 오류 메시지 |

1. Manual Trigger로 실행하여 세 경로가 각각 1회 이상 처리되는지 확인합니다.
2. 합격·불합격 시트의 기록과 Discord 메시지를 확인합니다.
3. 프로젝트 2 워크플로우를 활성화합니다.
4. Executions에서 Schedule Trigger 실행 성공 여부와 분기별 item 수를 확인합니다.
5. 같은 식별값을 다시 처리했을 때 새 행이 계속 추가되지 않고 기존 행이 갱신되는지 확인합니다.

## 관리 명령

```powershell
docker compose logs -f n8n
docker compose down
```

`docker compose down -v`는 n8n 설정, 워크플로우와 자격증명이 저장된 볼륨까지 삭제하므로 완전히 초기화할 때만 사용합니다.
