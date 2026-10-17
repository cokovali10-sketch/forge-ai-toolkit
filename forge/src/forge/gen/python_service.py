"""Python service generator: микросервис на stdlib (http.server), ноль зависимостей.

Generates: pyproject.toml, service.py (GET /health + /hello, потоки),
test_service.py (urllib, свободный порт), README.
Проверяется: импорт + запуск health-check в тесте генератора? Нет —
генератор только пишет и валидирует структуру; запуск — дело lab/pipe.
"""
from __future__ import annotations

from pathlib import Path

SERVICE = '''"""Microservice on stdlib only: GET /health, GET /hello?name=."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import json as _json


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        body = _json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        u = urlparse(self.path)
        if u.path == "/health":
            return self._send(200, {"ok": True})
        if u.path == "/hello":
            name = parse_qs(u.query).get("name", ["world"])[0][:50]
            return self._send(200, {"hello": name})
        return self._send(404, {"error": "not found"})


def run(port=8090):
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    run()
'''

TEST = '''import threading
import urllib.request
import service


def test_health():
    srv = service.ThreadingHTTPServer(("127.0.0.1", 0), service.Handler)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        body = urllib.request.urlopen(f"http://127.0.0.1:{port}/health",
                                      timeout=5).read()
        assert b'"ok": true' in body
    finally:
        srv.shutdown()
        th.join(timeout=5)
'''


def _slug(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in (name or "app")) or "app"


def generate(out_dir: str | Path, name: str = "svc") -> dict:
    """Generates a service project. Returns {dir, files} (+ok/problems)."""
    safe = _slug(name)
    out = Path(out_dir)
    files = {"pyproject.toml": '[project]\nname = "%s"\nversion = "0.1.0"\n'
                                'requires-python = ">=3.10"\n' % safe,
             "service.py": SERVICE,
             "test_service.py": TEST,
             "README.md": f"# {safe}\n\n`python service.py` — :8090, "
                          f"`pytest -q` — проверка.\n"}
    made = []
    for rel, content in files.items():
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        made.append(rel)
    problems = []
    try:
        compile(files["service.py"], "service.py", "exec")
    except SyntaxError as e:
        problems.append(f"service.py: {e}")
    return {"dir": str(out), "files": made,
            "ok": not problems, "problems": problems}
