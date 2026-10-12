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
