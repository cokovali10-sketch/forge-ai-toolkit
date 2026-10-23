"""Tests for FORGE Web Studio: presets, generator, audit, CLI, MCP."""
import json
from pathlib import Path


FILES = ("index.html", "styles.css", "app.js", "README.md", "site.json")


def test_presets_are_complete():
    from forge.webstudio import PRESETS, list_presets
    items = list_presets()
    assert set(PRESETS) == {p["key"] for p in items}
    assert len(items) >= 6
    for item in items:
        assert item["title"] and item["hint"] and item["animations"]


def test_generate_every_preset(tmp_path):
    from forge.webstudio import PRESETS, generate
    for key in PRESETS:
        out = tmp_path / key
        res = generate(out, f"Demo {key}", preset=key, lang="en",
                       tagline="A fast demo site.")
        assert res["ok"] is True, (key, res["problems"])
        assert res["score"] >= 95, (key, res["score"], res["problems"])
        for name in FILES:
            assert (out / name).is_file(), (key, name)
        html = (out / "index.html").read_text(encoding="utf-8")
        assert f"<title>Demo {key}</title>" in html
        assert 'http://' not in html and 'https://' not in html
        assert "prefers-reduced-motion" in (out / "styles.css").read_text(
            encoding="utf-8")
        assert "prefers-reduced-motion" in (out / "app.js").read_text(
            encoding="utf-8")
        spec = json.loads((out / "site.json").read_text(encoding="utf-8"))
        assert spec["preset"] == key and spec["lang"] == "en"


def test_unknown_preset_is_honest(tmp_path):
    from forge.webstudio import generate
    try:
        generate(tmp_path / "x", "X", preset="nope")
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "aurora" in str(e)


def test_audit_finds_real_problems(tmp_path):
    from forge.webstudio import audit, contrast, generate
    assert contrast("#ffffff", "#000000") >= 21
    assert contrast("#000000", "#ffffff") >= 21
    out = tmp_path / "site"
    assert generate(out, "Demo")["ok"] is True
    (out / "app.js").unlink()
    broken = audit(out)
    assert broken["ok"] is False and broken["score"] < 100
    assert any("missing" in p for p in broken["problems"])


def test_audit_detects_no_reduced_motion(tmp_path):
    from forge.webstudio import audit, generate
    out = tmp_path / "site"
    generate(out, "Demo")
    css = (out / "styles.css").read_text(encoding="utf-8")
    (out / "styles.css").write_text(
        css.replace("prefers-reduced-motion", "prefers-typo"), encoding="utf-8")
    res = audit(out)
    assert res["ok"] is False
    assert any("reduced-motion" in p for p in res["problems"])


def test_web_cli_and_mcp(tmp_path):
    from forge.cli.__main__ import main
    from forge.mcp.server import build_default_registry
    out = tmp_path / "site"
    assert main(["web", "new", "CLI Demo", "--out", str(out),
                 "--preset", "neon", "--tagline", "cli", "--json"]) == 0
    assert (out / "index.html").is_file()
    assert main(["web", "presets", "--json"]) == 0
    assert main(["web", "audit", str(out), "--json"]) == 0
    assert main(["web", "new", "--out", str(tmp_path)]) == 2
    reg = build_default_registry("")
    for tool in ("web.presets", "web.generate", "web.audit"):
        assert tool in reg.tool_owner
    res = reg.call("web.generate", {"out": str(tmp_path / "mcp"),
                                    "name": "MCP Demo", "preset": "glass"})
    assert res["ok"] is True
    assert (tmp_path / "mcp" / "index.html").is_file()


def test_gen_web_backwards_compatible(tmp_path):
    from forge.gen import web
    res = web.generate(tmp_path / "old", "Legacy")
    assert res["ok"] is True
    for name in FILES:
        assert (tmp_path / "old" / name).is_file()
    html = (tmp_path / "old" / "index.html").read_text(encoding="utf-8")
    assert "<title>Legacy</title>" in html and "<h1" in html
