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
        print("       forge gen web|python-service|go-cli|node-api|rust-cli "
              "--name X --out DIR")
        print("       forge gen web ... [--preset aurora|neon|glass|brutalist|"
              "minimal|retro] [--tagline \"...\"] [--lang ru|en]")
        return 0
    if args[0] in ("web", "python-service", "go-cli", "node-api", "rust-cli"):
        import json as _json
        o = _kv(args[1:])
        if not o.get("out"):
            print(f"usage: forge gen {args[0]} --name X --out DIR")
            return 2
        from forge.gen import go_cli as _g, node_api as _n, python_service as _p
        from forge.gen import rust_cli as _r, web as _w
        mod = {"web": _w, "python-service": _p, "go-cli": _g,
               "node-api": _n, "rust-cli": _r}[args[0]]
        try:
            if args[0] == "web":
                res = mod.generate(o["out"], o.get("name", "demo"),
                                   preset=o.get("preset", "aurora"),
                                   tagline=o.get("tagline", ""),
                                   lang=o.get("lang", "ru"))
            else:
                res = mod.generate(o["out"], o.get("name", "demo"))
        except (ValueError, OSError) as e:
            print(f"bad options: {e}")
            return 2
        print(_json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res.get("ok") else 1
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


def _fast(args: list[str]) -> int:
    """forge fast: batch writes/patches, context packs, blueprints."""
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    from forge.speed import api as _s
    usage = """usage:
  forge fast write --root DIR --spec FILE|--data JSON|--stdin [--json]
  forge fast patch --root DIR --spec FILE [--dry-run] [--json]
  forge fast search --root DIR --pattern RE [--pattern RE] [--json]
  forge fast context --root DIR [--path P] [--query RE] [--pack|--json]
  forge fast blueprint --root DIR --template T --name N [--force]
  forge fast recipes [--json]
  forge fast bench --root DIR [--files N] [--repeats N] [--overhead MS]"""
    if not args or args[0] in ("-h", "--help", "help"):
        print(usage)
        return 0
    sub = args[0]
    rest = args[1:]
    opts: dict[str, str] = {}
    multi: dict[str, list[str]] = {}
    pos: list[str] = []
    bools = {"json", "stdin", "dry_run", "no_diff", "no_tree", "ignore_case",
             "literal", "hidden", "force", "backup", "atomic", "no_atomic",
             "pack", "help"}
    takes = {"root", "spec", "data", "template", "name", "package", "query",
             "dir", "max_hits", "context", "max_files", "max_chars",
             "max_lines", "files", "repeats", "payload", "overhead"}
    i = 0
    while i < len(rest):
        a = rest[i]
        if a.startswith("--"):
            key = a[2:].replace("-", "_")
            if key in ("pattern", "path", "glob"):
                if i + 1 < len(rest) and not rest[i + 1].startswith("--"):
                    multi.setdefault(key, []).append(rest[i + 1])
                    i += 2
                else:
                    i += 1
            elif key in bools:
                opts[key] = "1"
                i += 1
            elif key in takes or (i + 1 < len(rest)
                                  and not rest[i + 1].startswith("--")):
                if i + 1 >= len(rest):
                    print(f"fast: --{key} needs a value")
                    return 2
                opts[key] = rest[i + 1]
                i += 2
            else:
                opts[key] = "1"
                i += 1
        else:
            pos.append(a)
            i += 1

    def payload():
        try:
            if opts.get("spec"):
                return _json.loads(Path(opts["spec"]).read_text(encoding="utf-8"))
            if opts.get("data"):
                return _json.loads(opts["data"])
            if "stdin" in opts:
                return _json.loads(sys.stdin.read() or "{}")
        except (OSError, ValueError) as e:
            raise ValueError(f"cannot read spec: {e}") from e
        return {}

    def root_of(data) -> str:
        if opts.get("root"):
            return opts["root"]
        if isinstance(data, dict):
            return str(data.get("root", ""))
        return ""

    try:
        if sub == "write":
            data = payload()
            root = root_of(data)
            files = data.get("files") if isinstance(data, dict) else None
            if files is None and isinstance(data, dict) and data:
                files = {k: v for k, v in data.items() if k != "root"}
            if not root or files is None:
                print(usage)
                return 2
            res = _s.write(root, files,
                           atomic="no_atomic" not in opts,
                           backup="backup" in opts,
                           dry_run="dry_run" in opts)
        elif sub == "patch":
            data = payload()
            root = root_of(data)
            edits = data if isinstance(data, list) else (
                data.get("edits") if isinstance(data, dict) else None)
            if not root or not edits:
                print(usage)
                return 2
            res = _s.patch(root, edits,
                           dry_run="dry_run" in opts,
                           backup="backup" in opts,
                           diff="no_diff" not in opts,
                           atomic="no_atomic" not in opts)
        elif sub == "search":
            patterns = multi.get("pattern", [])
            if opts.get("pattern"):
                patterns.append(opts["pattern"])
            if not patterns:
                patterns = pos
            root = opts.get("root", "")
            if not root or not patterns:
                print(usage)
                return 2
            res = _s.search(root, patterns,
                            dir=opts.get("dir", "."),
                            globs=multi.get("glob"),
                            max_hits=int(opts.get("max_hits", 200)),
                            context=int(opts.get("context", 0)),
                            ignore_case="ignore_case" in opts,
                            regex="literal" not in opts,
                            include_hidden="hidden" in opts)
        elif sub == "context":
            root = opts.get("root", "")
            if not root:
                print(usage)
                return 2
            res = _s.context(root, paths=multi.get("path") or None,
                             query=opts.get("query", ""),
                             globs=multi.get("glob"),
                             dir=opts.get("dir", "."),
                             max_files=int(opts.get("max_files", 24)),
                             max_chars=int(opts.get("max_chars", 160000)),
                             max_lines=int(opts.get("max_lines", 500)),
                             include_tree="no_tree" not in opts,
                             include_hidden="hidden" in opts)
        elif sub == "blueprint":
            data = payload()
            root = root_of(data)
            name = (opts.get("name") or (pos[0] if pos else "")
                    or (data.get("name") if isinstance(data, dict) else "")
                    or "Forge App")
            template = (opts.get("template")
                        or (data.get("template") if isinstance(data, dict) else "")
                        or "python-package")
            package = (opts.get("package")
                       or (data.get("package") if isinstance(data, dict) else "")
                       or "")
            if not root:
                print(usage)
                return 2
            res = _s.blueprint(root, name=name, template=template,
                               package=package,
                               files=data.get("files") if isinstance(data, dict) else None,
                               vars=data.get("vars") if isinstance(data, dict) else None,
                               force="force" in opts,
                               dry_run="dry_run" in opts,
                               backup="backup" in opts,
                               atomic="atomic" in opts)
        elif sub == "recipes":
            res = _s.recipes()
            if "json" in opts:
                print(_json.dumps(res, ensure_ascii=False, indent=2))
            else:
                for r in res["recipes"]:
                    print(f"{r['key']:16} {r['lang']:8} {r['title']}: "
                          f"{r['description']}")
            return 0
        elif sub == "bench":
            root = opts.get("root", "")
            if not root:
                print(usage)
                return 2
            res = _s.bench(root,
                           files=int(opts.get("files", 80)),
                           repeats=int(opts.get("repeats", 2)),
                           payload=int(opts.get("payload", 600)),
                           call_overhead_ms=float(opts.get("overhead", 2.0)))
            print(_json.dumps(res, ensure_ascii=False, indent=2))
            return 0 if res.get("ok") else 1
        else:
            print(f"fast: unknown command {sub!r}\n{usage}")
            return 2
    except (ValueError, OSError, PermissionError, KeyError) as e:
        print(f"fast: {e}")
        return 2
    if "json" in opts:
        print(_json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res.get("ok") else 1
    if sub == "context" and "pack" in opts:
        print(res.get("tree", ""))
        for f in res.get("files", []):
            print(f"\n### {f['path']}\n{f['content']}")
        return 0 if res.get("ok") else 1
    if sub == "search":
        for pat, hits in (res.get("hits") or {}).items():
            print(f"## {pat} ({len(hits)})")
            for h in hits:
                print(f"{h['file']}:{h['line']}: {h['text']}")
        print(f"\n{res.get('total', 0)} hits | "
              f"{res.get('files_scanned', 0)} files | "
              f"{res.get('elapsed_ms', 0)}ms")
        return 0 if res.get("ok") else 1
    if sub in ("write", "patch", "blueprint"):
        print(f"{sub}: {'ok' if res.get('ok') else 'FAIL'} | "
              f"{res.get('files', 0)} files | {res.get('duration_ms', 0)}ms")
        for w in res.get("written", []):
            print(f"  {w.get('status', 'written'):8} {w.get('path')}")
        for p in res.get("would_write", [])[:80]:
            print(f"  would  {p}")
        for s in res.get("skipped", [])[:80]:
            print(f"  skip   {s}")
        for e in res.get("errors", []):
            print(f"  ERROR  {e}")
        return 0 if res.get("ok") else 1
    print(_json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res.get("ok") else 1


def _factory(args: list[str]) -> int:
    """forge factory "<intent>" — плагин от идеи до живого сервера."""
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    from forge.factory import plan as _plan
    from forge.factory import render_text as _render
    from forge.factory import run as _run
    if not args or args[0] in ("-h", "--help", "help"):
        print('usage: forge factory "<intent>" [--out DIR] [--name N] '
              '[--package P] [--command C]')
        print("       [--no-build] [--no-e2e] [--server-jar P] [--api-jar P] "
              "[--java P] [--json]")
        print("       forge factory plan \"<intent>\"")
        return 0
    sub = args[0] if args[0] == "plan" else ""
    rest = args[1:] if sub else args
    opts: dict[str, str] = {}
    pos: list[str] = []
    i = 0
    while i < len(rest):
        a = rest[i]
        if a.startswith("--"):
            key = a[2:].replace("-", "_")
            if i + 1 < len(rest) and not rest[i + 1].startswith("--"):
                opts[key] = rest[i + 1]
                i += 2
            else:
                opts[key] = "1"
                i += 1
        else:
            pos.append(a)
            i += 1
    intent = " ".join(pos).strip()
    if not intent:
        print("factory: нужен intent, например: "
              "\"плагин магазин с GUI\"")
        return 2
    try:
        if sub == "plan":
            spec = _plan(intent, name=opts.get("name", ""),
                         package=opts.get("package", ""),
                         command=opts.get("command", ""))
            if "json" in opts:
                print(_json.dumps(spec, ensure_ascii=False, indent=2))
            else:
                print(_render(spec))
            return 0
        res = _run(intent, out=opts.get("out", "."),
                   name=opts.get("name", ""),
                   package=opts.get("package", ""),
                   command=opts.get("command", ""),
                   build="no_build" not in opts,
                   e2e="no_e2e" not in opts,
                   server_jar=opts.get("server_jar", ""),
                   api_jar=opts.get("api_jar", ""),
                   java_bin=opts.get("java", ""),
                   timeout_boot=int(opts.get("timeout") or 420),
                   build_timeout=int(opts.get("build_timeout") or 600))
    except (ValueError, OSError) as e:
        print(f"factory: {e}")
        return 2
    if "json" in opts:
        print(_json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"factory: {res['status']} · {res['spec']['name']} "
              f"· {res['duration_ms']}мс")
        for st in res["stages"]:
            print(f"  {st['status']:7} {st['name']:13} {st['detail'][:120]}")
        print(f"  dir:  {res['dir']}")
        if res.get("jar"):
            print(f"  jar:  {res['jar']}")
        if res.get("zip"):
            print(f"  zip:  {res['zip']}")
        if res.get("report"):
            print(f"  report: {res['report']}")
        for note in res.get("notes", []):
            print(f"  note: {note}")
    return 0 if res["ok"] else 1


def _studio(args: list[str]) -> int:
    """forge studio [list|add PATH] [--port 8100] [--open] [--store FILE]."""
    sys.path.insert(0, str(ROOT / "src"))
    from forge.studio import DEFAULT_STORE, Store
    from forge.studio import serve as _serve
    if args and args[0] in ("-h", "--help", "help"):
        args = []
    opts: dict[str, str] = {}
    pos: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("--"):
            key = a[2:].replace("-", "_")
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                opts[key] = args[i + 1]
                i += 2
            else:
                opts[key] = "1"
                i += 1
        else:
            pos.append(a)
            i += 1
    if not pos or pos[0] in ("help", "serve", "start"):
        if pos and pos[0] in ("help", "serve", "start"):
            pos = pos[1:]
        if not args or not pos and not args:
            print("usage: forge studio [--port 8100] [--open] [--store FILE]")
            print("       forge studio list [--store FILE]")
            print("       forge studio add PATH [--name NAME] [--store FILE]")
            if not args:
                return 0
        root = opts.get("workspace")
        port = int(opts.get("port", "8100") or 8100)
        return _serve(port=port, open_browser="open" in opts,
                      store_path=opts.get("store", DEFAULT_STORE),
                      **({"workspace": root} if root else {}),
                      ttl=float(opts.get("ttl", "20") or 20))
    store = Store(opts.get("store", DEFAULT_STORE))
    sub = pos[0]
    if sub == "list":
        items = store.list()
        if not items:
            print("studio: проектов нет")
        for p in items:
            print(f"{p.get('score') if p.get('score') is not None else '--':>3}  "
                  f"{p['name']:<24} {p['path']}")
        return 0
    if sub == "add":
        path = pos[1] if len(pos) > 1 else opts.get("path", "")
        if not path:
            print("usage: forge studio add PATH [--name NAME]")
            return 2
        try:
            item = store.add(path, opts.get("name", ""))
        except (ValueError, OSError) as e:
            print(f"studio: {e}")
            return 2
        print(f"studio: добавлен {item['name']} -> {item['path']}")
        return 0
    print(f"studio: неизвестная команда {sub!r}")
    return 2


def _web(args: list[str]) -> int:
    """forge web <presets|new|audit|preview>: анимированные сайты."""
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    from forge.webstudio import audit as _audit
    from forge.webstudio import generate as _generate
    from forge.webstudio import list_presets as _presets
    from forge.webstudio import render_text as _render
    from forge.webstudio import serve_site as _serve
    if not args or args[0] in ("-h", "--help", "help"):
        print("usage: forge web presets [--json]")
        print("       forge web new NAME [--out DIR] [--preset K] "
              "[--tagline \"...\"] [--lang ru|en] [--json]")
        print("       forge web audit DIR [--json]")
        print("       forge web preview DIR [--port 8100] [--open]")
        return 0
    opts: dict[str, str] = {}
    pos: list[str] = []
    i = 1
    while i < len(args):
        a = args[i]
        if a.startswith("--"):
            key = a[2:].replace("-", "_")
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                opts[key] = args[i + 1]
                i += 2
            else:
                opts[key] = "1"
                i += 1
        else:
            pos.append(a)
            i += 1
    sub = args[0]
    if sub == "presets":
        items = _presets()
        if "json" in opts:
            print(_json.dumps(items, ensure_ascii=False, indent=2))
        else:
            for p in items:
                print(f"{p['key']:10} {p['title']:12} {p['hint']}")
        return 0
    if sub == "new":
        name = opts.get("name") or (pos[0] if pos else "")
        if not name:
            print("usage: forge web new NAME [--out DIR] [--preset K]")
            return 2
        out = opts.get("out") or "."
        try:
            res = _generate(out, name, preset=opts.get("preset", "aurora"),
                            tagline=opts.get("tagline", ""),
                            lang=opts.get("lang", "ru"))
        except (ValueError, OSError) as e:
            print(f"web: {e}")
            return 2
        if "json" in opts:
            print(_json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"web: {res['preset_title']} -> {res['dir']}  "
                  f"({res['score']}/100)")
            for f in res["files"]:
                print(f"  {f}")
            if res["problems"]:
                for p in res["problems"]:
                    print(f"  FAIL {p}")
        return 0 if res["ok"] else 1
    if sub == "audit":
        target = pos[0] if pos else "."
        res = _audit(target)
        if "json" in opts:
            print(_json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(_render(res))
        return 0 if res["ok"] else 1
    if sub == "preview":
        target = pos[0] if pos else "."
        port = int(opts.get("port") or 8100)
        return _serve(target, port=port, open_browser="open" in opts)
    print(f"unknown web command: {sub}")
    return 2


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


def _refactor(args: list[str]) -> int:
    """forge refactor <file|dir> [--plan] [--suggest] [--sarif PATH] — чистый код."""
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    from forge.refactor import api as _api
    if not args or args[0] in ("-h", "--help", "help"):
        print("usage: forge refactor <file|dir> [--plan] [--suggest] [--sarif PATH]")
        print("       forge refactor <file.py> --apply [--test \"cmd\"]")
        print("  (без флагов)  список находок + оценка здоровья 0..100")
        print("  --plan        приоритетный план: что чинить первым, дешевле/серьёзнее")
        print("  --suggest     только советы, сгруппированные по файлам")
        print("  --sarif PATH  выгрузить находки в SARIF 2.1.0 (GitHub code scanning)")
        print("  --apply       авто-фикс: мёртвые импорты, повторяющиеся числа,")
        print("                сравнения == None -> is None (Python), с бэкапом,")
        print("                проверкой и авто-откатом")
        print("  --test \"cmd\"  прогнать тесты после фикса (иначе откат)")
        print("  --only KIND   только один фикс: imports | constants | comparisons")
        print("находит: длинные функции, вложенность, дубли, магические числа,")
        print("         много аргументов, God-классы, цикломатику, мёртвые импорты,")
        print("         сравнения с None/True/False")
        return 0
    target = args[0]
    if "--apply" in args:
        import shlex
        test_cmd = None
        run_tests = False
        if "--test" in args:
            i = args.index("--test")
            if i + 1 >= len(args):
                print("нужна команда после --test")
                return 2
            test_cmd = shlex.split(args[i + 1])
            run_tests = True
        from pathlib import Path as _P
        apply_fn = _api.apply_dir if _P(target).is_dir() else _api.apply
        res = apply_fn(target, test_cmd=test_cmd, run_tests=run_tests,
                       only=_flag(args, "--only"))
        print(_json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res.get("ok") else 1
    if "--sarif" in args:
        i = args.index("--sarif")
        if i + 1 >= len(args):
            print("нужен путь после --sarif")
            return 2
        out_path = args[i + 1]
        sarif = _api.sarif(target)
        from pathlib import Path as _P
        _P(out_path).write_text(_json.dumps(sarif, ensure_ascii=False, indent=2),
                                encoding="utf-8")
        print(f"SARIF: {len(sarif['runs'][0]['results'])} находок -> {out_path}")
        return 0
    if "--plan" in args:
        res = _api.plan(target)
        print(f"план: {res['total']} шагов, здоровье {res['score']}/100")
        for s in res["steps"]:
            print(f"  {s['order']:>3}. [{s['severity']}/{s['effort']}] "
                  f"{s['kind']} {s['file']}:{s['line']} — {s['suggestion']}")
        return 0
    res = _api.suggest(target) if "--suggest" in args else _api.inspect(target)
    print(_json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res.get("ok", True) else 1


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


_VALUE_FLAGS = {"--timeout", "--max-files", "--min-score", "--max-regression",
                "--path", "--fail-on", "--baseline", "--html", "--test",
                "--only"}


def _positionals(args: list[str]) -> list[str]:
    """Позиционные аргументы без флагов и их значений (напр. `--timeout 600`)."""
    out: list[str] = []
    skip = False
    for a in args:
        if skip:
            skip = False
            continue
        if a in _VALUE_FLAGS:
            skip = True
            continue
        if a.startswith("--"):
            continue
        out.append(a)
    return out


def _map(args: list[str]) -> int:
    """forge map <dir> [--json]: карта проекта (языки, LOC, вход, импорты)."""
    sys.path.insert(0, str(ROOT / "src"))
    from forge.kit import build_map, render_text
    if not args or args[0] in ("-h", "--help", "help"):
        print("usage: forge map <dir> [--json]")
        print("  карта проекта: языки и LOC, файлы сборки, точки входа,")
        print("  крупнейшие файлы, граф внутренних импортов и внешние зависимости")
        return 0
    m = build_map(_positionals(args)[0] if _positionals(args) else ".")
    if "--json" in args:
        import json as _json
        print(_json.dumps(m, ensure_ascii=False, indent=2))
    else:
        print(render_text(m))
    return 0 if m.get("ok") else 1


def _test(args: list[str]) -> int:
    """forge test <dir> [--detect] [--timeout S] [--json]: тесты проекта."""
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    from forge.kit import detect_test_command, run_tests
    if not args or args[0] in ("-h", "--help", "help"):
        print("usage: forge test <dir> [--detect] [--timeout S] [--json]")
        print("  сам определяет стек (pytest/npm/go/cargo/gradle/maven/make)")
        print("  и запускает родные тесты; нет тулчейна — это не провал")
        return 0
    root = _positionals(args)[0] if _positionals(args) else "."
    if "--detect" in args:
        print(_json.dumps(detect_test_command(root), ensure_ascii=False))
        return 0
    tmo = int(_flag(args, "--timeout")) if _flag(args, "--timeout") else 600
    out = run_tests(root, timeout=tmo)
    if "--json" in args:
        print(_json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if not out.get("ran"):
        print(f"тесты: пропущено ({out.get('reason', '')})")
        return 0
    mark = "OK" if out["ok"] else "FAIL"
    print(f"тесты ({out['kind']}): {mark}"
          + (f" — {out['summary']}" if out.get("summary") else ""))
    if not out["ok"]:
        print(out.get("log_tail", "")[-800:])
    return 0 if out["ok"] else 1


def _ci(args: list[str]) -> int:
    """forge ci <dir> [--force] [--json]: сгенерировать workflow GitHub Actions."""
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    from forge.kit import generate_ci
    if not args or args[0] in ("-h", "--help", "help"):
        print("usage: forge ci <dir> [--force] [--json]")
        print("  пишет .github/workflows/forge-ci.yml под стек проекта")
        return 0
    out = generate_ci(_positionals(args)[0] if _positionals(args) else ".",
                      force="--force" in args)
    if "--json" in args:
        print(_json.dumps(out, ensure_ascii=False, indent=2))
    elif out.get("ok"):
        print(f"workflow: {out['path']} (экосистемы: {', '.join(out['ecosystems'])})")
    else:
        print(f"ci: {out.get('error')}")
    return 0 if out.get("ok") else 1


def _secrets(args: list[str]) -> int:
    """forge secrets <dir> [--json]: скан утечек секретов."""
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    from forge.kit import scan_secrets
    if not args or args[0] in ("-h", "--help", "help"):
        print("usage: forge secrets <dir> [--json]")
        print("  ищет ключи/токены/приватные ключи/пароли (вывод маскируется)")
        return 0
    out = scan_secrets(_positionals(args)[0] if _positionals(args) else ".")
    if "--json" in args:
        print(_json.dumps(out, ensure_ascii=False, indent=2))
    elif out.get("ok"):
        print(f"секреты: найдено {out['count']} "
              f"(просканировано файлов {out['files_scanned']})")
        for f in out["findings"][:20]:
            print(f"  [{f['severity']}] {f['kind']} — {f['file']} ({f['preview']})")
    else:
        print(f"secrets: {out.get('error')}")
    return 0 if out.get("ok") else 1


def _audit(args: list[str]) -> int:
    """forge audit <dir> [--deep] [--json] [--min-score N]: здоровье проекта."""
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    from forge.kit import audit, render_audit
    if not args or args[0] in ("-h", "--help", "help"):
        print("usage: forge audit <dir> [--deep] [--json] [--min-score N]")
        print("  сводное здоровье проекта: карта, секреты, зависимости, качество")
        print("  (--deep: ещё и родные тесты). --min-score — гейт для CI.")
        return 0
    pos = _positionals(args)
    out = audit(pos[0] if pos else ".", deep="--deep" in args)
    if "--json" in args:
        print(_json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(render_audit(out))
    gate = _flag(args, "--min-score")
    if gate:
        try:
            threshold = int(gate)
        except ValueError:
            threshold = 0
        if out.get("score", 0) < threshold:
            print(f"audit: {out.get('score')} < {threshold} — гейт не пройден")
            return 1
    bl_path = _flag(args, "--baseline")
    if "--baseline" in args:
        from forge.kit import baseline as bl
        bres = bl.check(pos[0] if pos else ".", bl_path or None,
                        fail_on=_flag(args, "--fail-on") or "high")
        if "--json" not in args:
            print(bl.render_text(bres))
        if bres.get("ok") is False and not bres.get("baseline_missing"):
            return 1
    return 0 if out.get("ok") else 1


def _deps(args: list[str]) -> int:
    """forge deps <dir> [--check] [--json]: инвентарь зависимостей + гигиена."""
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    from forge.kit import scan_deps
    if not args or args[0] in ("-h", "--help", "help"):
        print("usage: forge deps <dir> [--check] [--json]")
        print("  зависимости всех экосистем (python/node/go/rust/java) и гигиена:")
        print("  неограниченные/свободные версии, дубликаты. --check — устаревшее.")
        return 0
    pos = _positionals(args)
    out = scan_deps(pos[0] if pos else ".", check="--check" in args)
    if "--json" in args:
        print(_json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if not out.get("ok"):
        print(f"deps: {out.get('error')}")
        return 1
    eco = ", ".join(f"{k}={v}" for k, v in out["by_ecosystem"].items()) or "нет"
    print(f"зависимости: {out['count']} ({eco})")
    for f in out["findings"][:20]:
        print(f"  [{f['severity']}] {f['kind']}: {f['detail']} — {f['file']}")
    return 0


def _doctor(args: list[str]) -> int:
    """forge doctor [dir] [--json]: аудит тулчейнов и возможностей."""
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    from forge.kit import doctor, render_doctor
    if args and args[0] in ("-h", "--help", "help"):
        print("usage: forge doctor [dir] [--json]")
        print("  что есть на машине (тулчейны, версии) и что FORGE здесь умеет;")
        print("  с путём — ещё стек тестов проекта. Только чтение.")
        return 0
    pos = _positionals(args)
    out = doctor(pos[0] if pos else None)
    if "--json" in args:
        print(_json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(render_doctor(out))
    return 0 if out.get("ok") else 1


def _init(args: list[str]) -> int:
    """forge init [dir] [--force] [--json]: онбординг проекта для FORGE."""
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    from forge.kit import init_project
    if args and args[0] in ("-h", "--help", "help"):
        print("usage: forge init [dir] [--force] [--json]")
        print("  создаёт недостающие файлы: CI (.github/workflows/forge-ci.yml)")
        print("  и .forge-suppress.json; ничего не перезаписывает без --force")
        return 0
    pos = _positionals(args)
    out = init_project(pos[0] if pos else ".", force="--force" in args)
    if "--json" in args:
        print(_json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if not out.get("ok"):
        print(f"init: {out.get('error') or '; '.join(out.get('problems', []))}")
        return 1
    print(f"init: {out['root']}")
    if out["created"]:
        print("  создано: " + ", ".join(out["created"]))
    if out["skipped"]:
        print("  уже есть: " + ", ".join(out["skipped"]))
    print("  дальше:")
    for c in out["next"]:
        print("    " + c)
    return 0


def _report(args: list[str]) -> int:
    """forge report [dir] [--deep] [--json]: единый свод (audit+тренд+...)."""
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    from forge.kit import full_report, render_report
    if args and args[0] in ("-h", "--help", "help"):
        print("usage: forge report [dir] [--deep] [--json] [--html FILE]")
        return 0
    pos = _positionals(args)
    rep = full_report(pos[0] if pos else ".", deep="--deep" in args)
    html_path = _flag(args, "--html")
    if html_path:
        from pathlib import Path as _P
        from forge.serve import render_static
        out = _P(html_path)
        try:
            out.write_text(render_static(rep), encoding="utf-8")
        except OSError as e:
            print(f"report: не записать {out}: {e}")
            return 1
        print(f"report: HTML -> {out}")
        return 0 if rep.get("ok") else 1
    if "--json" in args:
        print(_json.dumps(rep, ensure_ascii=False, indent=2))
        return 0 if rep.get("ok") else 1
    print(render_report(rep))
    return 0 if rep.get("ok") else 1


def _serve(args: list[str]) -> int:
    """forge serve [dir] [--port N] [--open] [--watch S]: дашборд + API."""
    sys.path.insert(0, str(ROOT / "src"))
    from forge.serve import serve
    if args and args[0] in ("-h", "--help", "help"):
        print("usage: forge serve [dir] [--port 8099] [--open] [--watch 30]")
        return 0
    pos = _positionals(args)
    root = pos[0] if pos else "."
    port = int(_flag(args, "--port") or 8099)
    watch = float(_flag(args, "--watch") or 0)
    return serve(root, port=port, open_browser="--open" in args, watch=watch)


def _baseline(args: list[str]) -> int:
    """forge baseline <save|check|diff> [dir] [--path P] [--fail-on L] [--json]."""
    import json as _json
    from pathlib import Path as _P
    sys.path.insert(0, str(ROOT / "src"))
    from forge.kit import baseline as bl
    sub = args[0] if args else "check"
    if sub in ("-h", "--help", "help") or sub not in ("save", "check", "diff"):
        print("usage: forge baseline <save|check|diff> [dir] "
              "[--path P] [--fail-on high|medium|low|none] [--json]")
        print("  save  - снять снимок текущих проблем (по умолчанию")
        print("          <dir>/.forge-baseline.json); check - падать только")
        print("          на НОВЫХ проблемах; diff - что нового/закрыто")
        return 0 if sub in ("-h", "--help", "help") else 2
    rest = args[1:]
    pos = _positionals(rest)
    root = pos[0] if pos else "."
    path = _flag(rest, "--path") or None

    if sub == "save":
        out = bl.save(root, path)
        if "--json" in args:
            print(_json.dumps(out, ensure_ascii=False, indent=2))
            return 0 if out.get("ok") else 1
        if not out.get("ok"):
            print(f"baseline save: {out.get('error')}")
            return 1
        print(f"baseline save: {out['count']} проблем -> {out['path']}")
        return 0

    if sub == "check":
        out = bl.check(root, path, fail_on=_flag(rest, "--fail-on") or "high")
        if "--json" in args:
            print(_json.dumps(out, ensure_ascii=False, indent=2))
            return 0 if out.get("ok") else 1
        print(bl.render_text(out))
        return 0 if out.get("ok") else 1

    snap = bl.collect(root)
    if not snap.get("ok"):
        print(f"baseline diff: {snap.get('error')}")
        return 1
    loaded = bl.load(path or str(_P(root) / bl.DEFAULT_NAME))
    d = bl.diff(snap["items"], loaded["items"])
    if "--json" in args:
        print(_json.dumps({"new": d["new"], "resolved": d["resolved"],
                           "new_counts": d["new_counts"]},
                          ensure_ascii=False, indent=2))
        return 0
    c = d["new_counts"]
    print(f"baseline diff: new={len(d['new'])} "
          f"(high={c['high']} medium={c['medium']} low={c['low']}), "
          f"resolved={len(d['resolved'])}, всего={d['current_count']}")
    for i in d["new"][:20]:
        print(f"  + [{i['severity']}] {i['area']}: {i['detail']} ({i['file']})")
    for i in d["resolved"][:10]:
        print(f"  - [{i['severity']}] {i['area']}: {i['detail']} ({i['file']})")
    return 0


def _fix(args: list[str]) -> int:
    """forge fix [dir] [--only KIND] [--test "cmd"] [--json]: пакетные автофиксы."""
    import json as _json
    import shlex
    sys.path.insert(0, str(ROOT / "src"))
    from forge.refactor import api as _api
    if args and args[0] in ("-h", "--help", "help"):
        print("usage: forge fix [dir] [--only imports|constants|comparisons] "
              "[--test \"cmd\"] [--json]")
        print("  безопасные автофиксы во всех .py проекта: бэкап, проверка")
        print("  синтаксиса и единый откат при падении тестов (--test)")
        return 0
    pos = _positionals(args)
    root = pos[0] if pos else "."
    test_cmd = None
    run_tests = False
    t = _flag(args, "--test")
    if t:
        test_cmd = shlex.split(t)
        run_tests = True
    res = _api.apply_dir(root, test_cmd=test_cmd, run_tests=run_tests,
                         only=_flag(args, "--only") or None)
    if "--json" in args:
        print(_json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res.get("ok") else 1
    if not res.get("ok") and res.get("error"):
        print(f"fix: {res['error']}")
        return 1
    if res.get("rolled_back"):
        print(f"fix: тесты упали ({res.get('tests_returncode')}) — "
              f"откат всех правок")
        return 1
    print(f"fix: изменено файлов {res['files_changed']} "
          f"из {res['files_scanned']}")
    for c in res.get("changed", [])[:20]:
        bits = []
        if c.get("removed_imports"):
            bits.append(f"импортов -{len(c['removed_imports'])}")
        if c.get("constants"):
            bits.append(f"констант {len(c['constants'])}")
        if c.get("fixed_comparisons"):
            bits.append(f"сравнений {c['fixed_comparisons']}")
        print(f"  {c['file']}: " + ", ".join(bits))
    for e in res.get("errors", [])[:10]:
        print(f"  ! {e.get('file')}: {e.get('error')}")
    return 0 if res.get("ok") else 1


def _evolve(args: list[str]) -> int:
    """forge evolve [dir] [--json]: что протухло и кому чинить."""
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    from forge.evolve.check import check as _check
    target = next((a for a in args if not a.startswith("--")), ".")
    out = _check(target, str(ROOT))
    if "--json" in args:
        print(_json.dumps(out, ensure_ascii=False))
    else:
        print(f"evolve {target}: задач: {out['total']}")
        for t in out["tasks"]:
            print(f"  [{t['priority']}] {t['area']}: {t['evidence'][:120]} "
                  f"-> {','.join(t['suggest'])}")
        if not out["tasks"]:
            print("  всё свежо, задач нет")
    return 0


def _make(args: list[str]) -> int:
    """forge make <web|python-service|go-cli> <name> [out-dir]: скаффолд + проверка."""
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    if not args or args[0] in ("-h", "--help", "help") or len(args) < 2:
        print("usage: forge make <web|python-service|go-cli> <name> [out-dir]")
        return 0 if args and args[0] in ("-h", "--help", "help") else 2
    from forge.gen.make import make as _mk
    out = _mk(args[0], args[1], args[2] if len(args) > 2 else ".", str(ROOT))
    if not out.get("ok"):
        print(_json.dumps(out, ensure_ascii=False, indent=2))
        return 1
    print(f"make {args[0]}/{args[1]}: скаффолд OK, проверка: {out['pipe']}")
    for name, status in out["stages"]:
        print(f"  {'OK ' if status == 'SUCCESS' else 'FAIL'} {name}")
    return 0


def _quality(args: list[str]) -> int:
    """forge quality <dir> [--min-score N] [--max-regression N] [--pipe] [--json]."""
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    from forge import quality
    if not args or args[0] in ("-h", "--help", "help"):
        print("usage: forge quality <dir> [--min-score N] [--max-regression N] "
              "[--pipe] [--json]")
        print("  сводный дашборд качества + тренд + регресс-гейт для CI")
        return 0
    root = args[0]
    min_score = float(_flag(args, "--min-score")) if _flag(args, "--min-score") else None
    max_reg = float(_flag(args, "--max-regression")) if _flag(args, "--max-regression") else None
    out = quality.check(root, str(ROOT), min_score=min_score,
                        max_regression=max_reg, run_pipe="--pipe" in args)
    if "--json" in args:
        print(_json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out["ok"] else 1
    arrow = {"up": "+", "down": "-", "flat": "="}[out["trend"]["direction"]]
    print(f"качество: {out['score']:.0f}/100  тренд {arrow} {out['trend']['delta']:+.0f} "
          f"(замеров: {out['trend']['samples']})")
    print(f"файлов: {out['files']}  замечаний: {out['issues']}")
    if out["langs"]:
        print("языки: " + ", ".join(f"{k}:{v}" for k, v in
                                    sorted(out["langs"].items(), key=lambda kv: -kv[1])))
    if out["by_kind"]:
        print("типы: " + ", ".join(f"{k}={v}" for k, v in list(out["by_kind"].items())[:6]))
    if "pipe" in out:
        print(f"конвейер: {out['pipe']}")
    if out["ok"]:
        print("гейт: ПРОЙДЕН")
    else:
        print("гейт: ПРОВАЛ — " + "; ".join(out["reasons"]))
    return 0 if out["ok"] else 1


def _do(args: list[str]) -> int:
    """forge do "<намерение>" [--root DIR] [--name N] [--run] [--json]."""
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    from forge.orchestrate import run as _orun
    if not args or args[0] in ("-h", "--help", "help"):
        print('usage: forge do "<намерение>" [--root DIR] [--name N] [--run] [--json]')
        print("  строит исполнимый план: цех, модули, скиллы, знания, проверка")
        print("  --run — сразу прогнать замкнутый контур loop и дать вердикт")
        return 0
    positional = [a for a in args if not a.startswith("--")]
    # значение флага --root/--name не должно попасть в намерение
    flags_with_value = {"--root", "--name", "--attempts"}
    intent_parts: list[str] = []
    skip = False
    for a in args:
        if skip:
            skip = False
            continue
        if a in flags_with_value:
            skip = True
            continue
        if a.startswith("--"):
            continue
        intent_parts.append(a)
    intent = " ".join(intent_parts).strip()
    root = _flag(args, "--root") or "."
    name = _flag(args, "--name") or "demo"
    out = _orun(intent, root, str(ROOT), name=name, execute="--run" in args)
    if "--json" in args:
        print(_json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"намерение: {intent}")
        if out.get("generator"):
            print(f"цех: {out['generator']}")
        if out.get("modules"):
            print("модули: " + ", ".join(m["module"] for m in out["modules"]))
        if out.get("skills"):
            print("скиллы: " + ", ".join(s["skill"] for s in out["skills"]))
        if out.get("knowledge"):
            print("знания: " + ", ".join(str(k.get("title")) for k in out["knowledge"]))
        print("план:")
        for i, s in enumerate(out["steps"], 1):
            print(f"  {i}. {s['step']}: {s['command']}")
        if "verify" in out:
            v = out["verify"]
            print(f"проверка: {v['status']} за {len(v['attempts'])} попыток")
    return 0


def _loop(args: list[str]) -> int:
    """forge loop <dir> [--attempts N] [--on-fail "cmd"] [--no-autofix] [--serial]."""
    import json as _json
    sys.path.insert(0, str(ROOT / "src"))
    from forge.pipe.loop import hook_command, run_loop
    if not args or args[0] in ("-h", "--help", "help"):
        print("usage: forge loop <dir> [--attempts N] [--on-fail \"cmd\"] [--no-autofix] [--serial]")
        print("  гоняет конвейер и пытается довести проект до зелёного сам:")
        print("  checkpoint -> pipe -> пакеты ремонта -> безопасные фиксы -> повтор")
        return 0
    target = args[0]
    attempts = 3
    if "--attempts" in args:
        i = args.index("--attempts")
        if i + 1 < len(args):
            attempts = max(1, int(args[i + 1]))
    hook = None
    if "--on-fail" in args:
        import shlex
        i = args.index("--on-fail")
        if i + 1 >= len(args):
            print("нужна команда после --on-fail")
            return 2
        hook = hook_command(shlex.split(args[i + 1]), target)
    out = run_loop(target, str(ROOT), max_attempts=attempts,
                   serial="--serial" in args, auto_fix="--no-autofix" not in args,
                   on_fail=hook)
    if "--json" in args:
        print(_json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out["ok"] else 1
    print(f"loop: {out['status']} за {len(out['attempts'])} попыток "
          f"(страховка: {'да' if out['safety_net'] else 'нет'})")
    for a in out["attempts"]:
        acts = a.get("actions", [])
        fixes = ", ".join(i.get("fix", i.get("hook", "?")) for i in acts)
        print(f"  попытка {a['attempt']}: {a['status']}"
              + (f" — действия: {fixes}" if fixes else ""))
    if not out["ok"] and out.get("hint"):
        print(f"  {out['hint']}")
    return 0 if out["ok"] else 1


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
        print("usage: forge <command> [args]")
        print("  inspect|map|audit|report|doctor|deps|secrets  project health")
        print("  pipe|loop|do|quality|fix|refactor             checks and repair")
        print("  gen|make|web|factory                          generators")
        print("  fast write|patch|search|context|blueprint     speed department")
        print("  serve|studio                                  local dashboards")
        print("  lab|bench|skills|modules|route|mcp            experts and MCP")
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
    if cmd == "make":
        return _make(args[1:])
    if cmd == "evolve":
        return _evolve(args[1:])
    if cmd == "edit":
        return _edit(args[1:])
    if cmd == "refactor":
        return _refactor(args[1:])
    if cmd == "lang":
        return _lang(args[1:])
    if cmd == "pipe":
        return _pipe(args[1:])
    if cmd == "loop":
        return _loop(args[1:])
    if cmd == "do":
        return _do(args[1:])
    if cmd == "quality":
        return _quality(args[1:])
    if cmd == "map":
        return _map(args[1:])
    if cmd == "test":
        return _test(args[1:])
    if cmd == "ci":
        return _ci(args[1:])
    if cmd == "secrets":
        return _secrets(args[1:])
    if cmd == "doctor":
        return _doctor(args[1:])
    if cmd == "deps":
        return _deps(args[1:])
    if cmd == "audit":
        return _audit(args[1:])
    if cmd == "init":
        return _init(args[1:])
    if cmd == "report":
        return _report(args[1:])
    if cmd == "serve":
        return _serve(args[1:])
    if cmd == "baseline":
        return _baseline(args[1:])
    if cmd == "fix":
        return _fix(args[1:])
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
    if cmd == "factory":
        return _factory(args[1:])
    if cmd == "fast":
        return _fast(args[1:])
    if cmd == "web":
        return _web(args[1:])
    if cmd == "studio":
        return _studio(args[1:])
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
