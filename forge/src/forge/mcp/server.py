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
    local.add(ToolDef("forge.ping", "Liveness probe"),
              lambda p: {"pong": True, "echo": p.get("echo")})
    for name, desc, schema, fn in TOOLS:
        local.add(ToolDef(name, desc, "0.1.0",
                          {"type": "object", "properties": {
                              k: {"type": "string", "description": v}
                              for k, v in schema.items()}}), fn)
    reg.add_backend("local", local)
    reg.add_module(ModuleDef("core", "FORGE core tools", "0.1.0", ["forge.ping"]))
    reg.add_module(ModuleDef("project", "Workspace-confined project tools",
                             "0.1.0", [t[0] for t in TOOLS]))
    _wire_lab(reg, local)
    if anvil_dir and Path(anvil_dir, "anvil_call.py").is_file():
        reg.add_backend("anvil", AnvilBackend(anvil_dir))
        reg.add_module(ModuleDef("anvil", "Anvil tool bridge", "0.1.0", []))
    return reg


def _wire_lab(reg, local) -> None:
    """Stateless lab tools only (env-bound ones stay in CLI/runner)."""
    from ..core.registry import ToolDef
    from ..lab import build as _b
    from ..lab import unittests as _u
    local.add(ToolDef("lab.detect_build", "Detect gradle/maven/javac"),
              lambda p: {"system": _b.detect(p.get("project", "."))})
    local.add(ToolDef("lab.build_plugin", "Clean build a plugin project"),
              lambda p: _b.build_plugin(p.get("project", "."),
                                        int(p.get("timeout", 900))))
    local.add(ToolDef("lab.run_unit_tests", "Gradle test suite with summary"),
              lambda p: _u.run_gradle_tests(p.get("project", "."),
                                            int(p.get("timeout", 900))))
    reg.add_module(ModuleDef("lab", "Testing Lab stateless tools", "0.1.0",
                             ["lab.detect_build", "lab.build_plugin",
                              "lab.run_unit_tests"]))


def main() -> None:
    import sys
    anvil_dir = sys.argv[1] if len(sys.argv) > 1 else ""
    McpServer(build_default_registry(anvil_dir)).serve()


if __name__ == "__main__":
    main()
