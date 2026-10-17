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
