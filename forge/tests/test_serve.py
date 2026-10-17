import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from forge.kit.report import full_report
from forge.serve.app import _Handler


def _py_project(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'x'\nversion = '0.1.0'\n", encoding="utf-8")
    (tmp_path / "mod.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    return tmp_path


def test_full_report_shape(tmp_path):
    root = _py_project(tmp_path)
    rep = full_report(root, with_doctor=False)
    assert rep["ok"] is True
    assert 0 <= rep["score"] <= 100
    assert "audit" in rep and "quality" in rep
    assert isinstance(rep["pipe"], list)
    assert isinstance(rep["arena"], list)
    assert "generated_at" in rep
    assert rep["quality"]["trend"]["direction"] in ("up", "down", "flat")


def test_full_report_missing_dir(tmp_path):
    rep = full_report(tmp_path / "nope")
    assert rep["ok"] is False


def test_serve_endpoints(tmp_path):
    root = _py_project(tmp_path)
    _Handler.root = str(root)
    _Handler.ttl = 0.0
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_port

    def get(path):
        with urllib.request.urlopen(
                f"http://127.0.0.1:{port}{path}", timeout=30) as r:
            return r.status, r.read().decode("utf-8")

    try:
        st, body = get("/api/health")
        assert st == 200 and json.loads(body)["ok"] is True

        st, body = get("/api/report")
        rep = json.loads(body)
        assert st == 200 and rep["ok"] is True
        assert "quality" in rep and "doctor" in rep

        st, body = get("/")
        assert st == 200 and "FORGE" in body and "api/report" in body

        try:
            get("/api/missing")
            raise AssertionError("expected 404")
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        srv.shutdown()
        srv.server_close()
