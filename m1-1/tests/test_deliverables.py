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
        "분석 주제",
        "분석 질문",
        "데이터 설명",
        "데이터 정제",
        "분석 결과 및 시각화",
        "인사이트",
        "결론",
        "한계점",
        "AI 사용 로그",
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
