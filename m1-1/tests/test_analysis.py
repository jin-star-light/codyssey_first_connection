import pandas as pd
import pytest

from analysis import payload_to_dataframe, validate_and_clean


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
