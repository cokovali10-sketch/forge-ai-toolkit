"""FORGE CLI: modules | skill <name> | know <query> | mcp."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _registry():
    sys.path.insert(0, str(ROOT / "src"))
    from forge.mcp.server import build_default_registry
    return build_default_registry(str(ROOT.parent.parent / "Anvil")
                                  if (ROOT.parent / "Anvil").is_dir()
                                  else "D:/PortfolioProjects/Anvil")


def _skills():
    sys.path.insert(0, str(ROOT / "src"))
    from forge.skills.loader import load_skills
    return load_skills(ROOT / "skills")


def _knowledge():
    sys.path.insert(0, str(ROOT / "src"))
    from forge.knowledge.store import KnowledgeStore
    ks = KnowledgeStore()
    seed = ROOT / "knowledge" / "seed.jsonl"
    if seed.is_file():
        ks.load_jsonl(seed)
    return ks


def _ui(args: list[str]) -> int:
    sys.path.insert(0, str(ROOT / "src"))
    if not args or args[0] in ("-h", "--help", "help"):
        print("usage: forge ui <brief \"...\"|pack>")
        return 0
    from forge.ui import assets as _a
    from forge.ui import brief as _b
    from forge.ui import strategy as _s
    from forge.ui import system as _sys
    if args[0] == "brief" and len(args) > 1:
        import json as _json
        text = " ".join(args[1:])
        br = _b.from_description(text)
        st = _s.select(br.needs_client_mod, br.needs_resource_pack)
        print(_json.dumps({"style": br.style, "screens": br.screens,
                           "features": br.features, "strategy": st["key"],
                           "strategy_name": st["name"],
                           "needs_client_mod": br.needs_client_mod,
                           "needs_resource_pack": br.needs_resource_pack,
                           "notes": br.notes}, ensure_ascii=False, indent=2))
        return 0
    if args[0] == "pack":
        out = ROOT / "examples" / "mythic-shop" / "resourcepack"
        manifest = _a.build_pack(_sys.preset_mythic(), out)
        _a.pack_mcmeta("Mythic dark-red theme", out)
        import json as _json
        print(_json.dumps({"assets": len(manifest["assets"]), "out": str(out)},
                          ensure_ascii=False))
        return 0
    if args[0] == "iterate":
        import json as _json
        from forge.ui import system as _sys2
        out = ROOT / "examples" / "mythic-shop" / "iteration"
        res = _a.iterate(_sys2.preset_mythic(), out)
        print(_json.dumps(res["best"], ensure_ascii=False))
        return 0
    if args[0] == "import" and len(args) > 2:
        import json as _json
        from forge.ui import system as _sys3
        res = _a.import_graphics(args[1], args[2], _sys3.preset_mythic())
        print(_json.dumps({"accepted": len(res["accepted"]),
                           "rejected": res["rejected"]}, ensure_ascii=False))
        return 0
    print(f"unknown ui command: {args[0]}")
    return 2


def _gen(args: list[str]) -> int:
    sys.path.insert(0, str(ROOT / "src"))
    if not args or args[0] in ("-h", "--help", "help"):
        print("usage: forge gen paper --name X [--package P] [--command C] [--out DIR]")
        return 0
    if args[0] != "paper":
        print(f"unknown generator: {args[0]}")
        return 2
    import json as _json
    opts = {"name": "Demo", "package": "com.forge.demo", "command": "hello",
            "out": str(ROOT / "examples" / "gen-demo")}
    i = 1
    while i < len(args):
        if args[i].startswith("--") and i + 1 < len(args):
            opts[args[i][2:].replace("-", "_")] = args[i + 1]
            i += 2
        else:
            i += 1
    from forge.gen import paper_plugin as _g
    try:
        res = _g.generate(opts["out"], opts["name"], opts["package"], opts["command"])
    except ValueError as e:
        print(f"bad options: {e}")
        return 2
    print(_json.dumps(res, ensure_ascii=False, indent=2))
    return 0


def _config(args: list[str]) -> int:
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    from forge.config.settings import example, load
    if args and args[0] == "example":
        print(example())
        return 0
    if args and args[0] == "init":
        p = ROOT / "forge.toml"
        if p.is_file():
            print(f"exists: {p}")
            return 0
        p.write_text(example(), encoding="utf-8")
        print(f"wrote {p}")
        return 0
    cfg, warnings = load()
    print(_json.dumps({"config": cfg, "warnings": warnings},
                      ensure_ascii=False, indent=2))
    return 0


def _fix(args: list[str]) -> int:
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    from forge.fix import loop as _fx
    if not args or args[0] in ("-h", "--help", "help"):
        print("usage: forge fix <checkpoint|diff|rollback|cycle> --project DIR [-- cmd...]")
        return 0
    sub, rest = args[0], args[1:]
    proj = "."
    cmd: list[str] = []
    if "--project" in rest:
        i = rest.index("--project")
        if i + 1 < len(rest):
            proj = rest[i + 1]
    if "--" in rest:
        cmd = rest[rest.index("--") + 1:]
    if sub == "checkpoint":
        print(_json.dumps(_fx.checkpoint(proj), ensure_ascii=False, indent=2))
        return 0
    if sub == "diff":
        print(_json.dumps(_fx.diff(proj), ensure_ascii=False, indent=2))
        return 0
    if sub == "rollback":
        r = _fx.rollback(proj)
        print(_json.dumps(r, ensure_ascii=False, indent=2))
        return 0 if r["ok"] else 1
    if sub == "cycle":
        if not cmd:
            print("usage: forge fix cycle --project DIR -- <check-cmd...>")
            return 2
        r = _fx.cycle(proj, cmd)
        print(_json.dumps({k: v for k, v in r.items()},
                          ensure_ascii=False, indent=2)[:3000])
        return 0 if r["ok"] else 1
    print(f"unknown fix command: {sub}")
    return 2


def _bench(args: list[str]) -> int:
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    from forge.bench.runner import load_task, run_suite, run_task
    from pathlib import Path as _P
    tasks = ROOT / "benchmarks" / "tasks"
    if not args or args[0] in ("-h", "--help", "help", "list"):
        for f in sorted(tasks.glob("*.json")):
            t = load_task(f)
            print(f"{t.get('id')}: {t.get('title')} ({len(t.get('checks', []))} checks)")
        return 0
    if args[0] == "run" and len(args) > 2:
        agent = "manual"
        rest = list(args[1:])
        if rest and rest[0].startswith("--agent="):
            agent = rest.pop(0).split("=", 1)[1]
        if len(rest) != 2:
            print("usage: forge bench run [--agent=X] <task|all> <candidate-dir>")
            return 2
        task_id, candidate = rest
        if task_id in ("all", "*"):
            res = run_suite(tasks, candidate, agent)
        else:
            r = run_task(load_task(tasks / f"{task_id}.json"), candidate, agent)
            res = {"agent": agent, "total": 1, "passed": 1 if r.passed else 0,
                   "failed": 0 if r.passed else 1, "results": [task_id]}
        print(_json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res["failed"] == 0 else 1
    print("usage: forge bench [list|run [--agent=X] <task|all> <candidate-dir>]")
    return 2


def _docs(args: list[str]) -> int:
    """Regenerate docs/tools.md + docs/modules.md from live registry."""
    sys.path.insert(0, str(ROOT / "src"))
    from forge.mcp.server import build_default_registry
    from forge.modules.manifest import load_packs
    reg = build_default_registry(_anvil_dir())
    lines = ["# Tool Catalog (generated — do not edit by hand)", "",
             f"SOURCE_OF_TRUTH = registry ({len(reg.tool_owner)} tools)", ""]
    for name in sorted(reg.tool_owner):
        back = reg.backends.get(reg.tool_owner[name])
        desc, schema = "?", {}
        if back is not None and hasattr(back, "schema_of"):
            try:
                schema, desc = back.schema_of(name)
            except Exception:
                pass
        mod = reg.tool_module.get(name, "?")
        lvl = reg.level_of(name)
        lines.append(f"## {name}")
        lines.append(f"- module: {mod}, backend: {reg.tool_owner[name]}, level: {lvl}")
        lines.append(f"- {desc}")
        lines.append("")
    (ROOT / "docs" / "tools.md").write_text("\n".join(lines), encoding="utf-8")
    packs = load_packs(ROOT / "module-packs")
    ml = ["# Module Catalog (generated)", ""]
    for mid in sorted(packs):
        m = packs[mid]
        ml.append(f"## {m.id} v{m.version} — {m.name}")
        ml.append(f"- {m.description}")
        ml.append(f"- capabilities: {', '.join(m.capabilities)}")
        ml.append(f"- tools: {', '.join(m.tools)}")
        ml.append("")
    (ROOT / "docs" / "modules.md").write_text("\n".join(ml), encoding="utf-8")
    print(f"wrote docs/tools.md ({len(reg.tool_owner)} tools), "
          f"docs/modules.md ({len(packs)} packs)")
    return 0


def _lab(args: list[str]) -> int:
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    if not args or args[0] in ("-h", "--help", "help"):
        print("usage: forge lab <detect <project>|e2e|mirror --jar F --deps A,B "
              "--fuzz c1,c2 --config-rel P --marker M [--load]>")
        return 0
    if args[0] == "detect" and len(args) > 1:
        from forge.lab import build as _b
        print(_b.detect(args[1]))
        return 0
    if args[0] == "e2e":
        import os as _os
        from forge.lab import runner as _r
        res = _r.e2e_fixture(
            ROOT / "lab-runs",
            "D:/Forge-Factority/lab-servers/purpur-1.21.11.jar",
            ROOT / "tests" / "fixture-plugin" / "src",
            java_bin=_java21())
        return _show(res)
    if args[0] == "mirror":
        import os as _os
        from forge.lab import runner as _r
        o = _kv(args[1:])
        deps = [d for d in o.get("deps", "").split(",") if d]
        fuzz = [c for c in o.get("fuzz", "").split(",") if c]
        ign = [s for s in o.get("ignore", "[Essentials],Essentials v,Nag author,plugin classloader for Essentials").split(",") if s]
        bad = ["", ":\t:\nnot yaml at all",
               "economy:\n  tax-percent: -50\n  min-price: banana\n"]
        res = _r.mirror(
            ROOT / "lab-runs", "D:/Forge-Factority/lab-servers/purpur-1.21.11.jar",
            o.get("jar", ""), java_bin=_java21(), extra_jars=deps,
            ignore_errors=ign, fuzz_commands=fuzz or None,
            config_rel=o.get("config-rel", ""), bad_configs=bad,
            enable_marker=o.get("marker", ""),
            with_load=o.get("load", "0") == "1")
        return _show(res)
    print(f"unknown lab command: {args[0]}")
    return 2


def _java21() -> str:
    import os as _os
    cands = [_os.environ.get("FORGE_JAVA21", ""),
             r"C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot\bin\java.exe"]
    return next((c for c in cands if c and Path(c).is_file()), "")


def _kv(args: list[str]) -> dict:
    out: dict = {}
    i = 0
    while i < len(args):
        if args[i].startswith("--") and i + 1 < len(args):
            out[args[i][2:]] = args[i + 1]
            i += 2
        else:
            i += 1
    return out


def _show(res: dict) -> int:
    import json as _json
    print(_json.dumps({k: v for k, v in res.items() if k != "checks"},
                      ensure_ascii=False, indent=2))
    for c in res.get("checks", []):
        print(("PASS " if c["ok"] else "FAIL ") + c["stage"])
    return 0 if res["ok"] else 1
    print(f"unknown lab command: {args[0]}")
    return 2


def _anvil_dir() -> str:
    cand = ROOT.parent / "Anvil"
    if cand.is_dir():
        return str(cand)
    if Path("D:/PortfolioProjects/Anvil").is_dir():
        return "D:/PortfolioProjects/Anvil"
    return ""


def _anvil_tool_names() -> list[str]:
    import subprocess
    d = _anvil_dir()
    if not d:
        return []
    try:
        out = subprocess.run(
            [sys.executable, "-m", "anvil", "list"], capture_output=True,
            text=True, timeout=60, cwd=d)
        names = []
        for line in (out.stdout or "").splitlines():
            if " - " in line:
                names.append(line.split(" - ", 1)[0].strip().split(".")[-1])
        return sorted(set(names))
    except Exception:
        return []


def _call_any(tool: str, params: dict):
    reg = _registry()
    res = reg.call(tool, params)
    if res.get("ok") or "unknown tool" not in str(res.get("error", "")):
        return res
    if tool.startswith("hermes."):
        from forge.bridges.hermes import HermesBackend
        return HermesBackend().call(tool, params)
    from forge.core.registry import AnvilBackend
    d = _anvil_dir()
    if not d:
        return res
    return AnvilBackend(d).call(tool, params)


def _pipe(args: list[str]) -> int:
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    if not args or args[0] in ("-h", "--help", "help") or args[0] not in ("run", "window", "watch"):
        print("usage: forge pipe run <dir> [--json] [--resume] [--report PATH] [--only inspect,review] [--heavy]")
        print("       forge pipe window [dir] [--resume]  (окно: только быстрые стадии)")
        print("       forge pipe watch <dir> [--only ...] [--interval S]")
        print("run = headless для ИИ (окна нет), window = окно для человека,")
        print("watch = слежка: перезапуск при изменении файлов")
        return 0 if args and args[0] in ("-h", "--help", "help") else 2
    from forge.pipe.runner import PipeRunner, exit_code
    from forge.pipe.stages import ALL_STAGES, DEFAULT_STAGES, HEAVY_STAGES
    mode = args[0]
    rest = args[1:]
    target = next((a for a in rest if not a.startswith("--")), ".")
    resume = "--resume" in rest
    heavy = "--heavy" in rest
    only = ""
    interval = 2.0
    for i, a in enumerate(rest):
        if a == "--only" and i + 1 < len(rest):
            only = rest[i + 1]
        if a == "--interval" and i + 1 < len(rest):
            try:
                interval = max(0.5, float(rest[i + 1]))
            except ValueError:
                pass

    def _select() -> list:
        if not only:
            return list(DEFAULT_STAGES) + (list(HEAVY_STAGES) if heavy else [])
        want = {s.strip() for s in only.split(",") if s.strip()}
        stages = [s for s in ALL_STAGES.values() if s.name in want]
        if not stages:
            print(f"unknown stages: {only} (есть: "
                  + ",".join(ALL_STAGES) + ")")
            raise SystemExit(2)
        return stages

    if mode == "window":
        from forge.pipe.window import main as _win
        return _win(target, str(ROOT), resume)
    if mode == "watch":
        from forge.pipe.watch import Watcher
        import time as _t
        try:
            stages = _select()
        except SystemExit as e:
            return int(e.code or 2)

        def _once(reason: str = "старт") -> None:
            runner = PipeRunner(stages, {"target": target, "forge_root": str(ROOT)},
                                checkpoint=str(Path(target) / "forge-pipe-checkpoint.json"))
            rep = runner.run(resume=False)
            print(f"[{reason}] {rep.status} за {rep.duration_ms}мс: "
                  + ", ".join(f"{s['name']}={s.get('status')}" for s in rep.to_dict()["stages"]))

        _once()
        print(f"слежу за {target} каждые {interval}с (Ctrl+C — стоп)")
        watcher = Watcher(target, lambda files: _once(f"изменено: {len(files)} ф."), interval_s=interval)
        watcher.start()
        try:
            while True:
                _t.sleep(1)
        except KeyboardInterrupt:
            watcher.stop()
            print("слежка остановлена")
            return 0
    # headless run: окна нет никогда, только stdout + exit code
    as_json = "--json" in rest
    rep_path = None
    for i, a in enumerate(rest):
        if a == "--report" and i + 1 < len(rest):
            rep_path = rest[i + 1]
    try:
        stages = _select()
    except SystemExit as e:
        return int(e.code or 2)
    runner = PipeRunner(stages, {"target": target, "forge_root": str(ROOT)},
                        checkpoint=str(Path(target) / "forge-pipe-checkpoint.json"))
    report = runner.run(resume=resume)
    out = report.to_dict()
    if rep_path:
        Path(rep_path).write_text(_json.dumps(out, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
    if as_json:
        print(_json.dumps(out, ensure_ascii=False))
    else:
        print(f"конвейер {target}: {report.status} за {report.duration_ms}мс")
        for s in out["stages"]:
            mark = "OK " if s.get("status") == "SUCCESS" else "FAIL"
            extra = " (чекпоинт)" if s.get("resumed") else ""
            extra = " (кэш)" if s.get("cached") else extra
            print(f"  {mark} {s.get('title', s['name'])} — {s.get('duration_ms', 0)}мс{extra}")
    return exit_code(report)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print("usage: forge <modules|skill <name>|know <query>|mcp>")
        return 0
    cmd = args[0]
    if cmd == "modules":
        reg = _registry()
        for m in reg.list_modules():
            print(f"{m.name} v{m.version} - {m.description}")
        return 0
    if cmd == "skill":
        skills = _skills()
        name = args[1] if len(args) > 1 else ""
        if name in skills:
            s = skills[name]
            print(f"# {s.title} (v{s.version}, {s.domain})\n\n{s.body[:2000]}")
            return 0
        print("available: " + ", ".join(sorted(skills)) if skills else "no skills")
        return 1 if name else 0
    if cmd == "skills":
        from forge.skills.loader import validate_skill
        skills = _skills()
        sub = args[1] if len(args) > 1 else "list"
        if sub == "list":
            for name in sorted(skills):
                s = skills[name]
                print(f"{name} v{s.version} [{s.domain}] - {s.title}")
            return 0
        if sub == "validate":
            bad = 0
            for name in sorted(skills):
                errs = validate_skill(skills[name])
                if errs:
                    bad += 1
                    print(f"{name}: FAIL: {'; '.join(errs)}")
                else:
                    print(f"{name}: OK")
            return 1 if bad else 0
        print("usage: forge skills [list|validate]")
        return 2
    if cmd == "know":
        ks = _knowledge()
        for r in ks.search(" ".join(args[1:]), limit=5):
            print(f"[{r['domain']}] {r['title']}\n{r['body'][:400]}\n")
        return 0
    if cmd == "route":
        sys.path.insert(0, str(ROOT / "src"))
        from forge.modules.manifest import load_packs, route
        packs = load_packs(ROOT / "module-packs")
        for mid, reasons in route(" ".join(args[1:]), packs):
            print(f"{mid}: {'; '.join(reasons)}")
        return 0
    if cmd == "inspect":
        if len(args) < 2:
            print("usage: forge inspect <project-dir>")
            return 2
        reg = _registry()
        import json as _json
        print(_json.dumps(reg.call("project.inspect", {"root": args[1]}),
                          ensure_ascii=False, indent=2))
        return 0
    if cmd == "lab":
        return _lab(args[1:])
    if cmd == "pipe":
        return _pipe(args[1:])
    if cmd == "docs":
        return _docs(args[1:])
    if cmd == "bench":
        return _bench(args[1:])
    if cmd == "config":
        return _config(args[1:])
    if cmd == "fix":
        return _fix(args[1:])
    if cmd == "gen":
        return _gen(args[1:])
    if cmd == "ui":
        return _ui(args[1:])
    if cmd == "mcp":
        sys.path.insert(0, str(ROOT / "src"))
        from forge.mcp.server import McpServer, build_default_registry
        McpServer(build_default_registry("D:/PortfolioProjects/Anvil")).serve()
        return 0
    if cmd == "tools":
        reg = _registry()
        names = sorted(reg.tool_owner)
        print(f"registry: {len(names)} tools")
        for n in names:
            print(f"  {n} [{reg.tool_owner[n]}]")
        for extra in _anvil_tool_names():
            if extra not in names:
                print(f"  {extra} [anvil]")
        return 0
    if cmd == "call":
        if len(args) < 2:
            print("usage: forge call <tool> [json-params]")
            return 2
        import json as _json
        tool = args[1]
        raw = args[2] if len(args) > 2 else "{}"
        try:
            params = _json.loads(raw) if not raw.startswith("@") else _json.loads(
                open(raw[1:], encoding="utf-8").read())
        except Exception as e:
            print(f"bad params: {e}")
            return 2
        print(_json.dumps(_call_any(tool, params), ensure_ascii=False, indent=2))
        return 0
    print(f"unknown command: {cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
