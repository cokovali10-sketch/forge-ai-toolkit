"""Tests for forge make (stamp: scaffold + verify)."""
from pathlib import Path


def test_make_all_kinds(tmp_path):
    from forge.gen.make import make
    for kind in ("web", "python-service", "go-cli"):
        r = make(kind, f"demo-{kind}", tmp_path, "D:/Forge-Factority/forge")
        assert r["ok"] is True, (kind, r)
        assert (tmp_path / f"demo-{kind}").is_dir()


def test_make_bad_kind(tmp_path):
    from forge.gen.make import make
    r = make("nope", "x", tmp_path, ".")
    assert r["ok"] is False


def test_make_cli_and_mcp(tmp_path):
    from forge.cli.__main__ import main
    from forge.mcp.server import build_default_registry
    assert main(["make", "web", "w1", str(tmp_path)]) == 0
    assert (tmp_path / "w1" / "index.html").is_file()
    assert main(["make", "web"]) == 2
    reg = build_default_registry("")
    assert "make.project" in reg.tool_owner
    r = reg.call("make.project", {"kind": "web", "name": "w2",
                                  "out": str(tmp_path)})
    assert r["ok"] is True and r["pipe"] == "SUCCESS"
