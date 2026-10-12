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
    assert reg.call("echo", {"v": 1}) == {"ok": True, "data": {"v": 1}}
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
