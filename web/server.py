#!/usr/bin/env python3
"""StudyBuddy Web UI server — Python standard library only.

    STUDYBUDDY_MODE=mock python web/server.py        # http://localhost:8000
    STUDYBUDDY_MODE=live python web/server.py

API (JSON):
  GET  /api/lessons                      built-in lesson list
  POST /api/session/start  {student, lesson_id}
  POST /api/session/quiz   {session_id}
  POST /api/session/grade  {session_id, answers: {qid: value}}
  GET  /api/progress?student=xiaoming

No third-party web framework is required, which keeps the demo easy to
run anywhere (including low-end school computers and free cloud tiers).
"""

from __future__ import annotations

import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studybuddy.config import load_settings  # noqa: E402
from studybuddy.session import SessionRunner  # noqa: E402

STATIC_DIR = Path(__file__).resolve().parent / "static"
SETTINGS = load_settings()
RUNNER = SessionRunner(SETTINGS)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    # -- plumbing ---------------------------------------------------------
    def log_message(self, *args):  # keep the console quiet for filming
        pass

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def _api(self, fn, *args, **kwargs):
        try:
            self._send_json(fn(*args, **kwargs))
        except (KeyError, ValueError) as exc:
            self._send_json({"error": str(exc)}, status=400)
        except Exception as exc:  # noqa: BLE001 - surface as API error
            self._send_json({"error": f"{type(exc).__name__}: {exc}"}, status=500)

    # -- routes -----------------------------------------------------------
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/lessons":
            return self._api(lambda: {"lessons": RUNNER.list_lessons()})
        if parsed.path == "/api/progress":
            student = parse_qs(parsed.query).get("student", ["xiaoming"])[0]
            return self._api(lambda: RUNNER.progress(student))
        return super().do_GET()  # static files (index.html)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/session/start":
            body = self._read_json()
            return self._api(
                RUNNER.start,
                body.get("student", "xiaoming"),
                body.get("lesson_id", "school-day"),
            )
        if parsed.path == "/api/session/quiz":
            body = self._read_json()
            return self._api(RUNNER.quiz, body.get("session_id", ""))
        if parsed.path == "/api/session/grade":
            body = self._read_json()
            return self._api(
                RUNNER.grade,
                body.get("session_id", ""),
                body.get("answers", {}),
            )
        return self._send_json({"error": "not found"}, status=404)


def main() -> int:
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"学伴 StudyBuddy Web UI → http://localhost:{port}  (mode={SETTINGS.mode})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
