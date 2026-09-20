"""서울 일별 기온 데이터 수집과 시계열 분석 도구."""

from __future__ import annotations

import pandas as pd


DATE_COLUMN = "date"
TEMPERATURE_COLUMNS = [
    "temperature_mean_c",
    "temperature_max_c",
    "temperature_min_c",
]
OPEN_METEO_FIELDS = {
    "time": DATE_COLUMN,
    "temperature_2m_mean": "temperature_mean_c",
    "temperature_2m_max": "temperature_max_c",
    "temperature_2m_min": "temperature_min_c",
}


def payload_to_dataframe(payload: dict) -> pd.DataFrame:
    """Open-Meteo의 일별 응답을 표준 컬럼의 DataFrame으로 변환한다."""
    daily = payload.get("daily")
    if not isinstance(daily, dict):
        raise ValueError("Open-Meteo payload must contain a daily object")

    missing = [field for field in OPEN_METEO_FIELDS if field not in daily]
    if missing:
        raise ValueError(f"daily payload is missing fields: {', '.join(missing)}")

    lengths = {field: len(daily[field]) for field in OPEN_METEO_FIELDS}
    if len(set(lengths.values())) != 1:
        raise ValueError("daily payload fields must have equal lengths")

    frame = pd.DataFrame(
        {target: daily[source] for source, target in OPEN_METEO_FIELDS.items()}
    )
    frame[DATE_COLUMN] = pd.to_datetime(frame[DATE_COLUMN], errors="raise")
    return frame


def _longest_missing_run(series: pd.Series) -> int:
    missing = series.isna()
    if not missing.any():
        return 0
    groups = missing.ne(missing.shift()).cumsum()
    return int(missing.groupby(groups).sum().max())


def validate_and_clean(
    df: pd.DataFrame, expected_start: str, expected_end: str
) -> tuple[pd.DataFrame, dict]:
    """날짜와 기온 규칙을 검증하고 최대 이틀의 짧은 결측만 보간한다."""
    required = [DATE_COLUMN, *TEMPERATURE_COLUMNS]
    missing_columns = [column for column in required if column not in df.columns]
    if missing_columns:
        raise ValueError(f"missing required columns: {', '.join(missing_columns)}")

    cleaned = df[required].copy()
    cleaned[DATE_COLUMN] = pd.to_datetime(cleaned[DATE_COLUMN], errors="raise")
    if cleaned[DATE_COLUMN].duplicated().any():
        raise ValueError("duplicate dates are not allowed")

    source_rows = len(cleaned)
    cleaned = cleaned.sort_values(DATE_COLUMN).set_index(DATE_COLUMN)
    expected_dates = pd.date_range(expected_start, expected_end, freq="D")
    missing_dates = int((~expected_dates.isin(cleaned.index)).sum())
    cleaned = cleaned.reindex(expected_dates)
    cleaned.index.name = DATE_COLUMN

    for column in TEMPERATURE_COLUMNS:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    missing_values_before = int(cleaned[TEMPERATURE_COLUMNS].isna().sum().sum())
    for column in TEMPERATURE_COLUMNS:
        if _longest_missing_run(cleaned[column]) > 2:
            raise ValueError(
                f"{column} has missing values for more than 2 consecutive days"
            )

    cleaned[TEMPERATURE_COLUMNS] = cleaned[TEMPERATURE_COLUMNS].interpolate(
        method="time", limit=2, limit_area="inside"
    )
    remaining_missing_values = int(
        cleaned[TEMPERATURE_COLUMNS].isna().sum().sum()
    )
    if remaining_missing_values:
        raise ValueError("temperature data still contains missing values")

    valid_order = (
        (cleaned["temperature_min_c"] <= cleaned["temperature_mean_c"])
        & (cleaned["temperature_mean_c"] <= cleaned["temperature_max_c"])
    )
    if not valid_order.all():
        raise ValueError("temperature values must satisfy min <= mean <= max")

    quality = {
        "expected_days": len(expected_dates),
        "source_rows": source_rows,
        "missing_dates": missing_dates,
        "missing_values_before": missing_values_before,
        "interpolated_values": missing_values_before - remaining_missing_values,
        "remaining_missing_values": remaining_missing_values,
    }
    return cleaned.reset_index(), quality
