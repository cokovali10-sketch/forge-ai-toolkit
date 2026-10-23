"""Tests for FORGE Studio: registry + HTTP API + UI + CLI."""
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest


def _request(base, path, method="GET", payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(base + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return r.status, r.headers, raw
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


def _json(base, path, method="GET", payload=None):
    code, _, raw = _request(base, path, method, payload)
    return code, json.loads(raw.decode("utf-8"))


@pytest.fixture()
def studio(tmp_path):
    from forge.studio.app import _Handler
    from forge.studio.store import Store
    _Handler.store = Store(tmp_path / "store.json")
    _Handler.workspace = tmp_path / "workspace"
    _Handler.ttl = 0.0
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{srv.server_port}", tmp_path
    finally:
        srv.shutdown()
        srv.server_close()


def _project(tmp_path):
    root = tmp_path / "demo-project"
    root.mkdir()
    (root / "main.py").write_text("def add(a, b):\n    return a + b\n",
                                  encoding="utf-8")
    (root / "README.md").write_text("# Demo\n", encoding="utf-8")
    return root


def test_store_roundtrip_and_selection(tmp_path):
    from forge.studio.store import Store
    st = Store(tmp_path / "s.json")
    a = _project(tmp_path)
    b = tmp_path / "other"
    b.mkdir()
    assert st.list() == []
    item = st.add(a)
    assert item["name"] == "demo-project" and st.selected()["path"] == item["path"]
    st.add(a, "Renamed")
    assert len(st.list()) == 1 and st.get(a)["name"] == "Renamed"
    st.add(b)
    assert st.selected()["path"] == str(b.resolve())
    st.remember_report(a, 91, "Отлично")
    assert st.get(a)["score"] == 91
    assert st.remove(a) is True
    assert st.get(a) is None
    assert st.selected()["path"] == str(b.resolve())
    assert Store(tmp_path / "s.json").get(b)["name"] == "other"
    with pytest.raises(ValueError):
        st.add(tmp_path / "missing")


def test_studio_page_and_empty_api(studio):
    base, _ = studio
    code, headers, raw = _request(base, "/")
    assert code == 200 and b"FORGE Studio" in raw
    assert b"/api/studio" in raw and b"/api/pipeline/run" in raw
    code, data = _json(base, "/api/studio")
    assert code == 200 and data["projects"] == []
    assert "aurora" in data["capabilities"]["presets"]
    code, data = _json(base, "/api/health")
    assert data["ok"] is True and data["projects"] == 0


def test_add_select_report_and_export(studio):
    base, tmp_path = studio
    root = _project(tmp_path)
    code, data = _json(base, "/api/projects", "POST", {"path": str(root)})
    assert code == 200 and data["project"]["name"] == "demo-project"
    code, studio_data = _json(base, "/api/studio")
    assert len(studio_data["projects"]) == 1
    assert studio_data["selected"] == str(root.resolve())
    code, rep = _json(base, "/api/report")
    assert code == 200 and rep["ok"] is True and isinstance(rep["score"], int)
    assert "sections" in rep and "findings" in rep
    code, st = _json(base, "/api/studio")
    assert st["projects"][0]["score"] == rep["score"]
    code, headers, raw = _request(base, "/api/report/html")
    assert code == 200 and b"text/html" in headers["Content-Type"].encode()
    assert "attachment" in headers["Content-Disposition"]
    assert b"__FORGE_DATA__" in raw
    code, bad = _json(base, "/api/projects", "POST", {"path": str(tmp_path / "nope")})
    assert code == 400 and bad["ok"] is False


def test_generate_preview_and_path_guard(studio):
    base, tmp_path = studio
    root = _project(tmp_path)
    _json(base, "/api/projects", "POST", {"path": str(root)})
    out = tmp_path / "workspace" / "site"
    code, data = _json(base, "/api/gen", "POST", {
        "project": str(root), "kind": "web", "name": "Studio Demo",
        "preset": "aurora", "out": str(out)})
    assert code == 200 and data["ok"] is True
    assert data["result"]["score"] == 100
    assert (out / "index.html").is_file() and (out / "app.js").is_file()
    code, headers, raw = _request(
        base, "/preview?root=" + str(out) + "&file=index.html")
    assert code == 200 and b"<!doctype html>" in raw.lower()
    code, _, _ = _request(base, "/preview?root=" + str(tmp_path) + "&file=store.json")
    assert code in (403, 404)
    code, bad = _json(base, "/api/gen", "POST", {
        "project": str(root), "kind": "web", "name": "Esc",
        "out": str(tmp_path / "outside")})
    assert code == 400 and bad["ok"] is False
    code, bad = _json(base, "/api/gen", "POST", {
        "project": str(root), "kind": "nope"})
    assert code == 400


def test_pipeline_inspect_and_history(studio):
    base, tmp_path = studio
    root = _project(tmp_path)
    code, data = _json(base, "/api/projects", "POST", {"path": str(root)})
    assert code == 200
    code, data = _json(base, "/api/pipeline/stages")
    assert code == 200 and len(data["stages"]) == 8
    code, data = _json(base, "/api/pipeline/run", "POST",
                       {"project": str(root), "only": "inspect"})
    assert code == 200 and data["ok"] is True
    assert len(data["report"]["stages"]) == 1
    assert data["report"]["stages"][0]["name"] == "inspect"
    assert data["report"]["stages"][0]["status"] == "SUCCESS"
    code, data = _json(base, "/api/pipeline/history")
    assert code == 200 and isinstance(data["history"], list)
    code, data = _json(base, "/api/pipeline/run", "POST",
                       {"project": str(tmp_path), "only": "inspect"})
    assert code == 404


def test_delete_project(studio):
    base, tmp_path = studio
    root = _project(tmp_path)
    _json(base, "/api/projects", "POST", {"path": str(root)})
    code, data = _json(base, "/api/projects?path=" + str(root), "DELETE")
    assert code == 200 and data["ok"] is True
    code, data = _json(base, "/api/studio")
    assert data["projects"] == [] and data["selected"] == ""


def test_studio_cli(tmp_path):
    from forge.cli.__main__ import main
    from forge.studio.store import Store
    root = _project(tmp_path)
    store = tmp_path / "cli-store.json"
    assert main(["studio", "list", "--store", str(store)]) == 0
    assert main(["studio", "add", str(root), "--store", str(store)]) == 0
    assert Store(store).list()[0]["name"] == "demo-project"
    assert main(["studio", "list", "--store", str(store)]) == 0
    assert main(["studio", "add", str(tmp_path / "missing"),
                 "--store", str(store)]) == 2
    assert main(["studio", "wat", "--store", str(store)]) == 2
