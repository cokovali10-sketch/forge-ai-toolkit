import json
from pathlib import Path

from forge.kit import baseline as bl
from forge.cli.__main__ import main

_GH = "ghp_" + "a" * 36
_SK = "sk_live_" + "b" * 24


def _proj(tmp_path: Path) -> Path:
    (tmp_path / "a.py").write_text("X = 42\n", encoding="utf-8")
    return tmp_path


def test_collect_fingerprints(tmp_path):
    _proj(tmp_path)
    snap = bl.collect(tmp_path)
    assert snap["ok"] and snap["count"] >= 1
    for i in snap["items"]:
        assert len(i["fingerprint"]) == 16
        assert i["severity"] in ("high", "medium", "low")


def test_fingerprint_stable_across_line_shift(tmp_path):
    (tmp_path / "a.py").write_text("A = 1\nB = 2\nX = 42\n", encoding="utf-8")
    before = {i["fingerprint"] for i in bl.collect(tmp_path)["items"]}
    (tmp_path / "a.py").write_text(
        "# c\n# c\nA = 1\nB = 2\nX = 42\n", encoding="utf-8")
    after = {i["fingerprint"] for i in bl.collect(tmp_path)["items"]}
    assert before == after


def test_save_check_hold_and_regression(tmp_path):
    _proj(tmp_path)
    saved = bl.save(tmp_path)
    assert saved["ok"] and Path(saved["path"]).is_file()

    ok = bl.check(tmp_path)
    assert ok["ok"] is True and sum(ok["new_counts"].values()) == 0

    (tmp_path / "b.py").write_text(f"KEY = '{_SK}'\n", encoding="utf-8")
    bad = bl.check(tmp_path)
    assert bad["ok"] is False
    assert bad["new_counts"]["high"] >= 1

    relaxed = bl.check(tmp_path, fail_on="none")
    assert relaxed["ok"] is True


def test_check_missing_baseline(tmp_path):
    _proj(tmp_path)
    res = bl.check(tmp_path)
    assert res["ok"] is False and res.get("baseline_missing") is True
    assert "baseline save" in bl.render_text(res)


def test_diff_reports_resolved(tmp_path):
    _proj(tmp_path)
    bl.save(tmp_path)
    (tmp_path / "a.py").write_text("X = 1\n", encoding="utf-8")
    loaded = bl.load(tmp_path / bl.DEFAULT_NAME)
    d = bl.diff(bl.collect(tmp_path)["items"], loaded["items"])
    assert len(d["resolved"]) >= 1


def test_cli_baseline_flow(tmp_path):
    _proj(tmp_path)
    assert main(["baseline", "save", str(tmp_path)]) == 0
    assert main(["baseline", "check", str(tmp_path), "--json"]) == 0
    assert main(["baseline", "diff", str(tmp_path)]) == 0
    (tmp_path / "c.py").write_text(f"T = '{_GH}'\n", encoding="utf-8")
    assert main(["baseline", "check", str(tmp_path)]) == 1


def test_audit_baseline_gate(tmp_path):
    _proj(tmp_path)
    assert main(["baseline", "save", str(tmp_path)]) == 0
    assert main(["audit", str(tmp_path), "--baseline"]) == 0
    (tmp_path / "d.py").write_text(f"K = '{_SK}'\n", encoding="utf-8")
    assert main(["audit", str(tmp_path), "--baseline"]) == 1
