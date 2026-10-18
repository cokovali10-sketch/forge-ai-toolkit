import sys
from pathlib import Path

from forge.refactor.apply import apply_dir
from forge.cli.__main__ import main
from forge.mcp.server import build_default_registry


def _project(tmp_path: Path) -> Path:
    (tmp_path / "a.py").write_text(
        "import os\nX = 42\nY = X + 42\nif X == None:\n    pass\n",
        encoding="utf-8")
    (tmp_path / "b.py").write_text("Z = 7\nW = Z + 7\n", encoding="utf-8")
    return tmp_path


def test_apply_dir_fixes_multiple(tmp_path):
    root = _project(tmp_path)
    res = apply_dir(root)
    assert res["ok"] is True
    assert res["files_changed"] == 2
    text = (root / "a.py").read_text(encoding="utf-8")
    assert "CONST_42 = 42" in text and "import os" not in text
    assert "X is None" in text


def test_apply_dir_only_filter(tmp_path):
    root = _project(tmp_path)
    res = apply_dir(root, only="imports")
    assert res["files_changed"] >= 1
    text = (root / "a.py").read_text(encoding="utf-8")
    assert "import os" not in text
    assert "CONST_42" not in text


def test_apply_dir_rollback_on_test_failure(tmp_path):
    root = _project(tmp_path)
    before = (root / "a.py").read_text(encoding="utf-8")
    res = apply_dir(root, run_tests=True,
                    test_cmd=[sys.executable, "-c", "raise SystemExit(1)"])
    assert res["rolled_back"] is True
    assert res["ok"] is False and res["files_changed"] == 0
    assert (root / "a.py").read_text(encoding="utf-8") == before


def test_apply_dir_keeps_changes_when_tests_pass(tmp_path):
    root = _project(tmp_path)
    res = apply_dir(root, run_tests=True,
                    test_cmd=[sys.executable, "-c", "print('ok')"])
    assert res["rolled_back"] is False and res["files_changed"] == 2


def test_apply_dir_bad_dir(tmp_path):
    res = apply_dir(tmp_path / "nope")
    assert res["ok"] is False and "error" in res


def test_cli_fix(tmp_path):
    root = _project(tmp_path)
    assert main(["fix", str(root), "--json"]) == 0
    assert "CONST_42" in (root / "a.py").read_text(encoding="utf-8")


def test_mcp_fix_dir_wired():
    reg = build_default_registry("")
    assert "refactor.fix_dir" in reg.tool_owner
