"""Minimal stdio MCP server: initialize, tools/list, tools/call.

Speaks JSON-RPC 2.0 over stdio with Content-Length framing omitted
(newline-delimited, like many embedded MCP servers). Tools come from
the Registry, so Anvil-backed tools are exposed without duplication.
"""
from __future__ import annotations

import json
import sys
from typing import Any

from ..core.registry import ModuleDef, Registry

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "forge-mcp", "version": "0.1.0"}


class McpServer:
    def __init__(self, registry: Registry) -> None:
        self.registry = registry

    def handle(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        method = msg.get("method", "")
        msg_id = msg.get("id")
        params = msg.get("params", {})
        if method == "initialize":
            return self._ok(msg_id, {
                "protocolVersion": PROTOCOL_VERSION,
                "serverInfo": SERVER_INFO,
                "capabilities": {"tools": {}},
            })
        if method == "tools/list":
            tools = []
            for name, owner in sorted(self.registry.tool_owner.items()):
                schema: dict = {"type": "object"}
                desc = f"FORGE tool via backend '{owner}'"
                back = self.registry.backends.get(owner)
                if back is not None and hasattr(back, "schema_of"):
                    try:
                        schema, desc = back.schema_of(name)
                    except Exception:
                        pass
                tools.append({"name": name, "description": desc,
                              "inputSchema": schema})
            return self._ok(msg_id, {"tools": tools})
        if method == "tools/call":
            name = params.get("name", "")
            args = params.get("arguments", {}) or {}
            res = self.registry.call(name, args)
            if res.get("ok"):
                return self._ok(msg_id, {
                    "content": [{"type": "text",
                                 "text": json.dumps(res.get("data"),
                                                    ensure_ascii=False)}],
                })
            return self._err(msg_id, -32000, str(res.get("error", "tool failed")))
        if method in ("notifications/initialized",):
            return None
        return self._err(msg_id, -32601, f"unknown method: {method}")

    @staticmethod
    def _ok(msg_id: Any, result: Any) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    @staticmethod
    def _err(msg_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": msg_id,
                "error": {"code": code, "message": message}}

    def serve(self, stdin=None, stdout=None) -> None:
        stdin = stdin or sys.stdin
        stdout = stdout or sys.stdout
        for line in stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            try:
                resp = self.handle(msg)
            except Exception as e:  # never kill stdio loop on a bad tool
                resp = self._err(msg.get("id"), -32603, f"{type(e).__name__}: {e}")
            if resp is not None:
                stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                stdout.flush()


def build_default_registry(anvil_dir: str = "") -> Registry:
    """Registry wired for CLI/MCP smoke use. Anvil attached when found."""
    from ..core.registry import AnvilBackend, LocalBackend, ModuleDef
    from ..project.inspect import TOOLS
    from pathlib import Path
    reg = Registry()
    local = LocalBackend()
    from ..core.registry import ToolDef
    local.add(ToolDef("forge.ping", "Liveness probe", level=0),
              lambda p: {"pong": True, "echo": p.get("echo")})
    for name, desc, schema, fn in TOOLS:
        local.add(ToolDef(name, desc, "0.1.0",
                          {"type": "object", "properties": {
                              k: {"type": "string", "description": v}
                              for k, v in schema.items()}}, level=0), fn)
    reg.add_backend("local", local)
    reg.add_module(ModuleDef("core", "FORGE core tools", "0.1.0", ["forge.ping"]))
    reg.add_module(ModuleDef("project", "Workspace-confined project tools",
                             "0.1.0", [t[0] for t in TOOLS]))
    _wire_lab(reg, local)
    _wire_gen(reg, local)
    _wire_ui(reg, local)
    _wire_langs(reg, local)
    _wire_edit(reg, local)
    _wire_evolve(reg, local)
    _wire_refactor(reg, local)
    _wire_pipe(reg, local)
    _wire_loop(reg, local)
    _wire_quality(reg, local)
    _wire_kit(reg, local)
    _wire_more(reg, local, anvil_dir)
    if anvil_dir and Path(anvil_dir, "anvil_call.py").is_file():
        reg.add_backend("anvil", AnvilBackend(anvil_dir))
        reg.add_module(ModuleDef("anvil", "Anvil tool bridge", "0.1.0", []))
    return reg


def _wire_lab(reg, local) -> None:
    """Stateless lab tools only (env-bound ones stay in CLI/runner)."""
    from ..core.registry import ToolDef
    from ..lab import build as _b
    from ..lab import unittests as _u
    local.add(ToolDef("lab.detect_build", "Detect gradle/maven/javac", level=0),
              lambda p: {"system": _b.detect(p.get("project", "."))})
    local.add(ToolDef("lab.build_plugin", "Clean build a plugin project",
                      level=2, timeout=900),
              lambda p: _b.build_plugin(p.get("project", "."),
                                        int(p.get("timeout", 900))))
    local.add(ToolDef("lab.run_unit_tests", "Gradle test suite with summary",
                      level=2, timeout=900),
              lambda p: _u.run_gradle_tests(p.get("project", "."),
                                            int(p.get("timeout", 900))))
    reg.add_module(ModuleDef("lab", "Testing Lab stateless tools", "0.1.0",
                             ["lab.detect_build", "lab.build_plugin",
                              "lab.run_unit_tests"]))


def _wire_langs(reg, local) -> None:
    """Language modules as MCP tools: detect/lint/test/scaffold per language."""
    from ..core.registry import ToolDef
    from ..langs import LANGS

    def _mod(p: dict) -> tuple[str, Any]:
        lid = str(p.get("lang", ""))
        if lid not in LANGS:
            raise ValueError(f"unknown language (есть: {','.join(LANGS)})")
        return lid, LANGS[lid]

    local.add(ToolDef("lang.detect_all", "Detect languages in a dir", level=0),
              lambda p: {"languages":
                         {lid: mod.detect(str(p.get("root", ".")))
                          for lid, mod in LANGS.items()}})
    local.add(ToolDef("lang.lint", "Syntax-check a language in a dir", level=1),
              lambda p: _mod(p)[1].lint(str(p.get("root", "."))).envelope())
    local.add(ToolDef("lang.test", "Run a language test suite", level=1),
              lambda p: _mod(p)[1].test(str(p.get("root", "."))).envelope())
    local.add(ToolDef("lang.scaffold", "Scaffold minimal project", level=1),
              lambda p: _mod(p)[1].scaffold(str(p.get("name", "app")),
                                            str(p.get("out", "."))))
    reg.add_module(ModuleDef("langs", "Language expert modules", "0.1.0",
                             ["lang.detect_all", "lang.lint",
                              "lang.test", "lang.scaffold"]))


def _wire_edit(reg, local) -> None:
    """Universal object editor: JSON natively, YAML via Anvil bridge."""
    from ..core.registry import ToolDef
    from ..edit import api as _api

    local.add(ToolDef("edit.inspect", "Show document structure", level=0),
              lambda p: _api.inspect(str(p.get("file", ""))))
    local.add(ToolDef("edit.get", "Get value by dotted path", level=0),
              lambda p: _api.get(str(p.get("file", "")),
                                 str(p.get("path", ""))))
    local.add(ToolDef("edit.set", "Set value (backup + optional schema)",
                      level=2),
              lambda p: _api.set(str(p.get("file", "")),
                                 str(p.get("path", "")),
                                 str(p.get("value", "null")),
                                 bool(p.get("dry", False)),
                                 str(p.get("schema", ""))))
    local.add(ToolDef("edit.validate", "Validate against lite-schema",
                      level=0),
              lambda p: _api.validate(str(p.get("file", "")),
                                       str(p.get("schema", ""))))
    local.add(ToolDef("edit.rollback", "Restore .forge-bak", level=2),
              lambda p: _api.rollback(str(p.get("file", ""))))
    reg.add_module(ModuleDef("edit", "Universal object editor", "0.1.0",
                             ["edit.inspect", "edit.get", "edit.set",
                              "edit.validate", "edit.rollback"]))


def _wire_evolve(reg, local) -> None:
    """Self-Update detector: staleness tasks for agents."""
    from pathlib import Path as _P
    from ..core.registry import ToolDef
    from ..evolve.check import check as _check
    local.add(ToolDef("evolve.check", "Find stale skills/rules/history", level=0),
              lambda p: _check(str(p.get("root", ".")),
                               str(_P(__file__).resolve().parents[3])))
    reg.add_module(ModuleDef("evolve", "Self-Update detector", "0.1.0",
                             ["evolve.check"]))


def _wire_refactor(reg, local) -> None:
    """Refactor advisor: find clean-code problems in a file/dir."""
    from ..core.registry import ToolDef
    from ..refactor import api as _api
    local.add(ToolDef("refactor.inspect", "Find clean-code problems in a file/dir", level=0),
              lambda p: _api.inspect(str(p.get("path", ""))))
    local.add(ToolDef("refactor.plan", "Prioritized refactor plan for a file/dir", level=0),
              lambda p: _api.plan(str(p.get("path", ""))))
    local.add(ToolDef("refactor.sarif", "Clean-code findings as SARIF 2.1.0", level=0),
              lambda p: _api.sarif(str(p.get("path", ""))))
    local.add(ToolDef("refactor.apply", "Apply safe auto-fixes (backup+verify+rollback)", level=2),
              lambda p: _api.apply(str(p.get("path", "")),
                                   test_cmd=p.get("test_cmd"),
                                   run_tests=bool(p.get("run_tests")),
                                   only=p.get("only")))
    reg.add_module(ModuleDef("refactor", "Clean-code advisor", "0.1.0",
                             ["refactor.inspect", "refactor.plan", "refactor.sarif",
                              "refactor.apply"]))


def _wire_gen(reg, local) -> None:
    """Project generators: web, python service, go cli, node api, rust cli, paper."""
    from ..core.registry import ToolDef
    from ..gen import go_cli as _g
    from ..gen import node_api as _n
    from ..gen import paper_plugin as _pp
    from ..gen import python_service as _ps
    from ..gen import rust_cli as _r
    from ..gen import web as _w
    local.add(ToolDef("gen.web", "Scaffold landing page", level=1),
              lambda p: _w.generate(str(p.get("out", ".")),
                                    str(p.get("name", "Site"))))
    local.add(ToolDef("gen.python_service", "Scaffold stdlib microservice",
                      level=1),
              lambda p: _ps.generate(str(p.get("out", ".")),
                                     str(p.get("name", "svc"))))
    local.add(ToolDef("gen.go_cli", "Scaffold Go CLI tool", level=1),
              lambda p: _g.generate(str(p.get("out", ".")),
                                    str(p.get("name", "cli"))))
    local.add(ToolDef("gen.node_api", "Scaffold Node HTTP API (zero deps)",
                      level=1),
              lambda p: _n.generate(str(p.get("out", ".")),
                                    str(p.get("name", "api"))))
    local.add(ToolDef("gen.rust_cli", "Scaffold Rust CLI tool (zero deps)",
                      level=1),
              lambda p: _r.generate(str(p.get("out", ".")),
                                    str(p.get("name", "cli"))))
    local.add(ToolDef("gen.paper", "Scaffold Paper plugin", level=1),
              lambda p: _pp.generate(
                  str(p.get("out", ".")), str(p.get("name", "Demo")),
                  str(p.get("package", "com.forge.demo")),
                  str(p.get("command", "hello"))))
    reg.add_module(ModuleDef("gen", "Project generators", "0.1.0",
                             ["gen.web", "gen.python_service",
                              "gen.go_cli", "gen.node_api", "gen.rust_cli",
                              "gen.paper"]))
    local.add(ToolDef("make.project", "Scaffold + verify project", level=2),
              lambda p: _make_project(p))
    reg.add_module(ModuleDef("make", "Project stamping", "0.1.0",
                             ["make.project"]))


def _make_project(p: dict) -> dict:
    from ..gen.make import make as _mk
    from pathlib import Path as _P
    return _mk(str(p.get("kind", "")), str(p.get("name", "demo")),
               str(p.get("out", ".")),
               str(_P(__file__).resolve().parents[3]))


def _wire_loop(reg, local) -> None:
    """Self-healing loop: pipe -> bundles -> safe fixes -> retry."""
    from pathlib import Path as _P
    from ..core.registry import ToolDef
    from ..orchestrate import plan as _do_plan, run as _do_run
    from ..pipe.loop import run_loop as _run_loop
    root = str(_P(__file__).resolve().parents[3])
    local.add(ToolDef("loop.run", "Run pipe and self-heal up to N attempts", level=2),
              lambda p: _run_loop(str(p.get("root", ".")), root,
                                  max_attempts=int(p.get("attempts", 3)),
                                  serial=bool(p.get("serial")),
                                  auto_fix=bool(p.get("auto_fix", True))))
    local.add(ToolDef("do.plan", "Turn an intent into an executable plan", level=0),
              lambda p: _do_plan(str(p.get("intent", "")), str(p.get("root", ".")),
                                 root, name=str(p.get("name", "demo"))))
    local.add(ToolDef("do.run", "Plan + verify intent via the loop", level=2),
              lambda p: _do_run(str(p.get("intent", "")), str(p.get("root", ".")),
                                root, name=str(p.get("name", "demo")),
                                execute=True,
                                max_attempts=int(p.get("attempts", 3))))
    reg.add_module(ModuleDef("loop", "Self-healing loop", "0.1.0",
                             ["loop.run", "do.plan", "do.run"]))


def _wire_quality(reg, local) -> None:
    """Unified quality dashboard + trend + regression gate."""
    from pathlib import Path as _P
    from ..core.registry import ToolDef
    from .. import quality as _q
    root = str(_P(__file__).resolve().parents[3])
    local.add(ToolDef("quality.report", "Quality snapshot + trend", level=0),
              lambda p: _q.check(str(p.get("root", ".")), root,
                                 min_score=p.get("min_score"),
                                 max_regression=p.get("max_regression"),
                                 run_pipe=bool(p.get("pipe")), save=False))
    reg.add_module(ModuleDef("quality", "Quality dashboard", "0.1.0",
                             ["quality.report"]))


def _wire_kit(reg, local) -> None:
    """Project cannon: map / test / ci / secrets / doctor."""
    from ..core.registry import ModuleDef, ToolDef
    from .. import kit as _kit
    local.add(ToolDef("map.project",
                      "Project map: languages, LOC, entries, imports", level=0),
              lambda p: _kit.build_map(str(p.get("root", ".")),
                                       max_files=int(p.get("max_files", 20000))))
    local.add(ToolDef("test.detect", "Detect the project's native test command",
                      level=0),
              lambda p: {"detected": _kit.detect_test_command(str(p.get("root", ".")))})
    local.add(ToolDef("test.run", "Run the project's native test suite", level=1),
              lambda p: _kit.run_tests(str(p.get("root", ".")),
                                       timeout=int(p.get("timeout", 600))))
    local.add(ToolDef("ci.generate",
                      "Generate a GitHub Actions workflow for the project stack",
                      level=1),
              lambda p: _kit.generate_ci(str(p.get("root", ".")),
                                         force=bool(p.get("force"))))
    local.add(ToolDef("secrets.scan",
                      "Scan for leaked secrets (masked output)", level=0),
              lambda p: _kit.scan_secrets(str(p.get("root", "."))))
    local.add(ToolDef("doctor.check",
                      "Audit toolchains/versions and FORGE capabilities", level=0),
              lambda p: _kit.doctor(p.get("root")))
    local.add(ToolDef("deps.scan",
                      "Dependency inventory + hygiene for all ecosystems",
                      level=0),
              lambda p: _kit.scan_deps(str(p.get("root", ".")),
                                       check=bool(p.get("check"))))
    reg.add_module(ModuleDef("kit", "Project cannon: map/test/ci/secrets/doctor",
                             "0.1.0",
                             ["map.project", "test.detect", "test.run",
                              "ci.generate", "secrets.scan", "doctor.check",
                              "deps.scan"]))


def _wire_ui(reg, local) -> None:
    """Real UI tools: brief, strategy, layout validation, pack structure."""
    from ..core.registry import ToolDef
    from ..ui import brief as _br
    from ..ui import components as _c
    from ..ui import strategy as _st
    local.add(ToolDef("ui.design_brief", "NL description -> brief+strategy", level=0),
              lambda p: _brief_dict(_br.from_description(p.get("text", ""))))
    local.add(ToolDef("ui.validate_layout", "Inventory slot/action/text checks", level=0),
              lambda p: {"errors": _c.validate_inventory(p.get("screen", {}))})
    local.add(ToolDef("ui.check_contrast", "Text/background contrast math", level=0),
              lambda p: {"errors": _c.validate_contrast(
                  int(str(p.get("fg", "0xFFFFFFFF")), 0),
                  int(str(p.get("bg", "0xFF000000")), 0),
                  p.get("where", "text"))})
    reg.add_module(ModuleDef("ui", "AAA Interface Engine tools", "0.1.0",
                             ["ui.design_brief", "ui.validate_layout",
                              "ui.check_contrast"]))


def _brief_dict(br) -> dict:
    from ..ui import strategy as _st
    st = _st.select(br.needs_client_mod, br.needs_resource_pack)
    return {"style": br.style, "screens": br.screens, "features": br.features,
            "strategy": st["key"], "strategy_name": st["name"],
            "notes": br.notes}


def _wire_pipe(reg, local) -> None:
    """Conveyor as MCP tools: any external agent can trigger the pipe."""
    from ..core.registry import ToolDef
    from ..pipe.runner import PipeRunner
    from ..pipe.stages import ALL_STAGES, DEFAULT_STAGES, HEAVY_STAGES
    from pathlib import Path as _P
    _heavy_names = {s.name for s in HEAVY_STAGES}
    _all = list(DEFAULT_STAGES) + list(HEAVY_STAGES)

    def _selected(only: str, heavy: bool) -> list:
        if only:
            want = {s.strip() for s in only.split(",") if s.strip()}
            return [s for s in _all if s.name in want]
        return list(DEFAULT_STAGES) + (list(HEAVY_STAGES) if heavy else [])

    local.add(ToolDef("pipe.stages", "List conveyor stages", level=0),
              lambda p: {"stages": [
                  {"name": s.name, "title": s.title,
                   "timeout_s": s.timeout_s, "allow_fail": s.allow_fail,
                   "heavy": s.name in _heavy_names,
                   "notes": s.notes} for s in _all]})
    local.add(ToolDef("pipe.run", "Run conveyor headless, returns report",
                      level=2, timeout=1800),
              lambda p: _mcp_run(p))

    local.add(ToolDef("pipe.status", "Checkpoint + history tail", level=0),
              lambda p: _pipe_status(str(p.get("root", "."))))
    local.add(ToolDef("pipe.heal", "Checkpoint + run + repair bundles",
                      level=2, timeout=900),
              lambda p: _pipe_heal(str(p.get("root", ".")),
                                   bool(p.get("serial", False))))
    reg.add_module(ModuleDef("pipe", "Conveyor pipeline tools", "0.1.0",
                             ["pipe.stages", "pipe.run", "pipe.status",
                              "pipe.heal"]))


def _mcp_run(p: dict) -> dict:
    from pathlib import Path as _P
    from ..pipe.runner import PipeRunner
    from ..pipe.stages import ALL_STAGES, DEFAULT_STAGES, HEAVY_STAGES, git_changed
    root = str(p.get("root", "."))
    ctx: dict = {"target": root,
                 "forge_root": str(_P(__file__).resolve().parents[3])}
    if p.get("changed"):
        ch = git_changed(root)
        if ch is not None:
            ctx["only"] = ch
    only = str(p.get("only", "") or "")
    if only:
        want = {s.strip() for s in only.split(",") if s.strip()}
        stages = [s for s in ALL_STAGES.values() if s.name in want]
    else:
        stages = list(DEFAULT_STAGES) + (list(HEAVY_STAGES)
                                          if p.get("heavy") else [])
    return PipeRunner(stages, ctx, checkpoint=str(
        _P(root) / "forge-pipe-checkpoint.json")).run(
        resume=bool(p.get("resume", False)),
        serial=bool(p.get("serial", False))).to_dict()


def _pipe_heal(root: str, serial: bool) -> dict:
    from ..pipe.heal import heal as _heal
    from pathlib import Path as _P
    return _heal(root, str(_P(__file__).resolve().parents[3]), serial=serial)


def _pipe_status(root: str) -> dict:
    from pathlib import Path as _P
    import json as _json
    base = _P(root)
    out: dict = {"checkpoint": None, "history": []}
    cp = base / "forge-pipe-checkpoint.json"
    if cp.is_file():
        try:
            out["checkpoint"] = _json.loads(cp.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            out["checkpoint"] = {"error": "unreadable"}
    hist = base / ".forge-pipe-history.jsonl"
    if hist.is_file():
        try:
            rows = []
            for line in hist.read_text(encoding="utf-8").splitlines()[-5:]:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(_json.loads(line))
                except ValueError:
                    continue  # битая строка не валит весь статус
            out["history"] = rows
        except OSError:
            pass
    return out


def _wire_more(reg, local, anvil_dir: str) -> None:
    """Minecraft (via Anvil), knowledge (seed store), code review."""
    from ..core.registry import AnvilBackend, ToolDef
    from ..knowledge.store import KnowledgeStore
    from ..quality.review import review as _review
    from pathlib import Path as _P

    seed_holder: dict = {}

    def _store() -> KnowledgeStore:
        if "ks" not in seed_holder:
            ks = KnowledgeStore()
            seed = _P(__file__).resolve().parents[3] / "knowledge" / "seed.jsonl"
            if seed.is_file():
                ks.load_jsonl(seed)
            seed_holder["ks"] = ks
        return seed_holder["ks"]

    def _anvil():
        if not anvil_dir or not _P(anvil_dir, "anvil_call.py").is_file():
            return None
        return AnvilBackend(anvil_dir)

    def _mc_meta(project: str) -> dict:
        base = _P(project)
        for cand in (base / "src" / "main" / "resources" / "plugin.yml",
                     base / "src" / "main" / "resources" / "paper-plugin.yml"):
            if cand.is_file():
                return {"meta": str(cand)}
        return {"meta": ""}

    local.add(ToolDef("minecraft.validate_plugin_metadata",
                      "plugin.yml lint via Anvil", level=1),
              lambda p: _anvil().call(
                  "plugin_yml_lint",
                  {"path": _mc_meta(p.get("project", "."))["meta"] or "plugin.yml"})
              if _anvil() else {"ok": False,
                                "error": "anvil backend not configured"})
    local.add(ToolDef("minecraft.check_permissions",
                      "permission checks vs declarations", level=1),
              lambda p: _anvil().call(
                  "perm_audit",
                  {"src": str(_P(p.get("project", ".")) / "src")})
              if _anvil() else {"ok": False,
                                "error": "anvil backend not configured"})
    local.add(ToolDef("minecraft.check_compatibility",
                      "api-version vs MC via Anvil", level=1),
              lambda p: _anvil().call("api_version_check", {
                  "api": p.get("api", ""), "mc": p.get("mc", "")})
              if _anvil() else {"ok": False,
                                "error": "anvil backend not configured"})
    local.add(ToolDef("minecraft.analyze_logs", "lifecycle+errors for a plugin", level=1),
              lambda p: _anvil().call("log_scan", {
                  "path": p.get("log", ""), "plugin": p.get("plugin", "")})
              if _anvil() else {"ok": False,
                                "error": "anvil backend not configured"})
    local.add(ToolDef("knowledge.search", "FTS over FORGE facts", level=0),
              lambda p: {"hits": _store().search(
                  p.get("query", ""), p.get("domain", ""),
                  int(p.get("limit", 5)))})
    local.add(ToolDef("knowledge.get_fact", "Single fact by id", level=0),
              lambda p: {"fact": _store().get(int(p.get("id", -1)))})
    local.add(ToolDef("code.review", "Static review: debt/dups/size", level=0),
              lambda p: _review(p.get("root", "."),
                               int(p.get("max_files", 500))))
    reg.add_module(ModuleDef("minecraft", "Minecraft checks via Anvil", "0.1.0",
                             ["minecraft.validate_plugin_metadata",
                              "minecraft.check_permissions",
                              "minecraft.check_compatibility",
                              "minecraft.analyze_logs"]))
    reg.add_module(ModuleDef("knowledge", "Knowledge tools", "0.1.0",
                             ["knowledge.search", "knowledge.get_fact"]))
    reg.add_module(ModuleDef("quality", "Static review", "0.1.0",
                             ["code.review"]))


def main() -> None:
    import sys
    anvil_dir = sys.argv[1] if len(sys.argv) > 1 else ""
    McpServer(build_default_registry(anvil_dir)).serve()


if __name__ == "__main__":
    main()
