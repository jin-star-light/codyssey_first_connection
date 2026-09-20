# Seoul Temperature Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible analysis of Seoul's 2025 daily temperatures with validated source data, four visualizations, and a Korean Markdown report that distinguishes observations from hypotheses.

**Architecture:** A single importable Python module owns API conversion, validation, feature engineering, summaries, chart generation, and the command-line entry point. Tests exercise those units with synthetic frames and mocked HTTP responses; the final task runs the same module against the real Open-Meteo archive and records the calculated results in the report.

**Tech Stack:** Python 3.10+, pandas, matplotlib, requests, pytest

**Spec:** `docs/superpowers/specs/2026-09-20-seoul-temperature-analysis-design.md`

## Global Constraints

- Analyze latitude `37.5665`, longitude `126.9780`, from `2025-01-01` through `2025-12-31` in timezone `Asia/Seoul`.
- Store temperatures in Celsius and preserve exactly the date, daily mean, daily maximum, and daily minimum source fields.
- Interpolate only numeric gaps of at most two consecutive days; reject longer gaps.
- Detect IQR outliers but never delete them automatically.
- Generate exactly the four named PNG charts under `m1-1/images` using a non-interactive Matplotlib backend.
- The report must separate `관찰(Fact)` from `해석(Hypothesis)` and include at least three evidence-backed insights.
- Default CLI execution must use the stored CSV; only `--refresh` may call the API.
- Do not claim long-term climate change or causal explanations from this one-year dataset.

## Review Focus

- Missing or malformed API keys must raise a readable schema error before an existing CSV is changed; pinned by `test_refresh_rejects_bad_payload_without_overwriting_csv` in Task 2.
- Duplicate, unordered, or absent calendar dates must be normalized or rejected deterministically; pinned by `test_validate_rejects_duplicate_dates` and `test_validate_reindexes_and_interpolates_two_day_gap` in Task 1.
- A gap longer than two days must not be silently interpolated; pinned by `test_validate_rejects_three_day_numeric_gap` in Task 1.
- Impossible temperature ordering (`min > mean` or `mean > max`) must fail validation; pinned by `test_validate_rejects_impossible_temperature_order` in Task 1.
- Plot generation must work without a display and produce non-empty, readable PNG files; pinned by `test_create_visualizations_writes_four_png_files` in Task 3.

---

### Task 1: Data conversion and quality validation

**Files:**
- Create: `m1-1/requirements.txt`
- Create: `m1-1/analysis.py`
- Create: `m1-1/tests/conftest.py`
- Create: `m1-1/tests/test_analysis.py`

**Interfaces:**
- Consumes: Open-Meteo JSON dictionaries and pandas DataFrames.
- Produces: `payload_to_dataframe(payload: dict) -> pd.DataFrame` and `validate_and_clean(df: pd.DataFrame, expected_start: str, expected_end: str) -> tuple[pd.DataFrame, dict]`.

- [ ] **Step 1: Declare runtime and test dependencies**

Create `m1-1/requirements.txt` with:

```text
pandas>=2.2,<3.0
matplotlib>=3.8,<4.0
requests>=2.31,<3.0
pytest>=8.0,<9.0
```

- [ ] **Step 2: Write the import fixture and failing validation tests**

Create `m1-1/tests/conftest.py`:

```python
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))
```

Start `m1-1/tests/test_analysis.py` with:

```python
import pandas as pd
import pytest

from analysis import payload_to_dataframe, validate_and_clean


def make_frame(start="2025-01-01", periods=365):
    dates = pd.date_range(start, periods=periods, freq="D")
    means = pd.Series(range(periods), dtype="float64") / 20 - 5
    return pd.DataFrame({
        "date": dates,
        "temperature_mean_c": means,
        "temperature_max_c": means + 4,
        "temperature_min_c": means - 4,
    })


def test_payload_to_dataframe_maps_open_meteo_fields():
    payload = {"daily": {
        "time": ["2025-01-01", "2025-01-02"],
        "temperature_2m_mean": [0.5, 1.5],
        "temperature_2m_max": [4.0, 5.0],
        "temperature_2m_min": [-3.0, -2.0],
    }}
    result = payload_to_dataframe(payload)
    assert result.columns.tolist() == [
        "date", "temperature_mean_c", "temperature_max_c", "temperature_min_c"
    ]
    assert result.loc[1, "temperature_mean_c"] == 1.5


def test_validate_reindexes_and_interpolates_two_day_gap():
    frame = make_frame()
    frame.loc[20:21, "temperature_mean_c"] = float("nan")
    cleaned, quality = validate_and_clean(frame, "2025-01-01", "2025-12-31")
    assert len(cleaned) == 365
    assert cleaned["temperature_mean_c"].isna().sum() == 0
    assert quality["interpolated_values"] == 2


def test_validate_rejects_three_day_numeric_gap():
    frame = make_frame()
    frame.loc[20:22, "temperature_mean_c"] = float("nan")
    with pytest.raises(ValueError, match="more than 2 consecutive days"):
        validate_and_clean(frame, "2025-01-01", "2025-12-31")


def test_validate_rejects_duplicate_dates():
    frame = make_frame()
    frame.loc[1, "date"] = frame.loc[0, "date"]
    with pytest.raises(ValueError, match="duplicate"):
        validate_and_clean(frame, "2025-01-01", "2025-12-31")


def test_validate_rejects_impossible_temperature_order():
    frame = make_frame()
    frame.loc[10, "temperature_min_c"] = frame.loc[10, "temperature_max_c"] + 1
    with pytest.raises(ValueError, match="min <= mean <= max"):
        validate_and_clean(frame, "2025-01-01", "2025-12-31")
```

- [ ] **Step 3: Run the focused tests and confirm the initial failure**

Run: `python -m pytest m1-1/tests/test_analysis.py -v`

Expected: collection fails because `analysis` does not exist or the imported functions are missing.

- [ ] **Step 4: Implement payload conversion and validation**

Create `m1-1/analysis.py` with constants for the four canonical column names. Implement `payload_to_dataframe` by requiring `payload["daily"]`, verifying the four Open-Meteo arrays exist and have equal lengths, renaming them to the canonical names, and parsing `date` with `pd.to_datetime`.

Implement `validate_and_clean` in this order:

```python
def validate_and_clean(df, expected_start, expected_end):
    # copy input; parse and sort dates
    # reject duplicate dates
    # reindex to pd.date_range(expected_start, expected_end, freq="D")
    # coerce the three temperature columns to numeric
    # inspect each column's consecutive missing runs and reject max run > 2
    # interpolate with method="time", limit=2, limit_area="inside"
    # reject any remaining missing value
    # verify min <= mean <= max on every row
    # return reset-index frame and a quality dictionary
```

The quality dictionary must contain `expected_days`, `source_rows`, `missing_dates`, `missing_values_before`, `interpolated_values`, and `remaining_missing_values`. Error messages must contain the phrases asserted by the tests.

- [ ] **Step 5: Run Task 1 tests**

Run: `python -m pytest m1-1/tests/test_analysis.py -v`

Expected: 5 tests pass.

- [ ] **Step 6: Commit Task 1**

```bash
git add m1-1/requirements.txt m1-1/analysis.py m1-1/tests/conftest.py m1-1/tests/test_analysis.py
git commit -m "feat: validate Seoul temperature data"
```

### Task 2: Reproducible API collection and local loading

**Files:**
- Modify: `m1-1/analysis.py`
- Modify: `m1-1/tests/test_analysis.py`

**Interfaces:**
- Consumes: `payload_to_dataframe` and `validate_and_clean` from Task 1.
- Produces: `fetch_weather_payload(session=requests) -> dict`, `refresh_weather_csv(csv_path: Path, session=requests) -> tuple[pd.DataFrame, dict]`, and `load_weather_csv(csv_path: Path) -> tuple[pd.DataFrame, dict]`.

- [ ] **Step 1: Add failing collection and overwrite-safety tests**

Append these test doubles and tests:

```python
from analysis import fetch_weather_payload, load_weather_csv, refresh_weather_csv


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.last_params = None

    def get(self, url, params, timeout):
        self.last_url = url
        self.last_params = params
        self.last_timeout = timeout
        return FakeResponse(self.payload)


def two_day_payload():
    return {"daily": {
        "time": ["2025-01-01", "2025-01-02"],
        "temperature_2m_mean": [0.5, 1.5],
        "temperature_2m_max": [4.0, 5.0],
        "temperature_2m_min": [-3.0, -2.0],
    }}


def test_fetch_uses_fixed_location_period_and_timezone():
    fake_session = FakeSession(two_day_payload())
    payload = fetch_weather_payload(fake_session)
    assert payload == fake_session.payload
    params = fake_session.last_params
    assert params["latitude"] == 37.5665
    assert params["longitude"] == 126.9780
    assert params["start_date"] == "2025-01-01"
    assert params["end_date"] == "2025-12-31"
    assert params["timezone"] == "Asia/Seoul"
    assert params["temperature_unit"] == "celsius"


def test_refresh_rejects_bad_payload_without_overwriting_csv(tmp_path):
    csv_path = tmp_path / "weather.csv"
    csv_path.write_text("original", encoding="utf-8")
    bad_session = FakeSession({"unexpected": {}})
    with pytest.raises(ValueError, match="daily"):
        refresh_weather_csv(csv_path, bad_session)
    assert csv_path.read_text(encoding="utf-8") == "original"


def test_load_weather_csv_does_not_use_network(tmp_path, monkeypatch):
    path = tmp_path / "weather.csv"
    make_frame().to_csv(path, index=False)
    monkeypatch.setattr("analysis.fetch_weather_payload", lambda session: pytest.fail("network used"))
    frame, quality = load_weather_csv(path)
    assert len(frame) == 365
    assert quality["remaining_missing_values"] == 0
```

- [ ] **Step 2: Run the new tests and verify missing interfaces**

Run: `python -m pytest m1-1/tests/test_analysis.py -k "fetch or refresh or load" -v`

Expected: collection errors name `fetch_weather_payload`, `refresh_weather_csv`, and `load_weather_csv`.

- [ ] **Step 3: Implement collection and safe persistence**

Use endpoint `https://archive-api.open-meteo.com/v1/archive`, timeout 30 seconds, and daily fields `temperature_2m_mean,temperature_2m_max,temperature_2m_min`. Convert and fully validate the response before creating the parent directory and calling `to_csv`. Wrap `requests.RequestException` as `RuntimeError` containing `Open-Meteo request failed`.

`load_weather_csv` must raise `FileNotFoundError` with an instruction to run `python analysis.py --refresh` when the CSV is absent. It must read and validate the stored data without importing network state.

- [ ] **Step 4: Run Task 2 tests**

Run: `python -m pytest m1-1/tests/test_analysis.py -v`

Expected: all Task 1 and Task 2 tests pass.

- [ ] **Step 5: Commit Task 2**

```bash
git add m1-1/analysis.py m1-1/tests/test_analysis.py
git commit -m "feat: collect reproducible Seoul weather data"
```

### Task 3: Time-series features, summaries, and charts

**Files:**
- Modify: `m1-1/analysis.py`
- Modify: `m1-1/tests/test_analysis.py`

**Interfaces:**
- Consumes: validated canonical DataFrame from Tasks 1 and 2.
- Produces: `add_time_series_features(df) -> pd.DataFrame`, `detect_iqr_outliers(series) -> pd.Series`, `monthly_summary(df) -> pd.DataFrame`, `seasonal_summary(df) -> pd.DataFrame`, `analysis_summary(df, quality) -> dict`, and `create_visualizations(df, output_dir: Path) -> list[Path]`.

- [ ] **Step 1: Add failing feature and summary tests**

Append tests for a small deterministic frame:

```python
def test_add_time_series_features_calculates_expected_values():
    frame = make_frame(periods=10)
    result = add_time_series_features(frame)
    assert pd.isna(result.loc[0, "daily_change_c"])
    assert result.loc[1, "daily_change_c"] == pytest.approx(0.05)
    assert result.loc[0, "diurnal_range_c"] == pytest.approx(8.0)
    assert result.loc[6, "rolling_mean_7d_c"] == pytest.approx(
        frame.loc[:6, "temperature_mean_c"].mean()
    )


def test_detect_iqr_outliers_marks_extreme_without_removing_it():
    series = pd.Series([10.0] * 8 + [40.0])
    mask = detect_iqr_outliers(series)
    assert mask.tolist() == [False] * 8 + [True]
    assert series[mask].iloc[0] == 40.0


def test_monthly_and_seasonal_summaries_use_calendar_groups():
    frame = add_time_series_features(make_frame())
    monthly = monthly_summary(frame)
    seasonal = seasonal_summary(frame)
    assert monthly.index.tolist() == list(range(1, 13))
    assert set(seasonal.index) == {"봄", "여름", "가을", "겨울"}
    assert monthly.loc[1, "days"] == 31
```

- [ ] **Step 2: Add a failing headless visualization test**

```python
def test_create_visualizations_writes_four_png_files(tmp_path):
    frame = add_time_series_features(make_frame())
    paths = create_visualizations(frame, tmp_path)
    assert [path.name for path in paths] == [
        "01_annual_temperature_trend.png",
        "02_monthly_temperature.png",
        "03_daily_temperature_change.png",
        "04_monthly_diurnal_range.png",
    ]
    assert all(path.read_bytes().startswith(b"\x89PNG") for path in paths)
    assert all(path.stat().st_size > 10_000 for path in paths)
```

- [ ] **Step 3: Run feature and chart tests to confirm failure**

Run: `python -m pytest m1-1/tests/test_analysis.py -k "features or outliers or summaries or visualizations" -v`

Expected: failures identify the missing feature, summary, and chart functions.

- [ ] **Step 4: Implement derived metrics and group summaries**

Use a 7-row rolling window with `min_periods=1`, `Series.diff()` for daily change, and maximum minus minimum for diurnal range. Map months to seasons with `{12, 1, 2}: 겨울`, `{3, 4, 5}: 봄`, `{6, 7, 8}: 여름`, and `{9, 10, 11}: 가을`. IQR detection must use strict bounds `value < Q1 - 1.5*IQR` or `value > Q3 + 1.5*IQR`.

`analysis_summary` must return JSON-serializable values for the hottest date/value, coldest date/value, largest warming date/value, largest cooling date/value, warmest month/value, coldest month/value, largest-diurnal-range month/value, IQR outlier count, and the quality dictionary.

- [ ] **Step 5: Implement the four charts**

Set `matplotlib.use("Agg")` before importing `pyplot`. Use English chart text to avoid platform-dependent Korean font failures, Celsius units on every temperature axis, month labels `Jan` through `Dec`, `tight_layout()`, 160 DPI, and `plt.close(fig)` after every save. Highlight the absolute daily changes of at least 5°C on chart 3.

- [ ] **Step 6: Run all unit tests**

Run: `python -m pytest m1-1/tests/test_analysis.py -v`

Expected: all tests pass and Matplotlib emits no GUI error.

- [ ] **Step 7: Commit Task 3**

```bash
git add m1-1/analysis.py m1-1/tests/test_analysis.py
git commit -m "feat: analyze and visualize Seoul temperatures"
```

### Task 4: CLI, real dataset, report, and submission verification

**Files:**
- Modify: `m1-1/analysis.py`
- Create: `m1-1/tests/test_deliverables.py`
- Create: `m1-1/data/seoul_weather_2025.csv`
- Create: `m1-1/images/01_annual_temperature_trend.png`
- Create: `m1-1/images/02_monthly_temperature.png`
- Create: `m1-1/images/03_daily_temperature_change.png`
- Create: `m1-1/images/04_monthly_diurnal_range.png`
- Create: `m1-1/REPORT.md`
- Create: `m1-1/README.md`

**Interfaces:**
- Consumes: all functions from Tasks 1–3 and the Open-Meteo Historical Weather API.
- Produces: `main(argv: list[str] | None = None) -> int`, the committed source CSV, four PNGs, Korean report, and reproduction guide.

- [ ] **Step 1: Add failing CLI and deliverable contract tests**

Add this CLI test to `m1-1/tests/test_analysis.py` so default mode and refresh mode are both pinned without performing HTTP or writing charts:

```python
import analysis


def test_main_refreshes_only_when_flag_is_present(monkeypatch, tmp_path):
    frame = make_frame()
    calls = []

    def fake_load(path):
        calls.append("load")
        return frame, {"remaining_missing_values": 0}

    def fake_refresh(path):
        calls.append("refresh")
        return frame, {"remaining_missing_values": 0}

    monkeypatch.setattr(analysis, "DATA_PATH", tmp_path / "weather.csv")
    monkeypatch.setattr(analysis, "IMAGES_DIR", tmp_path / "images")
    monkeypatch.setattr(analysis, "load_weather_csv", fake_load)
    monkeypatch.setattr(analysis, "refresh_weather_csv", fake_refresh)
    monkeypatch.setattr(analysis, "create_visualizations", lambda df, path: [])
    monkeypatch.setattr(analysis, "analysis_summary", lambda df, quality: {"ok": True})

    assert analysis.main([]) == 0
    assert analysis.main(["--refresh"]) == 0
    assert calls == ["load", "refresh"]
```

Create `m1-1/tests/test_deliverables.py`:

```python
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_submission_contains_complete_dataset_and_images():
    data = pd.read_csv(ROOT / "data" / "seoul_weather_2025.csv")
    assert len(data) == 365
    assert data["date"].nunique() == 365
    for name in (
        "01_annual_temperature_trend.png",
        "02_monthly_temperature.png",
        "03_daily_temperature_change.png",
        "04_monthly_diurnal_range.png",
    ):
        image = ROOT / "images" / name
        assert image.read_bytes().startswith(b"\x89PNG")
        assert image.stat().st_size > 10_000


def test_report_has_required_sections_and_working_image_links():
    report = (ROOT / "REPORT.md").read_text(encoding="utf-8")
    for heading in (
        "분석 주제", "분석 질문", "데이터 설명", "데이터 정제",
        "분석 결과 및 시각화", "인사이트", "결론", "한계점", "AI 사용 로그",
    ):
        assert heading in report
    assert report.count("관찰(Fact)") >= 3
    assert report.count("해석(Hypothesis)") >= 3
    for target in (
        "images/01_annual_temperature_trend.png",
        "images/02_monthly_temperature.png",
        "images/03_daily_temperature_change.png",
        "images/04_monthly_diurnal_range.png",
    ):
        assert target in report
        assert (ROOT / target).is_file()


def test_readme_documents_reproduction_and_attribution():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "python analysis.py --refresh" in readme
    assert "python analysis.py" in readme
    assert "Open-Meteo" in readme
    assert "CC BY 4.0" in readme
```

- [ ] **Step 2: Run contract tests and verify missing deliverables**

Run: `python -m pytest m1-1/tests/test_deliverables.py -v`

Expected: failures identify the absent CSV, images, report, and README.

- [ ] **Step 3: Implement the CLI**

Use `argparse` with `--refresh`, default paths resolved relative to `analysis.py`, and the following flow:

```python
frame, quality = (
    refresh_weather_csv(DATA_PATH) if args.refresh else load_weather_csv(DATA_PATH)
)
featured = add_time_series_features(frame)
paths = create_visualizations(featured, IMAGES_DIR)
summary = analysis_summary(featured, quality)
print(json.dumps(summary, ensure_ascii=False, indent=2))
print("Generated:", *(str(path) for path in paths), sep="\n- ")
return 0
```

Guard execution with `if __name__ == "__main__": raise SystemExit(main())`.

- [ ] **Step 4: Fetch and analyze the real dataset**

From `m1-1`, run: `python analysis.py --refresh`

Expected: `data/seoul_weather_2025.csv` has 365 rows, all four images are generated, and stdout prints the calculated JSON summary. Preserve that stdout for the next step.

- [ ] **Step 5: Write the Korean analysis report from calculated values**

Create `m1-1/REPORT.md` with the nine required headings from the contract test. Embed every image with a relative Markdown link. Use the exact JSON summary values in at least these three insight structures:

1. Annual seasonality: hottest/coldest date and value, plus warmest/coldest monthly mean.
2. Rapid transitions: largest warming and cooling date and magnitude; explain that the dataset establishes the change but not its meteorological cause.
3. Diurnal range: month with the largest average diurnal range and its value; frame any reason as a hypothesis requiring humidity/cloud/wind data.

Add a fourth insight if the graph exposes a clear pattern. State that Open-Meteo historical data are gridded reanalysis rather than a Seoul weather-station observation, and that one year cannot establish climate change. In `AI 사용 로그`, name preprocessing, test generation, visualization, interpretation drafting, the reason for each, and verification by automated tests, recomputation, and visual inspection.

- [ ] **Step 6: Write reproduction and attribution instructions**

Create `m1-1/README.md` with Python 3.10+ setup, Windows and POSIX virtual-environment activation, `pip install -r requirements.txt`, default offline reproduction (`python analysis.py`), optional refresh (`python analysis.py --refresh`), tests (`python -m pytest tests -v`), the folder tree, and attribution links to Open-Meteo Historical Weather API and its CC BY 4.0 terms. Explain that a refresh can change values slightly if the upstream reanalysis is revised.

- [ ] **Step 7: Run complete automated verification**

Run from repository root:

```bash
python -m pytest m1-1/tests -v
python m1-1/analysis.py
git diff --check
```

Expected: all tests pass, the offline analysis regenerates four images without network access, and `git diff --check` prints nothing.

- [ ] **Step 8: Visually inspect all four charts**

Open each PNG and verify that titles, dates, legend entries, Celsius units, bar labels, highlighted rapid-change dates, and source footers are readable and not clipped. If a chart fails inspection, adjust only its plotting function, rerun the focused chart test, regenerate images, and inspect again.

- [ ] **Step 9: Commit the completed submission**

```bash
git add m1-1/analysis.py m1-1/tests m1-1/data m1-1/images m1-1/REPORT.md m1-1/README.md
git commit -m "feat: complete Seoul temperature time-series analysis"
```
