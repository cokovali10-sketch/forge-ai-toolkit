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
    for fn in ("seed.jsonl", "mined.jsonl"):
        seed = ROOT / "knowledge" / fn
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
    if args[0] in ("arena", "board"):
        from forge.bench import arena as _a
        board = ROOT / "benchmarks" / "scoreboard.jsonl"
        if args[0] == "board":
            print(_a.render(_a.load_board(board)))
            return 0
        # arena <candidate> --agent NAME
        o = _kv(args[1:])
        cand = ""
        skip_next = False
        for a in args[1:]:
            if skip_next:
                skip_next = False
                continue
            if a.startswith("--"):
                skip_next = True
                continue
            if not cand:
                cand = a
        agent = o.get("agent", "manual")
        if not cand:
            print("usage: forge bench arena <candidate-dir> --agent NAME")
            return 2
        row = _a.record(tasks, cand, agent, board)
        print(_a.render(_a.load_board(board)))
        md = ROOT / "benchmarks" / "SCOREBOARD.md"
        md.write_text(_a.render(_a.load_board(board)), encoding="utf-8")
        print(f"табло: {board}, витрина: {md}")
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


_CI_WORKFLOW = """name: forge-pipe
on: [push, pull_request]
jobs:
  pipe:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: pip install -e ./forge
      - run: python -m pytest forge/tests -q
      - run: python -m forge.cli pipe run forge --sarif forge.sarif
      - uses: github/codeql-action/upload-sarif@v3
        if: always()
        with: {sarif_file: forge.sarif}
"""


def _know_mine(args: list[str]) -> int:
    """forge know mine <dir> [--apply]: превью найденного, --apply пишет в mined.jsonl."""
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    from forge.knowledge.mine import load_titles, mine_repo
    target = next((a for a in args if not a.startswith("--")), ".")
    entries = mine_repo(target)
    if not entries:
        print("фактов не найдено (пусто или нет манифестов) — ничего не выдумываю")
        return 0
    for e in entries:
        print(f"[{e['domain']}] {e['title']}\n  {e['body'][:200]}\n")
    if "--apply" not in args:
        print(f"превью: {len(entries)} записей. Добавь --apply чтобы записать.")
        return 0
    mp = ROOT / "knowledge" / "mined.jsonl"
    have = load_titles(ROOT / "knowledge" / "seed.jsonl") | load_titles(mp)
    fresh = [e for e in entries if (e["domain"], e["title"]) not in have]
    with open(mp, "a", encoding="utf-8") as f:
        for e in fresh:
            f.write(_json.dumps(e, ensure_ascii=False) + "\n")
    print(f"записано новых: {len(fresh)} из {len(entries)} (-> knowledge/mined.jsonl)")
    return 0


def _lang(args: list[str]) -> int:
    """forge lang detect <dir> | lint|test <id> [dir] | scaffold <id> <name> <out>."""
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    from forge.langs import LANGS
    if not args or args[0] in ("-h", "--help", "help"):
        print("usage: forge lang detect [dir]")
        print("       forge lang lint|test <python|javascript|rust|cpp|go> [dir]")
        print("       forge lang scaffold <id> <name> <out-dir>")
        return 0
    cmd = args[0]
    if cmd == "detect":
        target = args[1] if len(args) > 1 else "."
        print(_json.dumps({lid: mod.detect(target) for lid, mod in LANGS.items()
                           if mod.detect(target).get("present")},
                          ensure_ascii=False, indent=2))
        return 0
    if cmd in ("lint", "test"):
        if len(args) < 2 or args[1] not in LANGS:
            print(f"unknown language (есть: {','.join(LANGS)})")
            return 2
        target = args[2] if len(args) > 2 else "."
        res = getattr(LANGS[args[1]], cmd)(target)
        print(_json.dumps(res.envelope(), ensure_ascii=False, indent=2))
        return 0 if res.status == "SUCCESS" else 1
    if cmd == "scaffold":
        if len(args) < 4 or args[1] not in LANGS:
            print("usage: forge lang scaffold <id> <name> <out-dir>")
            return 2
        print(_json.dumps(LANGS[args[1]].scaffold(args[2], args[3]),
                          ensure_ascii=False, indent=2))
        return 0
    print(f"unknown lang command: {cmd}")
    return 2


def _edit(args: list[str]) -> int:
    """forge edit inspect|get|set|validate|rollback — JSON свой, YAML через Anvil."""
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    from forge.edit import api as _api
    if not args or args[0] in ("-h", "--help", "help"):
        print("usage: forge edit inspect <file>")
        print("       forge edit get <file> <dotted.path>")
        print("       forge edit set <file> <dotted.path> <value-json> [--dry] [--schema NAME|PATH]")
        print("       forge edit validate <file> --schema NAME|PATH")
        print("       forge edit rollback <file>")
        return 0
    cmd, rest = args[0], args[1:]
    try:
        if cmd == "inspect" and len(rest) >= 1:
            out = _api.inspect(rest[0])
        elif cmd == "get" and len(rest) >= 2:
            out = _api.get(rest[0], rest[1])
        elif cmd == "set" and len(rest) >= 3:
            out = _api.set(rest[0], rest[1], rest[2], "--dry" in rest,
                           _flag(rest, "--schema"))
        elif cmd == "validate" and len(rest) >= 1:
            out = _api.validate(rest[0], _flag(rest, "--schema"))
        elif cmd == "rollback" and len(rest) >= 1:
            out = _api.rollback(rest[0])
        else:
            print(f"usage: forge edit ... (неверные аргументы: {cmd})")
            return 2
    except Exception as e:  # noqa: BLE001 - CLI не падает с трейсом
        print(f"ошибка: {type(e).__name__}: {e}")
        return 1
    print(_json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("ok", True) and "error" not in out else 1


def _flag(args: list[str], name: str) -> str:
    for i, a in enumerate(args):
        if a == name and i + 1 < len(args):
            return args[i + 1]
    return ""


def _pipe(args: list[str]) -> int:
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    if not args or args[0] in ("-h", "--help", "help") or args[0] not in ("run", "window", "watch", "heal", "init-ci", "all", "hub"):
        print("usage: forge pipe run <dir> [--json] [--resume] [--report PATH] [--only inspect,review] [--heavy] [--serial] [--sarif PATH] [--no-plugins] [--changed]")
        print("       run = быстрые параллельно (--serial = строго по очереди)")
        print("       run = быстрые параллельно (--serial = строго по очереди)")
        print("       forge pipe window [dir] [--resume]  (окно: только быстрые стадии)")
        print("       forge pipe watch <dir> [--only ...] [--interval S]")
        print("       forge pipe heal <dir> [--json] [--serial]")
        print("       forge pipe hub <dir> [--port 8099] [--open]  (дашборд, только чтение)")
        print("       forge pipe init-ci [dir]  (workflow + SARIF + бейдж)")
        print("       forge pipe all <dir> [--json] [--clean]  (все подпроекты разом)")
        print("run = headless для ИИ (окна нет), window = окно для человека,")
        print("watch = слежка, heal = страховка + прогон + пакеты ремонта")
        print("--changed = hold-the-line: ревью только изменённых файлов (git)")
        return 0 if args and args[0] in ("-h", "--help", "help") else 2
    from forge.pipe.runner import PipeRunner, exit_code
    from forge.pipe.stages import ALL_STAGES, DEFAULT_STAGES, HEAVY_STAGES, git_changed
    mode = args[0]
    rest = args[1:]
    target = next((a for a in rest if not a.startswith("--")), ".")
    resume = "--resume" in rest
    heavy = "--heavy" in rest
    serial = "--serial" in rest
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

    def _safe_write(path: str, text: str) -> bool:
        """Запись отчёта: создаёт папки, не роняет конвейер при ошибке."""
        try:
            p = Path(path)
            if p.parent and str(p.parent) not in (".", ""):
                p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
            return True
        except OSError as e:
            print(f"не записал {path}: {e}")
            return False

    def _with_plugins(stages: list) -> list:
        from forge.pipe.plugins import load_plugins
        if only or "--no-plugins" in rest:
            return stages  # --only = ровно то, что просили; --no-plugins = только свои
        plug, skipped = load_plugins(target)
        for f, e in skipped.items():
            print(f"плагин {f} пропущен: {e}")
        if plug:
            print(f"плагины стадий: {', '.join(s.name for s in plug)}")
        return stages + plug

    base_ctx: dict = {"target": target, "forge_root": str(ROOT)}
    if "--changed" in rest:
        ch = git_changed(target)
        if ch is None:
            print("не git — проверяю всё целиком")
        else:
            base_ctx["only"] = ch
            print(f"hold-the-line: изменено файлов: {len(ch)}")

    if mode == "init-ci":
        wf = Path(target) / ".github" / "workflows" / "forge.yml"
        wf.parent.mkdir(parents=True, exist_ok=True)
        wf.write_text(_CI_WORKFLOW, encoding="utf-8")
        print(f"workflow: {wf}")
        print("бейдж в README:")
        print("[![forge-pipe](../../actions/workflows/forge.yml/badge.svg)](../../actions/workflows/forge.yml)")
        print("(шаблон под раскладку forge-ai-toolkit; под чужой проект адаптируй пути)")
        return 0
    if mode == "all":
        subs = sorted(d for d in Path(target).iterdir()
                      if d.is_dir() and not d.name.startswith(".")
                      and d.name not in ("__pycache__", ".venv", "venv",
                                         "node_modules", "lab-servers",
                                         "build", "target", "dist"))
        if not subs:
            print(f"нет подпроектов в {target}")
            return 2
        from forge.pipe.runner import PipeRunner as _PR
        rows = []
        worst = 0
        for sub in subs:
            r = _PR(list(DEFAULT_STAGES),
                    {"target": str(sub), "forge_root": str(ROOT)},
                    checkpoint=str(sub / "forge-pipe-checkpoint.json")).run()
            rows.append({"project": sub.name, "status": r.status,
                         "duration_ms": r.duration_ms})
            worst = max(worst, 0 if r.status == "SUCCESS" else 1)
            if "--clean" in rest:
                for art in ("forge-pipe-checkpoint.json", "forge-pipe-report.json",
                            ".forge-pipe-history.jsonl"):
                    try:
                        (sub / art).unlink()
                    except OSError:
                        pass
        if "--json" in rest:
            print(_json.dumps(rows, ensure_ascii=False))
        else:
            for row in rows:
                mark = "OK " if row["status"] == "SUCCESS" else "FAIL"
                print(f"  {mark} {row['project']} — {row['duration_ms']}мс")
            ok = sum(1 for r in rows if r["status"] == "SUCCESS")
            print(f"итого: {ok}/{len(rows)} зелёных")
        return worst
    if mode == "window":
        from forge.pipe.window import main as _win
        return _win(target, str(ROOT), resume)
    if mode == "hub":
        from forge.pipe.hub import serve as _serve
        port = 8099
        for i, a in enumerate(rest):
            if a == "--port" and i + 1 < len(rest):
                try:
                    port = int(rest[i + 1])
                except ValueError:
                    pass
        return _serve(target, port, "--open" in rest)
    if mode == "heal":
        from forge.pipe.heal import heal as _heal
        out = _heal(target, str(ROOT), serial="--serial" in rest)
        if "--json" in rest:
            print(_json.dumps(out, ensure_ascii=False))
        else:
            rep = out["report"]
            print(f"heal {target}: {rep['status']} "
                  f"(страховка: {'да' if out['safety_net'] else 'нет'})")
            if out["needed"]:
                print(f"нужен ремонт: {len(out['bundles'])} пакетов "
                      f"-> {out.get('bundles_file', '')}; откат: forge fix rollback {target}")
        return 0 if out["report"]["status"] == "SUCCESS" else 1
    if mode == "watch":
        from forge.pipe.watch import Watcher
        import time as _t
        try:
            stages = _with_plugins(_select())
        except SystemExit as e:
            return int(e.code or 2)

        def _once(reason: str = "старт") -> None:
            runner = PipeRunner(stages, dict(base_ctx),
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
    sarif_path = None
    for i, a in enumerate(rest):
        if a == "--report" and i + 1 < len(rest):
            rep_path = rest[i + 1]
        if a == "--sarif" and i + 1 < len(rest):
            sarif_path = rest[i + 1]
    try:
        stages = _with_plugins(_select())
    except SystemExit as e:
        return int(e.code or 2)
    runner = PipeRunner(stages, dict(base_ctx),
                        checkpoint=str(Path(target) / "forge-pipe-checkpoint.json"))
    report = runner.run(resume=resume, serial=serial)
    out = report.to_dict()
    if sarif_path:
        from forge.pipe.sarif import report_to_sarif
        _safe_write(sarif_path, _json.dumps(report_to_sarif(out, target),
                                            ensure_ascii=False, indent=2))
    if rep_path:
        _safe_write(rep_path, _json.dumps(out, ensure_ascii=False, indent=2))
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
        if len(args) > 1 and args[1] == "mine":
            return _know_mine(args[2:])
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
    if cmd == "edit":
        return _edit(args[1:])
    if cmd == "lang":
        return _lang(args[1:])
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
