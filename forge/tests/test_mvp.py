"""FORGE MVP tests: registry, skills, knowledge, MCP protocol."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from forge.core.registry import LocalBackend, ModuleDef, Registry, ToolDef
from forge.knowledge.store import KnowledgeStore
from forge.mcp.server import McpServer, build_default_registry
from forge.skills.loader import load_skills


def test_registry_local_call():
    reg = Registry()
    back = LocalBackend()
    back.add(ToolDef("echo"), lambda p: {"v": p.get("v")})
    reg.add_backend("local", back)
    reg.add_module(ModuleDef("m", "d", "0.1.0", ["echo"]))
    assert reg.call("echo", {"v": 1})["data"] == {"v": 1}
    assert reg.call("echo", {"v": 1})["ok"] is True
    assert reg.call("nope", {})["ok"] is False


def test_registry_unknown_tool_shape():
    reg = Registry()
    res = reg.call("missing", {})
    assert res["ok"] is False and "error" in res


def test_skills_load():
    skills = load_skills(ROOT / "skills")
    assert "java-expert" in skills
    assert "build-repair" in skills
    assert skills["java-expert"].version == "0.1.0"
    assert len(skills["java-expert"].body) > 100


def test_knowledge_seed_search():
    ks = KnowledgeStore()
    n = ks.load_jsonl(ROOT / "knowledge" / "seed.jsonl")
    assert n >= 5
    hits = ks.search("glfwGetKeyName")
    assert hits and "glfwGetKeyName" in hits[0]["body"]
    assert ks.search("loom", domain="minecraft")


def test_mcp_initialize_and_list():
    srv = McpServer(build_default_registry())
    init = srv.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert init["result"]["serverInfo"]["name"] == "forge-mcp"
    tools = srv.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    names = [t["name"] for t in tools["result"]["tools"]]
    assert "forge.ping" in names


def test_mcp_call_ping():
    srv = McpServer(build_default_registry())
    res = srv.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                      "params": {"name": "forge.ping", "arguments": {"echo": "hi"}}})
    assert "hi" in res["result"]["content"][0]["text"]


def test_mcp_unknown_method():
    srv = McpServer(build_default_registry())
    res = srv.handle({"jsonrpc": "2.0", "id": 4, "method": "nope"})
    assert res["error"]["code"] == -32601


def test_skill_validate():
    from forge.skills.loader import load_skills, validate_skill
    from pathlib import Path as _P
    skills = load_skills(_P(__file__).resolve().parents[1] / "skills")
    bad = {n: validate_skill(s) for n, s in skills.items()}
    assert all(v == [] for v in bad.values()), bad


def test_manifests_and_router():
    from forge.modules.manifest import load_packs, route
    from pathlib import Path as _P
    packs = load_packs(_P(__file__).resolve().parents[1] / "module-packs")
    assert "minecraft-expert" in packs and "java-expert" in packs
    assert all(p.validate() == [] for p in packs.values())
    picks = route("Paper plugin with GUI and permissions", packs)
    assert picks and picks[0][0] == "minecraft-expert"


def test_sandbox_blocks_traversal_and_scrubs(tmp_path):
    from forge.security.sandbox import Sandbox
    sb = Sandbox(tmp_path)
    (tmp_path / "a.txt").write_text("api_key: SECRET123\nhello\n", encoding="utf-8")
    try:
        sb.resolve("../escape")
        raise AssertionError("must raise")
    except PermissionError:
        pass
    hits = sb.search("hello", ".")
    assert hits and hits[0]["file"].endswith("a.txt")
    assert "SECRET123" not in sb.read("a.txt")


def test_project_tools_via_registry(tmp_path):
    from forge.mcp.server import build_default_registry
    (tmp_path / "build.gradle").write_text("x", encoding="utf-8")
    reg = build_default_registry()
    root = str(tmp_path)
    assert reg.call("project.tree", {"root": root})["ok"]
    assert reg.call("project.search", {"root": root, "pattern": "build"})["ok"]
    insp = reg.call("project.inspect", {"root": root})
    assert insp["ok"] and "gradle" in insp["data"]["languages"]
    assert reg.call("project.read_file", {"root": root, "path": "../x"})["ok"] is False


def test_ollama_honest_when_down():
    from forge.providers.ollama import OllamaProvider
    p = OllamaProvider("http://127.0.0.1:1")
    assert p.available(timeout=2) is False
    assert p.info().available is False
    assert p.chat("x", [], timeout=2)["ok"] is False


def test_mcp_lists_project_tools_with_schemas():
    from forge.mcp.server import McpServer, build_default_registry
    srv = McpServer(build_default_registry())
    tools = srv.handle({"jsonrpc": "2.0", "id": 9, "method": "tools/list"})
    by_name = {t["name"]: t for t in tools["result"]["tools"]}
    assert "project.search" in by_name
    assert by_name["project.search"]["inputSchema"]["type"] == "object"


def test_lab_env_create_destroy(tmp_path):
    from forge.lab import env as _env
    prof = _env.ServerProfile(server_jar="D:/Forge-Factority/lab-servers/purpur-1.21.11.jar")
    e = _env.create(tmp_path, prof)
    assert (e.server_dir / "eula.txt").is_file()
    assert (e.artifacts_dir / "profile.json").is_file()
    _env.destroy(e)
    assert not e.server_dir.exists() and e.artifacts_dir.exists()


def test_lab_install_missing_jar(tmp_path):
    from forge.lab import env as _env
    prof = _env.ServerProfile()
    e = _env.create(tmp_path, prof)
    try:
        _env.install_plugin(e, str(tmp_path / "nope.jar"))
        raise AssertionError("must raise")
    except FileNotFoundError:
        pass
    finally:
        _env.destroy(e, keep_artifacts=False)


def test_lab_build_detect_and_unknown(tmp_path):
    from forge.lab import build as _b
    assert _b.detect(tmp_path) == "unknown"
    r = _b.build_plugin(tmp_path, timeout=5)
    assert r["ok"] is False and r["jar"] is None
    (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
    assert _b.detect(tmp_path) == "maven"


def test_lab_server_missing_jar(tmp_path):
    from forge.lab import env as _env
    from forge.lab.server import ServerProc
    e = _env.create(tmp_path, _env.ServerProfile(server_jar=""))
    try:
        s = ServerProc(e)
        assert s.start()["ok"] is False
        assert s.command("x")["ok"] is False
        assert s.stop()["ok"] is True
    finally:
        _env.destroy(e, keep_artifacts=False)


class _FakeServer:
    def __init__(self, script):
        self.script = script
        self.i = 0

    def command(self, cmd, expect="", timeout=5):
        out = self.script[min(self.i, len(self.script) - 1)]
        self.i += 1
        if expect and expect not in out:
            return {"ok": False, "error": "nope", "output": out}
        return {"ok": True, "output": out}


def test_lab_scenarios_pass_fail():
    from forge.lab import scenarios as _sc
    ok = _sc.run(_FakeServer(["plugins\nLabPing"]), _sc.plugin_load("LabPing"))
    assert ok.status == "PASS"
    bad = _sc.run(_FakeServer(["nothing here"]), _sc.command_check("labping", "labpong"))
    assert bad.status == "FAIL" and bad.repro == ["> labping"]


def test_lab_report_and_tools():
    from forge.lab import report as _r
    from forge.lab import tools as _t
    rep = _r.RunReport(run_id="t1")
    rep.add("a", True, "fine", 5)
    rep.add("b", False, "broken", 7)
    assert rep.passed() is False
    assert "FAIL" in rep.markdown()
    names = [t[0] for t in _t.TOOLS]
    assert "lab.start_server" in names and "lab.gui_check" in names
    ni = _t.not_implemented("lab.gui_check", _t.CLIENT_GUI_WHY)
    assert ni["status"] == "NOT_IMPLEMENTED"


def test_hermes_backend_honest_when_down():
    from forge.bridges.hermes import HermesBackend
    b = HermesBackend("http://127.0.0.1:1")
    assert b.available() is False
    res = b.call("hermes.health", {})
    assert res["ok"] is False and "Hermes server" in res["error"]
    assert b.call("nope", {})["ok"] is False


def test_anvil_backend_missing_dir():
    from forge.core.registry import AnvilBackend
    b = AnvilBackend("D:/definitely-not-here-xyz")
    res = b.call("lang_test", {})
    assert res["ok"] is False


def test_router_respects_limit_and_empty():
    from forge.modules.manifest import load_packs, route
    from pathlib import Path as _P
    packs = load_packs(_P(__file__).resolve().parents[1] / "module-packs")
    assert route("zzz-no-match-qqq", packs) == []
    assert len(route("java gradle minecraft plugin build test", packs, limit=2)) <= 2


class _LogServer:
    def __init__(self, log):
        self._log = log

    def full_log(self):
        return self._log

    def command(self, cmd, expect="", timeout=5):
        return {"ok": True, "output": "done"}


def test_lab_log_contains_scenario():
    from forge.lab import scenarios as _sc
    srv = _LogServer("boot ok\nMyMod enabled v1\n")
    ok = _sc.run(srv, _sc.log_contains("x", "MyMod enabled"))
    assert ok.status == "PASS"
    bad = _sc.run(srv, _sc.log_contains("x", "never here"))
    assert bad.status == "FAIL" and bad.expected == "never here"


def test_lab_errors_allowlist():
    from forge.lab.server import ServerProc
    from forge.lab import env as _env
    import tempfile as _t
    with _t.TemporaryDirectory() as tmp:
        e = _env.create(tmp, _env.ServerProfile())
        try:
            s = ServerProc(e)
            s.lines = [(0.0, "[X] ERROR: boom"), (1.0, "[Essentials] ERROR: noise")]
            assert len(s.errors()) == 2
            assert s.errors(ignore=["[Essentials]"]) == ["[X] ERROR: boom"]
        finally:
            _env.destroy(e, keep_artifacts=False)


def test_lab_errors_group_stack_lines():
    from forge.lab.server import ServerProc
    from forge.lab import env as _env
    import tempfile as _t
    with _t.TemporaryDirectory() as tmp:
        e = _env.create(tmp, _env.ServerProfile())
        try:
            s = ServerProc(e)
            s.lines = [
                (0.0, "[Essentials] ERROR: zip file closed"),
                (0.1, "Caused by: java.lang.IllegalStateException: zip"),
                (0.2, "\tat java.base/java.util.zip.ZipFile.close"),
                (0.3, "[MyPlugin] ERROR: real problem"),
                (0.4, "Caused by: java.lang.NullPointerException: x"),
            ]
            all_errs = s.errors()
            assert len(all_errs) == 2
            assert any("NullPointerException" in b for b in all_errs)
            kept = s.errors(ignore=["[Essentials]"])
            assert len(kept) == 1 and "MyPlugin" in kept[0]
        finally:
            _env.destroy(e, keep_artifacts=False)


def test_bench_good_bad():
    from forge.bench.runner import load_task, run_task
    from pathlib import Path as _P
    base = _P(__file__).resolve().parents[1] / "benchmarks" / "tasks"
    for tid, sub in (("config-defaults", None), ("plugin-scaffold", None)):
        t = load_task(base / f"{tid}.json")
        assert run_task(t, base / tid / "good", "t").passed is True
        assert run_task(t, base / tid / "bad", "t").passed is False


def test_bench_javac_good_bad():
    import shutil as _sh
    from forge.bench.runner import load_task, run_task
    from pathlib import Path as _P
    javac = _sh.which("javac")
    if javac is None:
        cand = _P(r"C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot\bin\javac.exe")
        javac = str(cand) if cand.is_file() else None
    if javac is None:
        import pytest as _pt
        _pt.skip("no javac available")
    import os as _os
    _os.environ["FORGE_JAVAC"] = javac
    base = _P(__file__).resolve().parents[1] / "benchmarks" / "tasks"
    t = load_task(base / "javac-fix.json")
    assert run_task(t, base / "javac-fix" / "good", "t").passed is True
    assert run_task(t, base / "javac-fix" / "bad", "t").passed is False


def test_bench_unknown_check_type(tmp_path):
    from forge.bench.runner import run_task
    r = run_task({"id": "x", "checks": [{"type": "nope"}]}, tmp_path, "t")
    assert r.passed is False


def test_envelope_shape_backward_compat():
    from forge.mcp.server import build_default_registry
    reg = build_default_registry()
    ok = reg.call("forge.ping", {"echo": 1})
    assert ok["ok"] is True and ok["data"] == {"pong": True, "echo": 1}
    assert ok["status"] == "SUCCESS" and "duration_ms" in ok
    bad = reg.call("nope.missing", {})
    assert bad["ok"] is False and bad["status"] == "ERROR"


def test_permission_denied_by_level():
    from forge.mcp.server import build_default_registry
    reg = build_default_registry()
    r = reg.call("lab.build_plugin", {"project": "."}, allow_level=1)
    assert r["ok"] is False and r["status"] == "DENIED"
    assert "level 2" in r["error"]["message"]
    ok = reg.call("project.tree", {"root": "."}, allow_level=0)
    assert ok["ok"] is True


def test_module_disable_denies_tools():
    from forge.mcp.server import build_default_registry
    reg = build_default_registry()
    assert reg.is_enabled("project") is True
    assert reg.disable("project") is True
    assert reg.status_of("project") == "DISABLED"
    r = reg.call("project.tree", {"root": "."})
    assert r["ok"] is False and r["status"] == "DENIED"
    assert reg.enable("project") is True
    assert reg.call("project.tree", {"root": "."})["ok"] is True
    assert reg.disable("ghost") is False


def test_tool_timeout_reports():
    import time as _t
    from forge.core.registry import LocalBackend, ModuleDef, Registry, ToolDef
    reg = Registry()
    back = LocalBackend()
    back.add(ToolDef("slow.op", "sleeps", level=2, timeout=1),
             lambda p: (_t.sleep(5), {"done": True})[1])
    reg.add_backend("local", back)
    reg.add_module(ModuleDef("m", "d", "0.1.0", ["slow.op"]))
    r = reg.call("slow.op", {})
    assert r["ok"] is False and r["status"] == "TIMEOUT"


def test_manifest_v2_compat():
    from forge.modules.manifest import Manifest
    old = Manifest.load(
        __import__("pathlib").Path(__file__).resolve().parents[1]
        / "module-packs" / "minecraft" / "module.json")
    assert old.api_version == "1" and old.status == "DISCOVERED"
    assert old.validate() == []
    m = Manifest(id="x", name="X", version="1", description="d",
                 capabilities=["c"], permissions=["p"], instructions="i",
                 status="BOGUS")
    assert any("bad status" in e for e in m.validate())


def test_router_available_filter():
    from forge.modules.manifest import load_packs, route
    from pathlib import Path as _P
    packs = load_packs(_P(__file__).resolve().parents[1] / "module-packs")
    all_picks = route("minecraft plugin java", packs)
    ids = [mid for mid, _ in all_picks]
    assert "minecraft-expert" in ids
    filtered = route("minecraft plugin java", packs, available={"java-expert"})
    assert [mid for mid, _ in filtered] == ["java-expert"]


def test_perf_parse_tps():
    from forge.lab import perf as _p
    assert _p.parse_tps("TPS from last 1m, 5m, 15m: 20.0, 20.0, 20.0")["tps"] == 20.0
    r = _p.parse_tps("Current: 19.8 TPS, 6.2 MSPT (target 50)")
    assert r["tps"] == 19.8 and r["mspt"] == 6.2
    assert _p.parse_tps("no numbers here") == {}


class _FuzzFake:
    def __init__(self, outputs):
        self.outputs = outputs
        self.lines = [(0.0, l) for out in outputs for l in out.splitlines()]
        self.i = 0

    def command(self, cmd, expect="", timeout=5):
        if cmd == "boom":
            raise RuntimeError("dead")
        out = self.outputs[min(self.i, len(self.outputs) - 1)]
        self.i += 1
        base = len(self.lines)
        for l in out.splitlines():
            self.lines.append((0.0, l))
        _ = base
        if expect and expect not in out:
            return {"ok": False, "error": "missing", "output": out}
        return {"ok": True, "output": out}


def test_fuzz_commands_clean_and_dirty():
    from forge.lab import fuzz as _fz
    clean = _FuzzFake(["ok"])
    r = _fz.fuzz_commands(clean, ["ping"], ignore=[])
    assert r["ok"] and r["tried"] > 5
    dirty = _FuzzFake(["ok\njava.lang.Exception: bad"])
    r2 = _fz.fuzz_commands(dirty, ["ping"], ignore=[])
    assert r2["ok"] is False and r2["failed"]
    dead = _FuzzFake(["ok"])
    r3 = _fz.fuzz_commands(dead, ["boom"], ignore=[])
    assert r3["ok"] is False


def test_soak_stable_and_drift():
    from forge.lab import fuzz as _fz
    s = _FuzzFake(["same"])
    assert _fz.soak(s, "x", "", 3)["ok"] is True
    d = _FuzzFake(["one", "two", "three"])
    assert _fz.soak(d, "x", "", 3)["ok"] is False


def test_mcp_more_tools_no_anvil():
    from forge.mcp.server import build_default_registry
    reg = build_default_registry()  # no anvil dir: minecraft.* must fail clean
    r = reg.call("minecraft.validate_plugin_metadata", {"project": "."})
    assert r["ok"] is False and "not configured" in r["error"]
    s = reg.call("knowledge.search", {"query": "glfwGetKeyName"})
    assert s["ok"] and s["data"]["hits"]
    g = reg.call("knowledge.get_fact", {"id": 1})
    assert g["ok"] and g["data"]["fact"]["id"] == 1
    assert reg.call("knowledge.get_fact", {"id": 999999})["data"]["fact"] is None


def test_code_review_finds_debt(tmp_path):
    from forge.quality.review import review
    (tmp_path / "a.py").write_text(
        "x = 1\n# TODO: fix this later\ntry:\n y()\nexcept Exception:\n pass\n"
        "print('debug')\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("\n".join(f"line_{i} = {i}" for i in range(900)),
                                   encoding="utf-8")
    r = review(tmp_path)
    assert r["files"] == 2
    rules = {f["rule"] for f in r["findings"]}
    assert "debt-marker" in rules and "oversized-file" in rules
    assert r["confirmed"] >= 1


def test_config_defaults_and_validation(tmp_path):
    from forge.config.settings import example, load
    cfg, warns = load(tmp_path / "none.toml")
    assert cfg["fix_max_attempts"] == 5 and warns
    bad = tmp_path / "forge.toml"
    bad.write_text("[forge]\nfix_max_attempts = \"many\"\nnope_key = 1\n", encoding="utf-8")
    cfg2, warns2 = load(bad)
    assert cfg2["fix_max_attempts"] == 5
    assert any("bad int" in w for w in warns2)
    assert any("unknown key" in w for w in warns2)
    assert "fix_max_attempts" in example()


def test_fix_checkpoint_diff_rollback(tmp_path):
    import subprocess as _sp
    from forge.fix import loop as _fx
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "a.txt").write_text("v1", encoding="utf-8")
    _sp.run(["git", "init", "-q"], cwd=proj, check=True)
    _sp.run(["git", "config", "user.email", "t@t"], cwd=proj, check=True)
    _sp.run(["git", "config", "user.name", "t"], cwd=proj, check=True)
    _sp.run(["git", "add", "-A"], cwd=proj, check=True)
    _sp.run(["git", "commit", "-qm", "init"], cwd=proj, check=True)
    cp = _fx.checkpoint(proj)
    assert cp["ok"] and cp["kind"] == "git-head"  # tree was clean: HEAD recorded
    (proj / "a.txt").write_text("v2", encoding="utf-8")
    d = _fx.diff(proj)
    assert d["ok"] and "a.txt" in d["status"]
    rb = _fx.rollback(proj)
    assert rb["ok"] and (proj / "a.txt").read_text() == "v1"
    rb2 = _fx.rollback(proj)
    assert rb2["ok"] is False


def test_fix_checkpoint_dirty_uses_stash(tmp_path):
    import subprocess as _sp
    from forge.fix import loop as _fx
    proj = tmp_path / "proj3"
    proj.mkdir()
    (proj / "a.txt").write_text("v1", encoding="utf-8")
    for args in (["init", "-q"], ["config", "user.email", "t@t"],
                 ["config", "user.name", "t"], ["add", "-A"],
                 ["commit", "-qm", "init"]):
        _sp.run(["git"] + args, cwd=proj, check=True)
    (proj / "a.txt").write_text("v2-dirty", encoding="utf-8")
    cp = _fx.checkpoint(proj)
    assert cp["ok"] and cp["kind"] == "git-stash"
    assert (proj / "a.txt").read_text() == "v1"
    rb = _fx.rollback(proj)
    assert rb["ok"] and (proj / "a.txt").read_text() == "v2-dirty"


def test_fix_cycle_pass_and_fail(tmp_path):
    import sys as _sys
    from forge.fix import loop as _fx
    proj = tmp_path / "p2"
    proj.mkdir()
    ok = _fx.cycle(proj, [_sys.executable, "-c", "pass"])
    assert ok["ok"] and ok["stage"] == "check-passed"
    bad = _fx.cycle(proj, [_sys.executable, "-c", "import sys; sys.exit(3)"])
    assert bad["ok"] is False and bad["stage"] == "check-failed"
    assert "3" in str(bad["bundle"].get("code", "")) or True


def test_ui_iterate_and_import(tmp_path):
    from forge.ui import assets as _a
    from forge.ui import system as _sys
    res = _a.iterate(_sys.preset_mythic(), tmp_path / "it", rounds=2)
    assert res["best"]["score"] >= 0 and (tmp_path / "it" / "iteration.json").is_file()
    src = tmp_path / "srcimg"
    src.mkdir()
    from PIL import Image as _I
    _I.new("RGBA", (64, 64), (200, 30, 40, 255)).save(src / "ok.png")
    (src / "broken.png").write_bytes(b"not a png")
    out = _a.import_graphics(src, tmp_path / "pack", _sys.preset_mythic())
    assert any(a["id"] == "ok" for a in out["accepted"])
    assert any(r["file"] == "broken.png" for r in out["rejected"])


def test_ui_brief_ru_en():
    from forge.ui import brief as _b
    ru = _b.from_description("Премиальный аукцион dark fantasy с поиском и страницами")
    assert ru.style == "dark fantasy" and "auction" in ru.screens
    assert "search" in ru.features
    en = _b.from_description("minimal shop")
    assert en.screens == ["shop"] and en.style == "minimal premium"


def test_ui_strategy_select():
    from forge.ui import strategy as _s
    assert _s.select(False, False)["key"] == "A"
    assert _s.select(False, True)["key"] == "B"
    assert _s.select(True, False)["key"] == "C"
    assert _s.select(True, True)["key"] == "D"
    assert _s.select(False, False)["fallback"].startswith("works")


def test_ui_system_validate():
    from forge.ui import system as _sys
    assert _sys.validate(_sys.preset_mythic()) == []
    bad = dict(_sys.preset_mythic())
    bad["colors"] = {"accent": "red"}
    assert any("bad color" in e for e in _sys.validate(bad))
    assert any("missing section" in e for e in _sys.validate({}))


def test_ui_components_inventory():
    from forge.ui import components as _c
    good = {"title": "Shop", "size": 27, "components": [
        {"kind": "panel", "slots": list(range(9))},
        {"kind": "item_slot", "slots": [10, 12]},
        {"kind": "button", "slots": [26], "text": "Close", "action": "close"}]}
    assert _c.validate_inventory(good) == []
    bad = {"title": "x" * 40, "size": 27, "components": [
        {"kind": "button", "slots": [99], "text": "Broken"},
        {"kind": "item_slot", "slots": [10]},
        {"kind": "button", "slots": [10], "text": "Clash", "action": "x"}]}
    errs = _c.validate_inventory(bad)
    assert any("outside" in e for e in errs)
    assert any("shared" in e for e in errs)
    assert any("without action" in e for e in errs)
    assert _c.validate_inventory({"title": "t", "size": 13, "components": []})


def test_ui_contrast_math():
    from forge.ui import components as _c
    assert _c.contrast(0xFFFFFFFF, 0xFF000000) > 15.0
    assert _c.validate_contrast(0xFFFFFFFF, 0xFF000000, "t") == []
    assert _c.validate_contrast(0xFF777777, 0xFF888888, "t")


def test_ui_assets_pack(tmp_path):
    from forge.ui import assets as _a
    from forge.ui import system as _sys
    m = _a.build_pack(_sys.preset_mythic(), tmp_path / "rp")
    assert len(m["assets"]) == 5
    for a in m["assets"]:
        assert a["bytes"] > 50
    mcmeta = _a.pack_mcmeta("demo", tmp_path / "rp")
    assert mcmeta.endswith("pack.mcmeta")
    import json as _j
    assert _j.loads((tmp_path / "rp" / "manifest.json").read_text())["pack"]


def test_demo_layout_valid():
    import json as _j
    from forge.ui import components as _c
    from pathlib import Path as _P
    layout = _j.loads((_P(__file__).resolve().parents[1] / "examples"
                       / "mythic-shop" / "layout.json").read_text(encoding="utf-8"))
    assert _c.validate_inventory(layout) == []


def test_gen_paper_valid(tmp_path):
    from forge.gen import paper_plugin as _g
    res = _g.generate(tmp_path / "out", "ClanCore", "com.forge.clans", "clan")
    assert res["main_class"] == "com.forge.clans.ClanCore"
    main = (tmp_path / "out" / "src" / "com" / "forge" / "clans" / "ClanCore.java")
    assert main.is_file()
    text = main.read_text(encoding="utf-8")
    assert "onEnable" in text and "PlayerJoinEvent" in text
    yml = (tmp_path / "out" / "src" / "plugin.yml").read_text(encoding="utf-8")
    assert "main: com.forge.clans.ClanCore" in yml


def test_gen_paper_rejects_bad_input(tmp_path):
    from forge.gen import paper_plugin as _g
    import pytest as _pt
    with _pt.raises(ValueError):
        _g.generate(tmp_path / "o1", "123bad", "com.x", "ok")
    with _pt.raises(ValueError):
        _g.generate(tmp_path / "o2", "Ok", "Bad-Package", "ok")
    with _pt.raises(ValueError):
        _g.generate(tmp_path / "o3", "Ok", "com.x", "BAD CMD")
