import pandas as pd
import pytest

from analysis import (
    add_time_series_features,
    analysis_summary,
    create_visualizations,
    detect_iqr_outliers,
    fetch_weather_payload,
    load_weather_csv,
    monthly_summary,
    payload_to_dataframe,
    refresh_weather_csv,
    seasonal_summary,
    validate_and_clean,
)


def make_frame(start="2025-01-01", periods=365):
    dates = pd.date_range(start, periods=periods, freq="D")
    means = pd.Series(range(periods), dtype="float64") / 20 - 5
    return pd.DataFrame(
        {
            "date": dates,
            "temperature_mean_c": means,
            "temperature_max_c": means + 4,
            "temperature_min_c": means - 4,
        }
    )


def test_payload_to_dataframe_maps_open_meteo_fields():
    payload = {
        "daily": {
            "time": ["2025-01-01", "2025-01-02"],
            "temperature_2m_mean": [0.5, 1.5],
            "temperature_2m_max": [4.0, 5.0],
            "temperature_2m_min": [-3.0, -2.0],
        }
    }

    result = payload_to_dataframe(payload)

    assert result.columns.tolist() == [
        "date",
        "temperature_mean_c",
        "temperature_max_c",
        "temperature_min_c",
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
    return {
        "daily": {
            "time": ["2025-01-01", "2025-01-02"],
            "temperature_2m_mean": [0.5, 1.5],
            "temperature_2m_max": [4.0, 5.0],
            "temperature_2m_min": [-3.0, -2.0],
        },
        "daily_units": {
            "temperature_2m_mean": "°C",
            "temperature_2m_max": "°C",
            "temperature_2m_min": "°C",
        },
        "timezone": "Asia/Seoul",
    }


def test_fetch_uses_fixed_location_period_and_timezone():
    fake_session = FakeSession(two_day_payload())

    payload = fetch_weather_payload(fake_session)

    assert payload == fake_session.payload
    assert fake_session.last_url == "https://archive-api.open-meteo.com/v1/archive"
    assert fake_session.last_timeout == 30
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
    monkeypatch.setattr(
        "analysis.fetch_weather_payload",
        lambda session: pytest.fail("network used"),
    )

    frame, quality = load_weather_csv(path)

    assert len(frame) == 365
    assert quality["remaining_missing_values"] == 0


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


def test_analysis_summary_returns_serializable_extremes():
    frame = add_time_series_features(make_frame())

    summary = analysis_summary(frame, {"remaining_missing_values": 0})

    assert summary["hottest_day"]["date"] == "2025-12-31"
    assert summary["hottest_day"]["temperature_max_c"] == pytest.approx(17.2)
    assert summary["coldest_day"]["date"] == "2025-01-01"
    assert summary["coldest_day"]["temperature_min_c"] == pytest.approx(-9.0)
    assert summary["quality"] == {"remaining_missing_values": 0}


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
