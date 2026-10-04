from __future__ import annotations

import csv
import io
from datetime import date, timedelta
from pathlib import Path


HEADERS = ["date", "value", "memo"]
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "data" / "study_hours.csv"


def generate_records() -> list[dict[str, str]]:
    start = date(2025, 1, 1)
    memos = ["알고리즘", "영어 복습", "프로젝트", "강의 수강", "주간 복습"]
    records = []
    for index in range(140):
        day = start + timedelta(days=index)
        weekend_adjustment = -0.6 if day.weekday() >= 5 else 0.4
        cycle_adjustment = (index % 9) * 0.15
        value = max(0.5, 2.2 + weekend_adjustment + cycle_adjustment)
        records.append(
            {
                "date": day.isoformat(),
                "value": f"{value:.1f}",
                "memo": memos[index % len(memos)],
            }
        )
    return records


def render_csv(records: list[dict[str, str]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=HEADERS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return output.getvalue()


def write_csv(path: Path = DEFAULT_OUTPUT) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_csv(generate_records()), encoding="utf-8", newline="")


if __name__ == "__main__":
    write_csv()
    print(f"Generated {len(generate_records())} rows: {DEFAULT_OUTPUT}")
