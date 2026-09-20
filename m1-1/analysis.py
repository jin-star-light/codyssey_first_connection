"""서울 일별 기온 데이터 수집과 시계열 분석 도구."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import requests


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
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
START_DATE = "2025-01-01"
END_DATE = "2025-12-31"


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


def fetch_weather_payload(session=requests) -> dict:
    """Open-Meteo에서 서울의 2025년 일별 기온 응답을 가져온다."""
    params = {
        "latitude": 37.5665,
        "longitude": 126.9780,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "daily": ",".join(
            [
                "temperature_2m_mean",
                "temperature_2m_max",
                "temperature_2m_min",
            ]
        ),
        "timezone": "Asia/Seoul",
        "temperature_unit": "celsius",
    }
    try:
        response = session.get(OPEN_METEO_URL, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Open-Meteo request failed: {exc}") from exc


def refresh_weather_csv(
    csv_path: Path, session=requests
) -> tuple[pd.DataFrame, dict]:
    """원격 데이터를 완전히 검증한 후 CSV를 갱신한다."""
    payload = fetch_weather_payload(session)
    frame = payload_to_dataframe(payload)
    cleaned, quality = validate_and_clean(frame, START_DATE, END_DATE)
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(csv_path, index=False, date_format="%Y-%m-%d")
    return cleaned, quality


def load_weather_csv(csv_path: Path) -> tuple[pd.DataFrame, dict]:
    """저장된 CSV를 네트워크 접근 없이 읽고 검증한다."""
    csv_path = Path(csv_path)
    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Weather data not found at {csv_path}. Run python analysis.py --refresh."
        )
    frame = pd.read_csv(csv_path)
    return validate_and_clean(frame, START_DATE, END_DATE)


def add_time_series_features(df: pd.DataFrame) -> pd.DataFrame:
    """검증된 일별 자료에 이동평균, 변화량, 일교차를 추가한다."""
    featured = df.copy()
    featured[DATE_COLUMN] = pd.to_datetime(featured[DATE_COLUMN])
    featured["rolling_mean_7d_c"] = featured["temperature_mean_c"].rolling(
        window=7, min_periods=1
    ).mean()
    featured["daily_change_c"] = featured["temperature_mean_c"].diff()
    featured["diurnal_range_c"] = (
        featured["temperature_max_c"] - featured["temperature_min_c"]
    )
    return featured


def detect_iqr_outliers(series: pd.Series) -> pd.Series:
    """IQR 경계 밖의 값을 삭제하지 않고 불리언 마스크로 반환한다."""
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return (series < lower) | (series > upper)


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """달력 월별 기온과 일교차 통계를 계산한다."""
    grouped = df.assign(month=pd.to_datetime(df[DATE_COLUMN]).dt.month).groupby(
        "month"
    )
    result = grouped.agg(
        mean_temperature_c=("temperature_mean_c", "mean"),
        mean_max_c=("temperature_max_c", "mean"),
        mean_min_c=("temperature_min_c", "mean"),
        mean_diurnal_range_c=("diurnal_range_c", "mean"),
        days=(DATE_COLUMN, "count"),
    )
    return result.reindex(range(1, 13))


def seasonal_summary(df: pd.DataFrame) -> pd.DataFrame:
    """대한민국의 일반적인 달력 계절 구분으로 통계를 계산한다."""
    season_by_month = {
        1: "겨울",
        2: "겨울",
        3: "봄",
        4: "봄",
        5: "봄",
        6: "여름",
        7: "여름",
        8: "여름",
        9: "가을",
        10: "가을",
        11: "가을",
        12: "겨울",
    }
    seasons = pd.to_datetime(df[DATE_COLUMN]).dt.month.map(season_by_month)
    grouped = df.assign(season=seasons).groupby("season")
    result = grouped.agg(
        mean_temperature_c=("temperature_mean_c", "mean"),
        mean_max_c=("temperature_max_c", "mean"),
        mean_min_c=("temperature_min_c", "mean"),
        mean_diurnal_range_c=("diurnal_range_c", "mean"),
        days=(DATE_COLUMN, "count"),
    )
    return result.reindex(["봄", "여름", "가을", "겨울"])


def analysis_summary(df: pd.DataFrame, quality: dict) -> dict:
    """리포트 작성에 사용할 주요 수치를 JSON 직렬화 가능한 값으로 만든다."""
    monthly = monthly_summary(df)
    hottest = df.loc[df["temperature_max_c"].idxmax()]
    coldest = df.loc[df["temperature_min_c"].idxmin()]
    warming = df.loc[df["daily_change_c"].idxmax()]
    cooling = df.loc[df["daily_change_c"].idxmin()]
    warmest_month = int(monthly["mean_temperature_c"].idxmax())
    coldest_month = int(monthly["mean_temperature_c"].idxmin())
    range_month = int(monthly["mean_diurnal_range_c"].idxmax())

    def date_text(row: pd.Series) -> str:
        return pd.Timestamp(row[DATE_COLUMN]).strftime("%Y-%m-%d")

    return {
        "hottest_day": {
            "date": date_text(hottest),
            "temperature_max_c": float(hottest["temperature_max_c"]),
        },
        "coldest_day": {
            "date": date_text(coldest),
            "temperature_min_c": float(coldest["temperature_min_c"]),
        },
        "largest_warming": {
            "date": date_text(warming),
            "daily_change_c": float(warming["daily_change_c"]),
        },
        "largest_cooling": {
            "date": date_text(cooling),
            "daily_change_c": float(cooling["daily_change_c"]),
        },
        "warmest_month": {
            "month": warmest_month,
            "mean_temperature_c": float(
                monthly.loc[warmest_month, "mean_temperature_c"]
            ),
        },
        "coldest_month": {
            "month": coldest_month,
            "mean_temperature_c": float(
                monthly.loc[coldest_month, "mean_temperature_c"]
            ),
        },
        "largest_diurnal_range_month": {
            "month": range_month,
            "mean_diurnal_range_c": float(
                monthly.loc[range_month, "mean_diurnal_range_c"]
            ),
        },
        "iqr_outlier_count": int(
            detect_iqr_outliers(df["temperature_mean_c"]).sum()
        ),
        "quality": quality,
    }


def _finish_chart(fig: plt.Figure, path: Path) -> None:
    fig.text(
        0.99,
        0.01,
        "Source: Open-Meteo Historical Weather API",
        ha="right",
        fontsize=8,
        color="#555555",
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def create_visualizations(df: pd.DataFrame, output_dir: Path) -> list[Path]:
    """리포트용 네 개의 시계열 PNG 그래프를 만든다."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    dates = pd.to_datetime(df[DATE_COLUMN])
    paths = [
        output_dir / "01_annual_temperature_trend.png",
        output_dir / "02_monthly_temperature.png",
        output_dir / "03_daily_temperature_change.png",
        output_dir / "04_monthly_diurnal_range.png",
    ]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.fill_between(
        dates,
        df["temperature_min_c"],
        df["temperature_max_c"],
        color="#bcdff5",
        alpha=0.45,
        label="Daily min-max range",
    )
    ax.plot(dates, df["temperature_mean_c"], color="#8093a0", alpha=0.55, label="Daily mean")
    ax.plot(dates, df["rolling_mean_7d_c"], color="#d1495b", linewidth=2.2, label="7-day moving average")
    ax.set(title="Seoul Daily Temperature Trend (2025)", ylabel="Temperature (°C)", xlabel="Date")
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left")
    _finish_chart(fig, paths[0])

    monthly = monthly_summary(df)
    labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(labels, monthly["mean_max_c"], marker="o", color="#d1495b", label="Average daily maximum")
    ax.plot(labels, monthly["mean_temperature_c"], marker="o", color="#2d6a9f", linewidth=2.5, label="Monthly mean")
    ax.plot(labels, monthly["mean_min_c"], marker="o", color="#52a675", label="Average daily minimum")
    ax.set(title="Monthly Temperature Comparison", ylabel="Temperature (°C)", xlabel="Month")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    _finish_chart(fig, paths[1])

    changes = df["daily_change_c"].fillna(0)
    colors = ["#f28e2b" if abs(value) >= 5 else ("#d1495b" if value >= 0 else "#2d6a9f") for value in changes]
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(dates, changes, color=colors, width=1.0)
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.axhline(5, color="#f28e2b", linewidth=0.9, linestyle="--", alpha=0.8)
    ax.axhline(-5, color="#f28e2b", linewidth=0.9, linestyle="--", alpha=0.8)
    ax.set(title="Day-to-Day Mean Temperature Change", ylabel="Change (°C)", xlabel="Date")
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.grid(axis="y", alpha=0.2)
    _finish_chart(fig, paths[2])

    fig, ax = plt.subplots(figsize=(11, 6))
    bars = ax.bar(labels, monthly["mean_diurnal_range_c"], color="#59a14f")
    ax.bar_label(bars, fmt="%.1f", padding=3)
    ax.set(title="Average Monthly Diurnal Temperature Range", ylabel="Daily max - min (°C)", xlabel="Month")
    ax.grid(axis="y", alpha=0.25)
    _finish_chart(fig, paths[3])

    return paths
