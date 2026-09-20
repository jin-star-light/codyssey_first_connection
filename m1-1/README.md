# 2025년 서울 일별 기온 변화 분석

Open-Meteo의 2025년 서울 일별 평균·최고·최저기온 365개를 검증하고, 이동평균·일별 변화량·월별/계절별 통계·일교차를 분석하는 프로젝트입니다. 최종 해석은 [REPORT.md](REPORT.md)에서 확인할 수 있습니다.

## 폴더 구조

```text
m1-1/
├── M1-1. subject.md
├── README.md
├── REPORT.md
├── analysis.py
├── requirements.txt
├── data/
│   └── seoul_weather_2025.csv
├── images/
│   ├── 01_annual_temperature_trend.png
│   ├── 02_monthly_temperature.png
│   ├── 03_daily_temperature_change.png
│   └── 04_monthly_diurnal_range.png
└── tests/
    ├── conftest.py
    ├── test_analysis.py
    └── test_deliverables.py
```

## 실행 환경

- Python 3.10 이상
- 인터넷 연결: 최초 데이터 갱신 시에만 필요

### 1. 가상환경 생성 및 활성화

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS 또는 Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 저장된 데이터로 분석 재현

`m1-1` 폴더에서 실행합니다. 이 명령은 인터넷에 접속하지 않고 저장된 CSV로 통계와 그래프를 다시 만듭니다.

```bash
python analysis.py
```

### 4. 원본 데이터 다시 수집하기

Open-Meteo API에서 자료를 다시 받아 CSV와 그래프를 갱신하려면 다음 명령을 실행합니다.

```bash
python analysis.py --refresh
```

상류 재분석 자료의 품질 관리나 수정으로 인해 나중에 다시 수집한 값이 현재 CSV와 소폭 달라질 수 있습니다.

### 5. 자동 테스트

```bash
python -m pytest tests -v
```

테스트는 API 응답 변환, 날짜·결측치·기온 순서 검증, 이동평균과 변화량 계산, 월별·계절별 집계, CLI의 오프라인 기본 동작, 데이터 행 수와 이미지·리포트 링크를 확인합니다.

## 데이터 출처와 라이선스

- 데이터 서비스: [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api)
- 이용 조건: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- 위치와 기간: 서울 중심부(37.5665, 126.9780), 2025-01-01 ~ 2025-12-31, `Asia/Seoul`
- 기반 자료: Open-Meteo가 제공하는 ERA5 계열 등의 격자형 재분석 자료

이 자료는 서울의 특정 기상관측소 원시 관측값과 일치하지 않을 수 있으며, 한 해의 자료만으로 장기 기후변화를 판단해서는 안 됩니다.
