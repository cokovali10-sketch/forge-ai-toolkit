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
    if cmd == "mcp":
        sys.path.insert(0, str(ROOT / "src"))
        from forge.mcp.server import McpServer, build_default_registry
        McpServer(build_default_registry("D:/PortfolioProjects/Anvil")).serve()
        return 0
    print(f"unknown command: {cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
