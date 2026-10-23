"""Tests for FORGE Factory: intent spec, pipeline, CLI, MCP.

The real-server e2e is opt-in (FORGE_FACTORY_E2E=1) because it boots
Purpur; the build stage runs only when a paper-api jar is available.
"""
import json

import pytest


def test_plan_from_shopping_intent():
    from forge.factory import plan
    spec = plan("сделай плагин магазин с GUI и анимациями",
                name="My Shop")
    assert spec["domain"] == "shop"
    assert spec["name"] == "MyShop"
    assert spec["class"] == "MyShop"
    assert spec["package"] == "com.forge.shop"
    assert spec["command"] == "shop"
    assert spec["gui"] is True
    assert "gui" in spec["features"] and "config" in spec["features"]
    assert spec["resourcepack"] is False
    assert spec["preset"] in ("aurora", "neon", "glass", "brutalist",
                              "minimal", "retro")


def test_plan_rejects_bad_ids():
    from forge.factory import plan
    with pytest.raises(ValueError):
        plan("магазин", package="Bad Package")
    with pytest.raises(ValueError):
        plan("магазин", name="!!!")
    with pytest.raises(ValueError):
        plan("магазин", command="bad-cmd")
    with pytest.raises(ValueError):
        plan("   ")


def test_run_without_build_or_server(tmp_path):
    from forge.factory import run
    res = run("плагин магазин с GUI", out=tmp_path, build=False, e2e=False)
    assert res["status"] == "PASS" and res["ok"] is True
    dest = tmp_path / "ForgeShop"
    for name in ("factory.json", "factory-report.json", "FACTORY.md",
                 "README.md", "src/plugin.yml", "src/config.yml"):
        assert (dest / name).is_file(), name
    main = dest / "src" / "com" / "forge" / "shop" / "ForgeShop.java"
    assert main.is_file()
    code = main.read_text(encoding="utf-8")
    assert "openInventory" in code and "forge-factory" in code
    assert (dest / "dist" / "ForgeShop-0.1.0-forge.zip").is_file()
    stages = {s["name"]: s["status"] for s in res["stages"]}
    assert stages["generate"] == "PASS" and stages["validate"] == "PASS"
    assert stages["build"] == "SKIPPED" and stages["e2e"] == "SKIPPED"
    assert stages["package"] == "PASS"
    report = json.loads((dest / "factory-report.json").read_text(
        encoding="utf-8"))
    assert report["status"] == "PASS"


def test_build_when_paper_api_available(tmp_path):
    from forge.factory.pipeline import _find_api_jars, _javac
    from forge.factory import run
    if not _find_api_jars() or not _javac():
        pytest.skip("paper-api or javac is not available on this machine")
    res = run("аукцион с GUI", out=tmp_path, e2e=False)
    stages = {s["name"]: s for s in res["stages"]}
    assert stages["build"]["status"] == "PASS", stages["build"]
    assert res["jar"] and (tmp_path / "ForgeAuction" / "build").is_dir()
    assert res["status"] == "PASS" and res["ok"] is True


def test_resourcepack_is_real_when_pillow_present(tmp_path):
    pytest.importorskip("PIL")
    from forge.factory import run
    res = run("магазин GUI с анимациями и текстурами", out=tmp_path,
              build=False, e2e=False)
    stages = {s["name"]: s["status"] for s in res["stages"]}
    assert stages["resourcepack"] == "PASS"
    pack = tmp_path / "ForgeShop" / "resourcepack"
    assert (pack / "manifest.json").is_file()
    assert (pack / "pack.mcmeta").is_file()
    assert (pack / "textures" / "panel.png").is_file()


def test_factory_cli_and_mcp(tmp_path):
    from forge.cli.__main__ import main
    from forge.mcp.server import build_default_registry
    out = tmp_path / "cli"
    assert main(["factory", "магазин с GUI", "--out", str(out),
                 "--no-build", "--no-e2e", "--json"]) == 0
    assert (out / "ForgeShop" / "FACTORY.md").is_file()
    assert main(["factory", "plan", "магазин", "--json"]) == 0
    assert main(["factory", "--no-build"]) == 2
    reg = build_default_registry("")
    assert "factory.plan" in reg.tool_owner
    assert "factory.run" in reg.tool_owner
    spec = reg.call("factory.plan", {"intent": "плагин кит"})["data"]
    assert spec["domain"] == "kits" and spec["command"] == "kit"


@pytest.mark.skipif(
    not __import__("os").environ.get("FORGE_FACTORY_E2E"),
    reason="set FORGE_FACTORY_E2E=1 to boot a real server")
def test_real_server_e2e(tmp_path):
    from forge.factory import run
    res = run("плагин магазин с GUI", out=tmp_path, timeout_boot=300)
    stages = {s["name"]: s["status"] for s in res["stages"]}
    assert stages["e2e"] == "PASS", res["stages"]
    assert res["ok"] is True
