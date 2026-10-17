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


def test_window_clean_code_rows(tmp_path):
    from forge.pipe.window import clean_code_rows
    (tmp_path / "bad.py").write_text(
        "x = 99999\n" * 3 + "def f(a, b, c, d, e):\n    return a\n",
        encoding="utf-8")
    rows = clean_code_rows(str(tmp_path))
    assert rows and "здоровье" in rows[0]
    assert any("too-many-args" in r for r in rows[1:])
    assert clean_code_rows(str(tmp_path / "missing")) != [] or True  # never raises


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


def test_review_ignores_debt_markers_in_strings(tmp_path):
    from forge.quality.review import review
    (tmp_path / "a.py").write_text(
        '"""Doc mentions TODO/FIXME as examples only."""\n'
        'PATTERN = r"\\b(TODO|FIXME|XXX|HACK)\\b"\n'
        'LABEL = "Debt marker (TODO/FIXME/XXX/HACK)"\n'
        '# TODO: real one\n',
        encoding="utf-8")
    r = review(tmp_path)
    got = [f["detail"] for f in r["findings"] if f["rule"] == "debt-marker"]
    assert len(got) == 1 and "real one" in got[0]


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
    assert [s["name"] for s in lst["data"]["stages"]] == ["inspect", "secrets", "review", "skills", "knowledge", "langs", "clean-code", "lab-e2e"]
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


def test_safety_hardening(tmp_path):
    import json as _json
    from forge.cli.__main__ import main
    from forge.pipe.runner import PipeRunner
    from forge.pipe.stages import DEFAULT_STAGES
    # 1. ротация истории: 205 строк -> остаётся 200
    mk = lambda: PipeRunner(list(DEFAULT_STAGES),
                            {"target": str(tmp_path),
                             "forge_root": str(tmp_path)},
                            checkpoint=str(tmp_path / "cp.json"))
    hp = tmp_path / ".forge-pipe-history.jsonl"
    hp.write_text("\n".join([_json.dumps({"ts": 1, "status": "SUCCESS",
                                          "duration_ms": 1, "stages": []})
                              for _ in range(205)]), encoding="utf-8")
    mk().run()
    assert len(hp.read_text(encoding="utf-8").splitlines()) == 200
    # 2. битая строка истории не валит pipe.status
    with open(hp, "a", encoding="utf-8") as f:
        f.write("not-json{{{\n")
    from forge.mcp.server import _pipe_status
    st = _pipe_status(str(tmp_path))
    assert isinstance(st["history"], list)
    # 3. --report в несуществующую вложенность: папки создаются
    deep = tmp_path / "a" / "b" / "rep.json"
    assert main(["pipe", "run", str(tmp_path), "--report", str(deep),
                 "--only", "inspect"]) == 0
    assert deep.is_file()
    # 4. --no-plugins: чужой код не выполняется
    plug = tmp_path / ".forge-stages"
    plug.mkdir()
    (plug / "evil.py").write_text(
        "from forge.pipe.stages import Stage\n"
        "from forge.core.result import ToolResult\n"
        "STAGE = Stage('evil', 'Evil', "
        "lambda c: ToolResult(status='FAILED', error={'message': 'pwned'}))\n",
        encoding="utf-8")
    rep = tmp_path / "r1.json"
    assert main(["pipe", "run", str(tmp_path), "--report", str(rep),
                 "--only", "inspect"]) == 0
    names = [s["name"] for s in
             _json.loads(rep.read_text(encoding="utf-8"))["stages"]]
    assert "evil" not in names  # --only = ровно то, что просили
    rep2 = tmp_path / "r2.json"
    assert main(["pipe", "run", str(tmp_path), "--report", str(rep2),
                 "--no-plugins"]) == 0
    names2 = [s["name"] for s in
              _json.loads(rep2.read_text(encoding="utf-8"))["stages"]]
    assert "evil" not in names2
    rep3 = tmp_path / "r3.json"
    main(["pipe", "run", str(tmp_path), "--report", str(rep3)])
    names3 = [s["name"] for s in
              _json.loads(rep3.read_text(encoding="utf-8"))["stages"]]
    assert "evil" in names3  # а по умолчанию плагин подхватывается


def _mk_tasks(d):
    d.mkdir(exist_ok=True)
    import json as _json
    (d / "t1.json").write_text(_json.dumps({
        "id": "t1", "title": "T1",
        "checks": [{"type": "exists", "path": "ok.txt"}]}), encoding="utf-8")


def test_arena_records_and_renders(tmp_path):
    import json as _json
    from forge.bench import arena as _a
    tasks = tmp_path / "tasks"
    _mk_tasks(tasks)
    cand = tmp_path / "cand"
    cand.mkdir()
    (cand / "ok.txt").write_text("x", encoding="utf-8")
    board = tmp_path / "board.jsonl"
    r1 = _a.record(tasks, cand, "agent-a", board)
    assert r1["passed"] == 1
    r2 = _a.record(tasks, tmp_path / "empty", "agent-b", board)
    assert r2["passed"] == 0
    rows = _a.load_board(board)
    assert len(rows) == 2
    md = _a.render(rows)
    assert "agent-a" in md and "1/1" in md and "agent-b" in md
    # повторный прогон того же агента: в таблице только свежий
    (cand / "ok.txt").unlink()
    _a.record(tasks, cand, "agent-a", board)
    md2 = _a.render(_a.load_board(board))
    assert md2.count("agent-a") == 1 and "0/1" in md2
    # битые строки табло не валят чтение
    with open(board, "a", encoding="utf-8") as f:
        f.write("garbage{{{\n")
    assert len(_a.load_board(board)) == 3


def test_forge_ignore_and_size_cap(tmp_path):
    import importlib
    _r = importlib.import_module("forge.quality.review")
    from forge.quality.review import review
    assert hasattr(_r, "MAX_FILE_BYTES") and hasattr(_r, "IGNORE_MARK")
    (tmp_path / "a.py").write_text(
        "# TODO: real\n# TODO: quiet # forge-ignore\n"
        "# TODO: other # forge-ignore: empty-catch\n", encoding="utf-8")
    r = review(tmp_path)
    got = [f["detail"] for f in r["findings"] if f["rule"] == "debt-marker"]
    assert len(got) == 2 and any("real" in d for d in got)  # 1 тихий, 1 чужое правило
    big = tmp_path / "big.py"
    big.write_bytes(b"# TODO: huge\n" + b"x" * (5 * 1024 * 1024))
    r2 = review(tmp_path)
    assert all("big.py" not in f["file"] for f in r2["findings"])


def test_hold_the_line_git(tmp_path):
    import subprocess as _sp
    from forge.pipe.stages import git_changed, stage_review
    assert git_changed(tmp_path) is None  # не репозиторий
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    import os as _os
    e = dict(_os.environ, **env)
    (tmp_path / "a.py").write_text("# TODO: old\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("x = 1\n", encoding="utf-8")
    _sp.run(["git", "init", "-q"], cwd=tmp_path, env=e, check=True)
    _sp.run(["git", "add", "."], cwd=tmp_path, env=e, check=True)
    _sp.run(["git", "commit", "-qm", "init"], cwd=tmp_path, env=e, check=True)
    with open(tmp_path / "b.py", "a", encoding="utf-8") as f:
        f.write("# TODO: new\n")
    ch = git_changed(tmp_path)
    assert ch == {"b.py"}
    res = stage_review({"target": str(tmp_path), "forge_root": str(tmp_path),
                        "only": ch})
    assert res.status == "FAILED"
    files = {f["file"] for f in res.result["findings"]}
    assert files == {"b.py"}  # старый TODO в a.py не тронут


def test_hub_collect_and_serve(tmp_path):
    import json as _json
    import threading as _th
    import time as _t
    import urllib.request as _url
    from forge.pipe import hub as _hub
    assert _hub.collect_projects(tmp_path / "nope") == []
    (tmp_path / "p1").mkdir()
    (tmp_path / "p1" / ".forge-pipe-history.jsonl").write_text(
        _json.dumps({"ts": 1, "status": "SUCCESS", "duration_ms": 10,
                     "stages": []}) + "\n"
        + _json.dumps({"ts": 2, "status": "FAILED", "duration_ms": 20,
                       "stages": []}) + "\n"
        + "garbage\n", encoding="utf-8")
    (tmp_path / "p2").mkdir()
    rows = _hub.collect_projects(tmp_path)
    assert [(r["project"], r["status"], r["runs"], r["ok_rate"])
            for r in rows] == [("p1", "FAILED", 2, 0.5), ("p2", "—", 0, None)]
    srv = _hub.ThreadingHTTPServer(("127.0.0.1", 0),
                                   type("H", (_hub._Handler,), {}))
    srv.RequestHandlerClass.root = str(tmp_path)
    th = _th.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        base = f"http://127.0.0.1:{srv.server_port}"
        page = _url.urlopen(base + "/", timeout=5).read().decode("utf-8")
        assert "FORGE" in page and "p1" in page
        api = _json.loads(_url.urlopen(base + "/api/projects",
                                       timeout=5).read().decode("utf-8"))
        assert api[0]["project"] == "p1"
    finally:
        srv.shutdown()
        th.join(timeout=5)


def test_evolve_detects_staleness(tmp_path):
    import json as _json
    from forge.evolve.check import check
    from forge.cli.__main__ import main
    # пустая папка, настоящий forge_root: скиллы ок, истории нет
    r = check(str(tmp_path), "D:/Forge-Factority/forge")
    assert isinstance(r["tasks"], list)
    assert all(set(t) == {"area", "priority", "evidence", "suggest"}
               for t in r["tasks"])
    # правило с 3 подавлениями -> задача на калибровку
    (tmp_path / ".forge-suppress.json").write_text(_json.dumps(
        [{"rule": "debt-marker", "file": f"f{i}.py", "reason": "t"}
         for i in range(3)]), encoding="utf-8")
    r2 = check(str(tmp_path), "D:/Forge-Factority/forge")
    assert any(t["area"] == "rules" and "debt-marker" in t["evidence"]
               for t in r2["tasks"])
    # история с 3 падениями стадии -> задача
    (tmp_path / ".forge-pipe-history.jsonl").write_text("\n".join(
        [_json.dumps({"ts": 1, "status": "FAILED", "duration_ms": 1,
                      "stages": [{"name": "review", "status": "FAILED"}]})
         for _ in range(3)]), encoding="utf-8")
    r3 = check(str(tmp_path), "D:/Forge-Factority/forge")
    assert any(t["area"] == "history" and "review" in t["evidence"]
               for t in r3["tasks"])
    assert main(["evolve", str(tmp_path)]) == 0
    from forge.mcp.server import build_default_registry
    reg = build_default_registry("")
    assert "evolve.check" in reg.tool_owner


def test_secrets_stage_high_fails_medium_warns(tmp_path):
    from forge.pipe.stages import stage_secrets
    (tmp_path / "k.py").write_text('x = "AKIAABCDEFGHIJKLMNOP"\n',  # forge:allow-secret
                                   encoding="utf-8")
    r = stage_secrets({"target": str(tmp_path)})
    assert r.status == "FAILED" and r.result["count"] == 1
    (tmp_path / "k.py").write_text('password = "hunter2secret"\n',  # forge:allow-secret
                                   encoding="utf-8")
    r2 = stage_secrets({"target": str(tmp_path)})
    assert r2.status == "SUCCESS" and r2.warnings
    (tmp_path / "k.py").write_text(
        'aws = "AKIAABCDEFGHIJKLMNOP"  # forge:allow-secret\n', encoding="utf-8")
    assert stage_secrets({"target": str(tmp_path)}).status == "SUCCESS"
