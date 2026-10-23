"""Tests for the Speed department: batch I/O, context packs, blueprints."""
from __future__ import annotations

import base64
import compileall
import json
import shutil
import subprocess
from pathlib import Path

import pytest


# --------------------------------------------------------------------------
# speed.write
# --------------------------------------------------------------------------

def test_write_batch_dict_and_list(tmp_path):
    from forge.speed import write
    res = write(tmp_path, {"a.txt": "hello", "nested/b.py": "print('x')\n"})
    assert res["ok"] is True
    assert res["files"] == 2
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "hello"
    assert (tmp_path / "nested/b.py").read_text(encoding="utf-8") == "print('x')\n"
    blob = base64.b64encode(b"\x00\x01").decode()
    res = write(tmp_path, [
        {"path": "a.txt", "content": "new"},
        {"path": "data.bin", "base64": blob},
        {"path": "append.txt", "content": "one"},
        {"path": "append.txt", "content": "+two", "mode": "append"},
    ])
    assert res["ok"] is True
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "new"
    assert (tmp_path / "data.bin").read_bytes() == b"\x00\x01"
    assert (tmp_path / "append.txt").read_text(encoding="utf-8") == "one+two"


def test_write_create_mode_dry_run_and_guards(tmp_path):
    from forge.speed import write
    (tmp_path / "exists.txt").write_text("old", encoding="utf-8")
    res = write(tmp_path, [{"path": "exists.txt", "content": "x", "mode": "create"}])
    assert res["ok"] is False and res["errors"][0]["error"] == "already exists"
    assert (tmp_path / "exists.txt").read_text(encoding="utf-8") == "old"
    res = write(tmp_path, {"dry.txt": "x"}, dry_run=True)
    assert res["ok"] is True and not (tmp_path / "dry.txt").exists()
    res = write(tmp_path, {"../escape.txt": "x"})
    assert res["ok"] is False
    res = write(tmp_path, {".git/config": "x"})
    assert res["ok"] is False


def test_write_atomic_rollback(tmp_path, monkeypatch):
    from forge.speed import files as _files
    from forge.speed import write
    (tmp_path / "a.txt").write_text("A", encoding="utf-8")
    (tmp_path / "b.txt").write_text("B", encoding="utf-8")
    real = _files._write_one

    def flaky(target, data, ensure_parent=True):
        if target.name == "b.txt":
            raise OSError("disk full")
        return real(target, data, ensure_parent=ensure_parent)

    monkeypatch.setattr(_files, "_write_one", flaky)
    res = write(tmp_path, {"a.txt": "new A", "b.txt": "new B"}, atomic=True)
    assert res["ok"] is False
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "A"
    assert (tmp_path / "b.txt").read_text(encoding="utf-8") == "B"


# --------------------------------------------------------------------------
# speed.patch
# --------------------------------------------------------------------------

def test_patch_exact_all_regex_and_dry_run(tmp_path):
    from forge.speed import patch
    f = tmp_path / "x.py"
    f.write_text("value = 1\nprint(value)\n", encoding="utf-8")
    res = patch(tmp_path, [{"path": "x.py", "find": "1", "replace": "2"}])
    assert res["ok"] is True and res["files"] == 1
    assert f.read_text(encoding="utf-8").startswith("value = 2")
    res = patch(tmp_path, [{"path": "x.py", "find": "value", "replace": "v"}])
    assert res["ok"] is False and "ambiguous" in res["errors"][0]["error"]
    res = patch(tmp_path, [{"path": "x.py", "find": "value",
                            "replace": "v", "all": True}])
    assert res["ok"] is True and f.read_text(encoding="utf-8") == "v = 2\nprint(v)\n"
    res = patch(tmp_path, [{"path": "x.py", "find": r"v = (\d+)",
                            "replace": r"v = 99", "regex": True}])
    assert res["ok"] is True and "v = 99" in f.read_text(encoding="utf-8")
    before = f.read_text(encoding="utf-8")
    res = patch(tmp_path, [{"path": "x.py", "find": "99", "replace": "7"}],
                dry_run=True)
    assert res["ok"] is True and res["dry_run"] is True
    assert f.read_text(encoding="utf-8") == before
    res = patch(tmp_path, [{"path": "x.py", "find": "nope", "replace": "x"}])
    assert res["ok"] is False


def test_patch_transaction_and_expected(tmp_path):
    from forge.speed import patch
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("alpha\n", encoding="utf-8")
    b.write_text("beta\n", encoding="utf-8")
    res = patch(tmp_path, [
        {"path": "a.txt", "find": "alpha", "replace": "ALPHA"},
        {"path": "b.txt", "find": "missing", "replace": "x"},
    ])
    assert res["ok"] is False
    assert a.read_text(encoding="utf-8") == "alpha\n"
    assert b.read_text(encoding="utf-8") == "beta\n"
    res = patch(tmp_path, [{"path": "a.txt", "find": "alpha",
                            "replace": "x", "expected": 2}])
    assert res["ok"] is False and "expected 2" in res["errors"][0]["error"]


# --------------------------------------------------------------------------
# speed.search / speed.context
# --------------------------------------------------------------------------

def test_search_multi_pattern_one_pass_and_context(tmp_path):
    from forge.speed import search
    (tmp_path / "a.py").write_text("def one():\n    pass\nclass A:\n    pass\n",
                                   encoding="utf-8")
    (tmp_path / "b.md").write_text("def in markdown\n", encoding="utf-8")
    (tmp_path / "secret.py").write_text("api_key = SECRET123\n", encoding="utf-8")
    res = search(tmp_path, ["def ", "class "], globs=["*.py"], context=1)
    assert res["ok"] is True
    assert res["files_scanned"] == 2
    assert len(res["hits"]["def "]) == 1
    assert res["hits"]["class "][0]["file"] == "a.py"
    assert res["hits"]["def "][0]["context"]
    lit = search(tmp_path, "def", globs=["*.md"], regex=False)
    assert lit["hits"]["def"][0]["file"] == "b.md"
    sec = search(tmp_path, "SECRET123")
    assert sec["hits"]["SECRET123"][0]["text"].endswith("[REDACTED]")


def test_context_paths_query_budget_and_scrub(tmp_path):
    from forge.speed import context
    (tmp_path / "a.py").write_text("api_key = SECRET123\nprint('a')\n",
                                   encoding="utf-8")
    (tmp_path / "b.py").write_text("needle\n" * 20, encoding="utf-8")
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    res = context(tmp_path, paths=["a.py"], max_chars=100)
    assert res["ok"] is True and res["file_count"] == 1
    assert "SECRET123" not in res["files"][0]["content"]
    assert "[REDACTED]" in res["files"][0]["content"]
    assert "README.md" in res["tree"]
    res = context(tmp_path, query="needle", max_files=2)
    assert res["files"][0]["path"] == "b.py"
    res = context(tmp_path, paths=["b.py"], max_lines=3)
    assert res["files"][0]["truncated"] is True
    assert res["files"][0]["content"].count("\n") == 2
    res = context(tmp_path, paths=["b.py"], max_chars=5000)
    assert res["tokens_est"] > 0


# --------------------------------------------------------------------------
# speed.blueprint
# --------------------------------------------------------------------------

def test_blueprint_python_recipes_compile(tmp_path):
    from forge.speed import blueprint, recipes
    assert recipes()["ok"] is True
    for template in ("python-package", "layered", "http-service"):
        target = tmp_path / template
        res = blueprint(target, "Demo App", template)
        assert res["ok"] is True, res
        assert res["files"] >= 8
        assert compileall.compile_dir(target, quiet=1), template
    assert (tmp_path / "python-package" / "pyproject.toml").is_file()


def test_blueprint_custom_force_and_dry_run(tmp_path):
    from forge.speed import blueprint
    files = {"src/{{module}}/__init__.py": "NAME = '{{name}}'\n",
             "docs/{{slug}}.md": "# {{title}}\n"}
    res = blueprint(tmp_path, "Custom Thing", "custom", files=files, dry_run=True)
    assert res["ok"] is True and not (tmp_path / "src").exists()
    assert "src/custom_thing/__init__.py" in res["would_write"]
    res = blueprint(tmp_path, "Custom Thing", "custom", files=files)
    assert res["ok"] is True
    assert (tmp_path / "src/custom_thing/__init__.py").read_text(
        encoding="utf-8") == "NAME = 'Custom Thing'\n"
    res = blueprint(tmp_path, "Custom Thing", "custom", files=files)
    assert res["ok"] is True and len(res["skipped"]) == 2
    res = blueprint(tmp_path, "Custom Thing", "custom", files=files, force=True)
    assert res["ok"] is True and len(res["written"]) == 2
    bad = blueprint(tmp_path, "X", "custom", files={"x": "{{unknown}}"})
    assert bad["ok"] is False and "unknown template variables" in bad["error"]
    assert blueprint(tmp_path, "X", "no-such-template")["ok"] is False


def test_blueprint_plugin_feature_and_javac(tmp_path):
    from forge.speed import blueprint
    root = tmp_path / "plugin"
    res = blueprint(root, "Shop Demo", "plugin-feature", package="com.forge.shop")
    assert res["ok"] is True and res["files"] == 9
    yml = (root / "plugin.yml").read_text(encoding="utf-8")
    assert "main: com.forge.shop.ShopDemoMain" in yml
    assert (root / "src/main/java/com/forge/shop/ShopDemoMain.java").is_file()
    jars = sorted((Path(__file__).resolve().parents[2] / "lab-servers" / "api")
                  .glob("*.jar"))
    javac = shutil.which("javac")
    if not jars or not javac:
        pytest.skip("javac or paper-api jars are not available")
    cp = ";".join(str(j) for j in jars)
    sources = [str(p) for p in (root / "src/main/java").rglob("*.java")]
    out = root / "classes"
    out.mkdir()
    r = subprocess.run([javac, "-cp", cp, "-d", str(out), *sources],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr


def test_blueprint_unknown_name_and_package(tmp_path):
    from forge.speed import blueprint
    res = blueprint(tmp_path / "s", "123 shop", "python-package")
    assert res["ok"] is True
    assert (tmp_path / "s" / "src" / "app_123_shop" / "__init__.py").is_file()


# --------------------------------------------------------------------------
# speed.bench
# --------------------------------------------------------------------------

def test_bench_reports_sections(tmp_path):
    from forge.speed import bench
    res = bench(tmp_path, files=8, repeats=1, call_overhead_ms=1.0)
    assert res["ok"] is True
    assert res["files"] == 8
    for key in ("write", "write_atomic", "patch", "search_4_patterns"):
        assert key in res
        assert res[key]["speedup"] >= 0
    assert not (tmp_path / ".forge-speed-bench").exists()


# --------------------------------------------------------------------------
# MCP + CLI + module pack
# --------------------------------------------------------------------------

def test_mcp_speed_tools(tmp_path):
    from forge.mcp.server import build_default_registry
    reg = build_default_registry("")
    names = set(reg.tool_owner)
    assert {"speed.write", "speed.patch", "speed.search", "speed.context",
            "speed.blueprint", "speed.recipes", "speed.bench"} <= names
    assert reg.tool_module["speed.write"] == "speed"
    assert reg.call("speed.recipes", {})["ok"] is True
    res = reg.call("speed.write", {"root": str(tmp_path),
                                   "files": {"mcp.txt": "hello"},
                                   "atomic": False})
    assert res["ok"] is True
    assert (tmp_path / "mcp.txt").read_text(encoding="utf-8") == "hello"
    assert reg.call("speed.context", {"root": str(tmp_path),
                                      "paths": ["mcp.txt"]})["file_count"] == 1


def test_cli_fast(tmp_path, capsys):
    from forge.cli.__main__ import main
    assert main(["fast", "recipes", "--json"]) == 0
    assert main(["fast", "blueprint", "--root", str(tmp_path),
                 "--template", "python-package", "--name", "CLI Demo",
                 "--json"]) == 0
    assert (tmp_path / "src" / "cli_demo" / "service.py").is_file()
    assert main(["fast", "write", "--root", str(tmp_path), "--data",
                 json.dumps({"cli.txt": "hello"}), "--json"]) == 0
    assert main(["fast", "search", "--root", str(tmp_path),
                 "--pattern", "hello", "--json"]) == 0
    assert main(["fast", "patch", "--root", str(tmp_path), "--data",
                 json.dumps([{"path": "cli.txt", "find": "hello",
                              "replace": "world"}]), "--json"]) == 0
    assert (tmp_path / "cli.txt").read_text(encoding="utf-8") == "world"
    assert main(["fast", "context", "--root", str(tmp_path),
                 "--path", "cli.txt", "--pack"]) == 0
    out = capsys.readouterr().out
    assert "### cli.txt" in out and "world" in out
    assert main(["fast", "blueprint", "--template", "python-package"]) == 2
    assert main(["fast", "nope"]) == 2


def test_speed_module_pack_routes_and_validates():
    from forge.modules.manifest import load_packs, route
    root = Path(__file__).resolve().parents[1]
    packs = load_packs(root / "module-packs")
    assert "speed" in packs
    assert packs["speed"].validate() == []
    picks = route("быстро создай сложную структуру проекта и много файлов",
                  packs)
    assert picks and any(p[0] == "speed" for p in picks)


def test_orchestrator_marks_speed_intent(tmp_path):
    from forge.orchestrate import plan
    (tmp_path / "app.py").write_text("print('x')\n", encoding="utf-8")
    fast = plan("быстро создай сложную структуру и много файлов",
                str(tmp_path), str(Path(__file__).resolve().parents[1]))
    assert fast["speed"] is True
    steps = [s["step"] for s in fast["steps"]]
    assert "speed-context" in steps and "speed-batch" in steps
    slow = plan("проверь проект", str(tmp_path),
                str(Path(__file__).resolve().parents[1]))
    assert slow["speed"] is False
    assert "speed-context" not in [s["step"] for s in slow["steps"]]
