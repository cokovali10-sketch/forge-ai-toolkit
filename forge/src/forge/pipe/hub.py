"""FORGE Report Hub: веб-дашборд здоровья проектов.

Только чтение (история прогонов), только stdlib (http.server), ноль записи.
Запуск: forge pipe hub <dir> [--port 8099] [--open]
"""
from __future__ import annotations

import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SKIP = {".git", ".venv", "venv", "__pycache__", "node_modules",
        "lab-servers", "build", "target", "dist"}


def collect_projects(root: str | Path) -> list[dict]:
    """Сводка по подпроектам: последний прогон + доля зелёных. Чистая функция."""
    base = Path(root)
    out = []
    if not base.is_dir():
        return out
    for sub in sorted((d for d in base.iterdir()
                       if d.is_dir() and d.name not in SKIP
                       and not d.name.startswith(".")),
                      key=lambda d: d.name):
        rows = []
        hp = sub / ".forge-pipe-history.jsonl"
        if hp.is_file():
            try:
                for line in hp.read_text(encoding="utf-8").splitlines()[-50:]:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        continue
            except OSError:
                pass
        last = rows[-1] if rows else None
        ok = sum(1 for r in rows if r.get("status") == "SUCCESS")
        out.append({"project": sub.name,
                    "status": last.get("status") if last else "—",
                    "duration_ms": last.get("duration_ms", 0) if last else 0,
                    "runs": len(rows),
                    "ok_rate": round(ok / len(rows), 2) if rows else None})
    return out


PAGE = """<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="10">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FORGE Hub</title>
<style>*{margin:0;box-sizing:border-box}
body{background:#0b0d14;color:#e2e8f0;font-family:system-ui;padding:32px}
h1{font-size:28px}h1 span{color:#22d3ee}
.sub{opacity:.6;margin:6px 0 20px;font-size:13px}
table{width:100%;border-collapse:collapse;font-size:14px}
th{text-align:left;opacity:.55;font-weight:600;padding:8px 10px;border-bottom:1px solid #22d3ee33}
td{padding:9px 10px;border-bottom:1px solid #ffffff12}
.ok{color:#4ade80;font-weight:700}.bad{color:#f87171;font-weight:700}.na{opacity:.4}
.bar{height:8px;border-radius:4px;background:#ffffff14;min-width:80px}
.bar>i{display:block;height:100%;border-radius:4px;background:#22d3ee}
</style></head><body>
<h1>⚡ FORGE <span>Hub</span></h1>
<p class="sub">Автообновление каждые 10с · только чтение · данные: .forge-pipe-history.jsonl</p>
<table><tr><th>Проект</th><th>Статус</th><th>Прогонов</th><th>Зелёных</th><th>Длительность</th></tr>
__ROWS__
</table></body></html>"""


def _row(p: dict) -> str:
    st = p["status"]
    cls = "ok" if st == "SUCCESS" else "bad" if st == "—" else "na"
    rate = p["ok_rate"]
    bar = (f'<div class="bar"><i style="width:{int(rate * 100)}%"></i></div>'
           if rate is not None else "—")
    return (f"<tr><td>{p['project']}</td>"
            f"<td class=\"{cls}\">{st}</td>"
            f"<td>{p['runs']}</td><td>{bar}</td>"
            f"<td>{p['duration_ms']}мс</td></tr>")


class _Handler(BaseHTTPRequestHandler):
    root = "."

    def log_message(self, *a) -> None:  # тихо: без спама в консоль
        pass

    def _send(self, body: bytes, ctype: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - http.server convention
        if self.path == "/api/projects":
            self._send(json.dumps(collect_projects(self.root),
                                  ensure_ascii=False).encode(), "application/json")
            return
        rows = "".join(_row(p) for p in collect_projects(self.root))
        self._send(PAGE.replace("__ROWS__", rows or
                                "<tr><td colspan=5>прогонов пока нет</td></tr>"
                                ).encode(), "text/html")


def serve(root: str, port: int = 8099, open_browser: bool = False) -> int:
    _Handler.root = root
    srv = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    url = f"http://127.0.0.1:{srv.server_port}/"
    print(f"FORGE Hub: {url} (Ctrl+C — стоп, только localhost)")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0
