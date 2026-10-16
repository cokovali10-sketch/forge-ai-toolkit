"""Tests for the forge pipe conveyor (headless-safe: no window is created)."""
import json
import time
from pathlib import Path

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
    assert [s["name"] for s in r.stages] == ["a", "x", "b"]  # параллельно: все добегают
    assert r.stages[1]["status"] == "ERROR"
    r2 = _mk(stages, tmp_path).run(serial=True)
    assert [s["name"] for s in r2.stages] == ["a", "x"]  # serial: стоп на первой упавшей


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


def test_run_appends_history(tmp_path):
    r = _mk([Stage("a", "A", _ok_fn)], tmp_path).run()
    assert r.status == "SUCCESS"
    hist = tmp_path / ".forge-pipe-history.jsonl"
    assert hist.is_file()
    row = json.loads(hist.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert row["status"] == "SUCCESS" and row["stages"][0]["name"] == "a"


def test_mcp_pipe_tools(tmp_path):
    from forge.mcp.server import build_default_registry
    reg = build_default_registry("")
    names = sorted(reg.tool_owner)
    assert "pipe.stages" in names and "pipe.run" in names and "pipe.status" in names
    lst = reg.call("pipe.stages", {})
    assert [s["name"] for s in lst["data"]["stages"]] == ["inspect", "review", "skills", "knowledge", "lab-e2e"]
    rep = reg.call("pipe.run", {"root": str(tmp_path), "only": "inspect"})
    assert rep["data"]["status"] == "SUCCESS"
    assert [s["name"] for s in rep["data"]["stages"]] == ["inspect"]
    st = reg.call("pipe.status", {"root": str(tmp_path)})
    assert isinstance(st["data"]["history"], list) and len(st["data"]["history"]) >= 1


def test_watch_snapshot_and_changed(tmp_path):
    from forge.pipe.watch import changed, snapshot
    (tmp_path / "a.py").write_text("x=1\n", encoding="utf-8")
    (tmp_path / "forge-pipe-checkpoint.json").write_text("{}", encoding="utf-8")
    s1 = snapshot(tmp_path)
    assert "a.py" in s1 and "forge-pipe-checkpoint.json" not in s1
    (tmp_path / "a.py").write_text("x=2\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("y=1\n", encoding="utf-8")
    s2 = snapshot(tmp_path)
    assert changed(s1, s2) == ["a.py", "b.py"]
    assert changed(s2, s2) == []


def test_watcher_fires_and_stops(tmp_path):
    import time as _t
    from forge.pipe.watch import Watcher
    hits: list = []
    w = Watcher(str(tmp_path), hits.append, interval_s=0.1, debounce_s=0.1)
    w.start()
    assert w.running
    _t.sleep(0.3)  # дать вотчеру снять начальный снапшот пустой папки
    (tmp_path / "a.py").write_text("x=1\n", encoding="utf-8")
    deadline = _t.time() + 5
    while not hits and _t.time() < deadline:
        _t.sleep(0.1)
    w.stop()
    assert hits and hits[0] == ["a.py"]
    assert not w.running


def test_tree_hash_stable_and_sensitive(tmp_path):
    from forge.pipe.stages import tree_hash
    (tmp_path / "a.py").write_text("x=1\n", encoding="utf-8")
    h1 = tree_hash(tmp_path)
    assert tree_hash(tmp_path) == h1
    (tmp_path / "a.py").write_text("x=2\n", encoding="utf-8")
    assert tree_hash(tmp_path) != h1
    # артефакты конвейера на хэш не влияют
    (tmp_path / "forge-pipe-checkpoint.json").write_text("{}", encoding="utf-8")
    h2 = tree_hash(tmp_path)
    (tmp_path / "forge-pipe-checkpoint.json").write_text("{\"x\": 1}", encoding="utf-8")
    assert tree_hash(tmp_path) == h2


def test_incremental_skips_unchanged(tmp_path):
    from forge.pipe.stages import tree_hash
    calls: list = []

    def _counted(_ctx):
        calls.append(1)
        return ToolResult(status="SUCCESS", result={})

    fp = lambda c: tree_hash(c["target"], {".py"})  # noqa: E731
    mk = lambda: _mk([Stage("a", "A", _counted, fingerprint=fp)], tmp_path)
    (tmp_path / "a.py").write_text("x=1\n", encoding="utf-8")
    r1 = mk().run()
    assert r1.status == "SUCCESS" and calls == [1]
    r2 = mk().run()  # без resume, но входы те же
    assert calls == [1]
    assert r2.stages[0].get("cached") is True
    (tmp_path / "a.py").write_text("x=2\n", encoding="utf-8")
    r3 = mk().run()
    assert calls == [1, 1] and not r3.stages[0].get("cached")


def test_incremental_ext_filter(tmp_path):
    from forge.pipe.stages import tree_hash
    calls: list = []

    def _counted(_ctx):
        calls.append(1)
        return ToolResult(status="SUCCESS", result={})

    fp = lambda c: tree_hash(c["target"], {".py"})  # noqa: E731
    mk = lambda: _mk([Stage("a", "A", _counted, fingerprint=fp)], tmp_path)
    (tmp_path / "a.py").write_text("x=1\n", encoding="utf-8")
    mk().run()
    (tmp_path / "pic.png").write_bytes(b"\x89PNG")
    r = mk().run()  # .png вне фильтра — кэш жив
    assert calls == [1] and r.stages[0].get("cached") is True


def test_heavy_stage_listed_and_gated(tmp_path):
    from forge.mcp.server import build_default_registry
    from forge.pipe.stages import HEAVY_STAGES, stage_lab_e2e
    assert [s.name for s in HEAVY_STAGES] == ["lab-e2e"]
    assert HEAVY_STAGES[0].timeout_s >= 900
    reg = build_default_registry("")
    names = [s["name"] for s in
             reg.call("pipe.stages", {})["data"]["stages"]]
    assert "lab-e2e" in names
    heavy = [s for s in reg.call("pipe.stages", {})["data"]["stages"]
             if s["name"] == "lab-e2e"][0]
    assert heavy["heavy"] is True
    # без окружения (чужой forge_root) — быстрый честный ERROR, не вис
    res = stage_lab_e2e({"target": str(tmp_path),
                         "forge_root": str(tmp_path)})
    assert res.status == "ERROR" and "env not ready" in str(res.error)


def _sleepy(sec=0.4):
    def _fn(_ctx):
        import time as _t
        _t.sleep(sec)
        return ToolResult(status="SUCCESS", result={})
    return _fn


def test_parallel_batch(tmp_path):
    import time as _t
    mk = lambda ss: _mk([Stage(n, n.upper(), _sleepy()) for n in ss], tmp_path)
    t0 = _t.time()
    r = mk(["a", "b", "c"]).run()
    wall = _t.time() - t0
    assert r.status == "SUCCESS"
    assert [s["name"] for s in r.stages] == ["a", "b", "c"]  # порядок объявлений
    assert wall < 1.0, f"not parallel: {wall:.2f}s"
    t0 = _t.time()
    r2 = mk(["a", "b", "c"]).run(serial=True)
    assert _t.time() - t0 > 1.1
    assert r2.status == "SUCCESS"


def test_parallel_failure_and_heavy_skip(tmp_path):
    stages = [Stage("a", "A", _ok_fn), Stage("x", "X", _boom_fn),
              Stage("h", "H", _ok_fn, heavy=True, timeout_s=5)]
    r = _mk(stages, tmp_path).run()
    assert r.status == "FAILED"
    got = {s["name"]: s["status"] for s in r.stages}
    assert got == {"a": "SUCCESS", "x": "ERROR", "h": "SKIPPED"}
    # serial: стоп на упавшей, тяжёлая помечена пропущенной
    r2 = _mk(stages, tmp_path).run(serial=True)
    got2 = {s["name"]: s["status"] for s in r2.stages}
    assert got2 == {"a": "SUCCESS", "x": "ERROR", "h": "SKIPPED"}


def test_history_rows_and_marks(tmp_path):
    import json as _json
    from forge.pipe.window import fmt_entry, icon, load_history_rows
    assert load_history_rows(str(tmp_path)) == []
    assert icon("SKIPPED") != "?"
    assert "(кэш)" in fmt_entry({"name": "a", "title": "T",
                                 "status": "SUCCESS", "duration_ms": 3,
                                 "cached": True})
    (tmp_path / ".forge-pipe-history.jsonl").write_text(
        _json.dumps({"ts": 1700000000, "status": "SUCCESS",
                     "duration_ms": 500,
                     "stages": [{"name": "a", "status": "SUCCESS"},
                                {"name": "b", "status": "FAILED"}]})
        + "\nbad-line\n", encoding="utf-8")
    rows = load_history_rows(str(tmp_path))
    assert len(rows) == 1 and "SUCCESS" in rows[0] and "1/2" in rows[0]


def test_heal_success_no_repair(tmp_path):
    from forge.pipe.heal import heal
    r = heal(str(tmp_path), str(tmp_path))
    assert r["report"]["status"] == "SUCCESS"
    assert r["needed"] is False and r["safety_net"] is True


def test_heal_failed_bundles(tmp_path):
    from forge.pipe.heal import heal
    (tmp_path / "a.py").write_text("# TODO: later\n", encoding="utf-8")
    r = heal(str(tmp_path), str(tmp_path))
    assert r["needed"] is True and r["report"]["status"] == "FAILED"
    assert r["bundles"] and r["bundles"][0]["stage"] == "review"
    assert r["bundles"][0]["files"] == ["a.py"]
    assert Path(r["bundles_file"]).is_file()


def test_stage_plugins(tmp_path):
    from forge.core.result import ToolResult
    from forge.pipe.plugins import load_plugins
    d = tmp_path / ".forge-stages"
    d.mkdir()
    (d / "good.py").write_text(
        "from forge.pipe.stages import Stage\n"
        "from forge.core.result import ToolResult\n"
        "STAGE = Stage('plug', 'Plug', "
        "lambda c: ToolResult(status='SUCCESS', result={}))\n",
        encoding="utf-8")
    (d / "broken.py").write_text("raise Boom\n", encoding="utf-8")
    (d / "empty.py").write_text("X = 1\n", encoding="utf-8")
    (d / "_priv.py").write_text("STAGE = 1\n", encoding="utf-8")
    stages, skipped = load_plugins(tmp_path)
    assert [s.name for s in stages] == ["plug"]
    assert set(skipped) == {"broken.py", "empty.py"}


def test_sarif_mapping():
    from forge.pipe.sarif import report_to_sarif
    rep = {"stages": [{"name": "review", "data": {"findings": [
        {"rule": "debt-marker", "level": "confirmed",
         "file": "a.py", "detail": "L5: # TODO x"},
        {"rule": "oversized-file", "level": "probable",
         "file": "b.py", "detail": "900 lines"},
        {"rule": "debt-marker", "level": "confirmed", "suppressed": True,
         "file": "c.py", "detail": "L1: x"},
    ]}}]}
    s = report_to_sarif(rep, ".")
    assert s["version"] == "2.1.0"
    res = s["runs"][0]["results"]
    assert len(res) == 2  # подавленная не попадает
    assert res[0]["level"] == "error" and res[0]["locations"][0][
        "physicalLocation"]["region"]["startLine"] == 5
    rules = {r["id"] for r in s["runs"][0]["tool"]["driver"]["rules"]}
    assert rules == {"forge/debt-marker", "forge/oversized-file"}


def test_init_ci_and_all(tmp_path):
    from forge.cli.__main__ import main
    assert main(["pipe", "init-ci", str(tmp_path)]) == 0
    wf = tmp_path / ".github" / "workflows" / "forge.yml"
    assert wf.is_file() and "upload-sarif" in wf.read_text(encoding="utf-8")
    (tmp_path / "p1").mkdir()
    (tmp_path / "p2").mkdir()
    (tmp_path / "p2" / "a.py").write_text("# TODO: x\n", encoding="utf-8")
    assert main(["pipe", "all", str(tmp_path), "--clean"]) == 1
    assert not (tmp_path / "p1" / "forge-pipe-checkpoint.json").exists()


def test_suppress_invalidates_cache(tmp_path):
    from forge.pipe.stages import DEFAULT_STAGES
    rev = next(s for s in DEFAULT_STAGES if s.name == "review")
    mk = lambda: _mk([rev], tmp_path)
    (tmp_path / "a.py").write_text("# TODO: later\n", encoding="utf-8")
    r1 = mk().run()
    assert r1.status == "FAILED" and not r1.stages[0].get("cached")
    (tmp_path / ".forge-suppress.json").write_text(
        "[{\"rule\": \"debt-marker\", \"file\": \"a.py\", "
        "\"reason\": \"test\"}]", encoding="utf-8")
    r2 = mk().run()
    assert r2.status == "SUCCESS" and not r2.stages[0].get("cached")


def test_cached_failure_still_fails(tmp_path):
    calls: list = []

    def _flaky(_ctx):
        calls.append(1)
        from forge.core.result import ToolResult
        return ToolResult(status="FAILED", error={"message": "x"})

    st = Stage("f", "F", _flaky, fingerprint=lambda c: "const")
    assert _mk([st], tmp_path).run().status == "FAILED"
    r2 = _mk([st], tmp_path).run()
    assert calls == [1]  # второй раз из кэша
    assert r2.stages[0].get("cached") is True
    assert r2.status == "FAILED"  # но статус честный
