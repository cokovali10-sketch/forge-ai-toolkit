"""Tests for language modules (python/js/rust/cpp/go) + langs stage + CLI/MCP."""
from pathlib import Path


def _scaffold_all(tmp_path):
    from forge.langs import LANGS
    for lid, mod in LANGS.items():
        mod.scaffold(f"demo-{lid}", tmp_path / lid)


def test_detect_all(tmp_path):
    from forge.langs import LANGS
    _scaffold_all(tmp_path)
    for lid, mod in LANGS.items():
        d = mod.detect(tmp_path / lid)
        assert d["present"], lid
        assert d["markers"], lid


def test_python_lint_and_test(tmp_path):
    from forge.langs import python
    d = tmp_path / "py"
    python.scaffold("t", d)
    assert python.lint(d).status == "SUCCESS"
    assert "нет тулчейна" not in " ".join(python.lint(d).warnings)
    (d / "bad.py").write_text("def broken(:\n", encoding="utf-8")
    assert python.lint(d).status != "SUCCESS"
    (d / "bad.py").unlink()
    assert python.test(d).status == "SUCCESS"


def test_go_full_cycle(tmp_path):
    from forge.langs import go
    d = tmp_path / "go"
    go.scaffold("t", d)
    assert (d / "go.mod").is_file()
    lr = go.lint(d)
    assert lr.status == "SUCCESS"
    assert "нет тулчейна" not in " ".join(lr.warnings)  # настоящий go, не заглушка
    assert go.test(d).status == "SUCCESS"


def test_missing_toolchains_degrade(tmp_path):
    from forge.langs import cpp, javascript, rust
    for mod, d in ((javascript, "js"), (rust, "rs"), (cpp, "cc")):
        mod.scaffold("t", tmp_path / d)
        r = mod.lint(tmp_path / d)
        assert r.status == "SUCCESS"
        assert isinstance(r.result, dict) and r.result.get("files_checked", 0) >= 0


def test_langs_stage(tmp_path):
    from forge.pipe.stages import stage_langs
    from forge.langs import python
    python.scaffold("t", tmp_path / "ok")
    assert stage_langs({"target": str(tmp_path / "ok")}).status == "SUCCESS"
    bad = tmp_path / "bad"
    (bad).mkdir()
    (bad / "x.py").write_text("def broken(:\n", encoding="utf-8")
    r = stage_langs({"target": str(bad)})
    assert r.status != "SUCCESS"


def test_lang_cli_and_mcp(tmp_path):
    from forge.cli.__main__ import main
    from forge.mcp.server import build_default_registry
    assert main(["lang", "lint", "nope", str(tmp_path)]) == 2
    assert main(["lang", "scaffold", "go", "t", str(tmp_path / "g")]) == 0
    assert (tmp_path / "g" / "go.mod").is_file()
    reg = build_default_registry("")
    det = reg.call("lang.detect_all", {"root": str(tmp_path / "g")})
    assert det["data"]["languages"]["go"]["present"] is True
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "x.py").write_text("def broken(:\n", encoding="utf-8")
    failed = reg.call("lang.lint", {"lang": "python", "root": str(bad)})
    assert failed.get("status") != "SUCCESS"
