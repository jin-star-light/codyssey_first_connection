import csv
import io
from datetime import date
from pathlib import Path

from scripts.generate_sample_csv import generate_records, render_csv, write_csv


def test_generated_dataset_is_deterministic_and_valid():
    first = generate_records()
    second = generate_records()
    assert first == second
    assert len(first) >= 120
    assert len({row["date"] for row in first}) == len(first)
    assert all(date.fromisoformat(row["date"]) <= date.today() for row in first)
    assert all(0 < float(row["value"]) <= 24 for row in first)
    assert any(row["memo"] for row in first)


def test_csv_has_exact_headers_and_regenerates_byte_for_byte(tmp_path: Path):
    rendered = render_csv(generate_records())
    reader = csv.DictReader(io.StringIO(rendered))
    assert reader.fieldnames == ["date", "value", "memo"]

    path = tmp_path / "study_hours.csv"
    write_csv(path)
    first = path.read_bytes()
    write_csv(path)
    assert path.read_bytes() == first
    assert first == rendered.encode("utf-8")
