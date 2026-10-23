"""FORGE Studio: a local web workspace over audit, pipe and generators.

Security model: binds 127.0.0.1, and every filesystem path comes from the
explicit project registry or the Studio workspace. Nothing outside those
roots can be read, generated into, or previewed.
"""
from __future__ import annotations

import json
import mimetypes
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ..kit.report import full_report
from ..serve.app import render_static
from .page import STUDIO_HTML
from .store import DEFAULT_STORE, FORGE_ROOT, REPO_ROOT, Store

_cache: dict = {"at": 0.0, "root": None, "deep": False, "data": None}
_lock = threading.Lock()
_run_lock = threading.Lock()
MAX_BODY = 2 * 1024 * 1024


def _report(root: str, deep: bool, ttl: float) -> dict:
    now = time.time()
    with _lock:
        fresh = (_cache["data"] is not None and _cache["root"] == root
                 and _cache["deep"] == deep and now - _cache["at"] < ttl)
        if fresh:
            return _cache["data"]
    data = full_report(root, deep=deep)
    with _lock:
        _cache.update({"at": now, "root": root, "deep": deep, "data": data})
    return data


def _under(child: Path, root: Path) -> bool:
    try:
        child.relative_to(root)
        return True
    except ValueError:
        return False


class _Handler(BaseHTTPRequestHandler):
    store: Store = Store(DEFAULT_STORE)
    workspace: Path = REPO_ROOT / "studio-workspace"
    ttl: float = 20.0

    def log_message(self, *a) -> None:  # quiet
        pass

    # ---- helpers -----------------------------------------------------
    def _send(self, body: bytes, ctype: str, code: int = 200,
              extra: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, data: dict, code: int = 200) -> None:
        self._send(json.dumps(data, ensure_ascii=False).encode("utf-8"),
                   "application/json", code)

    def _error(self, message: str, code: int = 400) -> None:
        self._json({"ok": False, "error": message}, code)

    def _body(self) -> dict:
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ValueError("bad Content-Length")
        if n > MAX_BODY:
            raise ValueError("payload too large (2 MB)")
        raw = self.rfile.read(n) if n else b"{}"
        data = json.loads(raw.decode("utf-8") or "{}")
        if not isinstance(data, dict):
            raise ValueError("JSON object expected")
        return data

    def _project(self, raw: str = "") -> tuple[Path | None, dict | None]:
        if raw:
            item = self.store.get(raw)
        else:
            item = self.store.selected()
        if item is None:
            return None, None
        return Path(item["path"]), item

    def _roots(self) -> list[Path]:
        return [Path(p["path"]) for p in self.store.list()] + [self.workspace]

    def _allowed(self, path: Path) -> bool:
        p = path.resolve()
        return any(_under(p, r.resolve()) for r in self._roots())

    def _safe_out(self, raw: str, fallback: Path) -> Path:
        out = Path(raw).expanduser().resolve() if raw else fallback.resolve()
        if not self._allowed(out):
            raise ValueError("out must be inside a registered project "
                             "or studio-workspace")
        return out

    # ---- routes ------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path in ("/", "/index.html"):
                self._send(STUDIO_HTML.encode("utf-8"), "text/html")
            elif u.path == "/api/health":
                self._json({"ok": True, "projects": len(self.store.list()),
                            "forge_root": str(FORGE_ROOT)})
            elif u.path == "/api/studio":
                self._json(self._studio_payload())
            elif u.path == "/api/report":
                self._report_route(q)
            elif u.path == "/api/report/html":
                self._report_html(q)
            elif u.path == "/api/pipeline/stages":
                self._json({"ok": True, "stages": self._stages_payload()})
            elif u.path == "/api/pipeline/history":
                self._history(q)
            elif u.path == "/preview":
                self._preview(q)
            else:
                self._error("not found", 404)
        except (ValueError, OSError) as e:
            self._error(str(e), 400 if isinstance(e, ValueError) else 500)
        except Exception as e:  # noqa: BLE001 - HTTP boundary
            self._error(f"{type(e).__name__}: {e}", 500)

    def do_POST(self) -> None:  # noqa: N802
        u = urlparse(self.path)
        try:
            data = self._body()
            if u.path == "/api/projects":
                self._add_project(data)
            elif u.path == "/api/projects/remove":
                self._remove_project(data)
            elif u.path == "/api/select":
                self._select(data)
            elif u.path == "/api/pipeline/run":
                self._run_pipeline(data)
            elif u.path == "/api/gen":
                self._generate(data)
            else:
                self._error("not found", 404)
        except (ValueError, OSError) as e:
            self._error(str(e), 400 if isinstance(e, ValueError) else 500)
        except Exception as e:  # noqa: BLE001 - HTTP boundary
            self._error(f"{type(e).__name__}: {e}", 500)

    def do_DELETE(self) -> None:  # noqa: N802
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path != "/api/projects":
            self._error("not found", 404)
            return
        raw = q.get("path", "")
        if not raw:
            self._error("path is required")
            return
        self._json({"ok": self.store.remove(raw)})

    # ---- endpoint implementations -----------------------------------
    def _capabilities(self) -> dict:
        from ..webstudio import PRESETS
        return {"presets": list(PRESETS),
                "generators": ["web", "paper"],
                "languages": ["ru", "en"]}

    def _studio_payload(self) -> dict:
        sel = self.store.selected()
        return {"ok": True, "forge_root": str(FORGE_ROOT),
                "repo_root": str(REPO_ROOT),
                "projects": self.store.list(),
                "selected": sel["path"] if sel else "",
                "capabilities": self._capabilities()}

    def _report_route(self, q: dict) -> None:
        root, item = self._project(q.get("project", ""))
        if root is None:
            self._error("project is not registered", 404)
            return
        if not root.is_dir():
            self._error("project directory is missing", 404)
            return
        data = _report(str(root), bool(q.get("deep")), self.ttl)
        if data.get("ok") is not None:
            self.store.remember_report(root, data.get("score"),
                                       data.get("verdict", ""))
        self._json(data)

    def _report_html(self, q: dict) -> None:
        root, _ = self._project(q.get("project", ""))
        if root is None or not root.is_dir():
            self._error("project is not registered", 404)
            return
        html = render_static(_report(str(root), True, self.ttl))
        name = f"{root.name}-forge-report.html"
        self._send(html.encode("utf-8"), "text/html",
                   extra={"Content-Disposition":
                          f'attachment; filename="{name}"'})

    def _stages_payload(self) -> list[dict]:
        from ..pipe.stages import DEFAULT_STAGES, HEAVY_STAGES
        return [{"name": s.name, "title": s.title, "notes": s.notes,
                 "timeout_s": s.timeout_s, "heavy": s.heavy}
                for s in list(DEFAULT_STAGES) + list(HEAVY_STAGES)]

    def _history(self, q: dict) -> None:
        root, _ = self._project(q.get("project", ""))
        if root is None:
            self._error("project is not registered", 404)
            return
        rows: list[dict] = []
        hist = root / ".forge-pipe-history.jsonl"
        if hist.is_file():
            lines = hist.read_text(encoding="utf-8",
                                   errors="replace").splitlines()[-20:]
            for line in reversed(lines):
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
        self._json({"ok": True, "history": rows})

    def _run_pipeline(self, data: dict) -> None:
        from ..pipe.runner import PipeRunner
        from ..pipe.stages import (ALL_STAGES, DEFAULT_STAGES, HEAVY_STAGES,
                                   git_changed)
        root, _ = self._project(str(data.get("project", "")))
        if root is None or not root.is_dir():
            self._error("project is not registered", 404)
            return
        ctx: dict = {"target": str(root), "forge_root": str(FORGE_ROOT)}
        if data.get("changed"):
            ch = git_changed(str(root))
            if ch is not None:
                ctx["only"] = ch
        only = str(data.get("only", "") or "")
        if only:
            want = {s.strip() for s in only.split(",") if s.strip()}
            stages = [s for s in ALL_STAGES.values() if s.name in want]
        else:
            stages = list(DEFAULT_STAGES) + (list(HEAVY_STAGES)
                                              if data.get("heavy") else [])
        if not stages:
            raise ValueError("no matching stages")
        with _run_lock:
            rep = PipeRunner(
                stages, ctx,
                checkpoint=str(root / "forge-pipe-checkpoint.json")).run(
                    resume=bool(data.get("resume", False)),
                    serial=bool(data.get("serial", True))).to_dict()
        self._json({"ok": rep["status"] == "SUCCESS", "report": rep})

    def _add_project(self, data: dict) -> None:
        path = str(data.get("path", "")).strip().strip('"')
        if not path:
            raise ValueError("path is required")
        item = self.store.add(path, str(data.get("name", "")).strip())
        self._json({"ok": True, "project": item})

    def _remove_project(self, data: dict) -> None:
        path = str(data.get("path", ""))
        if not path:
            raise ValueError("path is required")
        self._json({"ok": self.store.remove(path)})

    def _select(self, data: dict) -> None:
        path = str(data.get("path", ""))
        if not path:
            raise ValueError("path is required")
        item = self.store.select(path)
        if item is None:
            self._error("project is not registered", 404)
            return
        self._json({"ok": True, "selected": item["path"]})

    def _generate(self, data: dict) -> None:
        kind = str(data.get("kind", "web")).strip().lower()
        if kind not in ("web", "paper"):
            raise ValueError("kind must be 'web' or 'paper'")
        root, _ = self._project(str(data.get("project", "")))
        base = root if root is not None else self.workspace
        name = str(data.get("name", "")).strip() or (
            "Forge Site" if kind == "web" else "ForgePlugin")
        slug = "".join(c if c.isalnum() or c in "-_" else "-"
                       for c in name).strip("-") or "forge-output"
        fallback = base / ("generated" if kind == "paper" else "site") / slug
        out = self._safe_out(str(data.get("out", "")), fallback)
        out.mkdir(parents=True, exist_ok=True)
        payload: dict = {"ok": True, "kind": kind, "out": str(out)}
        if kind == "web":
            from ..webstudio import generate as _web
            payload["result"] = _web(
                out, name=name,
                preset=str(data.get("preset", "aurora")),
                tagline=str(data.get("tagline", "")),
                lang=str(data.get("lang", "ru")))
            payload["preview"] = "/preview?root=" + str(out) + "&file=index.html"
        else:
            from ..gen.paper_plugin import generate as _paper
            payload["result"] = _paper(
                out, name=name,
                package=str(data.get("package", "com.forge.demo")),
                command=str(data.get("command", "hello")),
                description=str(data.get("tagline", "")))
        self._json(payload)

    def _preview(self, q: dict) -> None:
        raw = q.get("root", "")
        root, _ = self._project(raw)
        base = Path(root) if root is not None else (
            Path(raw) if raw else None)
        if base is None:
            self._error("root is required")
            return
        base = base.resolve()
        if not self._allowed(base):
            self._error("preview root is not allowed", 403)
            return
        rel = q.get("file", "index.html") or "index.html"
        target = (base / rel).resolve()
        if not _under(target, base) or not target.is_file():
            self._error("file not found", 404)
            return
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self._send(target.read_bytes(), ctype)


def serve(port: int = 8100, open_browser: bool = False,
          store_path: str | Path = DEFAULT_STORE,
          workspace: str | Path = REPO_ROOT / "studio-workspace",
          ttl: float = 20.0) -> int:
    """Start Studio on 127.0.0.1 until Ctrl+C."""
    _Handler.store = Store(store_path)
    _Handler.workspace = Path(workspace)
    _Handler.ttl = ttl
    srv = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    url = f"http://127.0.0.1:{srv.server_port}/"
    print(f"FORGE Studio: {url}  (store: {store_path}; Ctrl+C — стоп)")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0
