"""Tests for forge do (intent orchestrator)."""
from pathlib import Path

# Корень forge (не пакета): skills/, module-packs/, knowledge/ лежат здесь.
FORGE_ROOT = str(Path(__file__).resolve().parents[1])


def _good_project(tmp_path):
    (tmp_path / "app.py").write_text("def add(a, b):\n    return a + b\n",
                                     encoding="utf-8")
    return tmp_path


def test_plan_detects_generator_and_verifies(tmp_path):
    from forge.orchestrate import plan, run
    p = _good_project(tmp_path)
    pl = plan("сделай лендинг для магазина", str(p), FORGE_ROOT)
    assert pl["generator"] == "web"
    assert any(s["step"] == "generate" for s in pl["steps"])
    assert any("web" in s["command"] for s in pl["steps"])
    assert pl["steps"][-1]["step"] == "inspect" or any(
        s["step"] == "verify" for s in pl["steps"])

    verified = run("проверь проект", str(p), FORGE_ROOT,
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


def test_skills_not_matched_on_generic_words(tmp_path):
    from forge.orchestrate import plan
    pl = plan("Хочу REST API сервис с базой данных и тестами", str(tmp_path),
              FORGE_ROOT)
    assert pl["generator"] == "python-service"
    assert all(s["domain"] != "minecraft" for s in pl["skills"])


def test_skills_match_explicit_domain(tmp_path):
    from forge.orchestrate import plan
    root = FORGE_ROOT
    mc = plan("сделай плагин для майнкрафта", str(tmp_path), root)
    assert any(s["domain"] == "minecraft" for s in mc["skills"])
    ref = plan("отрефактори код, слишком длинный и вложенный метод",
               str(tmp_path), root)
    assert any(s["domain"] == "clean-code" for s in ref["skills"])


def test_plan_suggests_audit_on_review_intent(tmp_path):
    from forge.orchestrate import plan
    root = FORGE_ROOT
    pl = plan("проверь проект на утечки и зависимости", str(tmp_path), root)
    assert pl["steps"][0]["step"] == "audit"
    assert "forge audit" in pl["steps"][0]["command"]
    plain = plan("сделай лендинг для кофейни", str(tmp_path), root)
    assert all(s["step"] != "audit" for s in plain["steps"])
