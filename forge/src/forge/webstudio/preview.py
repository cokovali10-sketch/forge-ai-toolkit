"""Local static preview for generated sites (stdlib only, localhost)."""
from __future__ import annotations

import functools
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args) -> None:  # noqa: N802 - http.server API
        pass


def serve_site(root: str | Path, port: int = 8100,
               open_browser: bool = False) -> int:
    base = Path(root).resolve()
    if not base.is_dir():
        print(f"web preview: not a directory: {base}")
        return 2
    if not (base / "index.html").is_file():
        print(f"web preview: no index.html in {base}")
        return 2
    handler = functools.partial(_Quiet, directory=str(base))
    srv = ThreadingHTTPServer(("127.0.0.1", port), handler)
    url = f"http://127.0.0.1:{srv.server_port}/"
    print(f"FORGE Web preview: {url}  ({base}; Ctrl+C — стоп)")
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0
