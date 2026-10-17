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


def test_node_api_generator(tmp_path):
    import json
    from forge.gen import node_api
    d = tmp_path / "api"
    assert node_api.generate(d, "demo")["ok"] is True
    for f in ("package.json", "server.js", "test/server.test.js", "README.md"):
        assert (d / f).is_file()
    pkg = json.loads((d / "package.json").read_text(encoding="utf-8"))
    assert pkg["scripts"]["test"] == "node --test"
    assert "createServer" in (d / "server.js").read_text(encoding="utf-8")


def test_rust_cli_generator(tmp_path):
    from forge.gen import rust_cli
    d = tmp_path / "cli"
    assert rust_cli.generate(d, "demo")["ok"] is True
    for f in ("Cargo.toml", "src/main.rs", "README.md"):
        assert (d / f).is_file()
    assert "[package]" in (d / "Cargo.toml").read_text(encoding="utf-8")
    assert "#[cfg(test)]" in (d / "src" / "main.rs").read_text(encoding="utf-8")


def test_new_gens_cli_and_mcp(tmp_path):
    from forge.cli.__main__ import main
    from forge.mcp.server import build_default_registry
    assert main(["gen", "node-api", "--name", "n", "--out", str(tmp_path / "n")]) == 0
    assert (tmp_path / "n" / "server.js").is_file()
    assert main(["gen", "rust-cli", "--name", "r", "--out", str(tmp_path / "r")]) == 0
    assert (tmp_path / "r" / "Cargo.toml").is_file()
    reg = build_default_registry("")
    assert "gen.node_api" in reg.tool_owner and "gen.rust_cli" in reg.tool_owner
