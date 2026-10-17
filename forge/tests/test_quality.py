"""Tests for forge quality (dashboard + trend + regression gate)."""


def _project(tmp_path):
    d = tmp_path / "proj"
    d.mkdir()
    (d / "app.py").write_text(
        "def add(a, b):\n    return a + b\n", encoding="utf-8")
    return d


def test_snapshot_and_langs(tmp_path):
    from forge.quality import snapshot
    d = _project(tmp_path)
    (d / "web.js").write_text("const x = 1;\n", encoding="utf-8")
    snap = snapshot(str(d), "D:/Forge-Factority/forge")
    assert snap["files"] >= 2
    assert snap["langs"].get("python") == 1
    assert snap["langs"].get("javascript") == 1
    assert snap["score"] > 0


def test_trend_and_gate(tmp_path):
    import forge.quality as q
    d = _project(tmp_path)
    forge = "D:/Forge-Factority/forge"
    first = q.check(str(d), forge, min_score=0)
    assert first["ok"] is True
    assert first["trend"]["samples"] == 1

    dirty = d / "dirty.py"
    dirty.write_text(
        "def f(a, b, c, d, e, f):\n"
        "    x = 12345\n    y = 12345\n    z = 12345\n"
        "    return a + b + c + d + e + f + x + y + z\n",
        encoding="utf-8")
    second = q.check(str(d), forge, max_regression=100000)
    assert second["trend"]["samples"] == 2
    assert second["issues"] > 0

    gate = q.check(str(d), forge, min_score=100, save=False)
    assert gate["ok"] is False
    assert gate["reasons"]


def test_quality_cli_and_mcp(tmp_path):
    from forge.cli.__main__ import main
    from forge.mcp.server import build_default_registry
    d = _project(tmp_path)
    (d / "dirty.py").write_text(
        "def f(a, b, c, d, e, f):\n    return a + 12345 + b + 12345 + c\n",
        encoding="utf-8")
    assert main(["quality", str(d), "--min-score", "0", "--json"]) == 0
    assert main(["quality", str(d), "--min-score", "100"]) == 1
    reg = build_default_registry("")
    assert "quality.report" in reg.tool_owner
    r = reg.call("quality.report", {"root": str(d)})
    assert r["score"] > 0
