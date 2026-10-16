"""Tests for project generators (web / python-service / go-cli)."""
from pathlib import Path


def test_web_landing(tmp_path):
    from forge.gen import web
    r = web.generate(tmp_path / "site", "Demo")
    assert r["ok"] is True
    for f in ("index.html", "styles.css", "app.js", "README.md"):
        assert (tmp_path / "site" / f).is_file()
    html = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    assert "<title>Demo</title>" in html and "<h1>" in html


def test_python_service_runs(tmp_path):
    from forge.gen import python_service
    from forge.langs import python
    d = tmp_path / "svc"
    assert python_service.generate(d, "svc")["ok"] is True
    assert python.lint(d).status == "SUCCESS"
    assert python.test(d).status == "SUCCESS"


def test_go_cli_builds(tmp_path):
    from forge.gen import go_cli
    from forge.langs import go
    d = tmp_path / "cli"
    assert go_cli.generate(d, "cli")["ok"] is True
    assert go.lint(d).status == "SUCCESS"
    assert go.test(d).status == "SUCCESS"


def test_gen_cli_and_mcp(tmp_path):
    from forge.cli.__main__ import main
    from forge.mcp.server import build_default_registry
    assert main(["gen", "web", "--name", "t", "--out", str(tmp_path / "w")]) == 0
    assert (tmp_path / "w" / "index.html").is_file()
    assert main(["gen", "nope", "--out", str(tmp_path)]) == 2
    reg = build_default_registry("")
    assert "gen.web" in reg.tool_owner and "gen.go_cli" in reg.tool_owner
    r = reg.call("gen.python_service", {"out": str(tmp_path / "s"), "name": "s"})
    assert (tmp_path / "s" / "service.py").is_file()
