"""Tests for the refactor clean-code advisor."""
from pathlib import Path


def _long_function(n: int = 60, args: int = 5) -> str:
    a = ", ".join(f"a{i}" for i in range(args))
    body = "\n".join(f"    step_{i} = {i}" for i in range(n))
    return f"def huge({a}):\n{body}\n    return step_0\n"


def _deep_nesting() -> str:
    return (
        "def nested(a, b, c, d):\n"
        "    for item in a:\n"
        "        if item > b:\n"
        "            if item < c:\n"
        "                if item == d:\n"
        "                    return item\n"
        "    return None\n"
    )


def _god_class(n: int = 210) -> str:
    attrs = "\n".join(f"        self.f{i} = {i}" for i in range(n))
    return f"class GodClass:\n    def __init__(self):\n{attrs}\n"


def _duplicate_block() -> str:
    block = "result = transform(99999)\ntotal = add(99999)\nratio = div(99999)\n"
    return block + block


def _branchy() -> str:
    conds = "\n".join(f"    if a and b or c:\n        x = {i}" for i in range(6))
    return f"def branchy(a, b, c):\n    x = 0\n{conds}\n    return x\n"


def test_all_kinds_detected(tmp_path):
    from forge.refactor.clean_code import analyze_file
    p = tmp_path / "bad.py"
    p.write_text(
        _long_function() + _deep_nesting() + _god_class() + _duplicate_block(),
        encoding="utf-8")
    res = analyze_file(p)
    assert res["ok"] is True
    kinds = {i["kind"] for i in res["issues"]}
    for expected in ("long-function", "too-many-args", "deep-nesting",
                     "god-class", "magic-number", "duplicate-block"):
        assert expected in kinds, (expected, kinds)


def test_nesting_reported_once(tmp_path):
    from forge.refactor.clean_code import analyze_file
    p = tmp_path / "n.py"
    p.write_text(_deep_nesting(), encoding="utf-8")
    n = [i for i in analyze_file(p)["issues"] if i["kind"] == "deep-nesting"]
    assert len(n) == 1  # depth 4 only once — no double AST traversal


def test_complexity_and_score(tmp_path):
    from forge.refactor.clean_code import analyze_file, score_of
    p = tmp_path / "cx.py"
    p.write_text(_branchy(), encoding="utf-8")
    res = analyze_file(p)
    kinds = {i["kind"] for i in res["issues"]}
    assert "high-complexity" in kinds
    assert 0 <= res["score"] < 100
    assert score_of([]) == 100
    good = tmp_path / "good.py"
    good.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    assert analyze_file(good)["score"] == 100


def test_clean_file_ok(tmp_path):
    from forge.refactor.clean_code import analyze_file
    p = tmp_path / "good.py"
    p.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    res = analyze_file(p)
    assert res["ok"] is True
    assert res["total"] == 0


def test_missing_and_broken(tmp_path):
    from forge.refactor.clean_code import analyze_file
    assert analyze_file(tmp_path / "nope.py")["ok"] is False
    bad = tmp_path / "broken.py"
    bad.write_text("def x(:\n", encoding="utf-8")
    assert analyze_file(bad)["ok"] is False


def test_api_dir_and_cli(tmp_path):
    from forge.cli.__main__ import main
    from forge.refactor import api as rapi
    (tmp_path / "bad.py").write_text(_long_function(), encoding="utf-8")
    res = rapi.inspect(str(tmp_path))
    assert res["files"] == 1
    assert res["total_issues"] > 0
    assert main(["refactor", str(tmp_path)]) == 0
    assert main(["refactor", str(tmp_path / "nope.py")]) == 1


def test_plan_and_sarif(tmp_path):
    from forge.cli.__main__ import main
    from forge.refactor import api as rapi
    (tmp_path / "bad.py").write_text(_long_function() + _duplicate_block(),
                                     encoding="utf-8")
    plan = rapi.plan(str(tmp_path))
    assert plan["total"] > 0
    order = {"high": 0, "medium": 1, "low": 2}
    sev = [order[s["severity"]] for s in plan["steps"]]
    assert sev == sorted(sev)
    assert all(s["effort"] in ("S", "M", "L") for s in plan["steps"])
    sar = rapi.sarif(str(tmp_path))
    assert sar["version"] == "2.1.0"
    results = sar["runs"][0]["results"]
    assert results and results[0]["ruleId"].startswith("forge/refactor/")
    assert main(["refactor", str(tmp_path), "--plan"]) == 0
    sp = tmp_path / "out.sarif"
    assert main(["refactor", str(tmp_path), "--sarif", str(sp)]) == 0
    assert sp.is_file()


def test_generic_js_long_function(tmp_path):
    from forge.refactor.clean_code import analyze_file
    body = "\n".join(f"  const v{i} = {i + 100};" for i in range(55))
    src = f"function big(a, b, c, d, e) {{\n{body}\n  return v0;\n}}\n"
    p = tmp_path / "s.js"
    p.write_text(src, encoding="utf-8")
    res = analyze_file(p)
    assert res["ok"] is True and res["lang"] == "generic"
    kinds = {i["kind"] for i in res["issues"]}
    assert "long-function" in kinds
    assert "too-many-args" in kinds


def test_generic_go_duplicate_and_magic(tmp_path):
    from forge.refactor.clean_code import analyze_file
    block = ("    total = total + value\n"
             "    count = count + 1\n"
             "    logger.Trace(total)\n")
    src = "func run(a int) {\n" + block + block + "    return 8080\n}\n"
    p = tmp_path / "s.go"
    p.write_text(src, encoding="utf-8")
    res = analyze_file(p)
    kinds = {i["kind"] for i in res["issues"]}
    assert "duplicate-block" in kinds
    assert "magic-number" in kinds


def test_generic_no_false_magic_in_strings_and_comments(tmp_path):
    from forge.refactor.clean_code import analyze_file
    p = tmp_path / "c.js"
    p.write_text('const s = "12345"; // 99999\n/* 77777 */\nconst n = 5;\n',
                 encoding="utf-8")
    res = analyze_file(p)
    assert res["total"] == 0


def test_apply_extracts_repeated_constants(tmp_path):
    from forge.refactor import api as rapi
    p = tmp_path / "m.py"
    p.write_text("def f(x):\n    if x > 99999:\n        return 99999\n"
                 "    return x\n", encoding="utf-8")
    res = rapi.apply(str(p))
    assert res["ok"] and res["changed"]
    text = p.read_text(encoding="utf-8")
    assert "CONST_99999 = 99999" in text
    assert text.count("CONST_99999") == 3
    assert not (tmp_path / "m.py.forgebak").exists()
    ns: dict = {}
    exec(compile(text, str(p), "exec"), ns)  # behavior preserved
    assert ns["f"](100000) == 99999 and ns["f"](1) == 1


def test_apply_noop_without_repeats(tmp_path):
    from forge.refactor import api as rapi
    p = tmp_path / "m.py"
    p.write_text("def f(x):\n    return x + 99999\n", encoding="utf-8")
    before = p.read_text(encoding="utf-8")
    res = rapi.apply(str(p))
    assert res["ok"] and not res["changed"]
    assert p.read_text(encoding="utf-8") == before


def test_apply_rollback_on_test_failure(tmp_path):
    import sys
    from forge.refactor import api as rapi
    p = tmp_path / "m.py"
    src = "def f(x):\n    return 99999 + 99999\n"
    p.write_text(src, encoding="utf-8")
    res = rapi.apply(str(p),
                     test_cmd=[sys.executable, "-c", "import sys; sys.exit(1)"],
                     run_tests=True)
    assert not res["ok"] and not res["changed"]
    assert p.read_text(encoding="utf-8") == src
    assert not (tmp_path / "m.py.forgebak").exists()


def test_apply_keeps_docstring_first(tmp_path):
    from forge.refactor import api as rapi
    p = tmp_path / "m.py"
    p.write_text('"""Doc."""\n\n\ndef f():\n    return 7 + 7\n',
                 encoding="utf-8")
    res = rapi.apply(str(p))
    assert res["ok"] and res["changed"]
    text = p.read_text(encoding="utf-8")
    assert text.startswith('"""Doc."""')
    assert "CONST_7 = 7" in text


def test_apply_non_python(tmp_path):
    from forge.refactor import api as rapi
    p = tmp_path / "m.js"
    p.write_text("const x = 1;\n", encoding="utf-8")
    res = rapi.apply(str(p))
    assert res["ok"] and not res["changed"]


def test_unused_import_detected(tmp_path):
    from forge.refactor.clean_code import analyze_file
    p = tmp_path / "u.py"
    p.write_text("import os\nimport sys\n\n\nprint(sys.argv)\n", encoding="utf-8")
    res = analyze_file(p)
    found = [i for i in res["issues"] if i["kind"] == "unused-import"]
    assert found and "os" in found[0]["message"]
    assert all("sys" not in i["message"] for i in found)


def test_unused_import_respects_noqa_and_strings(tmp_path):
    from forge.refactor.clean_code import analyze_file
    p = tmp_path / "u.py"
    p.write_text("import os  # noqa: F401\nimport json\n\n__all__ = ['json']\n",
                 encoding="utf-8")
    res = analyze_file(p)
    assert not [i for i in res["issues"] if i["kind"] == "unused-import"]


def test_apply_removes_unused_imports(tmp_path):
    from forge.refactor import api as rapi
    p = tmp_path / "u.py"
    p.write_text(
        "import os\n"
        "import sys\n"
        "from json import loads, dumps\n"
        "\n\n"
        "def f():\n"
        "    return sys.argv\n",
        encoding="utf-8")
    res = rapi.apply(str(p))
    assert res["ok"] and res["changed"]
    assert set(res["removed_imports"]) == {"os", "loads", "dumps"}
    text = p.read_text(encoding="utf-8")
    assert "import os" not in text
    assert "import sys" in text
    assert "json" not in text
    assert not (tmp_path / "u.py.forgebak").exists()
    ns: dict = {}
    exec(compile(text, str(p), "exec"), ns)  # behavior preserved


def test_apply_keeps_used_from_import(tmp_path):
    from forge.refactor import api as rapi
    p = tmp_path / "p.py"
    p.write_text("from json import loads, dumps\n\n\ndef g(t):\n    return loads(t)\n",
                 encoding="utf-8")
    res = rapi.apply(str(p))
    assert res["ok"] and res["changed"]
    text = p.read_text(encoding="utf-8")
    assert "from json import loads" in text
    assert "dumps" not in text


def test_apply_keeps_noqa_import(tmp_path):
    from forge.refactor import api as rapi
    p = tmp_path / "n.py"
    p.write_text("import os  # noqa: F401\n\n\nprint(1)\n", encoding="utf-8")
    res = rapi.apply(str(p))
    assert res["ok"] and not res["changed"]
    assert "import os" in p.read_text(encoding="utf-8")


def test_apply_handles_cyrillic_before_number(tmp_path):
    from forge.refactor import api as rapi
    p = tmp_path / "ru.py"
    p.write_text(
        'ROW = ("1/7 осмотр проекта", 60.0, 60.0)\n'
        '\n\n'
        'def f(x):\n'
        '    return x\n',
        encoding="utf-8")
    res = rapi.apply(str(p))
    assert res["ok"] and res["changed"]
    text = p.read_text(encoding="utf-8")
    assert '"1/7 осмотр проекта"' in text
    assert "CONST_60 = 60.0" in text
    ns: dict = {}
    exec(compile(text, str(p), "exec"), ns)
    assert ns["ROW"] == ("1/7 осмотр проекта", 60.0, 60.0)


def test_pipe_clean_code_stage(tmp_path):
    from forge.pipe.runner import PipeRunner
    from forge.pipe.stages import DEFAULT_STAGES
    (tmp_path / "bad.py").write_text(_long_function(), encoding="utf-8")
    stage = [s for s in DEFAULT_STAGES if s.name == "clean-code"]
    assert stage, "clean-code stage must be in the default conveyor"
    r = PipeRunner(stage, {"target": str(tmp_path),
                           "forge_root": "D:/Forge-Factority/forge"}).run()
    assert r.status == "SUCCESS"  # advisory: never fails
    warns = r.stages[0].get("warnings", [])
    assert any("чистый код" in w for w in warns)


def test_simplifiable_comparison_detected(tmp_path):
    from forge.refactor.clean_code import analyze_file
    p = tmp_path / "c.py"
    p.write_text("def f(x):\n    if x == None:\n        return True\n",
                 encoding="utf-8")
    kinds = {i["kind"] for i in analyze_file(p)["issues"]}
    assert "simplifiable-comparison" in kinds


def test_comparison_not_matched_for_ints(tmp_path):
    from forge.refactor.clean_code import analyze_file
    p = tmp_path / "c.py"
    p.write_text("def f(x):\n    return x == 1\n", encoding="utf-8")
    kinds = {i["kind"] for i in analyze_file(p)["issues"]}
    assert "simplifiable-comparison" not in kinds


def test_apply_comparisons_rewrites(tmp_path):
    from forge.refactor import api as rapi
    p = tmp_path / "c.py"
    p.write_text(
        "def f(x):\n"
        "    if x == None:\n"
        "        return 1\n"
        "    if x != True:\n"
        "        return 2\n"
        "    return 0\n", encoding="utf-8")
    res = rapi.apply(str(p), only="comparisons")
    assert res["ok"] and res["changed"]
    assert res["fixed_comparisons"] == 2
    text = p.read_text(encoding="utf-8")
    assert "is None" in text and "is not True" in text
    assert "== None" not in text and "!= True" not in text
    assert not (tmp_path / "c.py.forgebak").exists()
    ns: dict = {}
    exec(compile(text, str(p), "exec"), ns)  # behavior preserved
    assert ns["f"](None) == 1 and ns["f"](0) == 2 and ns["f"](True) == 0


def test_apply_comparisons_idempotent(tmp_path):
    from forge.refactor import api as rapi
    p = tmp_path / "c.py"
    p.write_text("def f(x):\n    return x is None\n", encoding="utf-8")
    res = rapi.apply(str(p), only="comparisons")
    assert res["ok"] and not res["changed"]


def test_bom_file_is_handled(tmp_path):
    from forge.refactor import api as rapi
    p = tmp_path / "b.py"
    p.write_bytes(b"\xef\xbb\xbfdef f(x):\n    if x == None:\n        return 1\n")
    res = rapi.apply(str(p), only="comparisons")
    assert res["ok"] and res["changed"]
    assert "is None" in p.read_text(encoding="utf-8")


def test_bom_file_can_be_analyzed(tmp_path):
    from forge.refactor.clean_code import analyze_file
    p = tmp_path / "b.py"
    p.write_bytes(b"\xef\xbb\xbfdef f(x):\n    if x == None:\n        return 1\n")
    res = analyze_file(p)
    assert res["ok"] is True
    assert any(i["kind"] == "simplifiable-comparison" for i in res["issues"])

