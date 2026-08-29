"""로컬 제출 증빙 캡처를 위한 정적 파일/API 통합 서버."""

from __future__ import annotations

import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from api.recommend import SEASON_NOTICE, error_payload, validate_date  # noqa: E402
from api.seasonal_data import get_monthly_fruits  # noqa: E402


class EvidenceHandler(SimpleHTTPRequestHandler):
    """프로젝트 정적 파일과 실제 추천 API를 함께 제공한다."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, directory=str(PROJECT_ROOT), **kwargs)

    def send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/recommend":
            self.send_json(404, error_payload("NOT_FOUND", "요청 경로를 찾을 수 없어요."))
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            selected = validate_date(payload.get("date"))
        except (AttributeError, UnicodeDecodeError, ValueError, json.JSONDecodeError):
            self.send_json(400, error_payload("INVALID_DATE", "올바른 날짜를 입력해 주세요."))
            return

        result = {
            "date": selected.isoformat(),
            "month": selected.month,
            "source": "fallback",
            "fruits": get_monthly_fruits(selected.month),
            "notice": f"오프라인 캡처 데모입니다. {SEASON_NOTICE}",
        }
        self.send_json(200, result)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8765), EvidenceHandler)
    print("Evidence server listening on http://127.0.0.1:8765", flush=True)
    server.serve_forever()
