"""Tests for forge loop (self-healing conveyor)."""


def _good_project(tmp_path):
    (tmp_path / "app.py").write_text("def add(a, b):\n    return a + b\n",
                                     encoding="utf-8")
    return tmp_path


def test_loop_green_immediately(tmp_path):
    from forge.pipe.loop import run_loop
    p = _good_project(tmp_path)
    out = run_loop(str(p), "D:/Forge-Factority/forge", max_attempts=3)
    assert out["ok"] is True and out["status"] == "SUCCESS"
    assert len(out["attempts"]) == 1


def test_loop_failed_no_fixer(tmp_path):
    from forge.pipe.loop import run_loop
    (tmp_path / "bad.py").write_text("def broken(:\n", encoding="utf-8")
    out = run_loop(str(tmp_path), "D:/Forge-Factority/forge", max_attempts=2,
                   auto_fix=False)
    assert out["ok"] is False and out["status"] == "FAILED"
    assert out["attempts"]
    assert any("stopped" in a for a in out["attempts"])


def test_loop_hook_repairs(tmp_path):
    import sys
    from forge.pipe.loop import hook_command, run_loop
    target = tmp_path / "proj"
    target.mkdir()
    (target / "bad.py").write_text("def broken(:\n", encoding="utf-8")
    fixer = tmp_path / "fixer.py"
    fixer.write_text(
        "import pathlib, sys\n"
        "p = pathlib.Path(sys.argv[1]) / 'bad.py'\n"
        "p.write_text('def ok(a):\\n    return a\\n', encoding='utf-8')\n",
        encoding="utf-8")
    hook = hook_command([sys.executable, str(fixer), str(target)], str(target))
    out = run_loop(str(target), "D:/Forge-Factority/forge", max_attempts=3,
                   auto_fix=False, on_fail=hook)
    assert out["ok"] is True, out
    assert out["attempts"][0]["status"] != "SUCCESS"
    assert out["attempts"][-1]["result"] == "green"


def test_loop_cli_and_mcp(tmp_path):
    from forge.cli.__main__ import main
    from forge.mcp.server import build_default_registry
    p = _good_project(tmp_path)
    assert main(["loop", str(p), "--json"]) == 0
    reg = build_default_registry("")
    assert "loop.run" in reg.tool_owner
    r = reg.call("loop.run", {"root": str(p), "attempts": 2})
    assert r["status"] == "SUCCESS"
