"""Tests for forge do (intent orchestrator)."""


def _good_project(tmp_path):
    (tmp_path / "app.py").write_text("def add(a, b):\n    return a + b\n",
                                     encoding="utf-8")
    return tmp_path


def test_plan_detects_generator_and_verifies(tmp_path):
    from forge.orchestrate import plan, run
    p = _good_project(tmp_path)
    pl = plan("сделай лендинг для магазина", str(p), "D:/Forge-Factority/forge")
    assert pl["generator"] == "web"
    assert any(s["step"] == "generate" for s in pl["steps"])
    assert any("web" in s["command"] for s in pl["steps"])
    assert pl["steps"][-1]["step"] == "inspect" or any(
        s["step"] == "verify" for s in pl["steps"])

    verified = run("проверь проект", str(p), "D:/Forge-Factority/forge",
                   execute=True)
    assert verified["generator"] == ""
    assert verified["verify"]["status"] == "SUCCESS"


def test_do_cli_and_mcp(tmp_path):
    from forge.cli.__main__ import main
    from forge.mcp.server import build_default_registry
    p = _good_project(tmp_path)
    assert main(["do", "сделай cli утилиту", "--root", str(p), "--json"]) == 0
    reg = build_default_registry("")
    assert "do.plan" in reg.tool_owner and "do.run" in reg.tool_owner
    r = reg.call("do.plan", {"intent": "сервис api", "root": str(p)})
    assert r["data"]["generator"] == "python-service"
    assert r["data"]["steps"]
