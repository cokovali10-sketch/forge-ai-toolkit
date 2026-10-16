"""Tests for the forge pipe conveyor (headless-safe: no window is created)."""
import json
import time

from forge.core.result import ToolResult
from forge.pipe.runner import PipeRunner, exit_code
from forge.pipe.stages import Stage
from forge.pipe.window import fmt_entry, icon


def _ok_fn(_ctx):
    return ToolResult(status="SUCCESS", result={"n": 1}, duration_ms=1)


def _boom_fn(_ctx):
    raise RuntimeError("stage exploded")


def _slow_fn(_ctx):
    time.sleep(5)
    return ToolResult(status="SUCCESS", result={})


def _mk(stages, tmp_path):
    return PipeRunner(stages, {"target": str(tmp_path),
                               "forge_root": str(tmp_path)},
                      checkpoint=str(tmp_path / "cp.json"),
                      on_event=lambda e: None)


def test_all_ok_and_report_json(tmp_path):
    r = _mk([Stage("a", "A", _ok_fn), Stage("b", "B", _ok_fn)], tmp_path).run()
    assert r.status == "SUCCESS"
    assert exit_code(r) == 0
    json.dumps(r.to_dict())  # must be JSON-serializable for AI/MCP
    assert [s["name"] for s in r.stages] == ["a", "b"]


def test_fail_stops_and_exit_1(tmp_path):
    stages = [Stage("a", "A", _ok_fn), Stage("x", "X", _boom_fn),
              Stage("b", "B", _ok_fn)]
    r = _mk(stages, tmp_path).run()
    assert r.status == "FAILED"
    assert exit_code(r) == 1
    assert [s["name"] for s in r.stages] == ["a", "x"]  # b never ran
    assert r.stages[1]["status"] == "ERROR"


def test_allow_fail_continues(tmp_path):
    stages = [Stage("x", "X", _boom_fn, allow_fail=True),
              Stage("b", "B", _ok_fn)]
    r = _mk(stages, tmp_path).run()
    assert r.status == "SUCCESS"
    assert [s["name"] for s in r.stages] == ["x", "b"]


def test_timeout(tmp_path):
    r = _mk([Stage("s", "S", _slow_fn, timeout_s=0.2)], tmp_path).run()
    assert r.stages[0]["status"] == "TIMEOUT"
    assert r.status == "FAILED"


def test_resume_skips_done(tmp_path):
    stages = [Stage("a", "A", _ok_fn), Stage("b", "B", _ok_fn)]
    _mk(stages, tmp_path).run()  # writes checkpoint
    calls = []
    stages2 = [Stage("a", "A", lambda c: (calls.append("a"), _ok_fn(c))[1]),
               Stage("b", "B", lambda c: (calls.append("b"), _ok_fn(c))[1])]
    r = _mk(stages2, tmp_path).run(resume=True)
    assert calls == []  # nothing re-ran
    assert all(s.get("resumed") for s in r.stages)


def test_window_helpers_without_window():
    assert icon("SUCCESS") == "\u2713"
    assert icon("NOPE") == "?"
    line = fmt_entry({"name": "a", "title": "T", "status": "SUCCESS",
                      "duration_ms": 12})
    assert "T" in line and "12" in line
    line2 = fmt_entry({"name": "a", "status": "FAILED", "duration_ms": 1,
                       "resumed": True})
    assert "чекпоинт" in line2


def test_review_suppress_needs_reason(tmp_path):
    from forge.quality.review import review
    (tmp_path / "a.py").write_text("# TODO: later\n", encoding="utf-8")
    assert review(tmp_path)["confirmed"] >= 1
    r = review(tmp_path, suppress=[{"rule": "debt-marker", "file": "a.py",
                                    "reason": "test"}])
    assert r["confirmed"] == 0 and r["suppressed"] == 1
    assert r["findings"][0].get("suppressed") is True
    # без причины подавление не действует
    r2 = review(tmp_path, suppress=[{"rule": "debt-marker", "file": "a.py"}])
    assert r2["confirmed"] >= 1 and r2["suppressed"] == 0


def test_review_stage_reads_suppress_file(tmp_path):
    import json as _json
    from forge.pipe.stages import stage_review
    (tmp_path / "a.py").write_text("# TODO: later\n", encoding="utf-8")
    (tmp_path / ".forge-suppress.json").write_text(_json.dumps(
        [{"rule": "debt-marker", "file": "a.py", "reason": "test"}]),
        encoding="utf-8")
    res = stage_review({"target": str(tmp_path), "forge_root": str(tmp_path)})
    assert res.status == "SUCCESS"
